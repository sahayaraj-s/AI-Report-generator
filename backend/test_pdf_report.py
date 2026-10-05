"""
test_pdf_report.py - Test generation of CCDP Student Report PDF
Automatically skips if real Excel data file is not present.
"""
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

EXCEL_PATH = os.path.join(os.path.dirname(ROOT), "Students Complete Details - CCDP 2(1).xlsx")

if not os.path.exists(EXCEL_PATH):
    print("SKIPPED: Real Excel file not found (safe behavior in clean repository / CI environment).")
    sys.exit(0)

from loader import load_all_sheets
from metrics import build_full_metrics
from pdf_generator import generate_student_report_pdf

print("Loading data for PDF validation...")
loader_result = load_all_sheets(EXCEL_PATH)
metrics_bundle = build_full_metrics(loader_result)
per_student = metrics_bundle["per_student"]

assert len(per_student) > 0, "No students found in bundle"

# Pick first available record for validation without printing PII
first_key = next(iter(per_student))
sample_rec = per_student[first_key]

pdf_bytes = generate_student_report_pdf(sample_rec, batch_name="CCDP 2")
assert len(pdf_bytes) > 1000, "Generated PDF is too small or empty"
assert pdf_bytes.startswith(b"%PDF"), "Output bytes do not have valid PDF header"
print(f"  [OK] Generated test PDF ({len(pdf_bytes)} bytes) successfully.")

print("\nPDF test complete!")
