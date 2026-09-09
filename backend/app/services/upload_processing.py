"""
Parses an uploaded student sheet (xlsx/xls/csv), validates it, and figures out
which columns are metadata (name, roll number, course, batch, contact info...)
vs. which are genuine CCDP skill score columns.

DATA HYGIENE & CCDP NORMALIZATION:
Strictly excludes all phone numbers, parents numbers, personal numbers, age,
registration numbers, roll numbers, serial numbers, pincodes, aadhar numbers,
and administrative fields from skill scoring.

Smartly detects score scale (e.g. "Out of 10", "Out of 25", "Out of 50")
and cleans skill names (e.g. "Communication Skill Out of 10" -> "Communication Skills").
"""
from __future__ import annotations
import io
import re
import pandas as pd

META_COLUMN_ALIASES = {
    "name": [
        "name", "student name", "full name", "student_name", "fullname",
        "candidate name", "name of candidate", "name of student", "student"
    ],
    "roll_number": [
        "roll", "roll no", "roll no.", "roll number", "id", "student id",
        "reg no", "reg no.", "reg number", "registration", "registration no",
        "registration number", "roll_number", "rollno", "enrollment", "enroll no",
        "register no", "register number", "admission no", "app no", "application no",
        "s.no", "sl.no", "s.no.", "sl.no.", "sr.no", "serial no"
    ],
    "email": ["email", "mail", "email id", "email_id", "emailid", "student email"],
    "phone": [
        "phone", "mobile", "contact", "phone no", "phone no.", "mobile no", "mobile no.",
        "contact no", "contact no.", "personal no", "personal no.", "personal number",
        "parents no", "parents no.", "parent contact", "parents contact", "father mobile",
        "mother mobile", "whatsapp no", "whatsapp number", "cell", "cell no", "phone number",
        "mobile number", "contact number", "emergency no", "alt contact", "alt mobile"
    ],
    "course": ["course", "program", "stream", "programme", "course name", "degree", "department"],
    "batch": [
        "batch", "section", "group", "batch name", "batch_name", "ccdp batch",
        "ccdp", "training batch", "cohort"
    ],
    "attendance": [
        "attendance", "attendance %", "attendance percentage", "attend",
        "attendance_pct", "50 days attendance", "days present", "total attendance"
    ],
}

# Regex patterns matching non-skill columns (case-insensitive)
NON_SKILL_PATTERNS = [
    # Contact & Personal info
    r"parent", r"father", r"mother", r"guardian", r"family",
    r"personal[\s_]?(no|num|number)?",
    r"contact[\s_]?(no|num|number)?",
    r"phone[\s_]?(no|num|number)?",
    r"mobile[\s_]?(no|num|number)?",
    r"cell[\s_]?(no|num|number)?",
    r"tel(ephone)?[\s_]?(no|num|number)?",
    r"whats[\s_]?app",
    r"emergency",
    r"landline",
    # Demographics & IDs
    r"^age$", r"\bage\b",
    r"gender", r"sex",
    r"dob", r"date[\s_]?of[\s_]?birth", r"birth[\s_]?date",
    r"blood[\s_]?(group|grp)?",
    r"aadhar", r"aadhaar", r"pan[\s_]?(card|no)?",
    r"passport", r"voter[\s_]?(id)?",
    r"address", r"city", r"state", r"pincode", r"pin[\s_]?code", r"zip", r"district", r"native", r"location",
    # Registration & Administrative identifiers
    r"reg(istration)?[\s_]?(no|num|number)?",
    r"roll[\s_]?(no|num|number)?",
    r"s\.?\s*no\.?", r"sr\.?\s*no\.?", r"serial[\s_]?no",
    r"sl\.?\s*no\.?", r"slno",
    r"id$", r"student[\s_]?id",
    r"enroll(ment)?[\s_]?(no|num|number)?",
    r"admission[\s_]?(no|num|number)?",
    r"app(lication)?[\s_]?(no|num|number)?",
    # Academic metadata
    r"college", r"institution", r"university", r"medium",
    r"year[\s_]?of[\s_]?(pass|passing|graduation|study)",
    r"yop", r"passed[\s_]?out",
    r"sem(ester)?$",
    r"cgpa", r"percentage$",
    # Financial / Operational
    r"fees?", r"amount", r"salary", r"stipend", r"balance", r"due",
    r"marks?[\s_]?obtained", r"total[\s_]?marks?", r"max(imum)?[\s_]?marks?"
]

_NON_SKILL_RE = re.compile("|".join(NON_SKILL_PATTERNS), re.IGNORECASE)


def _is_non_skill_column(col_name: str) -> bool:
    """Return True if this column should NEVER be treated as a skill score."""
    clean = col_name.strip().lower()
    # Direct alias match
    for meta_key, aliases in META_COLUMN_ALIASES.items():
        if clean in aliases:
            return True

    # Pattern match
    if _NON_SKILL_RE.search(clean):
        return True

    # Specific common patterns in Indian college / CCDP excel files
    tokens = re.split(r"[\s_./\-,]+", clean)
    excluded_tokens = {
        "parents", "parent", "father", "mother", "guardian", "family",
        "personal", "contact", "mobile", "phone", "cell", "tel", "whatsapp",
        "age", "gender", "sex", "dob", "blood", "group", "aadhar", "aadhaar",
        "reg", "roll", "sno", "slno", "id", "enrollment", "admission",
        "address", "city", "state", "pin", "pincode", "zip", "district",
        "college", "degree", "dept", "department", "branch", "yop", "sem", "semester"
    }
    if any(t in excluded_tokens for t in tokens):
        # Unless it's explicitly "Communication Skill" or similar
        if not any(k in clean for k in ["communication", "office", "excel", "analytical", "soft", "aptitude", "leadership", "creativity", "problem"]):
            return True

    return False


def _match_meta_column(col_name: str):
    lc = col_name.strip().lower()
    for meta_key, aliases in META_COLUMN_ALIASES.items():
        if lc in aliases:
            return meta_key
    return None


def extract_skill_meta(raw_col_name: str) -> tuple[str, float]:
    """
    Extracts a clean display name and scale factor from a column header.
    Examples:
      - 'Communication Skill Out Of 10' -> ('Communication Skills', 10.0)
      - 'Analytical Skill Out Of 10' -> ('Analytical Skills', 10.0)
      - 'Creativity Out Of 10' -> ('Creativity & Innovation', 10.0)
      - 'Leadership Skill Out Of 10' -> ('Leadership Skills', 10.0)
      - 'MS Office (25)' -> ('MS Office', 25.0)
      - 'Soft Skills' -> ('Soft Skills', 100.0)
    """
    clean = raw_col_name.strip()

    # Look for scale in header: "Out of 10", "out of 25", "(10)", "/ 10", etc.
    scale = 100.0
    scale_match = re.search(r"(?:out\s+of|\/|\()\s*(\d+(\.\d+)?)\s*\)?", clean, re.IGNORECASE)
    if scale_match:
        try:
            detected_scale = float(scale_match.group(1))
            if detected_scale > 0:
                scale = detected_scale
        except Exception:
            pass

    # Strip scale annotations from the name
    name_clean = re.sub(r"\(?out\s+of\s+\d+(\.\d+)?\)?", "", clean, flags=re.IGNORECASE)
    name_clean = re.sub(r"\/\s*\d+(\.\d+)?", "", name_clean)
    name_clean = re.sub(r"\(\s*\d+(\.\d+)?\s*\)", "", name_clean)
    name_clean = re.sub(r"[\s_]+", " ", name_clean).strip()

    # Canonical CCDP skill name formatting
    lc = name_clean.lower()
    if "communication" in lc:
        name_clean = "Communication Skills"
    elif "analytical" in lc or "aptitude" in lc or "reasoning" in lc:
        name_clean = "Analytical Skills"
    elif "problem" in lc or "logic" in lc:
        name_clean = "Problem Solving"
    elif "ms office" in lc or "excel" in lc or "word" in lc or "powerpoint" in lc or "computer" in lc:
        name_clean = "MS Office & IT"
    elif "soft skill" in lc or "interpersonal" in lc:
        name_clean = "Soft Skills"
    elif "leadership" in lc:
        name_clean = "Leadership Skills"
    elif "creativity" in lc or "innovation" in lc:
        name_clean = "Creativity & Innovation"
    elif "presentation" in lc:
        name_clean = "Presentation Skills"
    elif "english" in lc or "verbal" in lc:
        name_clean = "Verbal Ability"
    elif "domain" in lc or "healthcare" in lc or "hospital" in lc:
        name_clean = "Healthcare Domain"
    else:
        name_clean = name_clean.title()

    return name_clean, scale


def infer_scale_from_series(series: pd.Series, header_scale: float) -> float:
    """If header scale was default 100, inspect values to see if scale is 10, 5, 20, 25, 50."""
    if header_scale != 100.0:
        return header_scale
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if len(numeric) == 0:
        return 100.0
    max_val = numeric.max()
    if max_val <= 5.0 and max_val > 0.5:
        return 5.0
    if max_val <= 10.0 and max_val > 1.0:
        return 10.0
    if max_val <= 20.0 and max_val > 10.0:
        return 20.0
    if max_val <= 25.0 and max_val > 10.0:
        return 25.0
    if max_val <= 50.0 and max_val > 25.0:
        return 50.0
    return 100.0


def _detect_phone_or_id_column(series: pd.Series) -> bool:
    """Return True if a numeric column looks like phone numbers or IDs (> 1000 or >= 7 digits)."""
    try:
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if len(numeric) == 0:
            return False
        # If median or mean value is > 1000, it's definitely not a 0-100 skill score
        if numeric.median() > 1000 or numeric.mean() > 500:
            return True
        sample = numeric.head(10)
        long_count = sum(1 for v in sample if len(str(int(abs(v)))) >= 7)
        return long_count >= len(sample) * 0.6
    except Exception:
        return False


def read_all_sheets(filename: str, raw_bytes: bytes) -> dict[str, pd.DataFrame]:
    lower = filename.lower()
    if lower.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(raw_bytes))
        except Exception:
            df = pd.read_csv(io.BytesIO(raw_bytes), on_bad_lines="skip")
        return {"Sheet1": df}

    sheets_dict = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=None)
    return sheets_dict if isinstance(sheets_dict, dict) else {"Sheet1": sheets_dict}


def analyze_sheet(filename: str, raw_bytes: bytes):
    """
    Scans ALL sheets in the uploaded workbook.
    Returns (combined_df, meta_columns, skill_columns_meta, warnings, sheets_summary)
    where skill_columns_meta is a dict: {raw_column_name: {"clean_name": str, "scale": float}}
    """
    warnings = []
    sheets_dict = read_all_sheets(filename, raw_bytes)

    processed_dfs = []
    global_skill_meta = {}  # raw_col -> {clean_name, scale}
    global_meta_cols = {}
    sheets_summary = []

    for sheet_name, df in sheets_dict.items():
        if df.empty:
            continue
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]

        if df.duplicated(subset=None).any():
            warnings.append(f"Sheet '{sheet_name}': Duplicate rows detected — duplicates removed.")
            df = df.drop_duplicates()

        dup_cols = df.columns[df.columns.duplicated()].tolist()
        if dup_cols:
            warnings.append(f"Sheet '{sheet_name}': Duplicate columns found: {dup_cols}.")
            df = df.loc[:, ~df.columns.duplicated()]

        meta_columns = {}
        for col in df.columns:
            matched = _match_meta_column(col)
            if matched and matched not in meta_columns:
                meta_columns[matched] = col
                if matched not in global_meta_cols:
                    global_meta_cols[matched] = col

        # Skill columns are numeric columns not in meta AND not non-skill columns
        sheet_skills = []
        excluded_cols = []
        for col in df.columns:
            if col in meta_columns.values():
                continue

            # Data hygiene check by column header name
            if _is_non_skill_column(col):
                excluded_cols.append(col)
                continue

            # Check if column is numeric or can be coerced to numeric
            numeric_series = pd.to_numeric(df[col], errors="coerce")
            if numeric_series.dropna().empty:
                excluded_cols.append(col)
                continue

            # Data hygiene check by value pattern (phone / id / roll numbers)
            if _detect_phone_or_id_column(numeric_series):
                excluded_cols.append(col)
                warnings.append(
                    f"Sheet '{sheet_name}': Column '{col}' excluded from skill scoring (values look like phone/ID/age data, not skill scores)."
                )
                continue

            # Clean name and scale extraction
            clean_name, header_scale = extract_skill_meta(col)
            scale = infer_scale_from_series(numeric_series, header_scale)

            global_skill_meta[col] = {
                "clean_name": clean_name,
                "scale": scale,
            }
            sheet_skills.append(clean_name)

        if excluded_cols:
            warnings.append(
                f"Sheet '{sheet_name}': Non-skill columns excluded ({len(excluded_cols)}): {', '.join(excluded_cols[:5])}{'...' if len(excluded_cols) > 5 else ''}."
            )

        # Store sheet name metadata
        df["_sheet_name"] = sheet_name

        # Auto-detect batch name if sheet name looks like a batch name (e.g. CCDP 1, CCDP 2)
        if "batch" not in meta_columns and re.search(r"ccdp|batch", sheet_name, re.IGNORECASE):
            df["_detected_batch"] = sheet_name.strip()

        if "name" in meta_columns:
            processed_dfs.append((df, meta_columns, sheet_skills))
            sheets_summary.append({
                "sheet_name": sheet_name,
                "student_count": len(df),
                "detected_skills": sheet_skills,
                "has_name_column": True,
                "excluded_columns": excluded_cols,
            })
        else:
            warnings.append(f"Sheet '{sheet_name}': Skipped because no 'Name' column was detected.")
            sheets_summary.append({
                "sheet_name": sheet_name,
                "student_count": len(df),
                "detected_skills": sheet_skills,
                "has_name_column": False,
                "excluded_columns": excluded_cols,
            })

    if not processed_dfs:
        raise ValueError("No valid student sheets found with a 'Name' column.")

    combined_df = pd.concat([item[0] for item in processed_dfs], ignore_index=True)
    detected_skill_names = sorted(list({meta["clean_name"] for meta in global_skill_meta.values()}))

    if not detected_skill_names:
        warnings.append("No numeric skill-score columns detected — scores will default to 0.")

    return combined_df, global_meta_cols, global_skill_meta, warnings, sheets_summary
