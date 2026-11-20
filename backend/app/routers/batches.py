"""
batches.py - Batch Management, Upload, Data-Quality & Bulk Export Router
========================================================================
Supports generic multi-batch uploads, data-quality inspection, alias management,
bulk student report ZIP streaming, and batch summary PDF generation.
"""

from __future__ import annotations

import io
import os
import zipfile
from typing import Any, Dict, List, Optional
import yaml

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_optional_admin
from app.database import get_db
from app.models import Batch, Institute, Student, StudentScore
from app.services.data_quality import DataQualityEngine
from workbook_parser import BatchWorkbookParser, CONFIG_DIR
from metrics import build_full_metrics
from pdf_reportlab_engine import generate_student_reportlab_pdf

router = APIRouter(prefix="/api/batches", tags=["batches"])

# In-memory storage for recently parsed batches
_PARSED_BATCHES: Dict[str, Dict[str, Any]] = {}

def get_parsed_batch(batch_id: str) -> Dict[str, Any]:
    if batch_id in _PARSED_BATCHES:
        return _PARSED_BATCHES[batch_id]
    # Check if primary CCDP 2 fixture can be loaded as default batch "1"
    fixture_path = "Students Complete Details - CCDP 2(1).xlsx"
    if not os.path.exists(fixture_path):
        fixture_path = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures", "ccdp_batch_2.xlsx")
    if os.path.exists(fixture_path):
        parser = BatchWorkbookParser(fixture_path)
        parsed = parser.parse_all()
        metrics = build_full_metrics(parsed)
        dq = DataQualityEngine.inspect_workbook(parsed, parser.wb)
        batch_bundle = {
            "batch_id": "1",
            "batch_name": "CCDP 2",
            "parsed": parsed,
            "metrics": metrics,
            "dq": dq,
        }
        _PARSED_BATCHES["1"] = batch_bundle
        _PARSED_BATCHES["default"] = batch_bundle
        return batch_bundle
    raise HTTPException(404, f"Batch '{batch_id}' not found.")

@router.post("/upload")
async def upload_batch(
    file: UploadFile = File(...),
    batch_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(get_optional_admin),
):
    """
    Accepts any batch Excel workbook (.xlsx), detects schema, validates data quality,
    computes full metrics, and caches batch in memory.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only Excel files (.xlsx, .xls) are supported.")
        
    contents = await file.read()
    b_name = batch_name or os.path.splitext(file.filename)[0]
    
    try:
        parser = BatchWorkbookParser(io.BytesIO(contents), filename=file.filename)
        parsed = parser.parse_all()
        metrics = build_full_metrics(parsed)
        dq = DataQualityEngine.inspect_workbook(parsed, parser.wb)
    except Exception as e:
        raise HTTPException(422, f"Failed to parse workbook: {str(e)}")
        
    batch_id = str(len(_PARSED_BATCHES) + 1)
    batch_bundle = {
        "batch_id": batch_id,
        "batch_name": b_name,
        "filename": file.filename,
        "parsed": parsed,
        "metrics": metrics,
        "dq": dq,
    }
    _PARSED_BATCHES[batch_id] = batch_bundle
    _PARSED_BATCHES["default"] = batch_bundle
    
    return {
        "success": dq["is_valid"],
        "batch_id": batch_id,
        "batch_name": b_name,
        "student_count": metrics["student_count"],
        "total_max_marks": metrics["total_batch_max"],
        "class_avg_overall_pct": metrics["class_avg_overall_pct"],
        "data_quality": dq,
    }

@router.get("/{batch_id}/data-quality")
def get_batch_data_quality(batch_id: str):
    """Returns data quality report (blockers and warnings) for a batch."""
    b = get_parsed_batch(batch_id)
    return b["dq"]

@router.post("/{batch_id}/aliases")
async def save_batch_aliases(
    batch_id: str,
    payload: Dict[str, str],
    admin=Depends(get_optional_admin),
):
    """
    Allows user/admin to save cross-sheet name aliases dynamically.
    Updates config/name_aliases.yaml.
    """
    aliases_file = os.path.join(CONFIG_DIR, "name_aliases.yaml")
    existing_aliases = {}
    if os.path.exists(aliases_file):
        with open(aliases_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            existing_aliases = data.get("aliases", {})
            
    for k, v in payload.items():
        clean_k = str(k).strip().lower().replace(".", "")
        clean_v = str(v).strip().lower().replace(".", "")
        existing_aliases[clean_k] = clean_v
        
    with open(aliases_file, "w", encoding="utf-8") as f:
        yaml.dump({"aliases": existing_aliases}, f, default_flow_style=False)
        
    return {"success": True, "total_aliases": len(existing_aliases)}

@router.get("/{batch_id}/students")
def get_batch_students(batch_id: str):
    """Returns all students in the batch with their key summary metrics."""
    b = get_parsed_batch(batch_id)
    students_list = []
    for cn, s in b["metrics"]["per_student"].items():
        p = s.get("placement") or {}
        students_list.append({
            "name": s["display_name"],
            "enrolment_no": s.get("enrolment_no", ""),
            "class_rank": s["class_rank"],
            "is_top_performer": s["is_top_performer"],
            "total_score": s["total_score"],
            "total_max": s["total_max"],
            "overall_pct": s["overall_pct"],
            "attendance_pct": s["attendance_pct"],
            "typing_wpm": s.get("typing_wpm", 0),
            "is_placed": p.get("is_available", False),
            "designation": p.get("designation"),
            "organization": p.get("organization"),
            "salary": p.get("salary_display"),
            "cohort_rank": p.get("cohort_rank"),
        })
    students_list.sort(key=lambda x: x["class_rank"])
    return {"students": students_list, "total": len(students_list)}

@router.get("/{batch_id}/reports.zip")
def download_all_reports_zip(batch_id: str):
    """Generates all student reports as PDFs and streams them in a ZIP archive."""
    b = get_parsed_batch(batch_id)
    per_student = b["metrics"]["per_student"]
    batch_name = b["batch_name"]
    batch_metrics = b["metrics"]
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for cn, s_rec in per_student.items():
            pdf_bytes = generate_student_reportlab_pdf(s_rec, batch_name=batch_name, batch_metrics=batch_metrics)
            safe_name = str(s_rec.get("display_name", "Student")).replace(" ", "_")
            zip_file.writestr(f"{safe_name}_Dashboard_Report.pdf", pdf_bytes)
            
    zip_buffer.seek(0)
    filename = f"{batch_name.replace(' ', '_')}_All_Reports.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/{batch_id}/summary.pdf")
def download_batch_summary_pdf(batch_id: str):
    """Generates a high-quality Batch Summary PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    b = get_parsed_batch(batch_id)
    metrics = b["metrics"]
    batch_name = b["batch_name"]
    per_student = metrics["per_student"]
    batch_stats = metrics.get("batch_stats", {})
    
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=42.5,
        rightMargin=42.5,
        topMargin=42.5,
        bottomMargin=42.5,
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("BTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, textColor=colors.HexColor("#6B3591"), alignment=0)
    sub_style = ParagraphStyle("BSub", fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#5F6368"))
    h2_style = ParagraphStyle("BH2", fontName="Helvetica-Bold", fontSize=12, textColor=colors.HexColor("#6B3591"))
    body_style = ParagraphStyle("BBody", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#202124"))
    bold_style = ParagraphStyle("BBold", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#202124"))
    
    story = []
    story.append(Paragraph(f"Skill Bay Academy — Batch Summary Report", title_style))
    story.append(Paragraph(f"Comprehensive Career Development Programme (CCDP) · {batch_name}", sub_style))
    story.append(Spacer(1, 12))
    
    # Overview Table
    overview_data = [
        [Paragraph("Metric", bold_style), Paragraph("Value", bold_style)],
        [Paragraph("Total Students", body_style), Paragraph(str(metrics["student_count"]), bold_style)],
        [Paragraph("Total Assessment Marks", body_style), Paragraph(f"{metrics['total_batch_max']:g}", bold_style)],
        [Paragraph("Class Average %", body_style), Paragraph(f"{metrics['class_avg_overall_pct']:.1f}%", bold_style)],
        [Paragraph("Cohort Median Score", body_style), Paragraph(f"{batch_stats.get('median_score', 0):g}", body_style)],
        [Paragraph("Typing Speed Average", body_style), Paragraph(f"{metrics.get('typing_stats', {}).get('avg', 0)} WPM", body_style)],
        [Paragraph("Typing Speed Range", body_style), Paragraph(f"{metrics.get('typing_stats', {}).get('min', 0)} - {metrics.get('typing_stats', {}).get('max', 0)} WPM", body_style)],
    ]
    t_over = Table(overview_data, colWidths=[250, 260])
    t_over.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FAF7FC")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ECE3F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_over)
    story.append(Spacer(1, 14))
    
    # Top Performers Table
    story.append(Paragraph("<b>TOP PERFORMERS (COHORT RANK 1 - 5)</b>", h2_style))
    story.append(Spacer(1, 6))
    toppers = sorted(per_student.values(), key=lambda s: s["class_rank"])[:5]
    top_data = [
        [Paragraph("Rank", bold_style), Paragraph("Student Name", bold_style), Paragraph("Total Score", bold_style), Paragraph("Overall %", bold_style), Paragraph("Placement", bold_style)]
    ]
    for s in toppers:
        p = s.get("placement") or {}
        p_str = f"{p.get('designation', '')} @ {p.get('organization', '')}" if p.get("is_available") else "Unplaced"
        top_data.append([
            Paragraph(f"#{s['class_rank']}", bold_style),
            Paragraph(s["display_name"], bold_style),
            Paragraph(f"{s['total_score']:g} / {s['total_max']:g}", body_style),
            Paragraph(f"{s['overall_pct']:.1f}%", bold_style),
            Paragraph(p_str, body_style),
        ])
    t_top = Table(top_data, colWidths=[50, 150, 90, 70, 150])
    t_top.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6B3591")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ECE3F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_top)
    story.append(Spacer(1, 14))
    
    # Component Breakdown
    story.append(Paragraph("<b>SUBJECT-WISE ASSESSMENT BREAKDOWN</b>", h2_style))
    story.append(Spacer(1, 6))
    comp_data = [
        [Paragraph("Component", bold_style), Paragraph("Max Marks", bold_style), Paragraph("Class Avg Score", bold_style), Paragraph("Class Avg %", bold_style)]
    ]
    class_avg_subjs = metrics.get("class_avg_pct_per_subject", {})
    max_marks = metrics.get("max_marks", {})
    for comp, pct in class_avg_subjs.items():
        mx = max_marks.get(comp, 0.0)
        sc = round(pct * mx / 100.0, 1) if mx > 0 else 0.0
        comp_data.append([
            Paragraph(comp, body_style),
            Paragraph(f"{mx:g}", body_style),
            Paragraph(f"{sc:g}", body_style),
            Paragraph(f"{pct:.1f}%", bold_style),
        ])
    t_comp = Table(comp_data, colWidths=[200, 100, 100, 110])
    t_comp.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6B3591")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ECE3F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_comp)
    
    doc.build(story)
    buf.seek(0)
    filename = f"{batch_name.replace(' ', '_')}_Summary_Report.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
