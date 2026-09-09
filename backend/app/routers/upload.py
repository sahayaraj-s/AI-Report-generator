from __future__ import annotations
import json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.models import ActivityLog, Institute, Upload
from app.services.pipeline import build_student_records, persist_student_record
from app.services.upload_processing import analyze_sheet

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_EXTENSIONS = (".xlsx", ".xls", ".csv")


@router.post("/preview")
async def preview_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(400, "Only .xlsx, .xls, or .csv files are accepted")

    raw = await file.read()
    try:
        df, meta_columns, skill_columns_meta, warnings, sheets_summary = analyze_sheet(file.filename, raw)
    except Exception as exc:
        raise HTTPException(400, f"Could not read file: {exc}")

    display_cols = [c for c in df.columns if not c.startswith("_")]
    detected_skills = sorted(list({meta["clean_name"] for meta in skill_columns_meta.values()}))

    # Aggregate excluded non-skill columns across sheets
    all_excluded = set()
    for s in sheets_summary:
        all_excluded.update(s.get("excluded_columns", []))

    # Auto-detected batch
    detected_batch = None
    if "batch" in meta_columns and not df.empty:
        sample_batch = str(df[meta_columns["batch"]].iloc[0]).strip()
        if sample_batch and sample_batch.lower() != "nan":
            detected_batch = sample_batch
    if not detected_batch and "_detected_batch" in df:
        detected_batch = str(df["_detected_batch"].iloc[0]).strip()

    upload_row = Upload(
        filename=file.filename,
        mode="preview",
        student_count=len(df),
        detected_columns=json.dumps(display_cols),
        detected_skills=json.dumps(detected_skills),
        status="previewed",
    )
    db.add(upload_row)
    db.commit()
    db.refresh(upload_row)

    return {
        "upload_id": upload_row.id,
        "filename": file.filename,
        "student_count": len(df),
        "detected_columns": display_cols,
        "detected_skills": detected_skills,
        "excluded_columns": sorted(list(all_excluded)),
        "detected_batch": detected_batch,
        "detected_course": "CCDP (Career & Competency Development Program)",
        "sheets_summary": sheets_summary,
        "file_size_kb": round(len(raw) / 1024, 1),
        "warnings": warnings,
    }


@router.post("/process")
async def process_upload(
    file: UploadFile = File(...),
    mode: str = Form(...),  # "live" | "save" | "update"
    course_name: str = Form(default="CCDP (Career & Competency Development Program)"),
    batch_name: str = Form(default="CCDP 1"),
    overwrite: bool = Form(default=False),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    if mode not in ("live", "save", "update"):
        raise HTTPException(400, "mode must be one of: live, save, update")
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(400, "Only .xlsx, .xls, or .csv files are accepted")

    raw = await file.read()
    try:
        df, meta_columns, skill_columns_meta, warnings, sheets_summary = analyze_sheet(file.filename, raw)
    except Exception as exc:
        raise HTTPException(400, f"Could not read file: {exc}")
    if "name" not in meta_columns:
        raise HTTPException(400, "Sheet must have a Name column")

    final_course = course_name.strip() or "CCDP (Career & Competency Development Program)"
    final_batch = batch_name.strip() or "CCDP 1"

    # Load admin-configured scoring weights
    institute = db.query(Institute).first()
    skill_w = (institute.skill_weight_pct or 75.0) / 100.0 if institute else 0.75
    att_w = (institute.attendance_weight_pct or 25.0) / 100.0 if institute else 0.25

    records = await build_student_records(
        df,
        meta_columns,
        skill_columns_meta,
        default_course=final_course,
        default_batch=final_batch,
        skill_weight=skill_w,
        att_weight=att_w,
    )

    detected_skills = sorted(list({meta["clean_name"] for meta in skill_columns_meta.values()}))

    result = {
        "mode": mode,
        "filename": file.filename,
        "student_count": len(records),
        "sheets_summary": sheets_summary,
        "warnings": warnings,
    }

    if mode == "live":
        result["students"] = records
    else:
        saved, skipped = 0, 0
        for record in records:
            _, was_written = persist_student_record(
                db,
                record,
                final_course,
                final_batch,
                overwrite=(mode == "update" and overwrite) or mode == "save",
            )
            if was_written:
                saved += 1
            else:
                skipped += 1

        display_cols = [c for c in df.columns if not c.startswith("_")]
        upload_row = Upload(
            filename=file.filename,
            mode=mode,
            student_count=len(records),
            detected_columns=json.dumps(display_cols),
            detected_skills=json.dumps(detected_skills),
            status="processed",
        )
        db.add(upload_row)
        db.add(ActivityLog(
            action=f"upload:{mode}",
            detail=f"{file.filename} (Batch: {final_batch}) — {saved} saved, {skipped} skipped"
        ))
        db.commit()

        result["saved"] = saved
        result["skipped"] = skipped
        result["batch"] = final_batch

    return result
