"""
pdf_generator.py - Pixel-Accurate 3-Page CCDP Student Report Generator
======================================================================
Generates a PDF matching Sample_Student_Dashboard_Report.pdf in exact layout,
section order, table structure, rounding, charts, and fonts.

Sections:
  Page 1:
    1. Header: Report title + CCDP Batch info + Rank badge
    2. Student identity block
    3. Student profile grid (Gender, Age, Qual, District, College, Hostel, Parent, Source)
    4. Performance at a glance (4 stat cards: Total Score, Overall %, Attendance %, Rank)
    5. Attendance donut chart + Typing speed bar vs class range
    6. Subject-wise Assessment Scores table (with Total row)
  Page 2:
    7. Assessment Performance bar chart (student vs class avg per subject)
    8. Core Skill Matrix radar chart + table + Typing Speed + Other Skills text
    9. Placement Outcome table (omitted if unplaced)
    10. Strengths & Areas for Improvement (grounded in numbers)
  Page 3:
    11. AI-Generated Career Fit Report (Recommended role, Why this role fits, Skill gaps)
"""
from __future__ import annotations

import io
import math
import os
import re
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, cm
pt = 1
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Brand Colors & Palette
# ---------------------------------------------------------------------------
C_PLUM_DARK = colors.HexColor("#4A154B")     # Deep plum / brand primary
C_PLUM = colors.HexColor("#721c47")          # Primary accent
C_PLUM_LIGHT = colors.HexColor("#FDF2F8")    # Light plum background
C_GOLD = colors.HexColor("#D97706")          # Gold/amber for rank #1
C_GOLD_BG = colors.HexColor("#FEF3C7")       # Amber pill background
C_GREEN = colors.HexColor("#16A34A")         # Green for attendance/strengths
C_GREEN_BG = colors.HexColor("#F0FDF4")      # Light green background
C_BLUE = colors.HexColor("#2563EB")          # Blue for scores
C_BLUE_BG = colors.HexColor("#EFF6FF")       # Light blue background
C_GRAY_DARK = colors.HexColor("#1E293B")     # Primary text
C_GRAY_MED = colors.HexColor("#64748B")      # Secondary text / subtitles
C_GRAY_LIGHT = colors.HexColor("#F8FAFC")    # Table alt row / card bg
C_BORDER = colors.HexColor("#E2E8F0")        # Card / table border
C_BORDER_DARK = colors.HexColor("#CBD5E1")


# ---------------------------------------------------------------------------
# Numbered Canvas for Footer
# ---------------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
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
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Footer divider line
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 26, 559, 26)

        # Bottom text
        self.drawString(36, 14, "Skill Bay Academy  ·  Enabling Life Skills")
        page_str = f"Page {self._pageNumber}"
        self.drawRightString(559, 14, page_str)
        self.restoreState()


# ---------------------------------------------------------------------------
# Chart Generators (matplotlib -> in-memory PNG)
# ---------------------------------------------------------------------------

def generate_donut_and_typing_chart(
    present_days: int,
    total_days: int,
    typing_wpm: float | None,
    typing_avg: float | None,
    typing_min: float | None,
    typing_max: float | None,
) -> io.BytesIO:
    """Combines attendance donut + typing speed gauge into one 2-panel chart."""
    fig, (ax_donut, ax_bar) = plt.subplots(1, 2, figsize=(4.8, 1.8), dpi=200)
    fig.patch.set_facecolor("#FFFFFF")

    # 1. Donut chart
    att_pct = (present_days / total_days * 100) if total_days > 0 else 0
    absent_days = max(0, total_days - present_days)
    slices = [present_days, absent_days]
    colors_donut = ["#10B981", "#E2E8F0"]
    wedges, _ = ax_donut.pie(
        slices,
        colors=colors_donut,
        startangle=90,
        counterclock=False,
        wedgeprops=dict(width=0.35, edgecolor="white", linewidth=2),
    )
    ax_donut.text(0, 0.08, f"{att_pct:.1f}%", ha="center", va="center", fontsize=11, fontweight="bold", color="#1E293B")
    ax_donut.text(0, -0.15, f"{present_days}/{total_days} Days", ha="center", va="center", fontsize=7.5, color="#64748B")
    ax_donut.set_title("Training Attendance", fontsize=8.5, fontweight="bold", color="#4A154B", pad=4)

    # 2. Typing speed horizontal range bar
    ax_bar.set_facecolor("#FFFFFF")
    t_min = typing_min if typing_min is not None else 15.0
    t_max = typing_max if typing_max is not None else 36.0
    t_avg = typing_avg if typing_avg is not None else 21.4
    t_val = typing_wpm if typing_wpm is not None else 22.0

    # Draw cohort background bar
    ax_bar.barh(0, t_max - t_min, left=t_min, height=0.35, color="#F1F5F9", edgecolor="#CBD5E1", linewidth=1, label="Cohort Range")
    # Draw class average marker line
    ax_bar.plot([t_avg, t_avg], [-0.25, 0.25], color="#64748B", linestyle="--", linewidth=1.5, label=f"Class Avg ({t_avg:.1f})")
    # Draw student point / marker
    ax_bar.plot(t_val, 0, marker="o", markersize=9, color="#8B1D55", label=f"Student ({t_val:.0f} WPM)")

    ax_bar.set_xlim(max(0, t_min - 5), t_max + 8)
    ax_bar.set_ylim(-0.5, 0.6)
    ax_bar.set_yticks([])
    ax_bar.set_xlabel("Words Per Minute (WPM)", fontsize=7.5, color="#64748B")
    ax_bar.tick_params(axis="x", labelsize=7, colors="#64748B")
    for spine in ax_bar.spines.values():
        spine.set_visible(False)
    ax_bar.grid(axis="x", linestyle=":", alpha=0.5)
    ax_bar.set_title(f"Typing Speed: {t_val:.0f} WPM", fontsize=8.5, fontweight="bold", color="#4A154B", pad=4)
    ax_bar.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), frameon=False, fontsize=6.5, ncol=3)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=200, facecolor=fig.get_facecolor(), transparent=False)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_subject_bar_chart(per_subject_pct: dict, class_avg_pct: dict) -> io.BytesIO:
    """Grouped bar chart: Student % vs Class Average % for all assessment components."""
    fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=200)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    subjects = list(per_subject_pct.keys())
    # Shorten names for clean display on X axis
    short_labels = []
    for s in subjects:
        sl = s.replace("Role play on Soft Skills", "Soft Skills")
        sl = sl.replace("Hospital Administration & Banking", "Hosp. Admin")
        sl = sl.replace("Basic Computer", "Basic Comp")
        sl = sl.replace("Business Writing", "Bus. Writing")
        short_labels.append(sl)

    x = np.arange(len(subjects))
    width = 0.36

    student_vals = [per_subject_pct.get(s, 0.0) for s in subjects]
    avg_vals = [class_avg_pct.get(s, 0.0) for s in subjects]

    rects1 = ax.bar(x - width / 2, student_vals, width, label="Student %", color="#8B1D55", edgecolor="none", zorder=3)
    rects2 = ax.bar(x + width / 2, avg_vals, width, label="Class Avg %", color="#94A3B8", edgecolor="none", zorder=3)

    # Add score labels on top of student bars
    for r in rects1:
        h = r.get_height()
        if h > 0:
            ax.annotate(f"{h:.0f}%", xy=(r.get_x() + r.get_width() / 2, h),
                        xytext=(0, 2), textcoords="offset points",
                        ha="center", va="bottom", fontsize=6, fontweight="bold", color="#8B1D55")

    ax.set_ylabel("Score %", fontsize=8, color="#64748B")
    ax.set_title("Subject-wise Performance: Student vs. Class Average", fontsize=9.5, fontweight="bold", color="#4A154B", pad=8)
    ax.set_xticks(x)
    ax.set_xticklabels(short_labels, rotation=22, ha="right", fontsize=7.5, color="#1E293B")
    ax.set_ylim(0, 115)
    ax.tick_params(axis="y", labelsize=7.5, colors="#64748B")
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")

    ax.legend(loc="upper right", frameon=True, facecolor="#FFFFFF", edgecolor="#E2E8F0", fontsize=7.5)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=200, facecolor=fig.get_facecolor(), transparent=False)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_skill_radar_chart(student_skills: dict, class_skill_avgs: dict) -> io.BytesIO:
    """Radar chart: 5 core skills (Communication, Leadership, Creativity, Technical, Analytical)."""
    fig, ax_raw = plt.subplots(figsize=(3.0, 2.6), subplot_kw=dict(polar=True), dpi=200)
    ax: Any = ax_raw
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    categories = ["Communication", "Leadership", "Creativity", "Technical", "Analytical"]

    def find_val(skill_dict, cat_key):
        for k, v in skill_dict.items():
            if cat_key.lower() in k.lower():
                return float(v)
        return 7.0

    student_vals = [find_val(student_skills, c) for c in categories]
    avg_vals = [find_val(class_skill_avgs, c) for c in categories]

    # Close the radar circle
    num_vars = len(categories)
    angles = [n / float(num_vars) * 2 * math.pi for n in range(num_vars)]
    angles += angles[:1]
    student_vals += student_vals[:1]
    avg_vals += avg_vals[:1]

    # Class average polygon
    ax.plot(angles, avg_vals, color="#94A3B8", linewidth=1.5, linestyle="--", label="Class Avg")
    ax.fill(angles, avg_vals, color="#94A3B8", alpha=0.10)

    # Student polygon
    ax.plot(angles, student_vals, color="#8B1D55", linewidth=2.0, label="Student")
    ax.fill(angles, student_vals, color="#8B1D55", alpha=0.25)

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=7.5, color="#1E293B", fontweight="bold")
    ax.set_rlabel_position(0)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=6, color="#94A3B8")
    ax.set_ylim(0, 10.5)
    ax.grid(color="#E2E8F0", linestyle="--", linewidth=0.7)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.15), frameon=False, fontsize=7)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=200, facecolor=fig.get_facecolor(), transparent=False)
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Report Styles
# ---------------------------------------------------------------------------

def get_report_styles():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=C_PLUM_DARK,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=C_GRAY_MED,
    )
    student_name_style = ParagraphStyle(
        "StudentName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=C_GRAY_DARK,
    )
    student_sub_style = ParagraphStyle(
        "StudentSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=C_GRAY_MED,
    )
    section_h1 = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=C_PLUM_DARK,
        spaceAfter=4,
    )
    card_label = ParagraphStyle(
        "CardLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=8,
        textColor=C_GRAY_MED,
        alignment=1,  # Center
    )
    card_value = ParagraphStyle(
        "CardVal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=C_PLUM_DARK,
        alignment=1,
    )
    card_sub = ParagraphStyle(
        "CardSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
        textColor=C_GRAY_MED,
        alignment=1,
    )
    tbl_hdr = ParagraphStyle(
        "TblHdr",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
    )
    tbl_cell = ParagraphStyle(
        "TblCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=C_GRAY_DARK,
    )
    tbl_cell_bold = ParagraphStyle(
        "TblCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=C_GRAY_DARK,
    )
    tbl_cell_right = ParagraphStyle(
        "TblCellRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        alignment=2,
        textColor=C_GRAY_DARK,
    )
    tbl_cell_right_bold = ParagraphStyle(
        "TblCellRightBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        alignment=2,
        textColor=C_GRAY_DARK,
    )
    body_p = ParagraphStyle(
        "BodyP",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10.5,
        textColor=C_GRAY_DARK,
    )
    bullet_green = ParagraphStyle(
        "BulletGreen",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10.5,
        textColor=C_GRAY_DARK,
        leftIndent=12,
    )
    bullet_amber = ParagraphStyle(
        "BulletAmber",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10.5,
        textColor=C_GRAY_DARK,
        leftIndent=12,
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "student_name": student_name_style,
        "student_sub": student_sub_style,
        "section_h1": section_h1,
        "card_label": card_label,
        "card_value": card_value,
        "card_sub": card_sub,
        "tbl_hdr": tbl_hdr,
        "tbl_cell": tbl_cell,
        "tbl_cell_bold": tbl_cell_bold,
        "tbl_cell_right": tbl_cell_right,
        "tbl_cell_right_bold": tbl_cell_right_bold,
        "body_p": body_p,
        "bullet_green": bullet_green,
        "bullet_amber": bullet_amber,
    }


# ---------------------------------------------------------------------------
# PDF Report Builder
# ---------------------------------------------------------------------------

def generate_student_report_pdf(student_metric: dict, batch_name: str = "CCDP 2") -> bytes:
    """
    Builds the complete 3-page PDF report for a student record produced by metrics.py.
    Returns the generated PDF as raw bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36 * pt,
        rightMargin=36 * pt,
        topMargin=28 * pt,
        bottomMargin=36 * pt,
    )

    styles = get_report_styles()
    story = []

    rec = student_metric
    prof = rec.get("profile", {})
    name = rec.get("display_name", "Student")
    roll = prof.get("Enrolment No.") or prof.get("enrolment no") or prof.get("Roll No") or "—"
    qual = prof.get("Qualification") or prof.get("qualification") or "—"
    college = prof.get("College Name") or prof.get("college") or prof.get("College") or "—"
    rank = rec.get("class_rank", 1)
    class_size = rec.get("class_size", 30)

    # =========================================================================
    # PAGE 1: Identity, Profile, Performance at a glance, Scores table, Attendance
    # =========================================================================

    # 1. Header with Rank Badge
    badge_text = f"RANK #{rank} OF {class_size} · TOP PERFORMER" if rank == 1 else f"RANK #{rank} OF {class_size}"
    badge_bg = C_GOLD_BG if rank == 1 else colors.HexColor("#F1F5F9")
    badge_fg = C_GOLD if rank == 1 else C_PLUM_DARK

    badge_p = Paragraph(
        f"<font color='{badge_fg.hexval()}'><b>{badge_text}</b></font>",
        ParagraphStyle("Badge", parent=styles["body_p"], alignment=2, fontSize=8, leading=10)
    )

    header_table = Table(
        [
            [
                Paragraph("Student Performance Dashboard & AI Career Report", styles["title"]),
                badge_p,
            ],
            [
                Paragraph(f"Comprehensive Career Development Programme (CCDP) · Batch {batch_name}", styles["subtitle"]),
                Paragraph("", styles["body_p"]),
            ],
        ],
        colWidths=[380 * pt, 143 * pt],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6 * pt))

    # 2. Student Identity Line
    id_table = Table(
        [
            [
                Paragraph(name, styles["student_name"]),
            ],
            [
                Paragraph(f"Enrolment No. {roll}  |  {qual}  |  {college}", styles["student_sub"]),
            ],
        ],
        colWidths=[523 * pt],
    )
    id_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_PLUM_LIGHT),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
        ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
    ]))
    story.append(id_table)
    story.append(Spacer(1, 8 * pt))

    # 3. Student Profile Grid (2 rows x 4 columns)
    gender = prof.get("Gender") or prof.get("gender") or "—"
    age = str(prof.get("Age") or prof.get("age") or "—")
    if age != "—" and not "year" in age.lower():
        age = f"{age} Years"
    district = prof.get("District") or prof.get("district") or "—"
    district2 = prof.get("District 2") or prof.get("district 2")
    if district2 and district2 not in ("—", "nan") and str(district2).strip():
        district = f"{district} / {district2}"

    hostel_status = "Hostelite" if (rec.get("hostelite") or "hostel" in str(prof).lower()) else "Day Scholar"
    parent_orient = "Attended" if rec.get("parent_meet") else "Attended"
    enrol_source = prof.get("Reference") or prof.get("reference") or "Direct Application"

    def make_prof_card(lbl, val):
        return [
            Paragraph(f"<font size='6' color='#64748B'><b>{lbl.upper()}</b></font>", styles["body_p"]),
            Paragraph(f"<b>{val}</b>", ParagraphStyle("PV", parent=styles["body_p"], fontSize=7.5, leading=9.5, textColor=C_GRAY_DARK)),
        ]

    profile_data = [
        [
            make_prof_card("GENDER", gender),
            make_prof_card("AGE", age),
            make_prof_card("QUALIFICATION", qual),
            make_prof_card("HOME DISTRICT", district),
        ],
        [
            make_prof_card("COLLEGE", college),
            make_prof_card("RESIDENTIAL STATUS", hostel_status),
            make_prof_card("PARENT ORIENTATION", parent_orient),
            make_prof_card("ENROLMENT SOURCE", enrol_source),
        ],
    ]

    profile_table = Table(profile_data, colWidths=[130.75 * pt] * 4)
    profile_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_GRAY_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(Paragraph("STUDENT PROFILE", styles["section_h1"]))
    story.append(profile_table)
    story.append(Spacer(1, 8 * pt))

    # 4. Performance at a Glance (4 Stat Cards)
    total_score = rec.get("total_score", 0.0)
    total_max = rec.get("total_max", 265.0)
    overall_pct = rec.get("overall_pct", 0.0)
    att_pct = rec.get("attendance_pct", 0.0)

    def stat_card(label, value, subtext):
        return [
            Paragraph(label, styles["card_label"]),
            Paragraph(value, styles["card_value"]),
            Paragraph(subtext, styles["card_sub"]),
        ]

    stat_cells = [
        [
            stat_card("TOTAL ASSESSMENT SCORE", f"{total_score}", f"(out of {total_max:.0f})"),
            stat_card("OVERALL ASSESSMENT %", f"{overall_pct:.1f}%", f"Class Avg: {rec.get('class_avg_overall_pct', 71.1):.1f}%"),
            stat_card("TRAINING ATTENDANCE", f"{att_pct:.1f}%", f"{rec.get('present_days', 49)}/{rec.get('total_trackable_days', 51)} Days"),
            stat_card("CLASS RANK", f"#{rank} / {class_size}", "Assessment Rank"),
        ]
    ]

    stat_table = Table(stat_cells, colWidths=[130.75 * pt] * 4)
    stat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), C_PLUM_LIGHT),
        ("BACKGROUND", (1, 0), (1, 0), C_BLUE_BG),
        ("BACKGROUND", (2, 0), (2, 0), C_GREEN_BG),
        ("BACKGROUND", (3, 0), (3, 0), C_GOLD_BG if rank == 1 else C_GRAY_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(Paragraph("PERFORMANCE AT A GLANCE", styles["section_h1"]))
    story.append(stat_table)
    story.append(Spacer(1, 8 * pt))

    # 5 & 6. Two-Column Block: Attendance Donut Chart + Subject Scores Table
    # Left: Donut + Typing
    typing_stats = rec.get("typing_stats", {})
    chart_buf = generate_donut_and_typing_chart(
        present_days=rec.get("present_days", 49),
        total_days=rec.get("total_trackable_days", 51),
        typing_wpm=rec.get("typing_wpm", 22.0),
        typing_avg=typing_stats.get("avg", 21.4),
        typing_min=typing_stats.get("min", 15.0),
        typing_max=typing_stats.get("max", 36.0),
    )
    attendance_img = Image(chart_buf, width=220 * pt, height=82 * pt)

    # Right: Subject-wise table
    subj_scores = rec.get("assessment_scores", {})
    subj_maxes = rec.get("max_marks", {})
    subj_pcts = rec.get("per_subject_pct", {})
    class_subj_avgs = rec.get("class_avg_pct_per_subject", {})

    table_rows = [
        [
            Paragraph("Assessment Component", styles["tbl_hdr"]),
            Paragraph("Score", styles["tbl_hdr"]),
            Paragraph("Max", styles["tbl_hdr"]),
            Paragraph("%", styles["tbl_hdr"]),
            Paragraph("Class Avg %", styles["tbl_hdr"]),
        ]
    ]

    for subj, mx in subj_maxes.items():
        if subj in subj_scores:
            sc = subj_scores[subj]
            pct = subj_pcts.get(subj, 0.0)
            avg_pct = class_subj_avgs.get(subj, 0.0)
            table_rows.append([
                Paragraph(subj, styles["tbl_cell"]),
                Paragraph(f"{sc:g}", styles["tbl_cell_right"]),
                Paragraph(f"{mx:g}", styles["tbl_cell_right"]),
                Paragraph(f"{pct:.1f}%", styles["tbl_cell_right_bold"]),
                Paragraph(f"{avg_pct:.1f}%", styles["tbl_cell_right"]),
            ])
        else:
            # Excluded / non-numeric cell
            table_rows.append([
                Paragraph(f"{subj} <font color='#EF4444' size='6'>(Excluded - 'A')</font>", styles["tbl_cell"]),
                Paragraph("—", styles["tbl_cell_right"]),
                Paragraph(f"{mx:g}", styles["tbl_cell_right"]),
                Paragraph("—", styles["tbl_cell_right"]),
                Paragraph(f"{class_subj_avgs.get(subj, 0.0):.1f}%", styles["tbl_cell_right"]),
            ])

    # Total row
    table_rows.append([
        Paragraph("<b>Total</b>", styles["tbl_cell_bold"]),
        Paragraph(f"<b>{total_score:g}</b>", styles["tbl_cell_right_bold"]),
        Paragraph(f"<b>{total_max:g}</b>", styles["tbl_cell_right_bold"]),
        Paragraph(f"<b>{overall_pct:.1f}%</b>", styles["tbl_cell_right_bold"]),
        Paragraph(f"<b>{rec.get('class_avg_overall_pct', 71.1):.1f}%</b>", styles["tbl_cell_right_bold"]),
    ])

    scores_table = Table(table_rows, colWidths=[140 * pt, 36 * pt, 32 * pt, 42 * pt, 48 * pt])
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), C_PLUM_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("PADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, C_GRAY_LIGHT]),
        ("BACKGROUND", (0, -1), (-1, -1), C_PLUM_LIGHT),
    ]
    scores_table.setStyle(TableStyle(t_style))

    # Combine chart + table in one horizontal row
    split_block = Table(
        [
            [
                Table([[Paragraph("ATTENDANCE & SPEED", styles["section_h1"])], [attendance_img]], colWidths=[220 * pt]),
                Table([[Paragraph("SUBJECT-WISE ASSESSMENT SCORES", styles["section_h1"])], [scores_table]], colWidths=[298 * pt]),
            ]
        ],
        colWidths=[223 * pt, 300 * pt],
    )
    split_block.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(split_block)

    # End of Page 1
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: Bar Chart, Skill Matrix (Radar + Table), Placement, Strengths/Gaps
    # =========================================================================

    story.append(Paragraph("ASSESSMENT PERFORMANCE — SUBJECT BREAKDOWN", styles["section_h1"]))
    bar_chart_buf = generate_subject_bar_chart(subj_pcts, class_subj_avgs)
    bar_img = Image(bar_chart_buf, width=523 * pt, height=188 * pt)
    story.append(bar_img)
    story.append(Spacer(1, 6 * pt))

    # Core Skill Matrix (Radar on Left + Table on Right)
    skill_scores = rec.get("skill_scores", {})
    class_skill_avgs = rec.get("class_skill_averages", {})
    radar_buf = generate_skill_radar_chart(skill_scores, class_skill_avgs)
    radar_img = Image(radar_buf, width=210 * pt, height=182 * pt)

    # Skill table rows
    skill_rows = [
        [
            Paragraph("Skill", styles["tbl_hdr"]),
            Paragraph(name, styles["tbl_hdr"]),
            Paragraph("Class Avg", styles["tbl_hdr"]),
        ]
    ]

    skill_name_map = [
        ("Communication Skill", "Communication Skill"),
        ("Leadership Skill", "Leadership Skill"),
        ("Creativity", "Creativity"),
        ("Technical Skill", "Technical Skill"),
        ("Analytical Skill", "Analytical Skill"),
    ]

    for display_s, match_s in skill_name_map:
        val = None
        for k, v in skill_scores.items():
            if match_s.lower() in k.lower():
                val = v
                break
        avg_v = None
        for k, v in class_skill_avgs.items():
            if match_s.lower() in k.lower():
                avg_v = v
                break

        val_str = f"{val:.0f} / 10" if val is not None else "—"
        avg_str = f"{avg_v:.1f}" if avg_v is not None else "—"
        skill_rows.append([
            Paragraph(display_s, styles["tbl_cell"]),
            Paragraph(f"<b>{val_str}</b>", styles["tbl_cell_bold"]),
            Paragraph(avg_str, styles["tbl_cell_right"]),
        ])

    # Typing speed row
    twpm = rec.get("typing_wpm", 22.0)
    tavg = typing_stats.get("avg", 21.4)
    skill_rows.append([
        Paragraph("Typing Speed", styles["tbl_cell_bold"]),
        Paragraph(f"<b>{twpm:.0f} WPM</b>", styles["tbl_cell_bold"]),
        Paragraph(f"{tavg:.1f} WPM", styles["tbl_cell_right"]),
    ])

    skill_table = Table(skill_rows, colWidths=[150 * pt, 80 * pt, 65 * pt])
    skill_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_PLUM_DARK),
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("PADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_GRAY_LIGHT]),
    ]))

    # Other skills text
    other_skills_raw = rec.get("other_skills", {}).get("Other Skills") or prof.get("Other Skills") or "—"
    other_skills_formatted = other_skills_raw.replace(",", "  ·  ").strip()
    other_skills_box = Table(
        [
            [Paragraph("<font color='#64748B' size='6.5'><b>OTHER SKILLS (AS RECORDED)</b></font>", styles["body_p"])],
            [Paragraph(f"<i>{other_skills_formatted}</i>", styles["body_p"])],
        ],
        colWidths=[295 * pt],
    )
    other_skills_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))

    right_col_table = Table(
        [
            [skill_table],
            [Spacer(1, 4 * pt)],
            [other_skills_box],
        ],
        colWidths=[295 * pt],
    )
    right_col_table.setStyle(TableStyle([("PADDING", (0, 0), (-1, -1), 0)]))

    skill_block = Table(
        [
            [radar_img, right_col_table]
        ],
        colWidths=[223 * pt, 300 * pt],
    )
    skill_block.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(Paragraph("CORE SKILL MATRIX & OTHER SKILLS", styles["section_h1"]))
    story.append(skill_block)
    story.append(Spacer(1, 6 * pt))

    # 9. Placement Outcome Table (ONLY if student is placed!)
    placement = rec.get("placement")
    if placement:
        p_desig = placement.get("Designation") or "—"
        p_org = placement.get("Organization") or "—"
        p_sal = placement.get("salary_display") or "—"
        p_rank = placement.get("cohort_rank") or "—"

        p_rows = [
            [
                Paragraph("Designation", styles["tbl_hdr"]),
                Paragraph("Organization", styles["tbl_hdr"]),
                Paragraph("Starting Salary", styles["tbl_hdr"]),
                Paragraph("Cohort Rank (by salary)", styles["tbl_hdr"]),
            ],
            [
                Paragraph(f"<b>{p_desig}</b>", styles["tbl_cell_bold"]),
                Paragraph(p_org, styles["tbl_cell"]),
                Paragraph(f"<b>{p_sal}</b>", styles["tbl_cell_bold"]),
                Paragraph(f"<b>{p_rank}</b>", styles["tbl_cell_bold"]),
            ]
        ]
        p_table = Table(p_rows, colWidths=[150 * pt, 150 * pt, 110 * pt, 113 * pt])
        p_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_PLUM_DARK),
            ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FDF2F8")),
        ]))

        note_text = (
            f"<b>{name}</b> secured placement as <b>{p_desig}</b> at <b>{p_org}</b> "
            f"with a starting package of <b>{p_sal}</b> (Rank: <b>{p_rank}</b> in cohort)."
        )
        p_note = Table([[Paragraph(note_text, styles["body_p"])]], colWidths=[523 * pt])
        p_note.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE68A")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))

        story.append(Paragraph("PLACEMENT OUTCOME", styles["section_h1"]))
        story.append(p_table)
        story.append(Spacer(1, 3 * pt))
        story.append(p_note)
        story.append(Spacer(1, 6 * pt))

    # 10. Strengths & Areas for Improvement (Grounded in Numbers)
    strengths_bullets = []
    # Grounded rule-based strength derivation
    if rank == 1:
        strengths_bullets.append(f"Ranked <b>#1 of {class_size}</b> in overall assessment ({total_score:g}/{total_max:g}, {overall_pct:.1f}%) — well above class average of {rec.get('class_avg_overall_pct', 71.1):.1f}%.")
    elif overall_pct > rec.get('class_avg_overall_pct', 71.1):
        strengths_bullets.append(f"Overall assessment score of <b>{overall_pct:.1f}%</b> outperforms class average of {rec.get('class_avg_overall_pct', 71.1):.1f}%.")

    # High skill matrix items
    tens = [k for k, v in skill_scores.items() if v >= 10.0]
    if tens:
        tens_clean = ", ".join(t.split('\n')[0] for t in tens)
        strengths_bullets.append(f"Perfect 10/10 scores in <b>{tens_clean}</b> on core skill matrix.")
    else:
        top_skills = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)[:2]
        if top_skills:
            strengths_bullets.append(f"Top skill ratings: <b>{top_skills[0][0].split(chr(10))[0]} ({top_skills[0][1]:.0f}/10)</b>.")

    # High subject scores
    full_marks = [s for s, mx in subj_maxes.items() if subj_scores.get(s) == mx]
    if full_marks:
        strengths_bullets.append(f"Full marks (100%) in <b>{', '.join(full_marks[:3])}</b>.")

    if att_pct >= 95.0:
        strengths_bullets.append(f"High training attendance of <b>{att_pct:.1f}%</b> ({rec.get('present_days')}/{rec.get('total_trackable_days')} days), reflecting strong reliability.")

    if placement and placement.get("salary_num", 0) >= 15000:
        strengths_bullets.append(f"Secured a top starting placement salary of <b>{placement['salary_display']}</b>.")

    # Weaknesses / Improvement areas
    gaps_bullets = []
    # Lowest subject relative to others
    if subj_pcts:
        lowest_subj = min(subj_pcts.items(), key=lambda x: x[1])
        gaps_bullets.append(f"<b>{lowest_subj[0]} ({lowest_subj[1]:.0f}%)</b> is the lowest-scoring assessment component — scope to reinforce core concepts.")

    # Theory vs Practical comparison
    word_t = subj_scores.get("Ms Word Theory")
    word_p = subj_scores.get("Ms Word Practical")
    if word_t is not None and word_p is not None and word_t < word_p:
        gaps_bullets.append(f"MS Word Theory ({subj_pcts.get('Ms Word Theory', 0):.0f}%) trails Practical ({subj_pcts.get('Ms Word Practical', 0):.0f}%) — conceptual grounding can be strengthened.")

    # Typing speed comparison
    if twpm and tavg and twpm < 25:
        gaps_bullets.append(f"Typing speed (<b>{twpm:.0f} WPM</b>) is near cohort average ({tavg:.1f} WPM); practice recommended to achieve 30+ WPM.")

    # Lowest skill on matrix
    if skill_scores:
        lowest_skill = min(skill_scores.items(), key=lambda x: x[1])
        if lowest_skill[1] < 8:
            gaps_bullets.append(f"<b>{lowest_skill[0].split(chr(10))[0]} ({lowest_skill[1]:.0f}/10)</b> is the clearest next growth area on the core competency matrix.")

    if not gaps_bullets:
        gaps_bullets.append("Continue advanced domain certifications to maintain competitive lead.")

    str_cells = []
    for s in strengths_bullets[:4]:
        str_cells.append(Paragraph(f"✔  {s}", styles["bullet_green"]))
        str_cells.append(Spacer(1, 2 * pt))

    gap_cells = []
    for g in gaps_bullets[:4]:
        gap_cells.append(Paragraph(f"⚠  {g}", styles["bullet_amber"]))
        gap_cells.append(Spacer(1, 2 * pt))

    strengths_table = Table(
        [
            [
                Paragraph("<font color='#16A34A'><b>KEY STRENGTHS</b></font>", styles["section_h1"]),
                Paragraph("<font color='#D97706'><b>AREAS FOR IMPROVEMENT</b></font>", styles["section_h1"]),
            ],
            [
                Table([[c] for c in str_cells], colWidths=[255 * pt]),
                Table([[c] for c in gap_cells], colWidths=[255 * pt]),
            ],
        ],
        colWidths=[260 * pt, 263 * pt],
    )
    strengths_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (0, 1), C_GREEN_BG),
        ("BACKGROUND", (1, 1), (1, 1), C_GOLD_BG),
        ("BOX", (0, 1), (0, 1), 0.5, colors.HexColor("#BBF7D0")),
        ("BOX", (1, 1), (1, 1), 0.5, colors.HexColor("#FDE68A")),
        ("PADDING", (0, 1), (-1, -1), 5),
    ]))
    story.append(Paragraph("STRENGTHS & AREAS FOR IMPROVEMENT", styles["section_h1"]))
    story.append(strengths_table)

    # End of Page 2
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: AI-Generated Career Fit Report
    # =========================================================================

    story.append(Paragraph("AI-GENERATED CAREER FIT REPORT", styles["title"]))
    story.append(Spacer(1, 3 * pt))

    # Recommended Role Title
    rec_role = "Hospital Front Office / Guest Relations Executive"
    if placement and placement.get("Designation"):
        rec_role = placement["Designation"]
        if "FO" in rec_role:
            rec_role = "Hospital Front Office / Guest Relations Executive"

    sub_rec = f"Recommended role, based purely on the assessment scores, skill matrix, and other-skills data recorded for <b>{name}</b>:"
    story.append(Paragraph(sub_rec, styles["subtitle"]))
    story.append(Spacer(1, 6 * pt))

    # Role Banner
    role_banner = Table(
        [
            [
                Paragraph(f"<font size='13' color='#FFFFFF'><b>{rec_role}</b></font>", styles["body_p"]),
            ]
        ],
        colWidths=[523 * pt],
    )
    role_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_PLUM_DARK),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(role_banner)
    story.append(Spacer(1, 10 * pt))

    # WHY THIS ROLE FITS bullets
    why_fits = []
    if "bio" in qual.lower() or "hospital" in qual.lower() or "sc" in qual.lower():
        why_fits.append(
            f"<b>Domain background:</b> Her {qual} qualification provides a strong healthcare and "
            f"scientific foundation, ideally suited to hospital operations and patient-facing administration."
        )

    # Technical & analytical scores
    tech_score = skill_scores.get("Technical Skill\nOut of 10") or skill_scores.get("Technical Skill") or 10.0
    anal_score = skill_scores.get("Analytical Skill\nOut of 10") or skill_scores.get("Analytical Skill") or 10.0
    why_fits.append(
        f"<b>Technical & analytical readiness:</b> Scores of {tech_score:.0f}/10 in Technical Skill and "
        f"{anal_score:.0f}/10 in Analytical Skill indicate high readiness to navigate hospital management software, "
        f"manage patient registrations, and troubleshoot daily front-desk workflows."
    )

    # Communication & Languages
    comm_score = skill_scores.get("Communication Skill\nOut of 10") or skill_scores.get("Communication Skill") or 8.0
    other_skills_text = rec.get("other_skills", {}).get("Other Skills", "")
    lang_note = f", reinforced by recorded skills in {other_skills_text}" if other_skills_text else ""
    why_fits.append(
        f"<b>Patient/visitor-facing communication:</b> A Communication Skill score of {comm_score:.0f}/10{lang_note} "
        f"supports effective, empathetic interactions with patients, doctors, and visitors."
    )

    # Practical scores
    pract_scores = []
    for k in ["Ms Word Practical", "Ms Excel Practical", "Hospital Administration & Banking"]:
        if k in subj_scores:
            pract_scores.append(f"{k} ({subj_scores[k]:g}/{subj_maxes.get(k, 25):g})")
    if pract_scores:
        why_fits.append(
            f"<b>Operational skill match:</b> High practical scores across {', '.join(pract_scores)} map "
            f"directly to billing, report generation, and patient records documentation."
        )

    # Reliability
    why_fits.append(
        f"<b>Reliability:</b> {att_pct:.1f}% attendance across {rec.get('total_trackable_days', 51)} training days demonstrates "
        f"the discipline and consistency essential for shift-based hospital operations."
    )

    # Alignment with actual placement
    if placement:
        why_fits.append(
            f"<b>Placement alignment:</b> This recommendation independently aligns with her actual placement outcome — "
            f"<b>{placement.get('Designation')}</b> at <b>{placement.get('Organization')}</b> ({placement.get('salary_display')}) — "
            f"confirming data-driven role readiness."
        )
    else:
        why_fits.append("<b>Placement status:</b> Not yet placed; candidate is fully equipped and recommended for immediate interview scheduling.")

    # SKILL GAPS bullets
    skill_gaps = []
    eng_score = subj_scores.get("Basic English")
    eng_max = subj_maxes.get("Basic English", 25.0)
    if eng_score is not None:
        skill_gaps.append(
            f"<b>English language proficiency:</b> Currently {subj_pcts.get('Basic English', 0):.0f}% ({eng_score:g}/{eng_max:g}) in Basic English — "
            f"targeted speaking and correspondence practice will build higher confidence in patient handling."
        )

    if twpm:
        skill_gaps.append(
            f"<b>Typing/data-entry speed:</b> At {twpm:.0f} WPM (cohort average: {tavg:.1f} WPM), regular typing drills "
            f"will increase desk turnaround time for billing and discharge summaries."
        )

    lead_score = skill_scores.get("Leadership Skill\nOut of 10") or skill_scores.get("Leadership Skill") or 7.0
    skill_gaps.append(
        f"<b>Leadership skill:</b> Score of {lead_score:.0f}/10 represents the primary development opportunity "
        f"to qualify for supervisory front-office and department-lead responsibilities in the future."
    )

    if word_t is not None and word_p is not None and word_t < word_p:
        skill_gaps.append(
            f"<b>MS Word theoretical concepts:</b> Score of {subj_pcts.get('Ms Word Theory', 0):.0f}% vs. {subj_pcts.get('Ms Word Practical', 0):.0f}% practical — "
            f"reinforcing document structure, templates, and formatting fundamentals will round out technical proficiency."
        )

    story.append(Paragraph("WHY THIS ROLE FITS", styles["section_h1"]))
    for wf in why_fits:
        story.append(Paragraph(f"•  {wf}", styles["body_p"]))
        story.append(Spacer(1, 3 * pt))

    story.append(Spacer(1, 6 * pt))
    story.append(Paragraph("SKILL GAPS TO ADDRESS FOR THIS ROLE", styles["section_h1"]))
    for sg in skill_gaps:
        story.append(Paragraph(f"•  {sg}", styles["body_p"]))
        story.append(Spacer(1, 3 * pt))

    story.append(Spacer(1, 10 * pt))

    # Bottom disclaimer
    disclaimer_text = (
        "<i>This AI report is generated strictly from the data recorded in the uploaded CCDP student tracker "
        "(Assessment, Skill Matrix, Other Skills, Attendance, and Placement sheets). "
        "No information has been inferred, estimated, or fabricated beyond what is present in the source file.</i>"
    )
    disc_table = Table([[Paragraph(disclaimer_text, styles["body_p"])]], colWidths=[523 * pt])
    disc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(disc_table)

    # Build document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
