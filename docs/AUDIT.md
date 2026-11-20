# System Audit: AI Placement Dashboard & Report Generator

**Date:** 2026-11-20  
**Project:** Skill Bay Academy — AI Placement Analytics & Report Generation  
**Goal:** Transition codebase from batch-specific (CCDP 2) implementation into a 100% generic, schema-driven, publication-grade multi-batch report generator with zero hardcoded constraints and strict data privacy.

---

## 1. Executive Summary & Codebase Map

| Component / Subsystem | Primary Files | Current Role & Status |
| :--- | :--- | :--- |
| **Ingestion & Parsing** | `backend/loader.py`, `backend/schema_detector.py`, `backend/upload_processing.py` | Extracts sheet data. Currently expects hardcoded CCDP 2 sheet names and assumptions (e.g. 265 total marks). Needs replacement with schema-driven `openpyxl(data_only=True)` generic parser. |
| **Scoring & Analytics** | `backend/metrics.py`, `backend/app/services/scoring.py`, `backend/app/services/analytics.py` | Computes percentiles, totals, attendance percentages, and class averages. Contains hardcoded total marks (265.0), fallback averages (71.1%), and fixed 51 attendance days. |
| **PDF Generation (HTML/Chromium)** | `backend/pdf_generator.py` | Playwright Chromium engine producing 3-page A4 PDF. Has layout overlaps, hardcoded student exceptions (`Jayasree A`), hardcoded 265 max marks, and placeholder leaks (`—`, `None`). |
| **PDF Generation (ReportLab)** | `backend/pdf_reportlab_engine.py` | Pure Python zero-dependency headless fallback engine matching the 3-page Canva layout on environments where Chromium is unavailable. |
| **AI Insights & LLM** | `backend/app/services/ai_service.py`, `backend/app/services/chat_service.py`, `backend/app/services/llm_manager.py` | Multi-provider Gemini RAG & prompt engine. Updated to active production models (`gemini-2.5-flash`, `gemini-2.0-flash`). Requires grounding validation to reject hallucinated numbers. |
| **API Routers** | `backend/app/routers/` (`reports.py`, `students.py`, `admin.py`, `upload.py`) | FastAPI endpoints for student metrics, chat, and PDF streaming. Fixed `Missing bearer token` bug via `get_optional_admin`. Needs batch management endpoints. |

---

## 2. Hardcoded Values & Batch-Specific Leakage Inventory

An exhaustive codebase scan identified hardcoded values that break multi-batch compatibility:

### A. Total Max Marks: `265.0`
- **Actual Batch Reality:** In the CCDP 2 `Assessment` sheet, components sum to `240.0` max marks (Role Play: 20, Basic Computer: 50, Word Theory: 25, Word Practical: 25, English: 25, Excel Theory: 25, Excel Practical: 25, Business Writing: 20, Hospital Admin: 25). The sheet's trailing Total column said 265 due to an outdated manual formula.
- **Hardcoded Occurrences:**
  - `backend/app/routers/reports.py:138, 1071`: `"total_max": 265.0`
  - `backend/loader.py:250, 596`: `total_max = info.get("total_max") or 265.0`
  - `backend/metrics.py:19, 40, 202`: `total_max_benchmark: float = 265.0`
  - `backend/pdf_generator.py:494`: `total_max = float(student_rec.get("total_max") or 265.0)`
  - `backend/schema_detector.py:500`: `total_max_detected = 265.0`
- **Fix:** Replace all occurrences with dynamic `total_max = sum(component_max_marks)` computed directly from Row 2 ("Out of N") of the Assessment sheet.

### B. Fallback Class Average: `71.1%`
- **Hardcoded Occurrences:**
  - `backend/app/routers/reports.py:149, 1082`: `"class_avg_overall_pct": bundle.get("class_avg_overall_pct", 71.1)`
  - `backend/app/services/chat_service.py:101, 165, 265, 303`: Fallback `71.1`
  - `backend/pdf_generator.py:502, 503`: `class_avg_overall_pct = ... or 71.1`
  - `backend/pdf_reportlab_engine.py:412`: `tot_avg = ... or 71.1`
- **Fix:** Dynamically compute mean of student overall percentages across all students in the batch. For CCDP 2, true average is `188.45 / 240 = 78.5%`.

### C. Total Attendance Days: `51`
- **Hardcoded Occurrences:**
  - `backend/app/routers/reports.py:141, 142, 1074, 1075`: `"total_trackable_days": 51`, `"present_days": int(att * 51 / 100)`
  - `backend/pdf_generator.py:499`: `total_days = ... or 51`
- **Fix:** Calculate trackable days per student dynamically as `count(P) + count(A)`. Days marked `-` (not applicable/late joiner) are excluded from the denominator.

### D. Cohort Size: `30`
- **Hardcoded Occurrences:**
  - `backend/app/routers/reports.py:136, 1064`: `"class_size": 30`
  - `backend/loader.py:59`: `expected_count: 30`
  - `backend/app/services/chat_service.py`: "Unplaced Students (X of 30 in CCDP 2)"
- **Fix:** Dynamically evaluate `len(batch.students)`.

### E. Hardcoded Student Logic & Placeholder Leaks
- **Student Name Special-Casing:**
  - `backend/pdf_generator.py:687-697`: Explicit check `if name == "Jayasree A": ...` providing custom sentence while giving a generic string to other students.
- **Placeholder String Leaks (`—`, `None`, `nan`):**
  - `backend/pdf_generator.py:695`: `"starting package of {placement.salary_display}"` outputs `"starting package of —"` or `"starting package of None"` when salary is unrecorded.
  - `backend/app/routers/reports.py:125-132`: Missing fields default to `" — "` instead of being handled gracefully.
- **Fix:** Generic summary generators, strict data sanitization, and suppression of missing placement sections.

---

## 3. Privacy & PII Protection Rules

The following fields must **never** be printed, logged, or exposed in generated PDFs, public UI, or non-admin API responses:
- Student mobile phone numbers (`Personal No.`)
- Parents' phone numbers (`Parents No.`)
- Student email addresses (`Email id`)
- Full street / postal addresses (`Present Address`, `Permanent Address`)
- Parents' names and occupations (`Father name`, `Mother name`, `Father's Occupation`, `Mother's Occupation`)
- Date of Birth (`DOB`) — only calculate and show `Age` (if configured in `batch.yaml`)

**Permitted Public Fields:**
- Name, Enrolment No.
- Qualification, College Name
- Home District (`District 2` if present, else `District`)
- Hostelite / Day Scholar status
- Academic, Attendance, and Placement metrics

---

## 4. Current Test Suite Analysis

- `backend/tests/test_analytics_consistency.py`: Tests 30-student synthetic fixture consistency.
- `backend/tests/test_consolidation_and_upload.py`: Tests consolidated upload endpoint.
- `backend/tests/test_readiness_edge_cases.py`: Tests score edge cases.
- **Gaps:**
  - No automated tests for the 6 Section 9 QA Gates (Layout, Chart Overlaps, Pixel Balance, Text Leaks, Number Accuracy, Synthetic Batch Variance).
  - No schema-detector tolerance test for batches with different component counts or optional sheets.

---

## 5. Implementation Roadmap

1. **Phase 1: Config Architecture (`config/`)**
   - Create `config/schema.yaml`, `config/mappings.yaml`, `config/name_aliases.yaml`, `config/batch.yaml`, `config/roles.yaml`, `config/actions.yaml`.
2. **Phase 2: Generic Tolerant Workbook Parser (`backend/workbook_parser.py`)**
   - Pure `openpyxl(data_only=True)` parser with fuzzy sheet resolution, 2-row header handling, robust name normalization, and PII exclusion.
3. **Phase 3: Statistics & Calculations Engine (`backend/metrics.py`)**
   - Decimal precision (`ROUND_HALF_UP`), competition ranking with ties (1, 2, 2, 4), dynamic batch aggregates.
4. **Phase 4: PDF Generation Unification (`backend/pdf_generator.py` & `backend/pdf_reportlab_engine.py`)**
   - Strict content box alignment (15mm margins), square aspect ratios for charts, zero text overlap, balanced 3-page layout.
5. **Phase 5: Batch Operations & API Endpoints**
   - Bulk ZIP report generation and Batch Summary PDF generation.
6. **Phase 6: QA Gates Verification (`backend/qa_gates.py`)**
   - Regression validation against CCDP 2 primary fixture and synthetic 22-student fixture.
