from __future__ import annotations
# pyrefly: ignore-errors
import io
import json
import csv
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.models import AnalysisResult, Batch, Course, JobRoleModel, Skill, Student, StudentScore

router = APIRouter(prefix="/api/reports", tags=["reports"])

BRAND_PRIMARY = colors.HexColor("#8B1D55")
BRAND_PURPLE = colors.HexColor("#72398C")
BRAND_PINK = colors.HexColor("#DE4F73")
BRAND_YELLOW = colors.HexColor("#EFBC19")
BRAND_GREEN = colors.HexColor("#16A34A")
BRAND_BLUE = colors.HexColor("#2563EB")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], textColor=BRAND_PRIMARY, fontSize=16)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=BRAND_PURPLE, fontSize=11)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], textColor=BRAND_PRIMARY, fontSize=10)
    body = styles["BodyText"]
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8)
    return styles, title_style, h2, h3, body, small


def _fit_tier_color(tier: str):
    return {
        "Perfect Match": BRAND_GREEN,
        "Medium Fit": BRAND_BLUE,
        "Low Fit": BRAND_YELLOW,
        "Not Eligible": colors.grey,
    }.get(tier, colors.grey)


def _table_style_base():
    return [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]


# ---------------------------------------------------------------------------
# 1. Single Student PDF (existing, unchanged interface)
# ---------------------------------------------------------------------------

@router.get("/student/{student_id}/pdf")
def student_report_pdf(student_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    analysis = (
        db.query(AnalysisResult)
        .filter_by(student_id=student.id)
        .order_by(AnalysisResult.created_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(400, "No analysis available yet for this student — run analysis first")

    # 1. Try to generate Canva-matching 3-page PDF from live metrics data
    try:
        from pdf_generator import generate_student_report_pdf
        from app.services.chat_service import get_live_metrics_data
        bundle = get_live_metrics_data()
        student_rec = None
        if bundle and "per_student" in bundle:
            s_name = student.name.strip().lower()
            for cn, rec in bundle["per_student"].items():
                if cn in s_name or s_name in cn or rec.get("display_name", "").lower() == s_name:
                    student_rec = rec
                    break

        if student_rec:
            batch_label = student.batch.name if student.batch else "CCDP 2"
            pdf_bytes = generate_student_report_pdf(student_rec, batch_name=batch_label)
            filename = f"{student.name.replace(' ', '_')}_Dashboard_Report.pdf"
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
    except Exception as exc:
        print("Live PDF generator notice:", exc)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles, title_style, h2, h3, body, small = _get_styles()

    story: list[Any] = [
        Paragraph("Skill Bay Academy (Kauvery Hospital) — CCDP Placement Report", title_style),
        Spacer(1, 0.3 * cm),
        Paragraph(f"{student.name}  ·  {student.roll_number or '—'}  ·  Batch: {student.batch.name if student.batch else 'CCDP 1'}", styles["Heading3"]),
        Spacer(1, 0.5 * cm),
    ]

    summary_table = Table(
        [
            ["Overall Score", f"{analysis.overall_score}/100"],
            ["Placement Readiness", f"{analysis.placement_readiness_pct}%"],
            ["Attendance", f"{student.attendance_pct}%"],
            ["Predicted Salary Range", analysis.salary_range],
            ["Interview Readiness", analysis.interview_readiness],
        ],
        colWidths=[6 * cm, 9 * cm],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), BRAND_PRIMARY),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("AI Summary", h2))
    story.append(Paragraph(analysis.ai_summary or "—", body))
    story.append(Spacer(1, 0.4 * cm))

    strengths = json.loads(str(analysis.strengths or "[]"))
    weaknesses = json.loads(str(analysis.weaknesses or "[]"))
    story.append(Paragraph("Strengths", h2))
    story.append(Paragraph(", ".join(s.title() for s in strengths) or "—", body))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Areas to Improve", h2))
    story.append(Paragraph(", ".join(w.title() for w in weaknesses) or "—", body))
    story.append(Spacer(1, 0.4 * cm))

    roles = json.loads(str(analysis.recommended_roles or "[]"))
    story.append(Paragraph("Suitable Job Roles", h2))
    if roles:
        role_table = Table(
            [["Role", "Confidence", "Fit Tier"]] + [[r["role"], f"{r['confidence']}%", r.get("fit_tier", "—")] for r in roles],
            colWidths=[7 * cm, 4 * cm, 4 * cm],
        )
        role_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND_YELLOW),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(role_table)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Learning Roadmap", h2))
    for line in (analysis.learning_roadmap or "").split("\n"):
        if line.strip():
            story.append(Paragraph(line, body))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("30-Day Plan", h2))
    for line in (analysis.thirty_day_plan or "").split("\n"):
        if line.strip():
            story.append(Paragraph(line, body))
    story.append(Spacer(1, 0.3 * cm))

    certs = json.loads(str(analysis.recommended_certifications or "[]"))
    story.append(Paragraph("Recommended Certifications", h2))
    story.append(Paragraph(", ".join(certs) or "—", body))

    doc.build(story)
    buffer.seek(0)

    filename = f"{student.name.replace(' ', '_')}_placement_report.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# 2. Meta endpoint — lists available batches/courses for frontend selectors
# ---------------------------------------------------------------------------

@router.get("/meta")
def reports_meta(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    batches = db.query(Batch).all()
    courses = db.query(Course).all()
    return {
        "batches": [
            {
                "id": b.id,
                "name": b.name,
                "course": b.course.name if b.course else None,
                "student_count": db.query(Student).filter_by(batch_id=b.id).count(),
            }
            for b in batches
        ],
        "courses": [
            {
                "id": c.id,
                "name": c.name,
                "student_count": db.query(Student).filter_by(course_id=c.id).count(),
            }
            for c in courses
        ],
    }


# ---------------------------------------------------------------------------
# 3. Batch Summary PDF & CSV
# ---------------------------------------------------------------------------

@router.get("/batch/pdf")
@router.get("/batch/{batch_id}/pdf")
def batch_report_pdf(
    batch_id: int | None = None,
    batch: str = "",
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    batch_obj = None
    if batch_id:
        batch_obj = db.query(Batch).get(batch_id)
    elif batch:
        batch_obj = db.query(Batch).filter(Batch.name == batch).first()

    if batch_obj:
        students = db.query(Student).filter_by(batch_id=batch_obj.id).order_by(Student.overall_score.desc()).all()
        batch_title = batch_obj.name
        course_title = batch_obj.course.name if batch_obj.course else "—"
    elif batch:
        students = db.query(Student).join(Batch).filter(Batch.name == batch).order_by(Student.overall_score.desc()).all()
        batch_title = batch
        course_title = "—"
    else:
        students = db.query(Student).order_by(Student.overall_score.desc()).all()
        batch_title = "All Batches"
        course_title = "All Courses"

    if not students:
        raise HTTPException(400, "No students found for this batch")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles, title_style, h2, h3, body, small = _get_styles()

    # Aggregate stats
    total = len(students)
    ready = sum(1 for s in students if bool(getattr(s, "placement_ready", False)))
    avg_score = sum(float(str(getattr(s, "overall_score", 0) or 0)) for s in students) / total if total else 0
    avg_att = sum(float(str(getattr(s, "attendance_pct", 0) or 0)) for s in students) / total if total else 0

    story: list[Any] = [
        Paragraph("Skill Bay Academy — Batch Summary Report", title_style),
        Spacer(1, 0.2 * cm),
        Paragraph(f"Batch: {batch_title}  ·  Course: {course_title}", styles["Heading3"]),
        Spacer(1, 0.5 * cm),
    ]

    # Summary stats table
    summary = Table(
        [
            ["Total Students", "Placement Ready", "Avg Score", "Avg Attendance"],
            [str(total), f"{ready} ({round(ready/total*100,1) if total else 0}%)", f"{round(avg_score,1)}/100", f"{round(avg_att,1)}%"],
        ],
        colWidths=[3.75 * cm] * 4,
    )
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(summary)
    story.append(Spacer(1, 0.5 * cm))

    # Top 3 performers callout
    top3 = students[:3]
    story.append(Paragraph("Top Performers", h2))
    for i, s in enumerate(top3, 1):
        story.append(Paragraph(f"{i}. {s.name} — {s.overall_score}/100", body))
    story.append(Spacer(1, 0.4 * cm))

    # Per-student table
    story.append(Paragraph("Student Details", h2))
    headers = ["Name", "Roll No.", "Score", "Attendance", "Status", "Best Fit Role", "Fit Tier"]
    rows: list[list[str]] = [headers]
    for s in students:
        best_role = "—"
        fit_tier = "—"
        if s.analysis_results:
            roles_raw = json.loads(str(s.analysis_results[0].recommended_roles or "[]"))
            if roles_raw:
                best_role = str(roles_raw[0].get("role", "—"))
                fit_tier = str(roles_raw[0].get("fit_tier", "—"))
        rows.append([
            str(s.name)[:22],
            str(s.roll_number or "—"),
            f"{s.overall_score}",
            f"{s.attendance_pct}%",
            "Ready" if bool(s.placement_ready) else "Needs Training",
            best_role[:18],
            fit_tier,
        ])

    col_widths = [4 * cm, 2.5 * cm, 1.5 * cm, 2 * cm, 2.5 * cm, 3 * cm, 2.5 * cm]
    student_table = Table(rows, colWidths=col_widths)
    ts = _table_style_base()
    ts += [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PURPLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]
    for i, s in enumerate(students, 1):
        if bool(s.placement_ready):
            ts.append(("BACKGROUND", (4, i), (4, i), colors.HexColor("#D1FAE5")))
        else:
            ts.append(("BACKGROUND", (4, i), (4, i), colors.HexColor("#FEF3C7")))
    student_table.setStyle(TableStyle(ts))
    story.append(student_table)

    doc.build(story)
    buffer.seek(0)

    filename = f"batch_{batch_title.replace(' ', '_')}_report.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def sanitize_csv_cell(value: Any) -> Any:
    """
    Prevents CSV formula injection by prepending a single quote (') if the string
    starts with =, +, -, @, tab (\t), or carriage return (\r).
    """
    if value is None:
        return ""
    if isinstance(value, (int, float)) and value >= 0:
        return value
    str_val = str(value)
    if str_val and str_val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{str_val}"
    return value


@router.get("/batch/csv")
def batch_report_csv(
    batch: str = "",
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    q = db.query(Student)
    if batch:
        q = q.join(Batch).filter(Batch.name == batch)
    students = q.order_by(Student.overall_score.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    header = ["Name", "Roll Number", "Email", "Course", "Batch", "Attendance %", "Overall Score", "Placement Ready", "Best Fit Role", "Fit Tier"]
    writer.writerow([sanitize_csv_cell(h) for h in header])

    for s in students:
        best_role = "—"
        fit_tier = "—"
        if s.analysis_results:
            try:
                roles_raw = json.loads(s.analysis_results[0].recommended_roles or "[]")
                if roles_raw:
                    best_role = roles_raw[0].get("role", "—")
                    fit_tier = roles_raw[0].get("fit_tier", "—")
            except Exception:
                pass
        row = [
            s.name,
            s.roll_number or "",
            s.email or "",
            s.course.name if s.course else "",
            s.batch.name if s.batch else "",
            s.attendance_pct,
            s.overall_score,
            "Yes" if bool(s.placement_ready) else "No",
            best_role,
            fit_tier,
        ]
        writer.writerow([sanitize_csv_cell(cell) for cell in row])

    output.seek(0)
    filename = f"students_{batch.replace(' ', '_') if batch else 'all'}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# 4. Short Match Report — role × student matrix (PDF + CSV)
# ---------------------------------------------------------------------------

def _build_match_matrix(db: Session):
    """Returns (active_roles, students_with_analysis, matrix_rows)."""
    active_roles = db.query(JobRoleModel).filter(JobRoleModel.is_active.is_(True)).all()
    students = (
        db.query(Student)
        .join(AnalysisResult, AnalysisResult.student_id == Student.id)
        .order_by(Student.overall_score.desc())
        .all()
    )

    matrix = []
    for student in students:
        latest = student.analysis_results[0] if student.analysis_results else None
        roles_data = json.loads(latest.recommended_roles or "[]") if latest else []
        role_map = {r["role"]: r for r in roles_data}

        row = {"student": student, "matches": {}}
        for role in active_roles:
            match = role_map.get(role.name)
            if match:
                row["matches"][role.name] = {
                    "fit_tier": match.get("fit_tier", "—"),
                    "confidence": match.get("confidence", 0),
                }
            else:
                row["matches"][role.name] = {"fit_tier": "—", "confidence": 0}
        matrix.append(row)

    return active_roles, students, matrix


@router.get("/match/pdf")
@router.get("/match-matrix/pdf")
def match_matrix_pdf(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    active_roles, students, matrix = _build_match_matrix(db)
    if not active_roles:
        raise HTTPException(400, "No active job roles configured")
    if not students:
        raise HTTPException(400, "No analyzed students found")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles, title_style, h2, h3, body, small = _get_styles()

    story: list[Any] = [
        Paragraph("Skill Bay Academy — Job Role Match Matrix", title_style),
        Spacer(1, 0.3 * cm),
        Paragraph("Fit tiers: Perfect Match (green) · Medium Fit (blue) · Low Fit (yellow) · — (not matched)", small),
        Spacer(1, 0.4 * cm),
    ]

    role_names = [r.name for r in active_roles]
    headers = ["Student", "Score"] + [rn[:14] for rn in role_names]

    rows = [headers]
    ts = _table_style_base()
    ts += [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
    ]

    for row_idx, row in enumerate(matrix, 1):
        s = row["student"]
        data_row = [s.name[:18], str(s.overall_score)]
        for role in active_roles:
            match = row["matches"].get(role.name, {})
            tier = match.get("fit_tier", "—")
            conf = match.get("confidence", 0)
            cell = f"{tier[:7]}\n{conf}%" if tier != "—" else "—"
            data_row.append(cell)

            # Color cell by tier
            col_idx = 2 + list(r.name for r in active_roles).index(role.name)
            color = {
                "Perfect Match": colors.HexColor("#D1FAE5"),
                "Medium Fit": colors.HexColor("#DBEAFE"),
                "Low Fit": colors.HexColor("#FEF3C7"),
            }.get(tier)
            if color:
                ts.append(("BACKGROUND", (col_idx, row_idx), (col_idx, row_idx), color))

        rows.append(data_row)

    # Dynamic column widths
    page_w = landscape(A4)[0] - 3 * cm
    name_col = 3.5 * cm
    score_col = 1.5 * cm
    role_col_w = max((page_w - name_col - score_col) / max(len(active_roles), 1), 2 * cm)
    col_widths = [name_col, score_col] + [role_col_w] * len(active_roles)

    matrix_table = Table(rows, colWidths=col_widths)
    matrix_table.setStyle(TableStyle(ts))
    story.append(matrix_table)

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="match_matrix_report.pdf"'},
    )


@router.get("/match/csv")
@router.get("/match-matrix/csv")
def match_matrix_csv(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    active_roles, students, matrix = _build_match_matrix(db)

    output = io.StringIO()
    writer = csv.writer(output)

    role_names = [r.name for r in active_roles]
    header = ["Student", "Roll No.", "Score", "Placement Ready"] + role_names
    writer.writerow([sanitize_csv_cell(h) for h in header])

    for row in matrix:
        s = row["student"]
        cells = [s.name, s.roll_number or "", s.overall_score, "Yes" if s.placement_ready else "No"]
        for role in active_roles:
            match = row["matches"].get(role.name, {})
            tier = match.get("fit_tier", "—")
            conf = match.get("confidence", 0)
            cells.append(f"{tier} ({conf}%)" if tier != "—" else "—")
        writer.writerow([sanitize_csv_cell(c) for c in cells])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="match_matrix_report.csv"'},
    )


# ---------------------------------------------------------------------------
# 5. Full Institute Placement Audit PDF
# ---------------------------------------------------------------------------

@router.get("/institute/pdf")
def institute_report_pdf(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    from app.models import Institute

    institute = db.query(Institute).first()
    inst_name = institute.name if institute else "Skill Bay Academy"

    total_students = db.query(Student).count()
    if total_students == 0:
        raise HTTPException(400, "No students in the database")

    placement_ready = db.query(Student).filter(Student.placement_ready.is_(True)).count()
    avg_score = db.query(func.avg(Student.overall_score)).scalar() or 0.0
    avg_att = db.query(func.avg(Student.attendance_pct)).scalar() or 0.0

    # Course breakdown
    course_rows = (
        db.query(Course.name, func.avg(Student.overall_score), func.count(Student.id))
        .join(Student, Student.course_id == Course.id)
        .group_by(Course.name)
        .all()
    )

    # Top 5 performers
    top_students = db.query(Student).order_by(Student.overall_score.desc()).limit(5).all()

    # Weak skills
    skill_rows = (
        db.query(Skill.name, func.avg(StudentScore.score))
        .join(StudentScore, StudentScore.skill_id == Skill.id)
        .group_by(Skill.name)
        .order_by(func.avg(StudentScore.score).asc())
        .limit(8)
        .all()
    )

    # Active roles
    active_roles = db.query(JobRoleModel).filter(JobRoleModel.is_active.is_(True)).all()
    total_openings = sum(r.openings or 0 for r in active_roles)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles, title_style, h2, h3, body, small = _get_styles()

    story: list[Any] = [
        Paragraph(f"{inst_name}", title_style),
        Paragraph("Full Placement Audit Report", ParagraphStyle("Sub", parent=styles["Heading2"], textColor=BRAND_PURPLE)),
        Spacer(1, 0.5 * cm),
    ]

    # Institute stats
    inst_table = Table(
        [
            ["Total Students", "Placement Ready", "Avg Score", "Avg Attendance", "Active Roles", "Total Openings"],
            [
                str(total_students),
                f"{placement_ready} ({round(placement_ready/total_students*100,1) if total_students else 0}%)",
                f"{round(avg_score,1)}/100",
                f"{round(avg_att,1)}%",
                str(len(active_roles)),
                str(total_openings),
            ],
        ],
        colWidths=[2.75 * cm] * 6,
    )
    inst_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(inst_table)
    story.append(Spacer(1, 0.5 * cm))

    # Course breakdown
    story.append(Paragraph("Course-wise Breakdown", h2))
    c_rows = [["Course", "Students", "Avg Score"]]
    for name, avg, count in course_rows:
        c_rows.append([name, str(count), f"{round(avg or 0, 1)}/100"])
    c_table = Table(c_rows, colWidths=[8 * cm, 3 * cm, 4 * cm])
    c_table.setStyle(TableStyle(_table_style_base() + [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PURPLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ]))
    story.append(c_table)
    story.append(Spacer(1, 0.4 * cm))

    # Top performers
    story.append(Paragraph("Top Performers", h2))
    t_rows: list[list[str]] = [["Rank", "Name", "Score", "Status"]]
    for i, s in enumerate(top_students, 1):
        t_rows.append([str(i), str(s.name), f"{s.overall_score}/100", "✓ Ready" if bool(s.placement_ready) else "In Training"])
    t_table = Table(t_rows, colWidths=[1.5 * cm, 6 * cm, 3 * cm, 4.5 * cm])
    t_table.setStyle(TableStyle(_table_style_base() + [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_YELLOW),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(t_table)
    story.append(Spacer(1, 0.4 * cm))

    # Weak skills heatmap
    story.append(Paragraph("Skill Gap Heatmap (Weakest Skills)", h2))
    sk_rows = [["Skill", "Avg Score", "Priority"]]
    for name, avg in skill_rows:
        sc = round(avg or 0, 1)
        priority = "🔴 Critical" if sc < 40 else ("🟡 Moderate" if sc < 60 else "🟢 Good")
        sk_rows.append([name, f"{sc}/100", priority])
    sk_table = Table(sk_rows, colWidths=[6 * cm, 3 * cm, 6 * cm])
    sk_table.setStyle(TableStyle(_table_style_base() + [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PINK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(sk_table)
    story.append(Spacer(1, 0.4 * cm))

    # Active job roles
    story.append(Paragraph("Active Job Roles & Openings", h2))
    r_rows: list[list[str]] = [["Role", "Company", "Openings", "Demand Level"]]
    for r in active_roles:
        r_rows.append([str(r.name), str(r.company_name or "—"), str(r.openings or 0), str(r.demand_level or "Medium")])
    r_table = Table(r_rows, colWidths=[5 * cm, 4 * cm, 2.5 * cm, 3.5 * cm])
    r_table.setStyle(TableStyle(_table_style_base() + [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PURPLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(r_table)

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="institute_placement_audit.pdf"'},
    )


# ---------------------------------------------------------------------------
# 6. Live Session Report (PDF & Image) — generated from live preview data
# ---------------------------------------------------------------------------

def _build_live_report_pdf(students: list, batch_name: str, course_name: str, effort: str) -> io.BytesIO:
    """Build a styled PDF matching the sample template from live analysis data."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
    )
    styles, title_style, h2, h3, body, small = _get_styles()

    # Custom styles matching sample template
    cover_title = ParagraphStyle(
        "CoverTitle", parent=title_style,
        fontSize=14, textColor=colors.white, alignment=TA_LEFT, spaceAfter=2,
    )
    cover_sub = ParagraphStyle(
        "CoverSub", parent=title_style,
        fontSize=8, textColor=colors.HexColor("#FFCCDE"), alignment=TA_LEFT,
    )
    section_head = ParagraphStyle(
        "SectionHead", parent=styles["Normal"],
        fontSize=8, fontName="Helvetica-Bold", textColor=BRAND_PRIMARY,
        spaceBefore=8, spaceAfter=3,
    )
    cell_label = ParagraphStyle(
        "CellLabel", parent=styles["Normal"],
        fontSize=7, textColor=colors.HexColor("#64748B"), fontName="Helvetica",
    )
    cell_value = ParagraphStyle(
        "CellValue", parent=styles["Normal"],
        fontSize=8, textColor=colors.HexColor("#0F172A"), fontName="Helvetica-Bold",
    )
    kpi_num = ParagraphStyle(
        "KpiNum", parent=styles["Normal"],
        fontSize=16, textColor=BRAND_PRIMARY, fontName="Helvetica-Bold", alignment=TA_CENTER,
    )
    kpi_lab = ParagraphStyle(
        "KpiLab", parent=styles["Normal"],
        fontSize=7, textColor=colors.HexColor("#64748B"), alignment=TA_CENTER,
    )
    tbl_hdr = ParagraphStyle(
        "TblHdr", parent=styles["Normal"],
        fontSize=8, textColor=colors.white, fontName="Helvetica-Bold", alignment=TA_CENTER,
    )

    total = len(students)
    ready_count = sum(1 for s in students if s.get("placement_ready"))
    avg_score = sum(s.get("overall_score", 0) for s in students) / total if total else 0
    avg_att = sum(s.get("attendance_pct", 0) for s in students) / total if total else 0
    sorted_students = sorted(students, key=lambda s: s.get("overall_score", 0), reverse=True)
    ready_pct = round(ready_count / total * 100, 1) if total else 0

    story: list[Any] = []

    # ── COVER HEADER BANNER ──────────────────────────────────────
    sub_txt = f"Comprehensive Career Development Programme (CCDP) · {batch_name}"
    header_tbl = Table(
        [[Paragraph("Student Performance Dashboard & AI Career Report", cover_title)],
         [Paragraph(sub_txt, cover_sub)]],
        colWidths=[doc.width],
    )
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_PRIMARY),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (0, 0), 10),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BRAND_PRIMARY]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # ── KPI ROW ────────────────────────────────────────────────────
    story.append(Paragraph("PERFORMANCE AT A GLANCE", section_head))
    kpi_tbl = Table(
        [[
            Paragraph(str(total), kpi_num),
            Paragraph(f"{round(avg_score, 1)}", kpi_num),
            Paragraph(f"{ready_pct}%", kpi_num),
            Paragraph(f"{round(avg_att, 1)}%", kpi_num),
        ], [
            Paragraph("Total Candidates", kpi_lab),
            Paragraph("Avg. Score / 100", kpi_lab),
            Paragraph("Placement Ready", kpi_lab),
            Paragraph("Avg. Attendance", kpi_lab),
        ]],
        colWidths=[doc.width / 4] * 4,
    )
    kpi_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF5F8")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, 0), [colors.HexColor("#FFF5F8")]),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 0.5 * cm))

    # ── SUBJECT-WISE / SKILL TABLE (aggregate) ────────────────────
    # Collect all skills and compute averages
    skill_totals: dict = {}
    skill_counts: dict = {}
    for s in students:
        for sk_name, sk_val in (s.get("skill_scores") or {}).items():
            try:
                v = float(sk_val)
                skill_totals[sk_name] = skill_totals.get(sk_name, 0) + v
                skill_counts[sk_name] = skill_counts.get(sk_name, 0) + 1
            except Exception:
                pass

    story.append(Paragraph("SUBJECT-WISE ASSESSMENT SCORES (BATCH AVERAGE)", section_head))
    if skill_totals:
        sk_rows: list[list[Any]] = [[
            Paragraph("Assessment Component", tbl_hdr),
            Paragraph("Avg Score", tbl_hdr),
            Paragraph("Max", tbl_hdr),
            Paragraph("%", tbl_hdr),
        ]]
        for sname in sorted(skill_totals.keys()):
            avg = skill_totals[sname] / skill_counts[sname]
            pct = round(avg, 1)
            sk_rows.append([sname, f"{pct:.1f}", "100", f"{pct:.1f}%"])
        sk_tbl = Table(sk_rows, colWidths=[8 * cm, 2.5 * cm, 2 * cm, 3 * cm])
        sk_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FDF2F7")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(sk_tbl)
    else:
        story.append(Paragraph("No skill score data available.", small))
    story.append(Spacer(1, 0.5 * cm))

    # ── CANDIDATE DETAILS TABLE ───────────────────────────────────
    story.append(Paragraph("CANDIDATE SHORTLIST & PLACEMENT READINESS", section_head))
    cand_hdr = [
        Paragraph("Rank", tbl_hdr),
        Paragraph("Name", tbl_hdr),
        Paragraph("Score", tbl_hdr),
        Paragraph("Best Fit Role", tbl_hdr),
        Paragraph("Status", tbl_hdr),
    ]
    cand_rows: list[list[Any]] = [cand_hdr]
    for i, s in enumerate(sorted_students, 1):
        best_role = "—"
        if s.get("recommended_roles"):
            best_role = s["recommended_roles"][0].get("role", "—")
        status = "✓ Ready" if s.get("placement_ready") else "⚠ Needs Prep"
        cand_rows.append([
            str(i),
            s.get("name", "—"),
            f"{s.get('overall_score', 0):.1f}",
            best_role,
            status,
        ])
    cand_tbl = Table(
        cand_rows,
        colWidths=[1.2 * cm, 5 * cm, 2 * cm, 5.5 * cm, 2.5 * cm],
        repeatRows=1,
    )
    cand_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FDF2F7")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("ALIGN", (4, 0), (4, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(cand_tbl)
    story.append(Spacer(1, 0.5 * cm))

    # ── FOOTER ───────────────────────────────────────────────────
    footer_para = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=7, textColor=colors.HexColor("#94A3B8"), alignment=TA_CENTER,
    )
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0")))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Skill Bay Academy (Kauvery Hospital) · CCDP Placement Report · {batch_name} · Generated by SkillBay AI",
        footer_para,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


@router.post("/live/pdf")
async def live_report_pdf(
    payload: dict,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Generate a live-session PDF report from uploaded student analysis data."""
    students = payload.get("students", [])
    batch_name = payload.get("batch_name", "Live Session")
    course_name = payload.get("course_name", "CCDP")
    effort = payload.get("effort", "detailed")
    model = payload.get("model", "gemini-1.5-flash")

    if not students:
        raise HTTPException(400, "No student data provided")

    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    buffer = _build_live_report_pdf(students, batch_name, course_name, effort)
    safe_batch = batch_name.replace(" ", "_").replace("/", "-")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="CCDP_Live_Report_{safe_batch}_{date_str}.pdf"'},
    )


@router.post("/live/image")
async def live_report_image(
    payload: dict,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Generate a live-session PNG image of the report (renders first page of PDF as image)."""
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    students = payload.get("students", [])
    batch_name = payload.get("batch_name", "Live Session")
    course_name = payload.get("course_name", "CCDP")
    effort = payload.get("effort", "detailed")

    if not students:
        raise HTTPException(400, "No student data provided")

    pdf_buffer = _build_live_report_pdf(students, batch_name, course_name, effort)

    # Try to render PDF to image using pdf2image if available
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(pdf_buffer.read(), dpi=150, first_page=1, last_page=1)
        img_buffer = io.BytesIO()
        images[0].save(img_buffer, format="PNG")
        img_buffer.seek(0)
        safe_batch = batch_name.replace(" ", "_").replace("/", "-")
        return StreamingResponse(
            img_buffer,
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="CCDP_Live_Report_{safe_batch}_{date_str}.png"'},
        )
    except ImportError:
        # pdf2image not installed — return the PDF instead
        pdf_buffer.seek(0)
        safe_batch = batch_name.replace(" ", "_").replace("/", "-")
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="CCDP_Live_Report_{safe_batch}_{date_str}.pdf"'},
        )
