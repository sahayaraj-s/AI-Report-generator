"""
data_quality.py - Data Quality Assessment Engine
Validates uploaded batch workbooks, classifies issues into BLOCKERS and WARNINGS,
and ensures data integrity before report generation.
"""

from __future__ import annotations

from typing import Any, Dict, List
import openpyxl

class DataQualityEngine:
    @staticmethod
    def inspect_workbook(parser_result: Dict[str, Any], raw_wb: openpyxl.Workbook | None = None) -> Dict[str, Any]:
        """
        Runs comprehensive data quality checks on the parser output and workbook.
        Returns validation status, blockers, and categorized warnings.
        """
        blockers: List[Dict[str, str]] = []
        warnings: List[Dict[str, str]] = []
        
        # 1. Check parser blockers
        for b in parser_result.get("blockers", []):
            blockers.append({"type": "SCHEMA_BLOCKER", "message": str(b)})
            
        student_count = parser_result.get("student_count", 0)
        if student_count == 0:
            blockers.append({"type": "EMPTY_BATCH", "message": "Batch contains zero valid students."})
            
        assess_meta = parser_result.get("assessment_meta", {})
        components = assess_meta.get("components", [])
        if not components:
            blockers.append({"type": "NO_ASSESSMENT_COMPONENTS", "message": "No valid assessment components found."})
            
        # 2. Check formula differences (e.g. 265 in workbook vs 240 calculated)
        total_batch_max = assess_meta.get("total_batch_max", 0.0)
        if raw_wb and "Assessment" in raw_wb.sheetnames:
            ws = raw_wb["Assessment"]
            # Look for trailing Total column
            for c in range(1, ws.max_column + 1):
                h1 = str(ws.cell(1, c).value or "").strip().lower()
                h2 = str(ws.cell(2, c).value or "").strip()
                if "total" in h1:
                    import re
                    m = re.search(r"(\d+)", h2)
                    if m:
                        sheet_total_max = float(m.group(1))
                        if sheet_total_max != total_batch_max:
                            warnings.append({
                                "type": "FORMULA_DIFFERENCE",
                                "message": f"Workbook Assessment sheet has header '{h2}' for Total, but sum of components is {total_batch_max}. Dynamically using accurate sum ({total_batch_max})."
                            })
                    break

        # 3. Check for student absents
        students = parser_result.get("students", {})
        absent_count = 0
        for name, data in students.items():
            if data.get("has_absent"):
                absent_count += 1
                subjs = ", ".join(data.get("absent_subjects", []))
                warnings.append({
                    "type": "STUDENT_ABSENT",
                    "student": name,
                    "message": f"Student '{name}' marked Absent for {subjs}. Scored 0 marks; excluded from component class average."
                })

        # 4. Check parser warnings (aliased names, etc.)
        for w in parser_result.get("warnings", []):
            warnings.append({"type": "GENERAL_WARNING", "message": str(w)})

        # 5. Check unplaced count
        unplaced = [name for name, d in students.items() if not d.get("placement", {}).get("is_available")]
        if unplaced:
            warnings.append({
                "type": "UNPLACED_STUDENTS",
                "message": f"{len(unplaced)} students have no placement record recorded (e.g. {', '.join(unplaced[:3])})."
            })

        return {
            "is_valid": len(blockers) == 0,
            "blockers": blockers,
            "warnings": warnings,
            "student_count": student_count,
            "components_count": len(components),
            "total_max_marks": total_batch_max,
        }
