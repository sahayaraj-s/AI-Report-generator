"""
column_classifier.py - 5-Class Column Classifier for CCDP Workbooks
====================================================================
Every detected column in an uploaded spreadsheet gets exactly one class:
  1. 'skill': Scored, normalised to 0-100 using detected scale.
  2. 'metric': Typing speed WPM, benchmarked against target, kept OUT of skill mean.
  3. 'compliance': Shirt, Trouser, Tie, Shoe Size, Socks, Uniform. Kept OUT of skill mean. Sizes are never scores.
  4. 'derived': Total, Aggregate, Sum. Excluded from scoring; cross-checks sum.
  5. 'administrative/PII': Phone, Parents, Address, DOB, IDs, Dates, Gender. Excluded.
"""
from __future__ import annotations
import re
import unicodedata
from typing import Any, Literal
import pandas as pd

ColumnClass = Literal["skill", "metric", "compliance", "derived", "administrative/PII"]

# ---------------------------------------------------------------------------
# Classification Keyword & Pattern Dictionaries
# ---------------------------------------------------------------------------

COMPLIANCE_PATTERNS = [
    r"\buniform\b", r"\bshirt\b", r"\btrouser\b", r"\btie\b",
    r"\bshoe\b", r"\bshoe[\s_]?size\b", r"\bsocks\b", r"\bchudidhar\b",
    r"\bshawl\b", r"\bdress\b", r"\bblazer\b", r"\bapron\b",
    r"\bcoat\b", r"\blab[\s_]?coat\b", r"\buniform[\s_]?for\b",
    r"\bpants?\b", r"\bpant[\s_]?size\b",
]

METRIC_PATTERNS = [
    r"\btyping\b", r"\btyping[\s_]?speed\b", r"\bwpm\b", r"\bwords[\s_]?per[\s_]?minute\b",
]

DERIVED_PATTERNS = [
    r"^total$", r"^grand[\s_]?total$", r"^aggregate$", r"^sum$", r"^subtotal$",
    r"^total[\s_]?marks?$", r"^marks?[\s_]?obtained$", r"^max(imum)?[\s_]?marks?$",
    r"^marks?[\s_]?total$", r"^overall[\s_]?total$", r"^out[\s_]?of[\s_]?\d+$"
]

ADMIN_PII_PATTERNS = [
    # Identifiers
    r"^s[\.\s]?no\.?$", r"^sr[\.\s]?no\.?$", r"^sl[\.\s]?no\.?$", r"^serial",
    r"^roll[\s_]?(no|num|number)?$", r"^reg(istration)?[\s_]?(no|num|number)?$",
    r"^enrol(l)?(ment)?[\s_]?(no|num|number)?$", r"^admission[\s_]?(no|num|number)?$",
    r"^student[\s_]?id$", r"^id$",
    # Names
    r"^name$", r"^student[\s_]?name$", r"^candidate[\s_]?name$", r"^full[\s_]?name$",
    # Contact & Family
    r"parent", r"father", r"mother", r"guardian", r"family",
    r"personal[\s_]?(no|num|number)?", r"contact[\s_]?(no|num|number)?",
    r"phone[\s_]?(no|num|number)?", r"mobile[\s_]?(no|num|number)?",
    r"cell[\s_]?(no|num|number)?", r"whats[\s_]?app", r"emergency",
    r"email", r"mail",
    # Demographics & PII
    r"^age$", r"gender", r"sex", r"dob", r"date[\s_]?of[\s_]?birth", r"birth[\s_]?date",
    r"blood[\s_]?(group|grp)?", r"aadhar", r"aadhaar", r"\bpan[\s_]?(card|no)?\b",
    r"address", r"city", r"state", r"pincode", r"pin[\s_]?code", r"district", r"native",
    # Academic/Cohort
    r"college", r"institution", r"university", r"degree", r"department", r"dept",
    r"qualification", r"course", r"branch", r"batch", r"section", r"semester", r"sem",
    r"yop", r"year[\s_]?of[\s_]?pass",
    # Placement outcome meta (not scored as skills)
    r"designation", r"organization", r"company", r"employer",
    r"salary", r"package", r"stipend", r"ctc",
    # Dates
    r"^\d{1,2}[/\-\.]\d{1,2}([/\-\.]\d{2,4})?$", r"^day[\s_]?\d+$",
]

_COMPLIANCE_RE = re.compile("|".join(COMPLIANCE_PATTERNS), re.IGNORECASE)
_METRIC_RE = re.compile("|".join(METRIC_PATTERNS), re.IGNORECASE)
_DERIVED_RE = re.compile("|".join(DERIVED_PATTERNS), re.IGNORECASE)
_ADMIN_PII_RE = re.compile("|".join(ADMIN_PII_PATTERNS), re.IGNORECASE)


def _norm(s: Any) -> str:
    if s is None:
        return ""
    t = str(s).strip()
    t = unicodedata.normalize("NFKD", t)
    t = t.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def classify_column(col_name: str, sample_series: pd.Series | None = None) -> ColumnClass:
    """
    Classifies a column into exactly one of 5 classes.
    """
    clean = _norm(col_name)

    # 1. Compliance (Uniform, clothing, shoe size)
    if _COMPLIANCE_RE.search(clean):
        return "compliance"

    # 2. Metric (Typing speed WPM)
    if _METRIC_RE.search(clean):
        return "metric"

    # 3. Derived (Total, Aggregate, Sum)
    if _DERIVED_RE.search(clean) or clean == "total":
        return "derived"

    # 4. Administrative / PII
    if _ADMIN_PII_RE.search(clean):
        return "administrative/PII"

    # Check series values if provided
    if sample_series is not None and not sample_series.dropna().empty:
        # Check if values are typical uniform letter sizes (S, M, L, XL, XXL)
        str_vals = sample_series.dropna().astype(str).str.strip().str.upper()
        size_tokens = {"S", "M", "L", "XL", "XXL", "XXXL"}
        if len(str_vals) > 0 and (str_vals.isin(size_tokens).mean() > 0.4):
            return "compliance"

        # Check if values look like phone / registration numbers (long integers)
        numeric = pd.to_numeric(sample_series, errors="coerce").dropna()
        if len(numeric) > 0 and (numeric.median() > 1000 or numeric.mean() > 500):
            return "administrative/PII"

        # Check if column is completely non-numeric strings
        if numeric.empty and len(str_vals) > 0:
            return "administrative/PII"

    # 5. Otherwise, genuine competency / skill
    return "skill"


def extract_skill_scale(raw_col: str, series: pd.Series | None = None) -> tuple[str, float]:
    """
    Extracts canonical skill name and scale (e.g. 10.0, 50.0, 100.0).
    """
    clean = str(raw_col).strip()

    # Look for scale in header: "Out of 10", "out of 25", "(50)", "/ 10", etc.
    scale = 100.0
    scale_match = re.search(r"(?:out\s+of|\/|\()\s*(\d+(\.\d+)?)\s*\)?", clean, re.IGNORECASE)
    if scale_match:
        try:
            detected_scale = float(scale_match.group(1))
            if detected_scale > 0:
                scale = detected_scale
        except Exception:
            pass

    # Clean name
    name_clean = re.sub(r"\(?out\s+of\s+\d+(\.\d+)?\)?", "", clean, flags=re.IGNORECASE)
    name_clean = re.sub(r"\/\s*\d+(\.\d+)?", "", name_clean)
    name_clean = re.sub(r"\(\s*\d+(\.\d+)?\s*\)", "", name_clean)
    name_clean = re.sub(r"[\s_]+", " ", name_clean).strip(" ()-")

    # If scale was default 100, inspect series to see if max value suggests /10 or /50
    if scale == 100.0 and series is not None:
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if not numeric.empty:
            mv = numeric.max()
            if mv <= 10.0 and mv > 1.0:
                scale = 10.0
            elif mv <= 25.0 and mv > 10.0:
                scale = 25.0
            elif mv <= 50.0 and mv > 25.0:
                scale = 50.0

    return name_clean or clean, scale
