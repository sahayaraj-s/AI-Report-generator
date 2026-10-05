import pytest
import pandas as pd
from app.services.column_classifier import classify_column, extract_skill_scale

def test_clothing_and_compliance_classification():
    compliance_cols = [
        "Shirt", "Trouser", "Tie", "Shoe Size", "Socks", "Uniform",
        "Uniform For Male", "Uniform Size", "Pant Size"
    ]
    for col in compliance_cols:
        cls = classify_column(col)
        assert cls == "compliance", f"Expected '{col}' to be compliance, got '{cls}'"

def test_metric_classification():
    metric_cols = ["Typing Speed", "Typing WPM", "Net WPM", "Gross WPM"]
    for col in metric_cols:
        cls = classify_column(col)
        assert cls == "metric", f"Expected '{col}' to be metric, got '{cls}'"

def test_derived_classification():
    derived_cols = ["Total", "Grand Total", "Sum", "Marks Total"]
    for col in derived_cols:
        cls = classify_column(col)
        assert cls == "derived", f"Expected '{col}' to be derived, got '{cls}'"

def test_pii_and_admin_classification():
    pii_cols = [
        "S.No", "Roll Number", "Student Name", "Father Name", "Phone",
        "Mobile Number", "Email ID", "Address", "DOB", "Aadhaar",
        "Batch", "Course", "Date of Birth", "Contact Number"
    ]
    for col in pii_cols:
        cls = classify_column(col)
        assert cls == "administrative/PII", f"Expected '{col}' to be administrative/PII, got '{cls}'"

def test_genuine_skills_classification():
    skill_cols = [
        "Basic English", "MS Word", "MS Excel", "Hospital Administration",
        "Healthcare Operations", "Communication Skills", "Analytical Skills",
        "Problem Solving", "Leadership Skills", "Soft Skills", "Clinical Terminology"
    ]
    for col in skill_cols:
        cls = classify_column(col)
        assert cls == "skill", f"Expected '{col}' to be skill, got '{cls}'"

def test_numeric_marks_not_confused_with_uniform_sizes():
    # If a subject column has student marks in the 36-44 range (e.g. out of 50),
    # it must NOT be classified as compliance.
    marks_series = pd.Series([38, 40, 42, 36, 44, 39, 41])
    cls = classify_column("Healthcare Operations", marks_series)
    assert cls == "skill"
