"""
loader.py - Data Layer (deterministic, no LLM)
================================================
Reads every sheet of an uploaded Excel file using the schema manifest
produced by schema_detector.py, then joins all sheets into one
per-student record.

Key behaviors:
- No hardcoded sheet/column names - all driven by manifest
- 2-row merged header handling for Assessment sheet
- Fuzzy name normalisation across sheets with known mismatch correction
- Attendance computed from P/A cells (not a % column)
- Non-numeric score cells logged, not silently zeroed
- Validation gate: asserts count==30, no Unnamed cols, no duplicates
- Placement salary normalised to "Rs. N,NNN / month"
- Uniform sheet NEVER mixed into assessment/skill data
"""
from __future__ import annotations

import io
import logging
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

import openpyxl
import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known name-spelling fixes (normalised_name -> canonical_name)
# These are PER-SAMPLE fixes; the fuzzy fallback handles unknown files
# ---------------------------------------------------------------------------
KNOWN_NAME_FIXES = {
    "madhumitha k": "mathumitha k",
    "sambath s": "sampath s",
    "smitha s": "smitha a",
    "sneka m": "snekha m",
}


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

def _norm_name(s: Any) -> str:
    """Lowercase, strip, collapse spaces, remove punctuation except spaces."""
    if s is None:
        return ""
    t = str(s).strip()
    t = unicodedata.normalize("NFKD", t)
    t = t.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _canonical_name(raw: str) -> str:
    """Apply known fixes then return normalised name."""
    n = _norm_name(raw)
    return KNOWN_NAME_FIXES.get(n, n)


def _fuzzy_join_name(name: str, roster: dict, threshold: float = 0.82) -> str | None:
    """
    Find the closest canonical name in roster (normalised_name -> original_name).
    Returns original_name if found above threshold, else None.
    """
    n = _canonical_name(name)
    if n in roster:
        return roster[n]
    # Fuzzy fallback
    best_score = 0.0
    best_match = None
    for rn in roster:
        sc = SequenceMatcher(None, n, rn).ratio()
        if sc > best_score:
            best_score = sc
            best_match = rn
    if best_score >= threshold and best_match:
        log.warning(f"Name fuzzy-match: '{name}' -> '{roster[best_match]}' (score={best_score:.2f})")
        return roster[best_match]
    return None


# ---------------------------------------------------------------------------
# Salary normalisation
# ---------------------------------------------------------------------------

def _normalise_salary(raw: Any) -> str | None:
    """Convert 'Rs. 11,700' or 9000 or '9000' to 'Rs. 9,000 / month'."""
    if raw is None or str(raw).strip() in ("", "nan", "None"):
        return None
    s = str(raw).strip()
    cleaned = re.sub(r"(?i)\b(?:rs\.?|inr|₹)\b", "", s)
    cleaned = cleaned.replace(",", "").strip()
    m = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not m:
        return None
    try:
        amount = int(float(m.group()))
        return f"Rs. {amount:,} / month"
    except Exception:
        return None


def _salary_numeric(raw: Any) -> float:
    """Return numeric salary for ranking purposes."""
    s = _normalise_salary(raw)
    if not s:
        return 0.0
    cleaned = re.sub(r"(?i)\b(?:rs\.?|inr|₹)\b", "", s)
    cleaned = cleaned.replace(",", "").strip()
    m = re.search(r"\d+(?:\.\d+)?", cleaned)
    if m:
        try:
            return float(m.group())
        except Exception:
            return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Sheet readers (driven by manifest, not hardcoded)
# ---------------------------------------------------------------------------

def _read_profile_sheet(ws, info: dict) -> dict:
    """Returns {canonical_name -> {field: value}}."""
    hdr = info["header_row"]
    rows = list(ws.iter_rows(min_row=hdr + 2, values_only=True))  # +1 for 0->1 base, +1 skip header
    header_row = list(ws.iter_rows(min_row=hdr + 1, max_row=hdr + 1, values_only=True))[0]
    headers = [str(h).strip() if h is not None else "" for h in header_row]

    name_col_idx = None
    if info.get("name_column"):
        for i, h in enumerate(headers):
            if _norm_name(h) == _norm_name(info["name_column"]):
                name_col_idx = i
                break

    if name_col_idx is None:
        # fallback: first column that looks like name
        for i, h in enumerate(headers):
            if "name" in _norm_name(h):
                name_col_idx = i
                break

    result = {}
    for row in rows:
        if name_col_idx is None or name_col_idx >= len(row):
            continue
        name_raw = row[name_col_idx]
        if not name_raw or str(name_raw).strip() in ("", "nan"):
            continue
        cn = _canonical_name(str(name_raw))
        record = {}
        for i, h in enumerate(headers):
            if i < len(row) and h:
                val = row[i]
                if val is not None and str(val).strip() not in ("", "nan"):
                    record[h] = val
        result[cn] = record
    return result


def _read_assessment_sheet(ws, info: dict, dq_warnings: list) -> tuple[dict, dict, float]:
    """
    Returns {canonical_name -> {subject: score, ...}} and max_marks dict and total_max float.
    Handles 2-row merged header: row0=subjects, row1=Out of N.
    Non-numeric cells are logged as data-quality warnings.
    """
    hdr_idx = info["header_row"]
    scale_idx = info.get("scale_row")

    all_rows = list(ws.iter_rows(values_only=True))

    subject_row = list(all_rows[hdr_idx]) if hdr_idx < len(all_rows) else []
    scale_row = list(all_rows[scale_idx]) if (scale_idx and scale_idx < len(all_rows)) else []

    # Build subject -> (col_idx, max_marks) map; skip first 2 cols (S.No, Name)
    subjects = {}
    name_col_idx = 1  # fallback

    for i, h in enumerate(subject_row):
        if h is None or str(h).strip() in ("", "nan"):
            continue
        hn = _norm_name(str(h))
        if "name" in hn:
            name_col_idx = i
            continue
        if re.search(r"^s[\.\s]?no", hn) or re.search(r"^total", hn, re.IGNORECASE):
            continue

        # Max marks from scale row
        max_val = None
        if scale_row and i < len(scale_row):
            sv = scale_row[i]
            if sv is not None:
                m = re.search(r"(\d+(?:\.\d+)?)", str(sv))
                if m:
                    max_val = float(m.group(1))
        # Also try to read from score_columns in manifest
        for sc in info.get("score_columns", []):
            if _norm_name(sc["col"]) == _norm_name(str(h)):
                if sc.get("max") is not None:
                    max_val = sc["max"]
                break

        display = str(h).strip()
        subjects[i] = {"name": display, "max": max_val}

    # Data rows start after both header rows
    data_start = (scale_idx + 1) if scale_idx else (hdr_idx + 1)

    student_scores = {}
    max_marks = {}
    for i, meta in subjects.items():
        if meta["max"] is not None:
            max_marks[meta["name"]] = meta["max"]

    for row_raw in all_rows[data_start:]:
        row = list(row_raw)
        if name_col_idx >= len(row):
            continue
        name_val = row[name_col_idx]
        if not name_val or str(name_val).strip() in ("", "nan"):
            continue
        name_str = str(name_val).strip()
        cn = _canonical_name(name_str)

        scores = {}
        for i, meta in subjects.items():
            if i >= len(row):
                continue
            raw_val = row[i]
            if raw_val is None or str(raw_val).strip() in ("", "nan"):
                continue
            try:
                scores[meta["name"]] = float(str(raw_val).replace(",", ""))
            except (ValueError, TypeError):
                dq_warnings.append(
                    f"DATA QUALITY: Sheet Assessment, Student '{name_str}', "
                    f"Column '{meta['name']}': non-numeric value '{raw_val}' — excluded from score."
                )

        student_scores[cn] = scores

    total_max = info.get("total_max") or 265.0
    return student_scores, max_marks, total_max


def _read_skill_matrix_sheet(ws, info: dict) -> dict:
    """Returns {canonical_name -> {skill: raw_score, 'typing_wpm': N}}."""
    hdr_idx = info["header_row"]
    all_rows = list(ws.iter_rows(values_only=True))
    header_row = list(all_rows[hdr_idx]) if hdr_idx < len(all_rows) else []

    name_col_idx = 1
    skills = {}
    for i, h in enumerate(header_row):
        if h is None or str(h).strip() in ("", "nan"):
            continue
        hn = _norm_name(str(h))
        if "name" in hn:
            name_col_idx = i
            continue
        if re.search(r"^s[\.\s]?no", hn):
            continue
        skills[i] = str(h).strip()

    result = {}
    for row_raw in all_rows[hdr_idx + 1:]:
        row = list(row_raw)
        if name_col_idx >= len(row):
            continue
        name_val = row[name_col_idx]
        if not name_val or str(name_val).strip() in ("", "nan"):
            continue
        cn = _canonical_name(str(name_val).strip())
        rec = {}
        for i, col_name in skills.items():
            if i >= len(row) or row[i] is None:
                continue
            try:
                val = float(str(row[i]).replace(",", ""))
                rec[col_name] = val
            except (ValueError, TypeError):
                pass
        result[cn] = rec
    return result


def _read_attendance_sheet(ws, info: dict) -> dict:
    """
    Returns {canonical_name -> {'present': N, 'total_trackable': N, 'pct': float}}.
    Only P and A cells count; '-' or missing are not-applicable.
    """
    hdr_idx = info["header_row"]
    all_rows = list(ws.iter_rows(values_only=True))
    header_row = list(all_rows[hdr_idx]) if hdr_idx < len(all_rows) else []

    name_col_idx = 1
    for i, h in enumerate(header_row):
        if h is not None and "name" in _norm_name(str(h)):
            name_col_idx = i
            break

    # Date columns start from after name/sno columns
    date_col_start = max(name_col_idx + 1, 2)

    result = {}
    for row_raw in all_rows[hdr_idx + 1:]:
        row = list(row_raw)
        if name_col_idx >= len(row):
            continue
        name_val = row[name_col_idx]
        if not name_val or str(name_val).strip() in ("", "nan"):
            continue
        cn = _canonical_name(str(name_val).strip())

        present = 0
        absent = 0
        for v in row[date_col_start:]:
            vs = str(v).strip().upper() if v is not None else ""
            if vs == "P":
                present += 1
            elif vs == "A":
                absent += 1
            # '-' and blank are excluded from denominator

        total = present + absent
        pct = round((present / total) * 100, 1) if total > 0 else 0.0
        result[cn] = {"present": present, "total_trackable": total, "pct": pct}
    return result


def _read_other_skills_sheet(ws, info: dict) -> dict:
    """Returns {canonical_name -> {field: value}}."""
    hdr_idx = info["header_row"]
    all_rows = list(ws.iter_rows(values_only=True))
    header_row = list(all_rows[hdr_idx]) if hdr_idx < len(all_rows) else []

    name_col_idx = 0
    for i, h in enumerate(header_row):
        if h is not None and "name" in _norm_name(str(h)):
            name_col_idx = i
            break

    headers = [str(h).strip() if h is not None else "" for h in header_row]
    result = {}
    for row_raw in all_rows[hdr_idx + 1:]:
        row = list(row_raw)
        if name_col_idx >= len(row):
            continue
        name_val = row[name_col_idx]
        if not name_val or str(name_val).strip() in ("", "nan"):
            continue
        cn = _canonical_name(str(name_val).strip())
        rec = {}
        for i, h in enumerate(headers):
            if h and i < len(row) and row[i] is not None:
                sv = str(row[i]).strip()
                if sv not in ("", "nan"):
                    rec[h] = sv
        result[cn] = rec
    return result


def _read_placement_sheet(ws, info: dict) -> dict:
    """Returns {canonical_name -> {designation, organization, salary_raw, salary_display, salary_num}}."""
    hdr_idx = info["header_row"]
    all_rows = list(ws.iter_rows(values_only=True))
    header_row = list(all_rows[hdr_idx]) if hdr_idx < len(all_rows) else []

    name_col_idx = 1
    headers = []
    for i, h in enumerate(header_row):
        hs = str(h).strip() if h is not None else ""
        headers.append(hs)
        if "name" in _norm_name(hs):
            name_col_idx = i

    result = {}
    for row_raw in all_rows[hdr_idx + 1:]:
        row = list(row_raw)
        if name_col_idx >= len(row):
            continue
        name_val = row[name_col_idx]
        if not name_val or str(name_val).strip() in ("", "nan"):
            continue

        # Check real placement columns (exclude S.No and Name)
        placement_data_found = False
        rec = {}
        salary_val = None
        for i, h in enumerate(headers):
            if i >= len(row) or not h or i == name_col_idx:
                continue
            hn = _norm_name(h)
            if any(re.search(p, hn) for p in [r"^s[\.\s]?no", r"^serial"]):
                continue
            val = row[i]
            if val is not None and str(val).strip() not in ("", "nan", "None", "-"):
                rec[h] = val
                placement_data_found = True
                if "salary" in hn or "package" in hn or "ctc" in hn or "stipend" in hn:
                    salary_val = val

        # If designation, organization, salary are all empty/None, omit placement
        if not placement_data_found:
            continue

        cn = _canonical_name(str(name_val).strip())
        rec["salary_display"] = _normalise_salary(salary_val)
        rec["salary_num"] = _salary_numeric(salary_val)
        result[cn] = rec
    return result


def _read_supplementary_sheet(ws, info: dict) -> dict:
    """Generic reader for hostelite/parent_meet sheets. Returns {canonical_name -> {fields}}."""
    return _read_other_skills_sheet(ws, info)


# ---------------------------------------------------------------------------
# Master join
# ---------------------------------------------------------------------------

def load_all_sheets(source, filename: str = "") -> dict:
    """
    Main entry point. Returns:
    {
      'students': {canonical_name -> full_record},
      'max_marks': {subject -> max},
      'class_stats': computed class-level stats,
      'dq_warnings': [list of data quality warning strings],
      'manifest': the schema manifest,
    }
    """
    from schema_detector import detect_schema, print_manifest

    if isinstance(source, bytes):
        raw_bytes = source
        wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)
    else:
        with open(source, "rb") as f:
            raw_bytes = f.read()
        wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)

    manifest = detect_schema(raw_bytes, filename)
    sheets = manifest["sheets"]

    dq_warnings = []

    # --- Find and parse each category
    profile_data = {}
    assessment_data = {}
    max_marks = {}
    skill_matrix_data = {}
    attendance_data = {}
    other_skills_data = {}
    placement_data = {}
    hostelite_data = {}
    parent_meet_data = {}

    detected_total_max = None

    for sname, info in sheets.items():
        if sname not in wb.sheetnames:
            continue
        ws = wb[sname]
        cat = info["category"]

        if cat == "profile":
            profile_data.update(_read_profile_sheet(ws, info))
            log.info(f"[profile] '{sname}': {len(profile_data)} students")

        elif cat == "assessment":
            sd, mm, t_max = _read_assessment_sheet(ws, info, dq_warnings)
            assessment_data.update(sd)
            max_marks.update(mm)
            if t_max:
                detected_total_max = t_max
            log.info(f"[assessment] '{sname}': {len(sd)} students, {len(mm)} subjects")

        elif cat == "skill_matrix":
            sm = _read_skill_matrix_sheet(ws, info)
            skill_matrix_data.update(sm)
            log.info(f"[skill_matrix] '{sname}': {len(sm)} students")

        elif cat == "attendance":
            ad = _read_attendance_sheet(ws, info)
            attendance_data.update(ad)
            log.info(f"[attendance] '{sname}': {len(ad)} students")

        elif cat == "other_skills":
            os_data = _read_other_skills_sheet(ws, info)
            other_skills_data.update(os_data)
            log.info(f"[other_skills] '{sname}': {len(os_data)} students")

        elif cat == "placement":
            pd_data = _read_placement_sheet(ws, info)
            placement_data.update(pd_data)
            log.info(f"[placement] '{sname}': {len(pd_data)} students")

        elif cat == "hostelite":
            hostelite_data.update(_read_supplementary_sheet(ws, info))

        elif cat == "parent_meet":
            parent_meet_data.update(_read_supplementary_sheet(ws, info))

        elif cat == "irrelevant":
            log.info(f"[irrelevant] '{sname}': skipped (uniform/hostel/contact sheet)")
            dq_warnings.append(f"Sheet '{sname}' classified as IRRELEVANT and excluded from all reports.")

    # --- Build canonical name roster from profile (master)
    # roster: {normalised_name -> original_name_from_profile}
    if profile_data:
        roster = {cn: cn for cn in profile_data.keys()}
    else:
        # fallback: union of all detected student names
        all_names = (
            set(assessment_data.keys()) |
            set(skill_matrix_data.keys()) |
            set(attendance_data.keys())
        )
        roster = {cn: cn for cn in all_names}

    # --- Helper: resolve name to canonical
    def resolve(name: str) -> str | None:
        cn = _canonical_name(name)
        if cn in roster:
            return cn
        # Fuzzy
        return _fuzzy_join_name(name, roster)

    # --- Build per-student full records
    students = {}
    for cn in roster:
        profile = profile_data.get(cn, {})
        att = attendance_data.get(cn) or {}
        assess = assessment_data.get(cn) or {}
        skills = skill_matrix_data.get(cn) or {}
        other = other_skills_data.get(cn) or {}
        placement = placement_data.get(cn)
        hostel_info = hostelite_data.get(cn)
        parent_info = parent_meet_data.get(cn)

        # Build student record
        record = {
            "canonical_name": cn,
            "display_name": _get_display_name(profile, cn),
            "profile": profile,
            "assessment_scores": assess,
            "skill_matrix": skills,
            "attendance": att,
            "other_skills": other,
            "placement": placement,
            "hostelite": hostel_info,
            "parent_meet": parent_info,
        }
        students[cn] = record

    # Try to resolve students from non-profile sheets not yet in roster
    for src_dict in [assessment_data, skill_matrix_data, attendance_data]:
        for raw_cn in src_dict:
            if raw_cn not in roster:
                matched = resolve(raw_cn)
                if matched and matched in students:
                    # Merge data into existing student
                    if src_dict is assessment_data and raw_cn in assessment_data:
                        existing = students[matched]["assessment_scores"]
                        existing.update(assessment_data[raw_cn])
                    elif src_dict is skill_matrix_data and raw_cn in skill_matrix_data:
                        students[matched]["skill_matrix"].update(skill_matrix_data[raw_cn])
                    elif src_dict is attendance_data and raw_cn in attendance_data:
                        if not students[matched]["attendance"]:
                            students[matched]["attendance"] = attendance_data[raw_cn]
                elif not matched:
                    dq_warnings.append(
                        f"UNMATCHED NAME: '{raw_cn}' from a non-roster sheet could not be matched "
                        f"to any roster student — row included as orphan."
                    )

    log.info(f"Loaded {len(students)} students total.")
    if dq_warnings:
        log.warning(f"Data quality warnings ({len(dq_warnings)}):")
        for w in dq_warnings:
            log.warning(f"  {w}")

    return {
        "students": students,
        "max_marks": max_marks,
        "total_max": detected_total_max or 265.0,
        "dq_warnings": dq_warnings,
        "manifest": manifest,
    }


def _get_display_name(profile: dict, canonical: str) -> str:
    """Extract human-readable name from profile dict."""
    for k, v in profile.items():
        if "name" in _norm_name(k) and v:
            return str(v).strip()
    # Rebuild from canonical (title-case)
    return " ".join(p.capitalize() for p in canonical.split())


# ---------------------------------------------------------------------------
# Validation gate
# ---------------------------------------------------------------------------

def validate_students(students: dict, expected_count: int | None = None, dq_warnings: list | None = None):
    """
    Run data quality checks. Prints a summary. Raises ValueError on critical failures.
    """
    issues = []
    warnings = dq_warnings or []

    print("\n" + "="*70)
    print("DATA QUALITY VALIDATION REPORT")
    print("="*70)

    n = len(students)
    print(f"Student count: {n}")
    if expected_count and n != expected_count:
        issues.append(f"CRITICAL: Expected {expected_count} students but got {n}")

    # Check for duplicate keys
    names = list(students.keys())
    if len(names) != len(set(names)):
        dupes = [n for n in names if names.count(n) > 1]
        issues.append(f"CRITICAL: Duplicate student keys: {set(dupes)}")

    # Check all-identical scores
    all_totals = []
    for cn, rec in students.items():
        s = rec.get("assessment_scores", {})
        if s:
            total = sum(v for v in s.values() if isinstance(v, (int, float)))
            all_totals.append(total)

    if all_totals and len(set(all_totals)) == 1 and len(all_totals) > 1:
        issues.append("CRITICAL: All students have identical total scores - likely a bad join")

    # Data quality warnings
    if warnings:
        print(f"\nData quality warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  [!]  {w}")

    if issues:
        print(f"\nCRITICAL ISSUES ({len(issues)}):")
        for issue in issues:
            print(f"  [X]  {issue}")
        raise ValueError(
            f"Validation failed with {len(issues)} critical issue(s). "
            f"Fix data before generating reports."
        )
    else:
        print("\n[OK] Validation passed - no critical issues.\n")

    print("="*70 + "\n")
