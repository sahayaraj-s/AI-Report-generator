# DIAGNOSIS: Root Cause Analysis of Inconsistencies and Failures

**Target System:** `ai-placement-dashboard` (Skill Bay Academy / Kauvery Hospital CCDP)  
**Date of Diagnosis:** 2026-10-05  
**Diagnosis Status:** Phase 0 Completed with File + Line Evidence

---

## 1. Executive Summary

Empirical inspection of the backend code, SQLite database (`placement.db`), runtime logs, and the Gemini API confirms that the observed discrepancies across the application stem from **architectural fragmentation, silent exception swallowing, lack of column schema classification, un-consolidated multi-sheet ingestion, and hardcoded synthetic fallbacks**:

| Area | Observed Symptom | Primary Root Cause |
|---|---|---|
| **AI Status & Responses** | Chat outputs identical batch summary for "hi", "low", "30th", etc.; badge says Gemini | Retired `gemini-1.5-flash` model returns HTTP 404; silent try/except swallows errors; fallback to naive keyword matcher that defaults to `batch_summary`. |
| **Score & Tier Discrepancy** | Dashboard shows 24/100 avg, Tier 4 (100%), 0 qualified; Chat shows ~71% avg, 27 placed | Dashboard queries DB populated with uniform sizes as skills at 0%; Chat bypasses DB and reads Excel via `metrics.py`. |
| **Attendance Discrepancy** | Dashboard shows 75% for all students; Chat shows ~96% | `pipeline.py` silently defaulted missing attendance to `75.0`; `metrics.py` parses actual P/A days. |
| **Upload Live Preview** | 254-256 candidates detected with 8.6/100 avg; Ingestion history counts 224/226/254/256/30 | `upload_processing.py` concatenates rows from all sheets without consolidating students; `upload.py` writes to DB on preview. |
| **Radar & Remediation** | Shirt, Trouser, Tie, Shoe Size, Total, Uniform at 0% | No column classification; numeric/coerced values treated as skill scores. |
| **Fake Charts** | Trajectory curve and AI Conf % appear synthetic | Hardcoded synthetic calculations in `app/routers/dashboard.py`. |

---

## 2. Detailed Root Cause Analysis with File + Line Evidence

### (a) Model ID, Gemini Returns, and Silent Swallowed Fallbacks
- **Configured Model**: `backend/app/config.py` line 16 defines `gemini_model: str = "gemini-1.5-flash"`. `backend/.env.example` line 27 also specifies `GEMINI_MODEL=gemini-1.5-flash`.
- **API Call & Error**: The live Gemini API was invoked with the configured environment key against `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent`.
  - **HTTP Status Returned**: `404 Not Found`.
  - **API Error Message**: `"models/gemini-1.5-flash is not found for API version v1beta, or is not supported for generateContent. Call ModelService.ListModels to see the list of available models and their supported methods."`
- **Key Prefix Gate**: In `backend/app/services/ai_service.py` (lines 129, 154) and `backend/app/services/chat_service.py` (line 340), code checked `if not api_key.startswith("AIza"): return None`. Modern AI Studio / GCP keys with other prefixes (e.g. `AQ...`) were immediately bypassed without ever contacting the API.
- **Silent Exception Swallowing**:
  - `backend/app/services/ai_service.py` lines 143–144:
    ```python
    except Exception:
        return generate_local_report(student_name, overall, strengths, weaknesses, top_roles)
    ```
  - `backend/app/services/chat_service.py` lines 380–382 & 404–409:
    ```python
    except Exception as exc:
        log.warning(f"Gemini grounded chat error: {exc}")
    return None
    ...
    llm_resp = await _gemini_grounded_chat(context_slice, user_message)
    if llm_resp:
        return llm_resp
    return answer_from_slice(user_message, context_slice)
    ```
- **False UI Status Badge**: In `frontend/src/pages/SkillBayAI.jsx` lines 257, 301, 316, the UI merely checked `settingsData?.gemini_api_key_configured`. Because an API key was present in `.env`, the UI unconditionally rendered `"Gemini AI"` and `gemini-1.5-flash`, hiding the fact that 404 errors forced every turn into local answering.
- **Local Keyword Failure**: In `backend/app/services/chat_service.py` lines 79–220 (`retrieve_grounded_slice`), inputs such as "hi", "low", "medium score students", "top 20", "30th", "10 rank" do not match specific student names, placement keywords, or subject keywords. They fall through to case 4 (lines 207–220), returning `query_type: "batch_summary"`. `answer_from_slice` (lines 322–331) then prints the identical static CCDP 2 batch summary text.
- **Available Models**: Querying `ModelService.ListModels` for the configured key confirmed active models supporting `generateContent`: `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-pro`.

---

### (b) Divergent Code Paths for Scores, Attendance, Readiness, and Tiers

There are **three separate, conflicting computation engines** in the repository:

#### Path 1: Dashboard Engine (`backend/app/routers/dashboard.py`)
- Reads persisted database rows from `students` and `student_scores`.
- `avg_score` computed at line 52: `q.with_entities(func.avg(Student.overall_score)).scalar()`.
- Result on active database: **24.04/100 average**, **100% in Tier 4 (<40%)**, **0 of 30 placement ready**.
- `attendance_pct` in DB is **75.0%** for all 30 students.
- `competency_radar` and `weak_skill_heatmap` (lines 108–141) query all rows in `student_scores`, where "Shirt", "Trouser", "Tie", "Shoe Size", "Total", "Uniform For Male" were saved with score `0.0`.

#### Path 2: Chat Service Engine (`backend/app/services/chat_service.py` + `backend/metrics.py`)
- In `backend/app/services/chat_service.py` lines 35–54, `get_live_metrics_data()` completely ignores the database and calls `loader.load_all_sheets()` directly on the disk Excel file, followed by `metrics.build_full_metrics()`.
- In `backend/metrics.py` lines 19–86:
  - Considers only columns in `assessment_scores`.
  - Calculates assessment average: `class_avg_overall_pct = 71.1%`.
  - Parses P/A attendance cells from attendance sheet: average **96.2%**.
  - Counts placements from placement sheet: **27 of 30 placed**.

#### Path 3: Upload Preview & Process Engine (`backend/app/services/upload_processing.py` + `backend/app/services/pipeline.py`)
- In `backend/app/services/upload_processing.py` line 383:
  - Concatenates every sheet having a "Name" column into one flat dataframe:
    `combined_df = pd.concat([item[0] for item in processed_dfs], ignore_index=True)`
  - Treats each sheet's 30 rows as distinct candidates (total 254–256 rows).
  - Normalizes scores across all columns: because each sheet only has 1 or 2 metrics, remaining columns are 0, plunging the overall score to **8.6/100** and individual candidate scores to **~1.5%**.

---

### (c) Column Classification Flaw & Leakage of Non-Skills

In `backend/app/services/upload_processing.py`:
- Lines 51–89 define `NON_SKILL_PATTERNS`.
- The regex list **omits** clothing, uniform, and sizing words:
  - "Shirt", "Trouser", "Tie", "Shoe Size", "Uniform For Male", "Socks" are NOT in `NON_SKILL_PATTERNS`.
  - "Total" is not matched because the regex only checks `r"total[\s_]?marks?"`.
  - "Typing Speed" is NOT excluded.
- Lines 325–330 coerce column values to numeric with `pd.to_numeric(df[col], errors="coerce")`.
- Numbers such as trouser size `32`, shoe size `6`, or typing speed `25` succeed.
- Text values like `"S"`, `"M"`, `"L"` coerce to `NaN` / `0.0`.
- In lines 340–346, `extract_skill_meta(col)` cleans the name and classifies them as skills.
- When saved in `backend/app/services/pipeline.py` (lines 40–51), these non-skills are inserted into `student_scores` with 0% or low scores, dragging down the overall skill average to ~10–18%.

---

### (d) Why Preview Counts 256 Rows While Consolidated Save Produces ~30

- In `backend/app/services/upload_processing.py` lines 361–370:
  ```python
  if "name" in meta_columns:
      processed_dfs.append((df, meta_columns, sheet_skills))
  ```
  And line 383:
  ```python
  combined_df = pd.concat([item[0] for item in processed_dfs], ignore_index=True)
  ```
  The Excel workbook has multiple tabs ("CCDP 2 Details", "Skill Matrix", "Attendance", "Assessment", "Placement", "Uniform"). Each tab lists the same 30 students.
- `analyze_sheet` does NOT group by student name or reconcile identity; it stacks every row from all 6 tabs, creating $30 \times 6 \approx 254-256$ rows.
- Furthermore, `backend/app/routers/upload.py` lines 68–78:
  ```python
  upload_row = Upload(
      filename=file.filename,
      mode="preview",
      student_count=len(df),
      ...
  )
  db.add(upload_row)
  db.commit()
  ```
  Calling `/api/upload/preview` actively inserts an entry into the `uploads` table, causing ingestion history to record duplicate runs with counts of 254/256/30.

---

### (e) Origin of the 75% Attendance Default and Synthetic Trajectory Curve

1. **75% Attendance Default**:
   - `backend/app/services/pipeline.py` line 56:
     ```python
     attendance_pct = float(attendance_raw) if attendance_raw is not None else 75.0
     ```
   - `backend/app/services/pipeline.py` line 60:
     ```python
     except (TypeError, ValueError):
         attendance_pct = 75.0
     ```
   - In single-sheet imports where an explicit attendance percentage column was missing or unmapped, attendance was silently hardcoded to `75.0%`.
2. **Synthetic Trajectory Curve**:
   - `backend/app/routers/dashboard.py` lines 193–200:
     ```python
     if len(monthly_progress) <= 1 and total_students > 0:
         monthly_progress = [
             {"month": "Day 1 (Intake)", "average_score": round(max(30.0, avg_score - 28.0), 1), "analyzed_count": total_students},
             {"month": "Day 15 (Mid 1)", "average_score": round(max(42.0, avg_score - 18.0), 1), "analyzed_count": total_students},
             {"month": "Day 30 (Mid 2)", "average_score": round(max(55.0, avg_score - 8.0), 1), "analyzed_count": total_students},
             {"month": "Day 50 (Current)", "average_score": round(avg_score, 1), "analyzed_count": total_students},
         ]
     ```
   - This trajectory was completely fabricated from `avg_score - 28.0`, `-18.0`, `-8.0`.
3. **Synthetic AI Confidence**:
   - `backend/app/routers/dashboard.py` lines 246–256 calculate `ai_accuracy_pct` based on whether the first recommended role had `confidence >= 60`, which was hardcoded in `pipeline.py` / `import_ccdp2.py`.

---

## 3. Plan Validation and Adjustments

The initial hypotheses in the prompt are **100% verified by codebase evidence**.
- **Execution Strategy Confirmed**:
  - `PART A`: Establish `app/services/analytics.py` as the single computation kernel; unify column classification (`column_classifier.py`); unify roster consolidation (`consolidator.py`); pull attendance strictly from P/A cells (N/A when absent); link all thresholds to `Institute` settings.
  - `TASK 2`: Fix Cohort Placement Readiness gauge using unified analytics; handle loading, empty, and true 0% states.
  - `TASK 4`: Consolidate multi-sheet uploads in preview and save paths identically; make preview session-only with zero DB writes; add column classifier review and overrides; provide ReportLab PDF + HTML/PNG report generation with fallback.
  - `TASK 1`: Upgrade LLM pipeline using the official `google-genai` SDK with auto-discovery via `models.list`, automatic fallback, honest status reporting (`gemini`, `degraded`, `offline`), and tool calling over keyword routing.
  - `TASK 5`: Unify `SkillBay AI` page and `MiniChatbot` with shared React hooks, styled Markdown, real multipart file uploads, and conversation persistence.
  - `TASK 3`: Overhaul Power BI Dashboard with interactive cross-filtering, real weekly attendance, true radar skills, and zero fabricated series.
