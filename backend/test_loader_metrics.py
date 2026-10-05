r"""
Test script: validates loader.py + metrics.py against the CCDP 2 sample file.
Automatically skips if real Excel file is not present.
"""
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

EXCEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Students Complete Details - CCDP 2(1).xlsx"
)

if not os.path.exists(EXCEL_PATH):
    print("SKIPPED: Real Excel file not found (safe behavior in clean repository / CI environment).")
    sys.exit(0)

from loader import load_all_sheets, validate_students
from metrics import build_full_metrics

print(f"Loading Excel file...")
loader_result = load_all_sheets(EXCEL_PATH, os.path.basename(EXCEL_PATH))
print(f"DQ Warnings count: {len(loader_result['dq_warnings'])}")

validate_students(loader_result["students"], expected_count=30, dq_warnings=loader_result["dq_warnings"])

metrics = build_full_metrics(loader_result)
per_student = metrics["per_student"]

assert metrics['student_count'] > 0, "Student count must be positive"
assert metrics['class_avg_overall_pct'] > 0, "Class avg must be positive"
assert len(loader_result['max_marks']) > 0, "Max marks must be populated"

print(f"\n[OK] Validation passed: {metrics['student_count']} students loaded with full metrics.")
