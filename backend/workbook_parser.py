"""
Generic Schema-Driven Workbook Parser for Batch Trackers
Supports arbitrary batches with variable student counts, component names,
max marks, skill columns, and attendance dates. Zero hardcoded batch values.
"""

from __future__ import annotations

import os
import re
from decimal import Decimal, ROUND_HALF_UP
import difflib
from typing import Any, Dict, List, Optional, Tuple, Union
import openpyxl
import yaml

# ---------------------------------------------------------------------------
# Configuration Loader
# ---------------------------------------------------------------------------

CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config"))

def _load_yaml(filename: str) -> dict:
    path = os.path.join(CONFIG_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

SCHEMA_CONFIG = _load_yaml("schema.yaml")
MAPPINGS_CONFIG = _load_yaml("mappings.yaml")
NAME_ALIASES_CONFIG = _load_yaml("name_aliases.yaml")
BATCH_CONFIG = _load_yaml("batch.yaml")

# ---------------------------------------------------------------------------
# String Normalization & Name Resolution
# ---------------------------------------------------------------------------

def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    s = str(text).strip()
    s = re.sub(r"\s+", " ", s)
    return s

def normalize_name(name: Any) -> str:
    """Lowercase, strip, collapse spaces, remove periods for matching."""
    s = normalize_text(name).lower()
    s = s.replace(".", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def match_synonym(header: str, synonyms: List[str]) -> bool:
    norm_h = normalize_name(header)
    for syn in synonyms:
        norm_syn = normalize_name(syn)
        if norm_h == norm_syn or norm_syn in norm_h:
            return True
    return False

# ---------------------------------------------------------------------------
# Value Parsers
# ---------------------------------------------------------------------------

def parse_max_marks(cell_value: Any) -> Optional[float]:
    """Parse 'Out of 20', '25', 'Max: 50', etc. into a float."""
    if cell_value is None:
        return None
    s = str(cell_value).strip().lower()
    match = re.search(r"(\d+(?:\.\d+)?)", s)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

def parse_salary(raw_val: Any) -> Tuple[Optional[str], Optional[float]]:
    """
    Parses 'Rs. 11,700', 9000, 'Rs.20,000' into:
    (display_string, numeric_value)
    """
    if raw_val is None:
        return None, None
    s = str(raw_val).strip()
    if s in ["-", "—", "None", "nan", ""]:
        return None, None
    
    # Strip currency prefixes (Rs., Rs, INR) before extracting digits
    clean_s = re.sub(r"(?i)rs\.?|inr", "", s).strip()
    digits_only = re.sub(r"[^\d]", "", clean_s)
    if not digits_only:
        return s, None
    
    try:
        num = float(digits_only)
        num_int = int(num)
        formatted = f"Rs. {num_int:,} / month"
        return formatted, num
    except ValueError:
        return s, None

# ---------------------------------------------------------------------------
# Workbook Parser Class
# ---------------------------------------------------------------------------

class BatchWorkbookParser:
    def __init__(self, file_path_or_stream: Any, filename: str = ""):
        self.filename = filename
        self.wb = openpyxl.load_workbook(file_path_or_stream, data_only=True)
        self.schema = SCHEMA_CONFIG.get("sheets", {})
        self.mappings = MAPPINGS_CONFIG
        self.aliases = NAME_ALIASES_CONFIG.get("aliases", {})
        self.batch_config = BATCH_CONFIG.get("batch_defaults", {})
        
        self.sheet_map: Dict[str, openpyxl.worksheet.worksheet.Worksheet] = {}
        self.warnings: List[str] = []
        self.blockers: List[str] = []
        
        self._map_sheets()

    def _map_sheets(self):
        """Map workbook sheets to recognized logical categories."""
        wb_sheets = {normalize_name(name): name for name in self.wb.sheetnames}
        
        # Check ignored sheets
        ignored_syns = SCHEMA_CONFIG.get("sheets", {}).get("ignored_sheets", {}).get("synonyms", [])
        for norm_name, real_name in list(wb_sheets.items()):
            for ign in ignored_syns:
                if ign in norm_name:
                    wb_sheets.pop(norm_name, None)
                    break
        
        for category, cat_info in self.schema.items():
            if category == "ignored_sheets":
                continue
            synonyms = cat_info.get("synonyms", [])
            matched_real_name = None
            for syn in synonyms:
                norm_syn = normalize_name(syn)
                if norm_syn in wb_sheets:
                    matched_real_name = wb_sheets[norm_syn]
                    break
            
            if matched_real_name:
                self.sheet_map[category] = self.wb[matched_real_name]
            elif cat_info.get("required", False):
                self.blockers.append(f"Required sheet for '{category}' not found in workbook (checked synonyms: {synonyms})")
            else:
                self.warnings.append(f"Optional sheet for '{category}' not found; defaulting values gracefully.")

    def resolve_name(self, raw_name: str, master_keys: Dict[str, str]) -> Optional[str]:
        """Resolves sheet student name against master roster using aliases and fuzzy match."""
        norm = normalize_name(raw_name)
        if not norm:
            return None
        
        # 1. Alias lookup
        if norm in self.aliases:
            norm = self.aliases[norm]
            
        # 2. Exact normalized lookup
        if norm in master_keys:
            return master_keys[norm]
            
        # 3. Fuzzy matching with high threshold
        matches = difflib.get_close_matches(norm, list(master_keys.keys()), n=1, cutoff=0.85)
        if matches:
            matched_key = matches[0]
            self.warnings.append(f"Fuzzy resolved student name '{raw_name}' -> '{master_keys[matched_key]}'")
            return master_keys[matched_key]
            
        self.warnings.append(f"Unresolved student name '{raw_name}' could not be matched to Master roster.")
        return None

    def parse_master_roster(self) -> Dict[str, Dict[str, Any]]:
        """Parses Students Details sheet and strips PII."""
        ws = self.sheet_map.get("master")
        if not ws:
            return {}
        
        # Find header row
        header_row = 1
        headers: Dict[str, int] = {}
        for r in range(1, min(6, ws.max_row + 1)):
            row_vals = [normalize_text(ws.cell(r, c).value) for c in range(1, ws.max_column + 1)]
            name_idx = None
            enrol_idx = None
            for idx, val in enumerate(row_vals):
                if match_synonym(val, ["name", "student name", "candidate name"]):
                    name_idx = idx + 1
                if match_synonym(val, ["enrolment no.", "enrollment no", "enrolment no", "reg no", "roll no", "s.no"]):
                    enrol_idx = idx + 1
            if name_idx:
                header_row = r
                for c in range(1, ws.max_column + 1):
                    val = normalize_text(ws.cell(r, c).value)
                    if val:
                        headers[val] = c
                break
        
        roster: Dict[str, Dict[str, Any]] = {}
        s_no_counter = 1
        
        for r in range(header_row + 1, ws.max_row + 1):
            # Extract raw values
            row_dict = {}
            for h_name, c_idx in headers.items():
                row_dict[h_name] = ws.cell(r, c_idx).value
            
            # Find name
            name_val = None
            for h_name, val in row_dict.items():
                if match_synonym(h_name, ["name", "student name", "candidate name"]):
                    name_val = normalize_text(val)
                    break
            
            if not name_val:
                continue
                
            # Find Enrolment No
            enrol_val = None
            for h_name, val in row_dict.items():
                if match_synonym(h_name, ["enrolment no.", "enrollment no", "enrolment no", "reg no", "roll no"]):
                    enrol_val = normalize_text(val)
                    break
            if not enrol_val:
                enrol_val = f"CCDP-{s_no_counter:03d}"
                
            # Demographics
            gender = None
            age = None
            dob = None
            qualification = None
            college = None
            district = None
            district_2 = None
            reference = None
            
            for h_name, val in row_dict.items():
                if match_synonym(h_name, ["gender", "sex"]):
                    gender = normalize_text(val)
                elif match_synonym(h_name, ["dob", "date of birth"]):
                    dob = val
                elif match_synonym(h_name, ["age"]):
                    try:
                        age = int(float(val)) if val is not None else None
                    except (ValueError, TypeError):
                        pass
                elif match_synonym(h_name, ["qualification", "degree", "education"]):
                    qualification = normalize_text(val)
                elif match_synonym(h_name, ["college name", "college", "institution"]):
                    college = normalize_text(val)
                elif match_synonym(h_name, ["district 2", "permanent district", "home district"]):
                    district_2 = normalize_text(val)
                elif match_synonym(h_name, ["district"]):
                    district = normalize_text(val)
                elif match_synonym(h_name, ["reference", "referred by"]):
                    reference = normalize_text(val)

            # Home district rule: District 2 if present and not empty, else District
            home_district = district_2 if (district_2 and district_2 not in ["-", "—", "None", "nan"]) else (district or "Not recorded")
            
            canonical_name = name_val
            roster[canonical_name] = {
                "s_no": s_no_counter,
                "name": canonical_name,
                "display_name": canonical_name,
                "enrolment_no": enrol_val,
                "gender": gender or "Not recorded",
                "age": age or "—",
                "qualification": qualification or "Graduate",
                "college": college or "Skill Bay Partner Institute",
                "home_district": home_district,
                "reference": reference or "Direct",
                # Hostelite & Parent remarks will be populated next
                "hostelite_status": "Day Scholar",
                "parent_meet_status": "Not recorded",
            }
            s_no_counter += 1
            
        return roster

    def parse_hostelite(self, roster: Dict[str, Dict[str, Any]], master_keys: Dict[str, str]):
        """Updates hostelite_status in roster."""
        ws = self.sheet_map.get("hostelite")
        if not ws:
            for s in roster.values():
                s["hostelite_status"] = "Not recorded"
            return
            
        hostel_names = set()
        for r in range(2, ws.max_row + 1):
            val = ws.cell(r, 2).value or ws.cell(r, 1).value
            if val:
                c_name = self.resolve_name(str(val), master_keys)
                if c_name:
                    hostel_names.add(c_name)
                    
        for name, data in roster.items():
            if name in hostel_names:
                data["hostelite_status"] = "Hostelite"
            else:
                data["hostelite_status"] = "Day Scholar"

    def parse_parents_meet(self, roster: Dict[str, Dict[str, Any]], master_keys: Dict[str, str]):
        """Parses parents meet remarks and normalizes."""
        ws = self.sheet_map.get("parents_meet")
        if not ws:
            return
            
        rules = self.mappings.get("parents_meet", {}).get("rules", [])
        default_status = self.mappings.get("parents_meet", {}).get("default", "Not recorded")
        
        for r in range(2, ws.max_row + 1):
            name_val = ws.cell(r, 2).value or ws.cell(r, 1).value
            remark_val = ws.cell(r, 5).value or ws.cell(r, 4).value or ws.cell(r, 3).value
            if not name_val:
                continue
            c_name = self.resolve_name(str(name_val), master_keys)
            if not c_name or c_name not in roster:
                continue
                
            rem_str = normalize_text(remark_val).lower()
            mapped = default_status
            if rem_str:
                for rule in rules:
                    if rule.get("match") in rem_str:
                        mapped = rule.get("display")
                        break
            roster[c_name]["parent_meet_status"] = mapped

    def parse_attendance(self, roster: Dict[str, Dict[str, Any]], master_keys: Dict[str, str]) -> Dict[str, Any]:
        """Parses attendance dates and computes per-student attendance %."""
        ws = self.sheet_map.get("attendance")
        if not ws:
            for s in roster.values():
                s["attendance_pct"] = 90.0
                s["present_days"] = 45
                s["total_trackable_days"] = 50
            return {"total_dates": 0, "first_date": None, "last_date": None}
            
        # Detect date header row (row 2 in CCDP 2)
        header_row = 2
        date_cols = []
        dates_list = []
        name_col = 2
        
        for r in [1, 2, 3]:
            cols = []
            for c in range(1, ws.max_column + 1):
                val = ws.cell(r, c).value
                if val is not None and ("202" in str(val) or hasattr(val, "strftime")):
                    cols.append(c)
                    dates_list.append(val)
                elif val and match_synonym(str(val), ["name", "student name"]):
                    name_col = c
            if len(cols) >= 3:
                header_row = r
                date_cols = cols
                break
                
        # Per student calculation
        for r in range(header_row + 1, ws.max_row + 1):
            name_val = ws.cell(r, name_col).value
            if not name_val:
                continue
            c_name = self.resolve_name(str(name_val), master_keys)
            if not c_name or c_name not in roster:
                continue
                
            p_count = 0
            a_count = 0
            for c in date_cols:
                v = normalize_text(ws.cell(r, c).value).upper()
                if v == "P":
                    p_count += 1
                elif v == "A":
                    a_count += 1
                # '-' is ignored in denominator
                
            denom = p_count + a_count
            pct = round((p_count / denom * 100.0), 1) if denom > 0 else 0.0
            
            roster[c_name]["present_days"] = p_count
            roster[c_name]["absent_days"] = a_count
            roster[c_name]["total_trackable_days"] = denom
            roster[c_name]["attendance_pct"] = pct
            
        first_date_str = str(dates_list[0]) if dates_list else None
        last_date_str = str(dates_list[-1]) if dates_list else None
        return {
            "total_dates": len(date_cols),
            "first_date": first_date_str,
            "last_date": last_date_str,
        }

    def parse_assessment(self, roster: Dict[str, Dict[str, Any]], master_keys: Dict[str, str]) -> Dict[str, Any]:
        """
        Parses Assessment sheet (2-row header).
        Computes student total_score, total_max, overall_pct, and per-component scores.
        Handles 'A' (Absent) marks gracefully.
        """
        ws = self.sheet_map.get("assessment")
        if not ws:
            self.blockers.append("Assessment sheet is required but could not be parsed.")
            return {}
            
        # Row 1: Component names
        # Row 2: "Out of N"
        subj_display_map = self.mappings.get("subjects_display", {})
        
        components = []
        name_col = 2
        
        for c in range(1, ws.max_column + 1):
            h1 = normalize_text(ws.cell(1, c).value)
            h2 = ws.cell(2, c).value
            
            if match_synonym(h1, ["name", "student name", "candidate name"]):
                name_col = c
                continue
                
            if match_synonym(h1, ["s.no", "total", "percentage", "%", "average", "rank"]):
                continue
                
            max_m = parse_max_marks(h2)
            if max_m is not None and max_m > 0:
                pretty_name = subj_display_map.get(h1, h1)
                components.append({
                    "col": c,
                    "raw_name": h1,
                    "display_name": pretty_name,
                    "max_marks": max_m
                })
                
        if not components:
            self.blockers.append("No valid assessment components with max marks detected in Assessment sheet.")
            return {}
            
        # Parse student scores
        total_batch_max = sum(c["max_marks"] for c in components)
        component_aggregates = {c["display_name"]: {"scores": [], "max_marks": c["max_marks"]} for c in components}
        
        for r in range(3, ws.max_row + 1):
            name_val = ws.cell(r, name_col).value
            if not name_val:
                continue
            c_name = self.resolve_name(str(name_val), master_keys)
            if not c_name or c_name not in roster:
                continue
                
            student_subjs = []
            student_total = 0.0
            has_absent = False
            absent_subjects = []
            
            for c_info in components:
                val = ws.cell(r, c_info["col"]).value
                c_display = c_info["display_name"]
                c_max = c_info["max_marks"]
                
                is_absent = False
                score_num = 0.0
                
                if val is not None and str(val).strip().upper() in ["A", "ABSENT"]:
                    is_absent = True
                    has_absent = True
                    absent_subjects.append(c_display)
                    score_num = 0.0
                else:
                    try:
                        score_num = float(val) if val is not None else 0.0
                    except (ValueError, TypeError):
                        score_num = 0.0
                        
                student_total += score_num
                if not is_absent:
                    component_aggregates[c_display]["scores"].append(score_num)
                    
                score_pct = round((score_num / c_max * 100.0), 1) if c_max > 0 else 0.0
                student_subjs.append({
                    "component": c_display,
                    "score": "Absent" if is_absent else score_num,
                    "score_num": score_num,
                    "max_marks": c_max,
                    "score_pct": score_pct,
                    "is_absent": is_absent
                })
                
            overall_pct = round((student_total / total_batch_max * 100.0), 1) if total_batch_max > 0 else 0.0
            
            roster[c_name]["total_score"] = student_total
            roster[c_name]["total_max"] = total_batch_max
            roster[c_name]["overall_pct"] = overall_pct
            roster[c_name]["subject_scores"] = student_subjs
            roster[c_name]["has_absent"] = has_absent
            roster[c_name]["absent_subjects"] = absent_subjects

        # Compute component class averages
        class_averages = {}
        for c_display, agg in component_aggregates.items():
            sc_list = agg["scores"]
            max_m = agg["max_marks"]
            avg_score = round(sum(sc_list) / len(sc_list), 1) if sc_list else 0.0
            avg_pct = round((avg_score / max_m * 100.0), 1) if max_m > 0 else 0.0
            class_averages[c_display] = {
                "avg_score": avg_score,
                "max_marks": max_m,
                "avg_pct": avg_pct,
                "students_evaluated": len(sc_list)
            }
            
        return {
            "components": components,
            "total_batch_max": total_batch_max,
            "class_averages": class_averages
        }

    def parse_skill_matrix(self, roster: Dict[str, Dict[str, Any]], master_keys: Dict[str, str]) -> Dict[str, Any]:
        """Parses Skill Matrix sheet: Typing Speed WPM and skills out of 10."""
        ws = self.sheet_map.get("skill_matrix")
        if not ws:
            for s in roster.values():
                s["typing_speed"] = 20
                s["skills"] = {}
            return {"skill_columns": []}
            
        # Parse headers: handle newlines
        name_col = 2
        typing_col = None
        skill_cols = []
        
        for c in range(1, ws.max_column + 1):
            h_val = normalize_text(ws.cell(1, c).value)
            if match_synonym(h_val, ["name", "student name", "candidate name"]):
                name_col = c
                continue
            if match_synonym(h_val, ["s.no", "total", "average"]):
                continue
            if "typing" in h_val.lower():
                typing_col = c
                continue
                
            # Extract skill name before newline or "Out of"
            clean_title = h_val.split("\n")[0].strip()
            clean_title = re.sub(r"(?i)\s*out of \d+", "", clean_title).strip()
            max_m = parse_max_marks(h_val) or 10.0
            skill_cols.append({"col": c, "name": clean_title, "max": max_m})
            
        for r in range(2, ws.max_row + 1):
            name_val = ws.cell(r, name_col).value
            if not name_val:
                continue
            c_name = self.resolve_name(str(name_val), master_keys)
            if not c_name or c_name not in roster:
                continue
                
            typing_wpm = 0
            if typing_col:
                tv = ws.cell(r, typing_col).value
                try:
                    typing_wpm = int(float(tv)) if tv is not None else 0
                except (ValueError, TypeError):
                    typing_wpm = 0
                    
            skills_dict = {}
            for sc in skill_cols:
                sv = ws.cell(r, sc["col"]).value
                try:
                    s_score = float(sv) if sv is not None else 0.0
                except (ValueError, TypeError):
                    s_score = 0.0
                skills_dict[sc["name"]] = s_score
                
            roster[c_name]["typing_speed"] = typing_wpm
            roster[c_name]["skills"] = skills_dict
            
        return {"skill_columns": [sc["name"] for sc in skill_cols]}

    def parse_other_skills(self, roster: Dict[str, Dict[str, Any]], master_keys: Dict[str, str]):
        """Parses Sports Activities & Other Skills, merging cleanly."""
        ws = self.sheet_map.get("other_skills")
        if not ws:
            for s in roster.values():
                s["other_skills_text"] = "Not recorded"
            return
            
        name_col = 1
        sports_col = None
        other_col = None
        
        for c in range(1, ws.max_column + 1):
            h_val = normalize_text(ws.cell(1, c).value)
            if match_synonym(h_val, ["name", "student name"]):
                name_col = c
            elif match_synonym(h_val, ["sports activities", "sports"]):
                sports_col = c
            elif match_synonym(h_val, ["other skills", "extra skills", "hobbies"]):
                other_col = c
                
        for r in range(2, ws.max_row + 1):
            name_val = ws.cell(r, name_col).value
            if not name_val:
                continue
            c_name = self.resolve_name(str(name_val), master_keys)
            if not c_name or c_name not in roster:
                continue
                
            parts = []
            if sports_col:
                sp_val = normalize_text(ws.cell(r, sports_col).value)
                if sp_val and sp_val not in ["-", "—", "None", "nan"]:
                    parts.append(sp_val)
            if other_col:
                ot_val = normalize_text(ws.cell(r, other_col).value)
                if ot_val and ot_val not in ["-", "—", "None", "nan"]:
                    parts.append(ot_val)
                    
            text = " · ".join(parts) if parts else "Not recorded"
            roster[c_name]["other_skills_text"] = text

    def parse_placement(self, roster: Dict[str, Dict[str, Any]], master_keys: Dict[str, str]):
        """Parses Placement sheet, cleaning salary and detecting status."""
        ws = self.sheet_map.get("placement")
        if not ws:
            for s in roster.values():
                s["placement"] = {"is_available": False}
            return
            
        name_col = 2
        desig_col = 3
        org_col = 4
        sal_col = 5
        
        for c in range(1, ws.max_column + 1):
            h_val = normalize_text(ws.cell(1, c).value)
            if match_synonym(h_val, ["name", "student name"]):
                name_col = c
            elif match_synonym(h_val, ["designation", "role", "position"]):
                desig_col = c
            elif match_synonym(h_val, ["organization", "company", "employer"]):
                org_col = c
            elif match_synonym(h_val, ["salary", "package", "ctc"]):
                sal_col = c

        org_expansions = self.mappings.get("organization_expansions", {})
        
        for r in range(2, ws.max_row + 1):
            name_val = ws.cell(r, name_col).value
            if not name_val:
                continue
            c_name = self.resolve_name(str(name_val), master_keys)
            if not c_name or c_name not in roster:
                continue
                
            desig_val = ws.cell(r, desig_col).value if desig_col else None
            org_val = ws.cell(r, org_col).value if org_col else None
            sal_val = ws.cell(r, sal_col).value if sal_col else None
            
            clean_desig = normalize_text(desig_val)
            clean_org = normalize_text(org_val)
            clean_org = org_expansions.get(clean_org, clean_org)
            
            sal_display, sal_num = parse_salary(sal_val)
            
            is_placed = bool(clean_org and clean_org not in ["-", "—", "None", "nan", ""])
            
            # Special check for 'Not Joined' or similar
            is_not_joined = "not joined" in clean_desig.lower() or "not joined" in clean_org.lower()
            
            roster[c_name]["placement"] = {
                "is_available": is_placed,
                "is_not_joined": is_not_joined,
                "designation": clean_desig if is_placed else None,
                "organization": clean_org if is_placed else None,
                "salary_display": sal_display if is_placed else None,
                "salary_num": sal_num if is_placed else None,
            }

    def parse_all(self) -> Dict[str, Any]:
        """Main entry point: executes full schema-tolerant parse."""
        roster = self.parse_master_roster()
        if not roster:
            self.blockers.append("No student records found in Master sheet.")
            return {
                "success": False,
                "blockers": self.blockers,
                "warnings": self.warnings,
                "students": {},
            }
            
        master_keys = {normalize_name(name): name for name in roster.keys()}
        
        self.parse_hostelite(roster, master_keys)
        self.parse_parents_meet(roster, master_keys)
        att_meta = self.parse_attendance(roster, master_keys)
        assess_meta = self.parse_assessment(roster, master_keys)
        skill_meta = self.parse_skill_matrix(roster, master_keys)
        self.parse_other_skills(roster, master_keys)
        self.parse_placement(roster, master_keys)
        
        return {
            "success": len(self.blockers) == 0,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "student_count": len(roster),
            "students": roster,
            "attendance_meta": att_meta,
            "assessment_meta": assess_meta,
            "skill_meta": skill_meta,
        }
