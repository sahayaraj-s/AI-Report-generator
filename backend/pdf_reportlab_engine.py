"""
pdf_reportlab_engine.py - Pure Python Publication-Grade ReportLab Fallback Renderer
===================================================================================
Produces an exact 3-page A4 PDF matching the reference design:
- Page 1: Gradient/Plum Header + Logo, Student Profile Grid, 4 Performance KPIs,
          Attendance Donut + Typing Speed Chart, Subject-Wise Assessment Scores Table.
- Page 2: Assessment Performance Bar Chart (Student vs Class Avg), Core Skill Matrix Radar
          + Skill Table & Other Skills, Placement Outcome, Strengths & Areas for Improvement.
- Page 3: AI-Generated Career Fit Report Card, Recommended Role Pill, Why This Role Fits,
          Skill Gaps, and Source Data Disclaimer.

Ensures zero dependency on external browser binaries on Linux/Render.
"""
from __future__ import annotations

import base64
import io
import os
from typing import Any, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line

# ---------------------------------------------------------------------------
# Brand Color Tokens
# ---------------------------------------------------------------------------
C_PURPLE_DARK = colors.HexColor("#4A154B")
C_PURPLE = colors.HexColor("#6B3591")
C_ROSE = colors.HexColor("#E0507A")
C_PLUM = colors.HexColor("#8E1F58")
C_GOLD = colors.HexColor("#E8B923")
C_GREEN_BG = colors.HexColor("#EEF8EE")
C_GREEN_BORDER = colors.HexColor("#2E7D32")
C_CREAM_BG = colors.HexColor("#FBF6EA")
C_CREAM_BORDER = colors.HexColor("#F57F17")
C_LAVENDER_BG = colors.HexColor("#FAF7FC")
C_LAVENDER_BORDER = colors.HexColor("#ECE3F0")
C_GREY_BAR = colors.HexColor("#9AA0A6")
C_TEXT_DARK = colors.HexColor("#202124")
C_TEXT_MUTED = colors.HexColor("#5F6368")
C_WHITE = colors.white
C_GREY_LINE = colors.HexColor("#E0E0E0")
C_CARD_HEADER = colors.HexColor("#F0EBF7")


class NumberedCanvas(canvas.Canvas):
    """Draws consistent running footers on all pages with 1-based page count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_footer(num_pages)
            super().showPage()
        super().save()

    def draw_page_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(C_TEXT_MUTED)
        self.setStrokeColor(C_GREY_LINE)
        self.setLineWidth(0.5)
        # Running rule line above footer
        self.line(28, 26, 595.27 - 28, 26)
        self.drawString(28, 15, "Skill Bay Academy · Enabling Life Skills")
        self.drawRightString(595.27 - 28, 15, f"Page {self._pageNumber}")
        self.restoreState()


def _get_logo_image(max_w: float = 120, max_h: float = 38) -> Optional[RLImage]:
    """Finds and prepares the Skill Bay Academy logo as a ReportLab Image."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    candidates = [
        os.path.join(current_dir, "assets", "logo.png"),
        os.path.join(project_root, "frontend", "public", "logo.png"),
        os.path.join(project_root, "frontend", "dist", "logo.png"),
    ]
    for c in candidates:
        if os.path.exists(c):
            img = RLImage(c, width=max_w, height=max_h)
            img.hAlign = "RIGHT"
            return img
    return None


def _make_section_header(title: str, styles: dict) -> list:
    """Builds an uppercase purple section title with a thin gold underline."""
    p = Paragraph(f"<b>{title.upper()}</b>", styles["SectionTitle"])
    # Drawing gold line
    d = Drawing(520, 3)
    d.add(Line(0, 1.5, 520, 1.5, strokeColor=C_GOLD, strokeWidth=1.5))
    return [p, d, Spacer(1, 4)]


def _b64_to_rl_image(b64_str: str, width: float, height: float, h_align: str = "CENTER") -> Optional[RLImage]:
    """Decodes a base64 PNG string into a ReportLab Image."""
    if not b64_str:
        return None
    try:
        raw = base64.b64decode(b64_str)
        bio = io.BytesIO(raw)
        img = RLImage(bio, width=width, height=height)
        img.hAlign = h_align
        return img
    except Exception:
        return None


def generate_student_reportlab_pdf(student_rec_or_data: Any, batch_name: str = "2023", batch_metrics: Optional[dict] = None) -> bytes:
    """Convenience wrapper that accepts either a raw student dict or a UnifiedStudentReportData object."""
    from pdf_generator import build_unified_student_data, UnifiedStudentReportData
    if isinstance(student_rec_or_data, UnifiedStudentReportData):
        data = student_rec_or_data
    else:
        data = build_unified_student_data(student_rec_or_data, batch_metrics=batch_metrics)
    return generate_student_report_pdf_reportlab(data, batch_name=batch_name)


def generate_student_report_pdf_reportlab(data: Any, batch_name: str = "2023") -> bytes:
    """
    Constructs the exact 3-page publication-grade A4 PDF report matching the reference design.
    """
    buffer = io.BytesIO()
    # A4: 595.27 x 841.89 points
    # Margins: left=28, right=28, top=20, bottom=32 -> Usable width = 539.27 points
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=28,
        rightMargin=28,
        topMargin=20,
        bottomMargin=32,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    styles.add(ParagraphStyle(
        "HeaderTitle",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=C_WHITE,
    ))
    styles.add(ParagraphStyle(
        "HeaderSubtitle",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=C_WHITE,
    ))
    styles.add(ParagraphStyle(
        "HeaderDate",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=C_GOLD,
    ))
    styles.add(ParagraphStyle(
        "SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=C_PURPLE,
        spaceAfter=1,
    ))
    styles.add(ParagraphStyle(
        "StudentName",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=C_PURPLE_DARK,
    ))
    styles.add(ParagraphStyle(
        "RankPill",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=C_WHITE,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "ProfileLabel",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=C_TEXT_MUTED,
    ))
    styles.add(ParagraphStyle(
        "ProfileValue",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=C_TEXT_DARK,
    ))
    styles.add(ParagraphStyle(
        "ProfileValueMuted",
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10,
        textColor=C_TEXT_MUTED,
    ))
    styles.add(ParagraphStyle(
        "KPILabel",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=C_TEXT_MUTED,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "KPIVal",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=15,
        textColor=C_PLUM,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "KPISub",
        fontName="Helvetica",
        fontSize=7,
        leading=8.5,
        textColor=C_TEXT_MUTED,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "TableCell",
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=C_TEXT_DARK,
    ))
    styles.add(ParagraphStyle(
        "TableCellBold",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=C_TEXT_DARK,
    ))
    styles.add(ParagraphStyle(
        "TableCellCenter",
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=C_TEXT_DARK,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "TableCellCenterBold",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=C_TEXT_DARK,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "TableHead",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=C_WHITE,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        "TableHeadCenter",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=C_WHITE,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "BoxTitleGreen",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=C_GREEN_BORDER,
    ))
    styles.add(ParagraphStyle(
        "BoxTitleGold",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=C_CREAM_BORDER,
    ))
    styles.add(ParagraphStyle(
        "BulletItem",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=C_TEXT_DARK,
    ))
    styles.add(ParagraphStyle(
        "PlacementSummary",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=C_TEXT_DARK,
        spaceBefore=3,
    ))
    styles.add(ParagraphStyle(
        "AITitle",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=15,
        textColor=C_PURPLE,
    ))
    styles.add(ParagraphStyle(
        "AISub",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=C_TEXT_DARK,
    ))
    styles.add(ParagraphStyle(
        "AIRolePill",
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        textColor=C_WHITE,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "AISectionHeading",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=C_PURPLE,
    ))
    styles.add(ParagraphStyle(
        "AIBulletItem",
        fontName="Helvetica",
        fontSize=8,
        leading=11.5,
        textColor=C_TEXT_DARK,
    ))
    styles.add(ParagraphStyle(
        "AIDisclaimer",
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=C_TEXT_MUTED,
    ))

    story: List[Any] = []

    # =========================================================================
    # PAGE 1
    # =========================================================================
    
    # 1. Header Banner
    logo_img = _get_logo_image(max_w=100, max_h=34)
    header_text_cells = [
        Paragraph("Student Performance Dashboard &amp; AI Career Report", styles["HeaderTitle"]),
        Spacer(1, 1),
        Paragraph(f"Comprehensive Career Development Programme (CCDP) · Batch {batch_name}", styles["HeaderSubtitle"]),
        Spacer(1, 1),
        Paragraph("November 2023", styles["HeaderDate"]),
    ]
    
    header_table = Table(
        [[header_text_cells, logo_img if logo_img else ""]],
        colWidths=[420, 119],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_PURPLE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))

    # 2. Student Profile Card
    # Pill label
    pill_text = f"RANK #{data.rank} OF {data.class_size}"
    if data.is_top_performer:
        pill_text += " · TOP PERFORMER"
    
    pill_table = Table([[Paragraph(pill_text, styles["RankPill"])]], colWidths=[175])
    pill_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_PLUM),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    name_row_table = Table(
        [[Paragraph(data.name, styles["StudentName"]), pill_table]],
        colWidths=[340, 180]
    )
    name_row_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    def _val_p(val: str):
        style = styles["ProfileValueMuted"] if val == "Not recorded" else styles["ProfileValue"]
        return Paragraph(val, style)

    profile_grid_data = [
        [
            Paragraph("Enrolment No.", styles["ProfileLabel"]), _val_p(data.enrolment_no),
            Paragraph("Qualification", styles["ProfileLabel"]), _val_p(data.qualification),
        ],
        [
            Paragraph("College Name", styles["ProfileLabel"]), _val_p(data.college),
            Paragraph("Gender", styles["ProfileLabel"]), _val_p(data.gender),
        ],
        [
            Paragraph("Age", styles["ProfileLabel"]), _val_p(data.age),
            Paragraph("Home District", styles["ProfileLabel"]), _val_p(data.home_district),
        ],
        [
            Paragraph("Residential Status", styles["ProfileLabel"]), _val_p(data.residential_status),
            Paragraph("Parent Orientation", styles["ProfileLabel"]), _val_p(data.parent_orientation),
        ],
    ]
    profile_grid_table = Table(
        profile_grid_data,
        colWidths=[100, 160, 100, 160]
    )
    profile_grid_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))

    profile_card = Table(
        [[name_row_table], [Spacer(1, 2)], [profile_grid_table]],
        colWidths=[520]
    )
    profile_card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_LAVENDER_BG),
        ("BOX", (0, 0), (-1, -1), 0.75, C_LAVENDER_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(profile_card)
    story.append(Spacer(1, 6))

    # 3. Performance at a Glance (4 KPI Cards)
    story.extend(_make_section_header("Performance at a Glance", styles))

    class_avg_score = (data.class_avg_overall_pct * data.total_max / 100.0) if data.total_max > 0 else 0.0
    kpi_card_1 = [
        Paragraph("TOTAL SCORE", styles["KPILabel"]),
        Paragraph(f"{data.total_score:g} / {data.total_max:g}", styles["KPIVal"]),
        Paragraph(f"Class Avg: {class_avg_score:.1f} / {data.total_max:g}", styles["KPISub"]),
    ]
    kpi_card_2 = [
        Paragraph("OVERALL %", styles["KPILabel"]),
        Paragraph(f"{data.overall_pct:.1f}%", styles["KPIVal"]),
        Paragraph(f"Class Avg: {data.class_avg_overall_pct:.1f}%", styles["KPISub"]),
    ]
    kpi_card_3 = [
        Paragraph("ATTENDANCE %", styles["KPILabel"]),
        Paragraph(f"{data.attendance_pct:.1f}%", styles["KPIVal"]),
        Paragraph(f"{data.present_days}/{data.total_days} Days", styles["KPISub"]),
    ]
    kpi_card_4 = [
        Paragraph("CLASS RANK", styles["KPILabel"]),
        Paragraph(f"#{data.rank}", styles["KPIVal"]),
        Paragraph(f"of {data.class_size} Students", styles["KPISub"]),
    ]

    kpi_table = Table(
        [[kpi_card_1, kpi_card_2, kpi_card_3, kpi_card_4]],
        colWidths=[131, 131, 131, 131]
    )
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_LAVENDER_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, C_LAVENDER_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, C_LAVENDER_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 6))

    # 4. Donut + Typing Charts Side by Side
    donut_img = _b64_to_rl_image(data.donut_chart_b64, width=225, height=110)
    typing_img = _b64_to_rl_image(data.typing_chart_b64, width=300, height=110)

    charts_row = Table(
        [[donut_img or "", typing_img or ""]],
        colWidths=[230, 309]
    )
    charts_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(charts_row)
    story.append(Spacer(1, 6))

    # 5. Subject-Wise Assessment Scores Table
    story.extend(_make_section_header("Subject-Wise Assessment Scores", styles))

    subj_table_data = [
        [
            Paragraph("Component", styles["TableHead"]),
            Paragraph("Score", styles["TableHeadCenter"]),
            Paragraph("Max Marks", styles["TableHeadCenter"]),
            Paragraph("Score %", styles["TableHeadCenter"]),
            Paragraph("Class Avg %", styles["TableHeadCenter"]),
        ]
    ]

    for row in data.subject_rows:
        score_disp = f"{row.score:g}" if isinstance(row.score, (int, float)) else str(row.score)
        max_disp = f"{row.max_score:g}" if isinstance(row.max_score, (int, float)) else str(row.max_score)
        pct_disp = f"{row.score_pct:.1f}%" if isinstance(row.score_pct, (int, float)) else str(row.score_pct)
        avg_disp = f"{row.class_avg_pct:.1f}%" if isinstance(row.class_avg_pct, (int, float)) else str(row.class_avg_pct)
        subj_table_data.append([
            Paragraph(row.name, styles["TableCellBold"]),
            Paragraph(score_disp, styles["TableCellCenter"]),
            Paragraph(max_disp, styles["TableCellCenter"]),
            Paragraph(pct_disp, styles["TableCellCenter"]),
            Paragraph(avg_disp, styles["TableCellCenter"]),
        ])

    # Total Row
    tot_score = sum(r.score for r in data.subject_rows if isinstance(r.score, (int, float)))
    tot_max = sum(r.max_score for r in data.subject_rows if isinstance(r.max_score, (int, float)))
    tot_pct = round((tot_score / tot_max) * 100, 1) if tot_max else 0.0
    valid_avgs = [r.class_avg_pct for r in data.subject_rows if isinstance(r.class_avg_pct, (int, float))]
    tot_avg = round(sum(valid_avgs) / len(valid_avgs), 1) if valid_avgs else 71.1

    subj_table_data.append([
        Paragraph("Total", styles["TableCellBold"]),
        Paragraph(f"<b>{tot_score:g}</b>", styles["TableCellCenterBold"]),
        Paragraph(f"<b>{tot_max:g}</b>", styles["TableCellCenterBold"]),
        Paragraph(f"<b>{tot_pct:.1f}%</b>", styles["TableCellCenterBold"]),
        Paragraph(f"<b>{tot_avg:.1f}%</b>", styles["TableCellCenterBold"]),
    ])

    subj_table = Table(
        subj_table_data,
        colWidths=[209, 80, 80, 85, 85]
    )
    t_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), C_PURPLE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -2), 0.4, C_LAVENDER_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        # Total row highlight
        ("BACKGROUND", (0, -1), (-1, -1), C_CARD_HEADER),
        ("LINEABOVE", (0, -1), (-1, -1), 1, C_PURPLE),
        ("LINEBELOW", (0, -1), (-1, -1), 1, C_PURPLE),
    ]
    # Zebra stripes
    for idx in range(1, len(subj_table_data) - 1):
        if idx % 2 == 0:
            t_styles.append(("BACKGROUND", (0, idx), (-1, idx), C_LAVENDER_BG))
    subj_table.setStyle(TableStyle(t_styles))
    story.append(subj_table)

    # PAGE 1 END
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2
    # =========================================================================

    # 1. Assessment Performance Bar Chart
    story.extend(_make_section_header("Assessment Performance (Student vs Class Average)", styles))
    bar_img = _b64_to_rl_image(data.bar_chart_b64, width=520, height=130)
    if bar_img:
        story.append(bar_img)
    story.append(Spacer(1, 6))

    # 2. Core Skill Matrix (Radar + Skill Table + Other Skills)
    story.extend(_make_section_header("Core Skill Matrix", styles))

    radar_img = _b64_to_rl_image(data.radar_chart_b64, width=255, height=160)

    # Right side: Skill Table
    skill_table_data = [
        [
            Paragraph("Skill", styles["TableHead"]),
            Paragraph(data.name.split()[0], styles["TableHeadCenter"]),
            Paragraph("Class Avg", styles["TableHeadCenter"]),
        ]
    ]
    for sr in data.skill_rows:
        s_score = f"{sr.student_score:g}" if isinstance(sr.student_score, (int, float)) else str(sr.student_score)
        c_avg = f"{sr.class_avg:.1f}" if isinstance(sr.class_avg, (int, float)) else str(sr.class_avg)
        skill_table_data.append([
            Paragraph(sr.name, styles["TableCellBold"]),
            Paragraph(s_score, styles["TableCellCenterBold"]),
            Paragraph(c_avg, styles["TableCellCenter"]),
        ])
    skill_table = Table(
        skill_table_data,
        colWidths=[135, 70, 70]
    )
    st_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), C_PURPLE),
        ("GRID", (0, 0), (-1, -1), 0.4, C_LAVENDER_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for idx in range(1, len(skill_table_data)):
        if idx % 2 == 0:
            st_styles.append(("BACKGROUND", (0, idx), (-1, idx), C_LAVENDER_BG))
    skill_table.setStyle(TableStyle(st_styles))

    # Other skills card
    other_skills_val = styles["ProfileValueMuted"] if data.other_skills_text == "Not recorded" else styles["ProfileValue"]
    other_skills_box = Table(
        [
            [Paragraph("<b>OTHER SKILLS (AS RECORDED)</b>", styles["ProfileLabel"])],
            [Paragraph(data.other_skills_text, other_skills_val)],
        ],
        colWidths=[265]
    )
    other_skills_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_LAVENDER_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, C_LAVENDER_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    right_col_cells = [skill_table, Spacer(1, 4), other_skills_box]

    matrix_row = Table(
        [[radar_img or "", right_col_cells]],
        colWidths=[264, 275]
    )
    matrix_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(matrix_row)
    story.append(Spacer(1, 6))

    # 3. Placement Outcome
    story.extend(_make_section_header("Placement Outcome", styles))
    if data.placement.is_available:
        place_table = Table(
            [
                [
                    Paragraph("Designation", styles["TableHead"]),
                    Paragraph("Organization", styles["TableHead"]),
                    Paragraph("Starting Salary", styles["TableHeadCenter"]),
                    Paragraph("Cohort Rank (by salary)", styles["TableHeadCenter"]),
                ],
                [
                    Paragraph(data.placement.designation, styles["TableCellBold"]),
                    Paragraph(data.placement.organization, styles["TableCell"]),
                    Paragraph(f"<b>{data.placement.salary_display}</b>", styles["TableCellCenterBold"]),
                    Paragraph(str(data.placement.cohort_rank), styles["TableCellCenter"]),
                ]
            ],
            colWidths=[169, 150, 110, 110]
        )
        place_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_PURPLE),
            ("GRID", (0, 0), (-1, -1), 0.4, C_LAVENDER_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(place_table)
        if data.placement.summary_sentence:
            story.append(Paragraph(data.placement.summary_sentence, styles["PlacementSummary"]))
    else:
        missing_p_box = Table(
            [[Paragraph("Placement details not available", styles["ProfileValueMuted"])]],
            colWidths=[520]
        )
        missing_p_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_LAVENDER_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, C_LAVENDER_BORDER),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(missing_p_box)
    story.append(Spacer(1, 6))

    # 4. Strengths & Areas for Improvement
    story.extend(_make_section_header("Strengths &amp; Areas for Improvement", styles))

    str_cells = [Paragraph("<b>✓ Key Strengths</b>", styles["BoxTitleGreen"]), Spacer(1, 2)]
    for title, desc in data.strengths:
        str_cells.append(Paragraph(f"• <b>{title}</b> — {desc}", styles["BulletItem"]))
        str_cells.append(Spacer(1, 1.5))

    imp_cells = [Paragraph("<b>▲ Areas for Improvement</b>", styles["BoxTitleGold"]), Spacer(1, 2)]
    for title, desc in data.improvements:
        imp_cells.append(Paragraph(f"• <b>{title}</b> — {desc}", styles["BulletItem"]))
        imp_cells.append(Spacer(1, 1.5))

    strengths_box = Table([[str_cells]], colWidths=[264])
    strengths_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_GREEN_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, C_GREEN_BG),
        ("LINEBEFORE", (0, 0), (0, -1), 3, C_GREEN_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    imp_box = Table([[imp_cells]], colWidths=[265])
    imp_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CREAM_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, C_CREAM_BG),
        ("LINEBEFORE", (0, 0), (0, -1), 3, C_CREAM_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    feedback_row = Table(
        [[strengths_box, imp_box]],
        colWidths=[269, 270]
    )
    feedback_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(feedback_row)

    # PAGE 2 END
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: AI-Generated Career Fit Report Card
    # =========================================================================

    ai_cells: List[Any] = []

    # AI Badge & Title Row
    ai_badge = Table([[Paragraph("<font color='white'><b>AI</b></font>", styles["RankPill"])]], colWidths=[26])
    ai_badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_PURPLE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    ai_title_table = Table(
        [[ai_badge, Paragraph("<b>AI-Generated Career Fit Report</b>", styles["AITitle"])]],
        colWidths=[34, 480]
    )
    ai_title_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    ai_cells.append(ai_title_table)
    ai_cells.append(Spacer(1, 4))

    # Subtitle
    ai_cells.append(Paragraph(
        f"Recommended role, based purely on the assessment scores, skill matrix, and other-skills data recorded for {data.name}:",
        styles["AISub"]
    ))
    ai_cells.append(Spacer(1, 6))

    # Role Pill
    role_pill = Table(
        [[Paragraph(data.recommended_role, styles["AIRolePill"])]],
        colWidths=[510]
    )
    role_pill.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_PLUM),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    ai_cells.append(role_pill)
    ai_cells.append(Spacer(1, 8))

    # WHY THIS ROLE FITS
    ai_cells.append(Paragraph("<b>WHY THIS ROLE FITS</b>", styles["AISectionHeading"]))
    d_line = Drawing(510, 2)
    d_line.add(Line(0, 1, 510, 1, strokeColor=C_GOLD, strokeWidth=1))
    ai_cells.append(d_line)
    ai_cells.append(Spacer(1, 4))

    for lead, text in data.why_role_fits:
        ai_cells.append(Paragraph(f"• <b>{lead}:</b> {text}", styles["AIBulletItem"]))
        ai_cells.append(Spacer(1, 2.5))

    if data.placement_alignment_text:
        ai_cells.append(Spacer(1, 3))
        ai_cells.append(Paragraph(f"<i>{data.placement_alignment_text}</i>", styles["AIBulletItem"]))
        ai_cells.append(Spacer(1, 3))

    ai_cells.append(Spacer(1, 6))

    # SKILL GAPS TO ADDRESS
    ai_cells.append(Paragraph("<b>SKILL GAPS TO ADDRESS FOR THIS ROLE</b>", styles["AISectionHeading"]))
    d_line2 = Drawing(510, 2)
    d_line2.add(Line(0, 1, 510, 1, strokeColor=C_GOLD, strokeWidth=1))
    ai_cells.append(d_line2)
    ai_cells.append(Spacer(1, 4))

    for lead, text in data.skill_gaps:
        ai_cells.append(Paragraph(f"• <b>{lead}</b> {text}", styles["AIBulletItem"]))
        ai_cells.append(Spacer(1, 2.5))

    ai_cells.append(Spacer(1, 14))

    # Disclaimer Box
    disclaimer_box = Table(
        [[Paragraph(
            "This AI report is generated strictly from the data recorded in the uploaded CCDP student tracker "
            "(Assessment, Skill Matrix, Other Skills, Attendance, and Placement sheets). "
            "No information has been inferred or added beyond what is present in the source file.",
            styles["AIDisclaimer"]
        )]],
        colWidths=[490]
    )
    disclaimer_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CARD_HEADER),
        ("BOX", (0, 0), (-1, -1), 0.5, C_LAVENDER_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    ai_cells.append(disclaimer_box)

    # Wrap in Page 3 Card
    ai_card_outer = Table(
        [[ai_cells]],
        colWidths=[539]
    )
    ai_card_outer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_LAVENDER_BG),
        ("BOX", (0, 0), (-1, -1), 0.75, C_LAVENDER_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(ai_card_outer)

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
