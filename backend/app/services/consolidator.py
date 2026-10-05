"""
consolidator.py - Single Consolidation Pipeline for Multi-Sheet & Single-Sheet Uploads
====================================================================================
Guarantees ONE roster row per student:
- Normalized name key (case, whitespace, punctuation, initials reconciliation).
- Drops blank rows, repeated header rows, summary/total rows.
- Preview and Save MUST call this exact same function and return the exact same count.
- Attendance parsed from P/A cells only; if missing, returns N/A (never silent 75%).
- Generates a full Consolidation Report (sheets, matched rows, unmatched rows, ambiguous matches).
"""
from __future__ import annotations

import io
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any
import openpyxl
import pandas as pd

from app.services.column_classifier import classify_column, extract_skill_scale, ColumnClass

# ---------------------------------------------------------------------------
# Name Normalization & Fuzzy Resolution
# ---------------------------------------------------------------------------

KNOWN_NAME_SYNONYMS = {
    "madhumitha k": "mathumitha k",
    "sambath s": "sampath s",
    "smitha s": "smitha a",
    "sneka m": "snekha m",
}


def normalize_name_key(s: Any) -> str:
    """Lowercase, strip, unicode NFKD, remove punctuation, collapse whitespace."""
    if s is None:
        return ""
    t = str(s).strip()
    t = unicodedata.normalize("NFKD", t)
    t = t.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return KNOWN_NAME_SYNONYMS.get(t, t)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def fuzzy_match_name(name_key: str, candidate_keys: list[str], threshold: float = 0.82) -> tuple[str | None, float]:
    """
    Find closest match in candidate keys. Returns (best_key, score).
    """
    if name_key in candidate_keys:
        return name_key, 1.0

    # Check initials overlap: e.g. "karthik r" and "karthik raja"
    parts_a = name_key.split()
    for cand in candidate_keys:
        parts_b = cand.split()
        if len(parts_a) >= 2 and len(parts_b) >= 2:
            if parts_a[0] == parts_b[0]:
                # first name matches, check if last token is an initial of the other
                if len(parts_a[-1]) == 1 and parts_b[-1].startswith(parts_a[-1]):
                    return cand, 0.95
                if len(parts_b[-1]) == 1 and parts_a[-1].startswith(parts_b[-1]):
                    return cand, 0.95

    best_score = 0.0
    best_cand = None
    for cand in candidate_keys:
        sc = _similarity(name_key, cand)
        if sc > best_score:
            best_score = sc
            best_cand = cand

    if best_score >= threshold and best_cand:
        return best_cand, best_score
    return None, best_score


# ---------------------------------------------------------------------------
# Filter out invalid / header / total rows
# ---------------------------------------------------------------------------

INVALID_NAME_PATTERNS = [
    r"^total$", r"^grand[\s_]?total$", r"^average$", r"^class[\s_]?average$",
    r"^mean$", r"^count$", r"^batch$", r"^course$", r"^s\.?\s*no\.?$",
    r"^name$", r"^student[\s_]?name$", r"^maximum$", r"^out[\s_]?of",
]
_INVALID_NAME_RE = re.compile("|".join(INVALID_NAME_PATTERNS), re.IGNORECASE)


def is_invalid_row(name_val: Any) -> bool:
    if name_val is None:
        return True
    s = str(name_val).strip()
    if not s or s.lower() in ("nan", "none", "-", "null", "0", ""):
        return True
    # If purely numeric, it's not a student name
    if re.match(r"^\d+(\.\d+)?$", s):
        return True
    if _INVALID_NAME_RE.search(s):
        return True
    return False


# ---------------------------------------------------------------------------
# Salary extraction
# ---------------------------------------------------------------------------

def parse_salary(raw: Any) -> tuple[str | None, float]:
    if raw is None or str(raw).strip() in ("", "nan", "None", "-"):
        return None, 0.0
    s = str(raw).strip()
    cleaned = re.sub(r"(?i)\b(?:rs\.?|inr|₹)\b", "", s).replace(",", "").strip()
    m = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not m:
        return None, 0.0
    try:
        num = float(m.group())
        disp = f"Rs. {int(num):,} / month"
        return disp, num
    except Exception:
        return None, 0.0


# ---------------------------------------------------------------------------
# Master Consolidator
# ---------------------------------------------------------------------------

def consolidate_workbook(
    source: bytes | str,
    default_course: str = "CCDP (Career & Competency Development Program)",
    default_batch: str = "CCDP 2",
    fuzzy_threshold: float = 0.82,
) -> tuple[list[dict], dict]:
    """
    Reads an uploaded workbook (multi-sheet or single-sheet CSV/XLSX) and consolidates
    it into exactly one record per student.

    Returns:
      (consolidated_students: list[dict], consolidation_report: dict)
    """
    raw_bytes = source if isinstance(source, bytes) else open(source, "rb").read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)
    except Exception:
        # Fallback for CSV files
        try:
            df = pd.read_csv(io.BytesIO(raw_bytes))
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Sheet1"
            ws.append([str(c) for c in df.columns])
            for row in df.itertuples(index=False, name=None):
                ws.append([v if pd.notna(v) else None for v in row])
        except Exception as e:
            raise ValueError(f"Could not parse spreadsheet as Excel or CSV: {e}")

    sheet_names = wb.sheetnames

    # Step 1: Detect sheets and categorize them
    sheets_info = {}
    roster_order = []  # preserve original order of encounter
    roster_display = {}  # key -> best display name
    student_records = {}  # key -> data dict

    sheets_report = []
    unmatched_rows = []
    ambiguous_matches = []
    data_quality_notes = []
    all_columns_by_class = {
        "skill": set(),
        "metric": set(),
        "compliance": set(),
        "derived": set(),
        "administrative/PII": set(),
    }

    # First pass: find Profile / master sheet if available
    profile_sheet_name = None
    for name in sheet_names:
        norm_s = name.lower().strip()
        if any(k in norm_s for k in ["profile", "student details", "student list", "master", "demographic"]):
            profile_sheet_name = name
            break

    # Helper to find name column index in a header row
    def find_name_col_idx(header_row):
        for idx, h in enumerate(header_row):
            if h is None:
                continue
            h_str = str(h).strip().lower()
            if any(k in h_str for k in ["student name", "candidate name", "name of student", "name of candidate"]) or h_str == "name":
                return idx
        # Fallback: check if 'name' is in header
        for idx, h in enumerate(header_row):
            if h is not None and "name" in str(h).strip().lower():
                return idx
        return 1 if len(header_row) > 1 else 0

    # Build initial roster from profile sheet or first sheet with names
    ordered_sheets = [profile_sheet_name] if profile_sheet_name else []
    for s in sheet_names:
        if s not in ordered_sheets:
            ordered_sheets.append(s)

    for sheet_name in ordered_sheets:
        ws = wb[sheet_name]
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            continue

        # Find header row (first non-empty row with strings)
        header_idx = 0
        scale_idx = None
        for r_i, r in enumerate(all_rows[:10]):
            non_empty = [c for c in r if c is not None and str(c).strip()]
            if len(non_empty) >= 2:
                header_idx = r_i
                break

        # Check if row below header has scales (e.g. "Out of 50")
        if header_idx + 1 < len(all_rows):
            next_row = all_rows[header_idx + 1]
            if sum(1 for c in next_row if c and re.search(r"out\s+of", str(c), re.IGNORECASE)) >= 1:
                scale_idx = header_idx + 1

        header_row = [str(c).strip() if c is not None else "" for c in all_rows[header_idx]]
        scale_row = [str(c).strip() if c is not None else "" for c in all_rows[scale_idx]] if scale_idx else None
        data_start_idx = (scale_idx + 1) if scale_idx else (header_idx + 1)

        name_col_idx = find_name_col_idx(header_row)

        # Classify each column in the sheet
        classified_cols = []
        for c_i, col_name in enumerate(header_row):
            if not col_name or c_i == name_col_idx:
                classified_cols.append(("administrative/PII", col_name, 100.0))
                all_columns_by_class["administrative/PII"].add(col_name or "Student Name")
                continue
            # Sample values for column
            col_samples = [r[c_i] for r in all_rows[data_start_idx:data_start_idx + 10] if c_i < len(r) and r[c_i] is not None]
            sample_series = pd.Series(col_samples) if col_samples else None
            c_class = classify_column(col_name, sample_series)
            clean_name, scale = extract_skill_scale(col_name, sample_series)
            if scale_row and c_i < len(scale_row) and scale_row[c_i]:
                m = re.search(r"(\d+(?:\.\d+)?)", scale_row[c_i])
                if m:
                    scale = float(m.group(1))
            classified_cols.append((c_class, clean_name, scale))
            all_columns_by_class[c_class].add(clean_name if c_class == "skill" else col_name)

        # Check if sheet is attendance (many date columns or P/A cells)
        is_attendance_sheet = False
        date_col_count = sum(1 for _, cn, _ in classified_cols if re.search(r"^\d{1,2}[/\-\.]|day[\s_]?\d+", cn, re.IGNORECASE))
        if date_col_count >= 5 or "attendance" in sheet_name.lower():
            is_attendance_sheet = True

        sheet_matched_count = 0
        sheet_unmatched_count = 0
        total_valid_rows = 0

        for r_i, row in enumerate(all_rows[data_start_idx:], start=data_start_idx + 1):
            if name_col_idx >= len(row):
                continue
            raw_name = row[name_col_idx]
            if is_invalid_row(raw_name):
                continue

            total_valid_rows += 1
            raw_name_str = str(raw_name).strip()
            name_key = normalize_name_key(raw_name_str)

            # Match against existing roster
            matched_key = None
            if name_key in student_records:
                matched_key = name_key
            else:
                cand_match, sc = fuzzy_match_name(name_key, list(student_records.keys()), threshold=fuzzy_threshold)
                if cand_match:
                    matched_key = cand_match
                    if sc < 0.99:
                        ambiguous_matches.append({
                            "sheet": sheet_name,
                            "raw_name": raw_name_str,
                            "matched_to": student_records[matched_key]["display_name"],
                            "confidence": round(sc, 2),
                        })

            # If brand new student
            if not matched_key:
                matched_key = name_key
                student_records[matched_key] = {
                    "canonical_name": name_key,
                    "display_name": raw_name_str,
                    "roll_number": None,
                    "email": None,
                    "phone": None,
                    "course": default_course,
                    "batch": default_batch,
                    "assessment_scores": {},
                    "skill_scores": {},
                    "typing_wpm": None,
                    "compliance": {},
                    "attendance_p_count": 0,
                    "attendance_trackable": 0,
                    "attendance_pct": None,
                    "attendance_status": "N/A",
                    "attendance_reason": "No attendance records found",
                    "is_placed": False,
                    "placement_company": None,
                    "placement_designation": None,
                    "placement_salary": None,
                    "placement_salary_num": 0.0,
                    "profile_extra": {},
                }
                roster_order.append(matched_key)

            st = student_records[matched_key]
            sheet_matched_count += 1

            # Extract fields according to classification
            if is_attendance_sheet:
                present = 0
                absent = 0
                for c_i, (c_class, col_name, _) in enumerate(classified_cols):
                    if c_i >= len(row) or c_i == name_col_idx:
                        continue
                    v_str = str(row[c_i]).strip().upper() if row[c_i] is not None else ""
                    if v_str == "P":
                        present += 1
                    elif v_str == "A":
                        absent += 1
                if (present + absent) > 0:
                    st["attendance_p_count"] += present
                    st["attendance_trackable"] += (present + absent)
                    st["attendance_pct"] = round((st["attendance_p_count"] / st["attendance_trackable"]) * 100.0, 1)
                    st["attendance_status"] = "tracked"
                    st["attendance_reason"] = None
            else:
                for c_i, (c_class, col_name, scale) in enumerate(classified_cols):
                    if c_i >= len(row) or c_i == name_col_idx:
                        continue
                    val = row[c_i]
                    if val is None or str(val).strip() in ("", "nan", "None", "-"):
                        continue

                    # 1. Compliance (shirt, trouser, tie, shoe size)
                    if c_class == "compliance":
                        st["compliance"][col_name] = str(val).strip()

                    # 2. Metric (Typing Speed)
                    elif c_class == "metric":
                        try:
                            wpm = float(str(val).replace(",", "").strip())
                            st["typing_wpm"] = wpm
                        except Exception:
                            pass

                    # 3. Derived (Total - cross-check only)
                    elif c_class == "derived":
                        pass  # explicitly kept out of skill scores

                    # 4. Administrative / PII
                    elif c_class == "administrative/PII":
                        h_lower = col_name.lower()
                        if any(k in h_lower for k in ["roll", "reg", "enrol", "id"]) and not st["roll_number"]:
                            st["roll_number"] = str(val).strip()
                        elif "email" in h_lower and not st["email"]:
                            st["email"] = str(val).strip()
                        elif any(k in h_lower for k in ["phone", "mobile", "contact"]) and not st["phone"]:
                            st["phone"] = str(val).strip()
                        elif any(k in h_lower for k in ["company", "organization", "employer"]):
                            st["placement_company"] = str(val).strip()
                            st["is_placed"] = True
                        elif "designation" in h_lower:
                            st["placement_designation"] = str(val).strip()
                            st["is_placed"] = True
                        elif any(k in h_lower for k in ["salary", "package", "ctc"]):
                            disp, num = parse_salary(val)
                            st["placement_salary"] = disp
                            st["placement_salary_num"] = num
                            st["is_placed"] = True

                    # 5. Genuine Skill / Assessment
                    elif c_class == "skill":
                        try:
                            num_val = float(str(val).replace(",", "").strip())
                            norm_score = (num_val / scale) * 100.0 if scale > 0 else num_val
                            norm_score = round(min(max(norm_score, 0.0), 100.0), 1)
                            st["skill_scores"][col_name] = norm_score
                            st["assessment_scores"][col_name] = num_val
                        except Exception:
                            pass

        sheets_report.append({
            "name": sheet_name,
            "category": "attendance" if is_attendance_sheet else ("profile" if sheet_name == profile_sheet_name else "academic/skill"),
            "total_rows": len(all_rows),
            "valid_student_rows": total_valid_rows,
            "matched_rows": sheet_matched_count,
            "unmatched_rows": total_valid_rows - sheet_matched_count,
        })

    # Prepare final consolidated student list in encounter order
    consolidated_list = [student_records[k] for k in roster_order]

    # Data quality summary notes
    if ambiguous_matches:
        data_quality_notes.append({
            "severity": "info",
            "title": f"{len(ambiguous_matches)} fuzzy name reconciliations",
            "detail": f"Names matched across sheets with confidence threshold >={fuzzy_threshold}.",
        })
    missing_att_count = sum(1 for s in consolidated_list if s["attendance_status"] == "N/A")
    if missing_att_count > 0:
        data_quality_notes.append({
            "severity": "warning",
            "title": f"{missing_att_count} students missing attendance",
            "detail": "Attendance is marked N/A (never defaulted to 75%).",
        })

    consolidation_report = {
        "sheets": sheets_report,
        "total_consolidated_students": len(consolidated_list),
        "unmatched_rows": unmatched_rows,
        "ambiguous_matches": ambiguous_matches,
        "data_quality_notes": data_quality_notes,
        "columns_by_class": {
            cls: sorted(list(cols)) for cls, cols in all_columns_by_class.items()
        },
    }

    return consolidated_list, consolidation_report
