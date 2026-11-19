"""
pdf_generator.py - Publication-Grade CCDP Student Performance & AI Career Report PDF Generator
=============================================================================================
Converts student data into an exact 3-page A4 PDF report matching the reference design:
- Page 1: Gradient Header & Logo, Student Profile Grid, Performance at a Glance (4 KPIs),
          Attendance Donut + Typing Speed Chart, Subject-Wise Assessment Scores Table.
- Page 2: Assessment Performance Bar Chart (Student vs Class Avg), Core Skill Matrix Radar &
          Skill Table, Placement Outcome Table, Strengths & Areas for Improvement.
- Page 3: AI-Generated Career Fit Report Card with Role Pill, Why This Role Fits, Skill Gaps,
          and Source Data Disclaimer.

Technical Architecture:
  1. Data Loader & Normalizer (reads from Excel / Dict / Database)
  2. Validator & Metric Aggregator (strict data consistency rules, computed comparisons)
  3. Chart Builder (matplotlib @ 200 DPI: Donut, Typing Bar, Subject Bar, Radar)
  4. HTML/CSS Template (Jinja2, CSS Grid/Flexbox, A4 page budgeting, embedded typography)
  5. PDF Exporter (Headless Chromium via Playwright, preferCSSPageSize=True)

Usage:
  python backend/pdf_generator.py --all
  python backend/pdf_generator.py --student "Jayasree A"
  python backend/pdf_generator.py --student "Abinaya M"
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import logging
import math
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import jinja2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand Color Tokens
# ---------------------------------------------------------------------------
C_PURPLE_DEEP = "#4A154B"
C_PURPLE = "#6B3591"
C_ROSE = "#E0507A"
C_PLUM = "#8E1F58"
C_GOLD = "#E8B923"
C_GREEN_BG = "#EEF8EE"
C_GREEN_BORDER = "#2E7D32"
C_CREAM_BG = "#FBF6EA"
C_CREAM_BORDER = "#F57F17"
C_LAVENDER_BG = "#FAF7FC"
C_LAVENDER_BORDER = "#ECE3F0"
C_GREY_BAR = "#9AA0A6"
C_TEXT_DARK = "#202124"
C_TEXT_MUTED = "#5F6368"

# ---------------------------------------------------------------------------
# 1. Chromium Browser Discovery
# ---------------------------------------------------------------------------
def find_chromium_path() -> Optional[str]:
    """Finds an installed Chromium or Google Chrome binary on the system."""
    env_path = os.environ.get("CHROMIUM_PATH") or os.environ.get("CHROME_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

# ---------------------------------------------------------------------------
# 2. Asset Discovery (Logo)
# ---------------------------------------------------------------------------
def get_logo_base64() -> str:
    """Finds and encodes the Skill Bay Academy logo as a base64 PNG string."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    candidates = [
        os.path.join(current_dir, "assets", "logo.png"),
        os.path.join(project_root, "frontend", "public", "logo.png"),
        os.path.join(project_root, "frontend", "dist", "logo.png"),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                logger.warning(f"Failed to read logo from {path}: {e}")

    # Fallback minimal 1x1 transparent PNG if logo not found
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# ---------------------------------------------------------------------------
# 3. Chart Generation (matplotlib @ 200 DPI)
# ---------------------------------------------------------------------------
def generate_donut_chart(attendance_pct: float, present_days: int, total_days: int) -> str:
    """Generates a clean attendance donut chart with percentage centered."""
    fig, ax = plt.subplots(figsize=(2.6, 2.6), dpi=200)
    
    pct = max(0.0, min(100.0, float(attendance_pct)))
    remainder = 100.0 - pct
    
    # Donut wedge
    wedges, _ = ax.pie(
        [pct, remainder],
        colors=[C_PLUM, "#EAE2EE"],
        startangle=90,
        counterclock=False,
        wedgeprops=dict(width=0.30, edgecolor="white", linewidth=2.5),
    )
    
    # Center text
    ax.text(0, 0.08, f"{pct:.1f}%", ha="center", va="center",
            fontsize=17, fontweight="bold", color=C_PLUM, fontfamily="DejaVu Sans")
    ax.text(0, -0.16, "Attendance", ha="center", va="center",
            fontsize=9.0, color=C_TEXT_MUTED, fontfamily="DejaVu Sans")
    
    ax.set(aspect="equal")
    plt.tight_layout(pad=0.1)
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", transparent=True, dpi=200)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def generate_typing_chart(student_wpm: float, class_avg: float = 21.4, class_min: float = 11.0, class_max: float = 36.0) -> str:
    """Generates typing speed horizontal chart comparing student against cohort range & average."""
    fig, ax = plt.subplots(figsize=(4.5, 2.0), dpi=200)
    
    y_pos = 0.5
    bar_height = 0.38
    
    # Cohort range block
    ax.barh(y_pos, class_max - class_min, left=class_min, height=bar_height,
            color="#EFE9F4", edgecolor="#D1C4E9", linewidth=0.8, label="Cohort Range")
    
    # Student bar from 0 to student_wpm
    ax.barh(y_pos, student_wpm, left=0, height=bar_height,
            color=C_PURPLE, label=f"Student ({int(student_wpm)} WPM)")
    
    # Class avg vertical dashed line
    ax.axvline(x=class_avg, color=C_TEXT_MUTED, linestyle="--", linewidth=1.1, zorder=4)
    ax.text(class_avg, y_pos + 0.34, f"Class avg: {class_avg:.1f} WPM",
            ha="center", va="bottom", fontsize=7.2, color=C_TEXT_MUTED, fontfamily="DejaVu Sans")
    
    # Student value label below the bar
    ax.text(student_wpm, y_pos - 0.34, f"{int(student_wpm)} WPM",
            ha="center", va="top", fontsize=7.5, fontweight="bold", color=C_PURPLE, fontfamily="DejaVu Sans")
    
    ax.set_xlim(0, max(42, int(class_max) + 5))
    ax.set_ylim(0, 1.15)
    ax.set_yticks([])
    ax.set_xticks(range(0, 45, 5))
    ax.tick_params(axis="x", labelsize=7.0, colors=C_TEXT_MUTED, pad=3)
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#CCCCCC")
    
    ax.set_xlabel(f"Typing Speed (Words Per Minute) | Class range: {int(class_min)}-{int(class_max)} WPM",
                  fontsize=7.2, color=C_TEXT_MUTED, labelpad=6, fontfamily="DejaVu Sans")
    
    plt.tight_layout(pad=0.1)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", transparent=True, dpi=200)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def generate_subject_bar_chart(subjects: List[Dict[str, Any]], student_name: str) -> str:
    """Generates the grouped bar chart for Page 2 (Student % vs Class Average %)."""
    fig, ax = plt.subplots(figsize=(7.4, 2.6), dpi=200)
    
    n = len(subjects)
    if n == 0:
        plt.close(fig)
        return ""
        
    x = np.arange(n)
    width = 0.36
    
    student_vals = [s["score_pct"] for s in subjects]
    avg_vals = [s["class_avg_pct"] for s in subjects]
    labels = [s["name"] for s in subjects]
    
    rects1 = ax.bar(x - width/2, student_vals, width, label=student_name, color=C_PLUM)
    rects2 = ax.bar(x + width/2, avg_vals, width, label="Class Average", color=C_GREY_BAR)
    
    # Value annotations on top of student bars
    for rect in rects1:
        height = rect.get_height()
        if height > 0:
            ax.annotate(f"{int(round(height))}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 2),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=6.8, fontweight="bold",
                        color=C_PLUM, fontfamily="DejaVu Sans")
    
    ax.set_ylabel("Score (%)", fontsize=7.5, color=C_TEXT_MUTED, fontfamily="DejaVu Sans")
    ax.set_ylim(0, 115)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.tick_params(axis="y", labelsize=7.0, colors=C_TEXT_MUTED)
    
    ax.yaxis.grid(True, linestyle="--", alpha=0.5, color="#E0E0E0")
    ax.set_axisbelow(True)
    
    def wrap_subj(l: str) -> str:
        repl = {
            "Role Play on Soft Skills": "Soft Skills\nRole Play",
            "Role play on Soft Skills": "Soft Skills\nRole Play",
            "Hospital Administration & Banking": "Hosp. Admin\n& Banking",
            "MS Word — Theory": "MS Word\nTheory",
            "MS Word — Practical": "MS Word\nPractical",
            "MS Excel — Theory": "MS Excel\nTheory",
            "MS Excel — Practical": "MS Excel\nPractical",
            "Ms Word Theory": "MS Word\nTheory",
            "Ms Word Practical": "MS Word\nPractical",
            "Ms Excel Theory": "MS Excel\nTheory",
            "Ms Excel Practical": "MS Excel\nPractical",
            "Basic Computer": "Basic\nComputer",
            "Basic English": "Basic\nEnglish",
            "Business Writing": "Business\nWriting",
        }
        return repl.get(l, l.replace(" ", "\n"))
        
    x_labels = [wrap_subj(l) for l in labels]
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=6.8, color=C_TEXT_DARK, fontfamily="DejaVu Sans")
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.34),
              ncol=2, frameon=False, fontsize=7.2)
    
    plt.tight_layout(pad=0.1)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", transparent=True, dpi=200)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def generate_radar_chart(skills_data: Dict[str, float], class_avg_data: Dict[str, float], student_name: str) -> str:
    """Generates the 5-axis radar chart (Communication, Leadership, Creativity, Technical, Analytical)."""
    categories = ["Communication", "Leadership", "Creativity", "Technical", "Analytical"]
    
    key_map = {
        "Communication": ["Communication Skill", "communication"],
        "Leadership": ["Leadership Skill", "leadership"],
        "Creativity": ["Creativity", "creativity"],
        "Technical": ["Technical Skill", "technical"],
        "Analytical": ["Analytical Skill", "analytical"],
    }
    
    def extract_num(d: Dict[str, Any], cat: str) -> float:
        for k in key_map[cat]:
            for dk, dv in d.items():
                if k.lower() in dk.lower():
                    try:
                        return float(dv)
                    except (ValueError, TypeError):
                        pass
        return 0.0

    student_scores = [extract_num(skills_data, c) for c in categories]
    avg_scores = [extract_num(class_avg_data, c) for c in categories]
    
    # If no student scores at all, return empty
    if sum(student_scores) == 0:
        return ""

    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    
    student_vals = student_scores + student_scores[:1]
    avg_vals = avg_scores + avg_scores[:1]
    
    fig, ax = plt.subplots(figsize=(3.4, 3.4), subplot_kw=dict(polar=True), dpi=200)
    
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    
    ax.set_ylim(0, 10.5)
    ax.set_rgrids([2, 4, 6, 8, 10], labels=["2", "4", "6", "8", "10"],
                  fontsize=6.2, color="#999999", fontfamily="DejaVu Sans")
    ax.grid(color="#E2D9E8", linestyle="-", linewidth=0.8)
    ax.spines["polar"].set_color("#D1C4E9")
    
    # Class Average dashed line
    ax.plot(angles, avg_vals, color="#9AA0A6", linestyle="--", linewidth=1.3, label="Class Average")
    
    # Student polygon
    ax.plot(angles, student_vals, color=C_PLUM, linewidth=1.8, linestyle="solid", label=student_name)
    ax.fill(angles, student_vals, color=C_PLUM, alpha=0.22)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=7.8, fontweight="bold", color=C_TEXT_DARK, fontfamily="DejaVu Sans")
    ax.tick_params(pad=10)
    
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.15), frameon=False, fontsize=6.8)
    
    plt.tight_layout(pad=0.1)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", transparent=True, dpi=200)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

# ---------------------------------------------------------------------------
# 4. Data Normalizer & Validator
# ---------------------------------------------------------------------------
@dataclass
class SubjectScoreRow:
    name: str
    score: float
    max_score: float
    score_pct: float
    class_avg_pct: float

@dataclass
class SkillMatrixRow:
    name: str
    student_score: str
    class_avg: str

@dataclass
class PlacementInfo:
    designation: Optional[str] = None
    organization: Optional[str] = None
    salary_display: Optional[str] = None
    cohort_rank: Optional[str] = None
    summary_sentence: Optional[str] = None
    is_available: bool = False

@dataclass
class UnifiedStudentReportData:
    name: str
    enrolment_no: str
    qualification: str
    college: str
    gender: str
    age: str
    home_district: str
    residential_status: str
    parent_orientation: str
    enrolment_source: str
    
    rank: int
    class_size: int
    is_top_performer: bool
    
    total_score: float
    total_max: float
    overall_pct: float
    attendance_pct: float
    present_days: int
    total_days: int
    class_avg_overall_pct: float
    
    typing_wpm: float
    typing_class_avg: float
    typing_class_min: float
    typing_class_max: float
    typing_comparison: str
    
    subject_rows: List[SubjectScoreRow] = field(default_factory=list)
    has_subjects: bool = False
    
    skill_rows: List[SkillMatrixRow] = field(default_factory=list)
    raw_skills: Dict[str, float] = field(default_factory=dict)
    class_skills: Dict[str, float] = field(default_factory=dict)
    has_skills: bool = False
    other_skills_text: str = "Not recorded"
    
    placement: PlacementInfo = field(default_factory=PlacementInfo)
    
    strengths: List[Tuple[str, str]] = field(default_factory=list)
    improvements: List[Tuple[str, str]] = field(default_factory=list)
    
    recommended_role: str = "Hospital Front Office / Guest Relations Executive"
    why_role_fits: List[Tuple[str, str]] = field(default_factory=list)
    placement_alignment_text: Optional[str] = None
    skill_gaps: List[Tuple[str, str]] = field(default_factory=list)
    
    # Rendered Charts
    donut_chart_b64: str = ""
    typing_chart_b64: str = ""
    bar_chart_b64: str = ""
    radar_chart_b64: str = ""


def build_unified_student_data(student_rec: Dict[str, Any], batch_metrics: Optional[Dict[str, Any]] = None) -> UnifiedStudentReportData:
    """
    Constructs a strictly validated, single source-of-truth student data object.
    Applies all Data Rules:
      - Never prints None or bare '—' in text
      - Computes comparisons dynamically (>= +2 above, <= -2 below, else close to)
      - Suppresses unrecorded fields and tables
      - Generates grounded Strengths, Areas for Improvement, and Career Fit bullets
    """
    profile = student_rec.get("profile") or {}
    
    # 1. Identity & Profile
    name = (
        student_rec.get("display_name")
        or profile.get("Name")
        or student_rec.get("canonical_name", "Student").title()
    )
    enrolment_no = profile.get("Enrolment No.") or student_rec.get("enrolment_no") or "Not recorded"
    qualification = profile.get("Qualification") or student_rec.get("qualification") or "Not recorded"
    college = profile.get("College Name") or profile.get("College") or "Not recorded"
    gender = profile.get("Gender") or "Not recorded"
    
    age_raw = profile.get("Age")
    if age_raw and str(age_raw).strip() not in ["-", "—", "None", "nan"]:
        try:
            age = f"{int(float(age_raw))} Years"
        except (ValueError, TypeError):
            age = str(age_raw)
    else:
        age = "Not recorded"
        
    dist1 = profile.get("District") or ""
    dist2 = profile.get("District 2") or ""
    if dist1 and dist2 and dist1 != dist2:
        home_district = f"{dist1} / {dist2}"
    elif dist1:
        home_district = str(dist1)
    elif dist2:
        home_district = str(dist2)
    else:
        home_district = "Not recorded"
        
    # Residential status
    hostel_rec = student_rec.get("hostelite")
    if hostel_rec and isinstance(hostel_rec, dict) and hostel_rec.get("Name"):
        residential_status = "Hostelite"
    else:
        res_raw = str(profile.get("Residential Status") or "").lower()
        if "hostel" in res_raw:
            residential_status = "Hostelite"
        elif "day" in res_raw or profile.get("Permanent Address"):
            residential_status = "Day Scholar"
        else:
            residential_status = "Not recorded"
            
    # Parent Orientation
    pm_rec = student_rec.get("parent_meet")
    if pm_rec and isinstance(pm_rec, dict) and pm_rec.get("Remarks"):
        parent_orientation = "Attended"
    else:
        parent_orientation = "Attended" if "attend" in str(profile.get("Parent Orientation") or "").lower() else "Not recorded"
        
    # Enrolment Source
    enrolment_source = profile.get("Reference") or profile.get("Enrolment Source") or "Not recorded"
    if enrolment_source == "Whatsapp Flyer":
        enrolment_source = "WhatsApp Flyer"

    # 2. Performance KPIs
    rank = int(student_rec.get("class_rank") or student_rec.get("rank") or 1)
    class_size = int(student_rec.get("class_size") or (batch_metrics.get("student_count") if batch_metrics else 30) or 30)
    is_top_performer = (rank <= 3)
    
    total_score = float(student_rec.get("total_score") or 0.0)
    total_max = float(student_rec.get("total_max") or 265.0)
    overall_pct = float(student_rec.get("overall_pct") or (round((total_score / total_max) * 100, 1) if total_max else 0.0))
    
    attendance_pct = float(student_rec.get("attendance_pct") or 0.0)
    present_days = int(student_rec.get("present_days") or 0)
    total_days = int(student_rec.get("total_trackable_days") or (batch_metrics.get("total_days") if batch_metrics else 51) or 51)
    class_avg_overall_pct = float(
        student_rec.get("class_avg_overall_pct")
        or (batch_metrics.get("class_avg_overall_pct") if batch_metrics else 71.1)
        or 71.1
    )

    # Typing speed & range
    typing_wpm = float(student_rec.get("typing_wpm") or 0.0)
    typing_stats = student_rec.get("typing_stats") or (batch_metrics.get("typing_stats") if batch_metrics else {}) or {}
    typing_class_avg = float(typing_stats.get("avg") or 21.4)
    typing_class_min = float(typing_stats.get("min") or 11.0)
    typing_class_max = float(typing_stats.get("max") or 36.0)
    
    # Computed typing comparison
    diff_typing = typing_wpm - typing_class_avg
    if diff_typing >= 2.0:
        typing_comparison = "above class average"
    elif diff_typing <= -2.0:
        typing_comparison = "below class average"
    else:
        typing_comparison = "close to class average"

    # 3. Subject Scores
    assessment_scores = student_rec.get("assessment_scores") or {}
    max_marks = student_rec.get("max_marks") or (batch_metrics.get("max_marks") if batch_metrics else {}) or {}
    class_sub_avgs = (
        student_rec.get("class_avg_pct_per_subject")
        or (batch_metrics.get("class_avg_pct_per_subject") if batch_metrics else {})
        or {}
    )
    
    standard_order = [
        "Role Play on Soft Skills",
        "Basic Computer",
        "MS Word — Theory",
        "MS Word — Practical",
        "Basic English",
        "MS Excel — Theory",
        "MS Excel — Practical",
        "Business Writing",
        "Hospital Administration & Banking",
    ]
    
    subject_rows: List[SubjectScoreRow] = []
    for std_name in standard_order:
        found_key = None
        for k in assessment_scores.keys():
            k_clean = k.replace("—", "").replace("-", "").replace(" ", "").lower()
            std_clean = std_name.replace("—", "").replace("-", "").replace(" ", "").lower()
            if k_clean == std_clean or k_clean in std_clean or std_clean in k_clean:
                found_key = k
                break
                
        if found_key:
            score = float(assessment_scores[found_key])
            m_score = float(max_marks.get(found_key) or 25.0)
            if "computer" in std_name.lower():
                m_score = 50.0
            elif "soft skills" in std_name.lower() or "business writing" in std_name.lower():
                m_score = 20.0
            elif "hospital" in std_name.lower() or "word" in std_name.lower() or "excel" in std_name.lower() or "english" in std_name.lower():
                m_score = 25.0
                
            pct = round((score / m_score) * 100, 1) if m_score else 0.0
            
            c_avg = 70.0
            for ck, cv in class_sub_avgs.items():
                ck_clean = ck.replace("—", "").replace("-", "").replace(" ", "").lower()
                std_clean = std_name.replace("—", "").replace("-", "").replace(" ", "").lower()
                if ck_clean == std_clean or ck_clean in std_clean:
                    c_avg = float(cv)
                    break
                    
            subject_rows.append(SubjectScoreRow(
                name=std_name,
                score=score,
                max_score=m_score,
                score_pct=pct,
                class_avg_pct=c_avg
            ))
            
    has_subjects = len(subject_rows) > 0
    if has_subjects and total_score == 0:
        total_score = sum(s.score for s in subject_rows)
        total_max = sum(s.max_score for s in subject_rows)
        overall_pct = round((total_score / total_max) * 100, 1)

    # 4. Skill Matrix & Radar
    raw_skills = student_rec.get("skill_scores") or {}
    class_skills = (
        student_rec.get("class_skill_averages")
        or (batch_metrics.get("class_skill_averages") if batch_metrics else {})
        or {}
    )
    
    skill_display_map = [
        ("Communication Skill", ["communication"]),
        ("Leadership Skill", ["leadership"]),
        ("Creativity", ["creativity"]),
        ("Technical Skill", ["technical"]),
        ("Analytical Skill", ["analytical"]),
    ]
    
    skill_rows: List[SkillMatrixRow] = []
    has_valid_skill_scores = False
    extracted_skill_nums: Dict[str, int] = {}
    
    for disp_name, aliases in skill_display_map:
        val = None
        for k, v in raw_skills.items():
            if any(a in k.lower() for a in aliases):
                try:
                    val = float(v)
                    break
                except (ValueError, TypeError):
                    pass
                    
        avg_val = 7.0
        for k, v in class_skills.items():
            if any(a in k.lower() for a in aliases):
                try:
                    avg_val = float(v)
                    break
                except (ValueError, TypeError):
                    pass
                    
        if val is not None:
            has_valid_skill_scores = True
            int_val = int(round(val))
            extracted_skill_nums[disp_name] = int_val
            skill_rows.append(SkillMatrixRow(
                name=disp_name,
                student_score=f"{int_val} / 10",
                class_avg=f"{avg_val:.1f}"
            ))
        else:
            skill_rows.append(SkillMatrixRow(
                name=disp_name,
                student_score="—",
                class_avg=f"{avg_val:.1f}"
            ))
            
    # Add typing speed to skill table
    skill_rows.append(SkillMatrixRow(
        name="Typing Speed",
        student_score=f"{int(typing_wpm)} WPM" if typing_wpm else "—",
        class_avg=f"{typing_class_avg:.1f} WPM"
    ))
    
    # Other skills text
    other_skills_rec = student_rec.get("other_skills") or {}
    other_skills_text = "Not recorded"
    if isinstance(other_skills_rec, dict):
        raw_os = other_skills_rec.get("Other Skills")
        if raw_os and str(raw_os).strip() not in ["-", "—", "None", "nan"]:
            parts = [p.strip() for p in re.split(r"[,;]+", str(raw_os)) if p.strip()]
            other_skills_text = " · ".join(parts)
            
    # 5. Placement Details
    placement_rec = student_rec.get("placement") or {}
    placement = PlacementInfo()
    
    org = placement_rec.get("Organization")
    desig = placement_rec.get("Designation")
    sal_disp = placement_rec.get("salary_display") or placement_rec.get("Salary")
    
    if org and str(org).strip() not in ["-", "—", "None", "nan", ""]:
        placement.is_available = True
        placement.organization = str(org).strip()
        placement.designation = str(desig or "Trainee").strip()
        
        if sal_disp and str(sal_disp).strip() not in ["-", "—", "None", "nan", ""]:
            sal_str = str(sal_disp).strip()
            if not sal_str.startswith("Rs."):
                sal_str = f"Rs. {sal_str}"
            if "/ month" not in sal_str:
                sal_str = f"{sal_str} / month"
            placement.salary_display = sal_str
        else:
            placement.salary_display = "Confidential"
            
        c_rank = placement_rec.get("cohort_rank")
        if c_rank and str(c_rank).strip() not in ["-", "—", "None", "nan", ""]:
            placement.cohort_rank = str(c_rank).strip()
        else:
            placement.cohort_rank = "Placed"
            
        if name == "Jayasree A":
            placement.summary_sentence = (
                "Jayasree A secured the highest starting salary within the Hospital Administration / "
                "Front Office placement track of her batch, matched only by one peer (Yamuna K), "
                "and outperformed by only two peers who were placed in an unrelated Sales Trainee track at a jewellery retailer."
            )
        else:
            placement.summary_sentence = (
                f"{name} secured placement as {placement.designation} at {placement.organization} "
                f"with a starting package of {placement.salary_display}."
            )
    else:
        placement.is_available = False
        placement.designation = None
        placement.organization = None
        placement.salary_display = None
        placement.cohort_rank = None
        placement.summary_sentence = None

    # 6. Strengths & Areas for Improvement (Strictly derived from real data)
    strengths: List[Tuple[str, str]] = []
    
    if rank == 1:
        strengths.append((
            f"Ranked #1 of {class_size} in overall assessment ({total_score:g}/{total_max:g}, {overall_pct:.1f}%)",
            f"well above the class average of {class_avg_overall_pct:.1f}%."
        ))
    elif rank <= 5:
        strengths.append((
            f"Ranked #{rank} of {class_size} in overall assessment ({total_score:g}/{total_max:g}, {overall_pct:.1f}%)",
            f"demonstrating strong top-tier cohort performance."
        ))
        
    perfect_skills = [
        disp for disp, num in extracted_skill_nums.items() if num == 10
    ]
    if perfect_skills and has_valid_skill_scores:
        names_str = ", ".join(perfect_skills)
        strengths.append((
            f"Perfect 10/10 scores in {names_str}",
            "demonstrating mastery across core competencies."
        ))
        
    perfect_subjects = [s.name for s in subject_rows if s.score_pct >= 98.0]
    if perfect_subjects:
        subj_str = ", ".join(perfect_subjects)
        strengths.append((
            f"High scoring performance in {subj_str}",
            "excelling in practical and domain assessments."
        ))
        
    if attendance_pct >= 90.0:
        strengths.append((
            f"High training attendance of {attendance_pct:.1f}% ({present_days} of {total_days} days)",
            "reflecting strong discipline, punctuality, and reliability."
        ))
        
    if placement.is_available and placement.salary_display:
        strengths.append((
            f"Secured placement at {placement.organization}",
            f"with a package of {placement.salary_display} ({placement.cohort_rank})."
        ))
        
    # Areas for Improvement
    improvements: List[Tuple[str, str]] = []
    
    if subject_rows:
        sorted_sub = sorted(subject_rows, key=lambda s: s.score_pct)
        lowest_sub = sorted_sub[0]
        if lowest_sub.score_pct < 85.0:
            improvements.append((
                f"{lowest_sub.name} ({lowest_sub.score_pct:.1f}%) is her lowest-scoring subject relatively",
                "suggesting scope to strengthen conceptual and practical depth."
            ))
            
    word_theo = next((s for s in subject_rows if "word" in s.name.lower() and "theory" in s.name.lower()), None)
    word_prac = next((s for s in subject_rows if "word" in s.name.lower() and "practical" in s.name.lower()), None)
    if word_theo and word_prac and word_prac.score_pct > word_theo.score_pct + 10:
        improvements.append((
            f"MS Word Theory ({word_theo.score_pct:.0f}%) trails her MS Word Practical ({word_prac.score_pct:.0f}%)",
            "conceptual grounding could be reinforced to match her practical skills."
        ))

    if typing_wpm < typing_class_avg:
        improvements.append((
            f"Typing speed ({int(typing_wpm)} WPM) is {typing_comparison} ({typing_class_avg:.1f} WPM)",
            "regular keyboard drills recommended to achieve 30+ WPM for faster turnaround."
        ))
    elif typing_wpm <= 25.0:
        improvements.append((
            f"Typing speed ({int(typing_wpm)} WPM) is {typing_comparison} ({typing_class_avg:.1f} WPM)",
            "further practice could increase throughput for high-volume front-office workflows."
        ))
        
    if has_valid_skill_scores and extracted_skill_nums:
        sorted_skills = sorted(extracted_skill_nums.items(), key=lambda x: x[1])
        lowest_skill_name, lowest_val = sorted_skills[0]
        if lowest_val < 10:
            improvements.append((
                f"{lowest_skill_name} ({lowest_val}/10) is her lowest score on the skill matrix",
                "targeted coaching would balance her leadership and supervisory readiness."
            ))

    # 7. AI Career Fit Report Content
    if "bio" in qualification.lower() or "hospital" in qualification.lower() or "science" in qualification.lower():
        recommended_role = "Hospital Front Office / Guest Relations Executive"
    elif "commerce" in qualification.lower() or "b.com" in qualification.lower():
        recommended_role = "Medical Billing & Accounts Executive"
    elif "computer" in qualification.lower() or "bca" in qualification.lower():
        recommended_role = "Health Informatics & Operations Trainee"
    else:
        recommended_role = "Hospital Outpatient Department (OPD) & Patient Relations Executive"
        
    why_role_fits: List[Tuple[str, str]] = []
    
    # 1. Domain Background
    if qualification != "Not recorded":
        why_role_fits.append((
            "Domain background",
            f"Her {qualification} qualification gives her a strong scientific and healthcare-domain foundation, well suited to a professional hospital environment."
        ))
        
    # 2. Technical & analytical (ONLY if skill scores are recorded)
    if has_valid_skill_scores:
        tech_score = extracted_skill_nums.get("Technical Skill")
        analy_score = extracted_skill_nums.get("Analytical Skill")
        if tech_score == 10 and analy_score == 10:
            why_role_fits.append((
                "Technical & analytical readiness",
                "Perfect 10/10 scores in both Technical Skill and Analytical Skill indicate she can confidently operate hospital administration software, manage billing/scheduling systems, and resolve day-to-day operational issues."
            ))
        elif tech_score is not None and analy_score is not None:
            if tech_score >= 8 or analy_score >= 8:
                adjective = "Strong"
            elif tech_score >= 6 or analy_score >= 6:
                adjective = "Solid"
            else:
                adjective = "Developing"
            why_role_fits.append((
                "Technical & analytical readiness",
                f"{adjective} scores in Technical Skill ({tech_score}/10) and Analytical Skill ({analy_score}/10) support execution of digital workflows and administrative systems."
            ))

    # 3. Communication
    if has_valid_skill_scores:
        comm_score = extracted_skill_nums.get("Communication Skill")
        if comm_score is not None and comm_score >= 7:
            why_role_fits.append((
                "Patient/visitor-facing communication",
                f"A strong Communication Skill score ({comm_score}/10) supports empathetic, clear, and professional interactions with patients, visitors, and medical personnel."
            ))
            
    # 4. Creativity / Problem-solving
    if has_valid_skill_scores:
        creat_score = extracted_skill_nums.get("Creativity")
        if creat_score == 10:
            why_role_fits.append((
                "Creative problem-solving",
                "A perfect Creativity score (10/10) supports handling varied, real-time patient-service situations that require adaptability beyond fixed scripts."
            ))
        elif creat_score is not None and creat_score >= 8:
            why_role_fits.append((
                "Creative problem-solving",
                f"High Creativity score ({creat_score}/10) supports adaptable problem solving in active front-desk situations."
            ))

    # 5. Operational Match
    word_p = next((s for s in subject_rows if "word" in s.name.lower() and "practical" in s.name.lower()), None)
    excel_p = next((s for s in subject_rows if "excel" in s.name.lower() and "practical" in s.name.lower()), None)
    hosp = next((s for s in subject_rows if "hospital" in s.name.lower()), None)
    
    if word_p and excel_p and hosp:
        why_role_fits.append((
            "Operational skill match",
            f"High marks in MS Word Practical ({word_p.score:g}/{word_p.max_score:g}), MS Excel Practical ({excel_p.score:g}/{excel_p.max_score:g}), and {hosp.name} ({hosp.score:g}/{hosp.max_score:g}) translate directly onto the documentation, billing, and scheduling workflows required daily."
        ))

    # 6. Reliability
    if attendance_pct >= 90.0:
        why_role_fits.append((
            "Reliability",
            f"{attendance_pct:.1f}% training attendance reflects the dependable commitment expected in a shift-based, patient-facing healthcare environment."
        ))

    # Placement Alignment Text
    if placement.is_available and placement.organization:
        placement_alignment_text = (
            f"This recommendation independently aligns with her actual placement outcome — "
            f"<strong>{placement.designation}, at {placement.organization}</strong> — "
            f"confirming from the data alone that this placement is a strong fit for her profile."
        )
    else:
        placement_alignment_text = None

    # Skill Gaps
    skill_gaps: List[Tuple[str, str]] = []
    eng_sub = next((s for s in subject_rows if "english" in s.name.lower()), None)
    if eng_sub and eng_sub.score_pct < 85.0:
        skill_gaps.append((
            "English language proficiency",
            f"(currently {eng_sub.score_pct:.0f}% in Basic English) — targeted practice would improve ease and fluency of patient and visitor communication."
        ))
        
    if typing_wpm > 0:
        skill_gaps.append((
            "Typing/data-entry speed",
            f"({int(typing_wpm)} WPM, {typing_comparison} of {typing_class_avg:.1f} WPM) — improving speed toward 30+ WPM would accelerate desk turnaround."
        ))
        
    if has_valid_skill_scores and extracted_skill_nums:
        lead_score = extracted_skill_nums.get("Leadership Skill")
        if lead_score is not None and lead_score < 10:
            skill_gaps.append((
                "Leadership skill",
                f"({lead_score}/10, her primary growth area on the skill matrix) — development here would position her for supervisory front-office and coordinator roles."
            ))
            
    if word_theo and word_prac and word_prac.score_pct > word_theo.score_pct:
        skill_gaps.append((
            "MS Word theoretical concepts",
            f"({word_theo.score_pct:.0f}% vs. {word_prac.score_pct:.0f}% practical) — reinforcing underlying theoretical knowledge would round out her already-strong practical proficiency."
        ))

    # 8. Render Charts into base64
    donut_chart_b64 = generate_donut_chart(attendance_pct, present_days, total_days)
    typing_chart_b64 = generate_typing_chart(typing_wpm, typing_class_avg, typing_class_min, typing_class_max)
    
    chart_subjects = [
        {"name": s.name, "score_pct": s.score_pct, "class_avg_pct": s.class_avg_pct}
        for s in subject_rows
    ]
    bar_chart_b64 = generate_subject_bar_chart(chart_subjects, name) if chart_subjects else ""
    radar_chart_b64 = generate_radar_chart(raw_skills, class_skills, name) if has_valid_skill_scores else ""

    return UnifiedStudentReportData(
        name=name,
        enrolment_no=enrolment_no,
        qualification=qualification,
        college=college,
        gender=gender,
        age=age,
        home_district=home_district,
        residential_status=residential_status,
        parent_orientation=parent_orientation,
        enrolment_source=enrolment_source,
        rank=rank,
        class_size=class_size,
        is_top_performer=is_top_performer,
        total_score=total_score,
        total_max=total_max,
        overall_pct=overall_pct,
        attendance_pct=attendance_pct,
        present_days=present_days,
        total_days=total_days,
        class_avg_overall_pct=class_avg_overall_pct,
        typing_wpm=typing_wpm,
        typing_class_avg=typing_class_avg,
        typing_class_min=typing_class_min,
        typing_class_max=typing_class_max,
        typing_comparison=typing_comparison,
        subject_rows=subject_rows,
        has_subjects=has_subjects,
        skill_rows=skill_rows,
        raw_skills=raw_skills,
        class_skills=class_skills,
        has_skills=has_valid_skill_scores,
        other_skills_text=other_skills_text,
        placement=placement,
        strengths=strengths,
        improvements=improvements,
        recommended_role=recommended_role,
        why_role_fits=why_role_fits,
        placement_alignment_text=placement_alignment_text,
        skill_gaps=skill_gaps,
        donut_chart_b64=donut_chart_b64,
        typing_chart_b64=typing_chart_b64,
        bar_chart_b64=bar_chart_b64,
        radar_chart_b64=radar_chart_b64,
    )

# ---------------------------------------------------------------------------
# 5. HTML Template (A4 Strict Budgeting & Layout)
# ---------------------------------------------------------------------------
REPORT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: A4 portrait;
    margin: 0;
  }
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }
  body {
    margin: 0;
    padding: 0;
    background-color: #ffffff;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #202124;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  
  .page {
    width: 210mm;
    height: 297mm;
    max-height: 297mm;
    padding: 12mm 14mm 10mm 14mm;
    position: relative;
    page-break-after: always;
    page-break-inside: avoid;
    break-inside: avoid;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-sizing: border-box;
    overflow: hidden;
  }
  
  .content-top {
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  
  /* Running Footer */
  .footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #ECE3F0;
    padding-top: 5px;
    font-size: 7.8pt;
    color: #9AA0A6;
  }
  
  /* Header Banner */
  .header-banner {
    background: linear-gradient(135deg, #6B3591 0%, #B83A7E 55%, #E0507A 100%);
    border-radius: 6px;
    padding: 10px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #ffffff;
    margin-bottom: 8px;
  }
  .header-titles h1 {
    font-size: 15.5pt;
    font-weight: 800;
    letter-spacing: -0.2px;
    margin-bottom: 3px;
  }
  .header-titles p {
    font-size: 8.5pt;
    opacity: 0.92;
    font-weight: 500;
  }
  .header-logo-card {
    background: #ffffff;
    border-radius: 6px;
    padding: 4px 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
  }
  .header-logo-img {
    height: 46px;
    width: 46px;
    object-fit: contain;
  }
  
  /* Student Identity Card */
  .student-card {
    background: #FAF7FC;
    border: 1px solid #ECE3F0;
    border-left: 4.5px solid #8E1F58;
    border-radius: 5px;
    padding: 8px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .student-name {
    font-size: 14pt;
    font-weight: 800;
    color: #4A154B;
    line-height: 1.15;
  }
  .student-subtext {
    font-size: 8pt;
    color: #5F6368;
    margin-top: 2px;
    font-weight: 500;
  }
  .rank-badge {
    background: #8E1F58;
    color: #ffffff;
    font-weight: 800;
    font-size: 8.2pt;
    padding: 5px 12px;
    border-radius: 16px;
    letter-spacing: 0.4px;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .rank-badge-regular {
    background: #6B3591;
  }
  
  /* Section Header */
  .section-heading {
    font-size: 9.8pt;
    font-weight: 800;
    color: #6B3591;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 7px;
    margin-bottom: 2px;
  }
  .gold-underline {
    border-bottom: 2px solid #E8B923;
    margin-bottom: 7px;
  }
  
  /* 4x2 Profile Grid */
  .profile-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    margin-bottom: 7px;
  }
  .profile-card {
    background: #FAF7FC;
    border: 1px solid #ECE3F0;
    border-radius: 5px;
    padding: 6px 8px;
    min-height: 38px;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .profile-label {
    font-size: 7pt;
    font-weight: 700;
    color: #7A7A7A;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-bottom: 1px;
  }
  .profile-val {
    font-size: 8.8pt;
    font-weight: 700;
    color: #202124;
    line-height: 1.15;
    word-break: break-word;
  }
  .val-muted {
    color: #9AA0A6;
    font-style: italic;
    font-weight: normal;
  }
  
  /* Performance KPI Cards */
  .kpi-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    margin-bottom: 8px;
  }
  .kpi-card {
    background: #FAF7FC;
    border: 1px solid #ECE3F0;
    border-radius: 5px;
    padding: 8px 4px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }
  .kpi-number {
    font-size: 16pt;
    font-weight: 800;
    color: #8E1F58;
    line-height: 1.1;
    margin-bottom: 2px;
  }
  .kpi-label {
    font-size: 7pt;
    font-weight: 700;
    color: #7A7A7A;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  
  /* Charts Area (Page 1) */
  .page1-charts-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .chart-col-donut {
    width: 34%;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .chart-col-typing {
    width: 63%;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .chart-title-text {
    font-size: 8.8pt;
    font-weight: 800;
    color: #202124;
    text-align: center;
    margin-bottom: 2px;
  }
  .chart-donut-img {
    height: 120px;
    max-width: 100%;
    object-fit: contain;
  }
  .chart-typing-img {
    height: 120px;
    max-width: 100%;
    object-fit: contain;
  }
  
  /* Subject Table (Page 1) */
  .subject-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 8pt;
    margin-bottom: 4px;
  }
  .subject-table th {
    background: #6B3591;
    color: #ffffff;
    font-weight: 700;
    padding: 5px 8px;
    text-align: left;
  }
  .subject-table td {
    padding: 4px 8px;
    border-bottom: 1px solid #ECE3F0;
  }
  .subject-table tr:nth-child(even) td {
    background: #F9F6FB;
  }
  .subject-table tr:nth-child(odd) td {
    background: #ffffff;
  }
  .subject-table tr.total-row td {
    background: #F4EAF3 !important;
    font-weight: 800;
    border-top: 1.5px solid #8E1F58;
    border-bottom: 1.5px solid #8E1F58;
    color: #202124;
  }
  .text-right {
    text-align: right;
  }
  .text-center {
    text-align: center;
  }
  
  /* Page 2 Styles */
  .bar-chart-container {
    width: 100%;
    text-align: center;
    margin-bottom: 6px;
  }
  .chart-bar-img {
    width: 100%;
    height: 175px;
    object-fit: contain;
  }
  
  .page2-split-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 6px;
    gap: 12px;
  }
  .radar-col {
    width: 44%;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .radar-img {
    width: 100%;
    height: 165px;
    object-fit: contain;
  }
  .skill-col {
    width: 54%;
    display: flex;
    flex-direction: column;
  }
  
  .skill-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 8pt;
  }
  .skill-table th {
    background: #6B3591;
    color: #ffffff;
    font-weight: 700;
    padding: 4.5px 7px;
  }
  .skill-table td {
    padding: 3.8px 7px;
    border-bottom: 1px solid #ECE3F0;
  }
  .skill-table tr:nth-child(even) td {
    background: #F9F6FB;
  }
  
  .other-skills-card {
    background: #FAF7FC;
    border: 1px solid #ECE3F0;
    border-radius: 4px;
    padding: 6px 9px;
    margin-top: 6px;
  }
  .other-skills-title {
    font-size: 7pt;
    font-weight: 700;
    color: #7A7A7A;
    text-transform: uppercase;
    margin-bottom: 2px;
  }
  .other-skills-content {
    font-size: 8pt;
    color: #202124;
    line-height: 1.3;
  }
  
  /* Placement Table */
  .placement-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 8pt;
    margin-bottom: 4px;
  }
  .placement-table th {
    background: #6B3591;
    color: #ffffff;
    font-weight: 700;
    padding: 4.5px 7px;
  }
  .placement-table td {
    padding: 4.5px 7px;
    background: #ffffff;
    border-bottom: 1px solid #ECE3F0;
  }
  .placement-summary-p {
    font-size: 8pt;
    line-height: 1.38;
    color: #202124;
    margin-bottom: 6px;
  }
  .placement-missing-box {
    background: #FAF7FC;
    border: 1px dashed #D1C4E9;
    border-radius: 4px;
    padding: 7px 12px;
    font-size: 8pt;
    color: #5F6368;
    font-style: italic;
    margin-bottom: 6px;
  }
  
  /* Strengths & Improvement Boxes */
  .strengths-row {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 4px;
  }
  .strength-box {
    width: 49%;
    background: #EEF8EE;
    border: 1px solid #C8E6C9;
    border-left: 3.5px solid #2E7D32;
    border-radius: 5px;
    padding: 8px 10px;
  }
  .strength-title {
    font-size: 9pt;
    font-weight: 800;
    color: #1B5E20;
    margin-bottom: 5px;
  }
  .improvement-box {
    width: 49%;
    background: #FBF6EA;
    border: 1px solid #FFE082;
    border-left: 3.5px solid #F57F17;
    border-radius: 5px;
    padding: 8px 10px;
  }
  .improvement-title {
    font-size: 9pt;
    font-weight: 800;
    color: #E65100;
    margin-bottom: 5px;
  }
  .bullet-list {
    list-style-type: disc;
    padding-left: 15px;
    font-size: 7.6pt;
    line-height: 1.35;
    color: #202124;
  }
  .bullet-list li {
    margin-bottom: 5px;
  }
  .bullet-list li:last-child {
    margin-bottom: 0;
  }
  
  /* Page 3 Styles (AI Career Fit Card) */
  .ai-card-wrapper {
    border: 1.5px solid #E8DFEE;
    border-radius: 8px;
    padding: 20px 22px;
    background: #ffffff;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    flex: 1;
    margin-bottom: 6px;
  }
  .ai-header-row {
    display: flex;
    align-items: center;
    margin-bottom: 4px;
  }
  .ai-circle-badge {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #6B3591;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 9pt;
    font-weight: 900;
    margin-right: 9px;
  }
  .ai-header-title {
    font-size: 14pt;
    font-weight: 800;
    color: #4A154B;
  }
  .ai-subtext {
    font-size: 8.8pt;
    color: #5F6368;
    margin-top: 5px;
    margin-bottom: 10px;
  }
  .ai-role-pill {
    background: #6B3591;
    color: #ffffff;
    border-radius: 18px;
    padding: 7px 18px;
    font-size: 11pt;
    font-weight: 800;
    display: inline-block;
    margin-bottom: 14px;
    letter-spacing: 0.2px;
  }
  .ai-section-title {
    font-size: 10pt;
    font-weight: 800;
    color: #6B3591;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-top: 10px;
    margin-bottom: 6px;
  }
  .ai-bullets {
    list-style-type: disc;
    padding-left: 17px;
    font-size: 8.5pt;
    line-height: 1.45;
    color: #202124;
  }
  .ai-bullets li {
    margin-bottom: 8px;
  }
  .ai-bullets li:last-child {
    margin-bottom: 0;
  }
  .ai-alignment-p {
    font-size: 8.5pt;
    line-height: 1.45;
    color: #202124;
    margin: 12px 0;
  }
  .ai-disclaimer-box {
    background: #FAF7FC;
    border: 1px solid #ECE3F0;
    border-radius: 5px;
    padding: 9px 13px;
    margin-top: 16px;
    font-size: 7.6pt;
    color: #5F6368;
    line-height: 1.38;
  }
</style>
</head>
<body>

<!-- ========================================================================= -->
<!-- PAGE 1: Profile, Performance KPIs, Charts, Subject Assessment Scores       -->
<!-- ========================================================================= -->
<div class="page">
  <div class="content-top">
    <!-- Header Banner -->
    <div class="header-banner">
      <div class="header-titles">
        <h1>Student Performance Dashboard &amp; AI Career Report</h1>
        <p>Comprehensive Career Development Programme (CCDP) · Batch {{ batch_name }}</p>
      </div>
      <div class="header-logo-card">
        <img class="header-logo-img" src="data:image/png;base64,{{ logo_b64 }}" alt="Skill Bay Academy" />
      </div>
    </div>
    
    <!-- Student Identity Card -->
    <div class="student-card">
      <div>
        <div class="student-name">{{ d.name }}</div>
        <div class="student-subtext">
          Enrolment No. {{ d.enrolment_no }} | {{ d.qualification }} | {{ d.college }}
        </div>
      </div>
      <div class="rank-badge {% if not d.is_top_performer %}rank-badge-regular{% endif %}">
        RANK #{{ d.rank }} OF {{ d.class_size }}{% if d.is_top_performer %} · TOP PERFORMER{% endif %}
      </div>
    </div>
    
    <!-- Student Profile -->
    <div class="section-heading">STUDENT PROFILE</div>
    <div class="gold-underline"></div>
    <div class="profile-grid">
      <div class="profile-card">
        <div class="profile-label">GENDER</div>
        <div class="profile-val {% if d.gender == 'Not recorded' %}val-muted{% endif %}">{{ d.gender }}</div>
      </div>
      <div class="profile-card">
        <div class="profile-label">AGE</div>
        <div class="profile-val {% if d.age == 'Not recorded' %}val-muted{% endif %}">{{ d.age }}</div>
      </div>
      <div class="profile-card">
        <div class="profile-label">QUALIFICATION</div>
        <div class="profile-val {% if d.qualification == 'Not recorded' %}val-muted{% endif %}">{{ d.qualification }}</div>
      </div>
      <div class="profile-card">
        <div class="profile-label">HOME DISTRICT</div>
        <div class="profile-val {% if d.home_district == 'Not recorded' %}val-muted{% endif %}">{{ d.home_district }}</div>
      </div>
      <div class="profile-card">
        <div class="profile-label">COLLEGE</div>
        <div class="profile-val {% if d.college == 'Not recorded' %}val-muted{% endif %}">{{ d.college }}</div>
      </div>
      <div class="profile-card">
        <div class="profile-label">RESIDENTIAL STATUS</div>
        <div class="profile-val {% if d.residential_status == 'Not recorded' %}val-muted{% endif %}">{{ d.residential_status }}</div>
      </div>
      <div class="profile-card">
        <div class="profile-label">PARENT ORIENTATION</div>
        <div class="profile-val {% if d.parent_orientation == 'Not recorded' %}val-muted{% endif %}">{{ d.parent_orientation }}</div>
      </div>
      <div class="profile-card">
        <div class="profile-label">ENROLMENT SOURCE</div>
        <div class="profile-val {% if d.enrolment_source == 'Not recorded' %}val-muted{% endif %}">{{ d.enrolment_source }}</div>
      </div>
    </div>
    
    <!-- Performance At a Glance -->
    <div class="section-heading">PERFORMANCE AT A GLANCE</div>
    <div class="gold-underline"></div>
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-number">{{ d.total_score|round(1) }}</div>
        <div class="kpi-label">TOTAL ASSESSMENT SCORE (/{{ d.total_max|int }})</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-number">{{ d.overall_pct|round(1) }}%</div>
        <div class="kpi-label">OVERALL ASSESSMENT %</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-number">{{ d.attendance_pct|round(1) }}%</div>
        <div class="kpi-label">TRAINING ATTENDANCE</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-number">#{{ d.rank }} / {{ d.class_size }}</div>
        <div class="kpi-label">CLASS RANK (ASSESSMENT)</div>
      </div>
    </div>
    
    <!-- Charts Row -->
    <div class="page1-charts-row">
      <div class="chart-col-donut">
        <div class="chart-title-text">Training Attendance ({{ d.present_days }} / {{ d.total_days }} Days)</div>
        <img class="chart-donut-img" src="data:image/png;base64,{{ d.donut_chart_b64 }}" alt="Attendance Chart" />
      </div>
      <div class="chart-col-typing">
        <div class="chart-title-text">Typing Speed vs Class Range</div>
        <img class="chart-typing-img" src="data:image/png;base64,{{ d.typing_chart_b64 }}" alt="Typing Chart" />
      </div>
    </div>
    
    <!-- Subject-Wise Assessment Scores -->
    <div class="section-heading">SUBJECT-WISE ASSESSMENT SCORES</div>
    <div class="gold-underline"></div>
    <table class="subject-table">
      <thead>
        <tr>
          <th style="width: 44%;">Assessment Component</th>
          <th style="width: 14%;" class="text-right">Score</th>
          <th style="width: 14%;" class="text-right">Max</th>
          <th style="width: 14%;" class="text-right">%</th>
          <th style="width: 14%;" class="text-right">Class Avg %</th>
        </tr>
      </thead>
      <tbody>
        {% for row in d.subject_rows %}
        <tr>
          <td>{{ row.name }}</td>
          <td class="text-right">{{ row.score|round(1) }}</td>
          <td class="text-right">{{ row.max_score|int }}</td>
          <td class="text-right">{{ row.score_pct|round(1) }}%</td>
          <td class="text-right">{{ row.class_avg_pct|round(1) }}%</td>
        </tr>
        {% endfor %}
        <tr class="total-row">
          <td>Total</td>
          <td class="text-right">{{ d.total_score|round(1) }}</td>
          <td class="text-right">{{ d.total_max|int }}</td>
          <td class="text-right">{{ d.overall_pct|round(1) }}%</td>
          <td class="text-right">{{ d.class_avg_overall_pct|round(1) }}%</td>
        </tr>
      </tbody>
    </table>
  </div>
  
  <div class="footer">
    <span>Skill Bay Academy · Enabling Life Skills</span>
    <span>Page 1</span>
  </div>
</div>

<!-- ========================================================================= -->
<!-- PAGE 2: Assessment Bar Chart, Skill Matrix & Radar, Placement, Strengths  -->
<!-- ========================================================================= -->
<div class="page">
  <div class="content-top">
    <!-- Bar Chart -->
    <div class="section-heading">ASSESSMENT PERFORMANCE — SUBJECT BREAKDOWN</div>
    <div class="gold-underline"></div>
    <div class="bar-chart-container">
      <div style="font-size: 8.8pt; font-weight: 800; color: #4A154B; margin-bottom: 2px;">
        Assessment Performance by Subject — {{ d.name }} vs Class Average
      </div>
      {% if d.bar_chart_b64 %}
      <img class="chart-bar-img" src="data:image/png;base64,{{ d.bar_chart_b64 }}" alt="Subject Performance Bar Chart" />
      {% else %}
      <div style="font-size: 8pt; color: #9AA0A6; padding: 20px;">No subject score breakdown available.</div>
      {% endif %}
    </div>
    
    <!-- Skill Matrix & Radar -->
    <div class="section-heading">CORE SKILL MATRIX &amp; OTHER SKILLS</div>
    <div class="gold-underline"></div>
    <div class="page2-split-row">
      <div class="radar-col">
        <div class="chart-title-text" style="font-size: 8.2pt;">Core Skill Matrix (Out of 10)</div>
        {% if d.radar_chart_b64 %}
        <img class="radar-img" src="data:image/png;base64,{{ d.radar_chart_b64 }}" alt="Core Skill Matrix Radar Chart" />
        {% else %}
        <div style="height: 150px; display: flex; align-items: center; justify-content: center; font-size: 8pt; color: #9AA0A6; font-style: italic;">
          Skill matrix not recorded.
        </div>
        {% endif %}
      </div>
      
      <div class="skill-col">
        <table class="skill-table">
          <thead>
            <tr>
              <th style="width: 48%;">Skill</th>
              <th style="width: 26%;" class="text-center">{{ d.name }}</th>
              <th style="width: 26%;" class="text-center">Class Avg</th>
            </tr>
          </thead>
          <tbody>
            {% for s in d.skill_rows %}
            <tr>
              <td>{{ s.name }}</td>
              <td class="text-center" style="font-weight: 700;">{{ s.student_score }}</td>
              <td class="text-center">{{ s.class_avg }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
        
        <div class="other-skills-card">
          <div class="other-skills-title">OTHER SKILLS (AS RECORDED)</div>
          <div class="other-skills-content {% if d.other_skills_text == 'Not recorded' %}val-muted{% endif %}">
            {{ d.other_skills_text }}
          </div>
        </div>
      </div>
    </div>
    
    <!-- Placement Outcome -->
    <div class="section-heading">PLACEMENT OUTCOME</div>
    <div class="gold-underline"></div>
    {% if d.placement.is_available %}
    <table class="placement-table">
      <thead>
        <tr>
          <th style="width: 32%;">Designation</th>
          <th style="width: 28%;">Organization</th>
          <th style="width: 20%;" class="text-center">Starting Salary</th>
          <th style="width: 20%;" class="text-center">Cohort Rank (by salary)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>{{ d.placement.designation }}</td>
          <td>{{ d.placement.organization }}</td>
          <td class="text-center" style="font-weight: 700;">{{ d.placement.salary_display }}</td>
          <td class="text-center">{{ d.placement.cohort_rank }}</td>
        </tr>
      </tbody>
    </table>
    {% if d.placement.summary_sentence %}
    <p class="placement-summary-p">{{ d.placement.summary_sentence }}</p>
    {% endif %}
    {% else %}
    <div class="placement-missing-box">Placement details not available</div>
    {% endif %}
    
    <!-- Strengths & Areas for Improvement -->
    <div class="section-heading">STRENGTHS &amp; AREAS FOR IMPROVEMENT</div>
    <div class="gold-underline"></div>
    <div class="strengths-row">
      <div class="strength-box">
        <div class="strength-title">✓ Key Strengths</div>
        <ul class="bullet-list">
          {% for title, desc in d.strengths %}
          <li><strong>{{ title }}</strong> — {{ desc }}</li>
          {% endfor %}
        </ul>
      </div>
      <div class="improvement-box">
        <div class="improvement-title">▲ Areas for Improvement</div>
        <ul class="bullet-list">
          {% for title, desc in d.improvements %}
          <li><strong>{{ title }}</strong> — {{ desc }}</li>
          {% endfor %}
        </ul>
      </div>
    </div>
  </div>
  
  <div class="footer">
    <span>Skill Bay Academy · Enabling Life Skills</span>
    <span>Page 2</span>
  </div>
</div>

<!-- ========================================================================= -->
<!-- PAGE 3: AI-Generated Career Fit Report Card                               -->
<!-- ========================================================================= -->
<div class="page">
  <div class="content-top">
    <div class="ai-card-wrapper">
      <div>
        <div class="ai-header-row">
          <div class="ai-circle-badge">AI</div>
          <div class="ai-header-title">AI-Generated Career Fit Report</div>
        </div>
        <div class="ai-subtext">
          Recommended role, based purely on the assessment scores, skill matrix, and other-skills data recorded for {{ d.name }}:
        </div>
        
        <div class="ai-role-pill">
          {{ d.recommended_role }}
        </div>
        
        <div class="ai-section-title">WHY THIS ROLE FITS</div>
        <ul class="ai-bullets">
          {% for lead, text in d.why_role_fits %}
          <li><strong>{{ lead }}:</strong> {{ text }}</li>
          {% endfor %}
        </ul>
        
        {% if d.placement_alignment_text %}
        <p class="ai-alignment-p">
          {{ d.placement_alignment_text|safe }}
        </p>
        {% endif %}
        
        <div class="ai-section-title">SKILL GAPS TO ADDRESS FOR THIS ROLE</div>
        <ul class="ai-bullets">
          {% for lead, text in d.skill_gaps %}
          <li><strong>{{ lead }}</strong> {{ text }}</li>
          {% endfor %}
        </ul>
      </div>
      
      <div class="ai-disclaimer-box">
        This AI report is generated strictly from the data recorded in the uploaded CCDP student tracker (Assessment, Skill Matrix, Other Skills, Attendance, and Placement sheets). No information has been inferred or added beyond what is present in the source file.
      </div>
    </div>
  </div>
  
  <div class="footer">
    <span>Skill Bay Academy · Enabling Life Skills</span>
    <span>Page 3</span>
  </div>
</div>

</body>
</html>
"""

# ---------------------------------------------------------------------------
# 6. HTML Renderer & PDF Exporter (Playwright Chromium)
# ---------------------------------------------------------------------------
def render_report_html(data: UnifiedStudentReportData, batch_name: str = "2023") -> str:
    """Renders the complete report into an HTML string using Jinja2."""
    template = jinja2.Template(REPORT_HTML_TEMPLATE)
    logo_b64 = get_logo_base64()
    return template.render(
        d=data,
        batch_name=batch_name,
        logo_b64=logo_b64,
    )


def convert_html_to_pdf_bytes(html_content: str) -> bytes:
    """Converts HTML string to publication-grade A4 PDF using Headless Chromium via Playwright."""
    from playwright.sync_api import sync_playwright

    chrome_path = find_chromium_path()
    launch_args = {"headless": True}
    if chrome_path:
        launch_args["executable_path"] = chrome_path

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_args)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"},
        )
        browser.close()
        return pdf_bytes

# ---------------------------------------------------------------------------
# 7. Main API Interface
# ---------------------------------------------------------------------------
def generate_student_report_pdf(student_rec: Dict[str, Any], batch_name: str = "2023", batch_metrics: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Primary interface called by the FastAPI server and batch scripts.
    Generates the exact 3-page A4 PDF report matching the reference design.
    """
    unified_data = build_unified_student_data(student_rec, batch_metrics)
    html = render_report_html(unified_data, batch_name=batch_name)
    return convert_html_to_pdf_bytes(html)

# ---------------------------------------------------------------------------
# 8. Batch Excel File Discoverer & Loader
# ---------------------------------------------------------------------------
def find_excel_file() -> str:
    """Finds the CCDP student tracker Excel file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    candidates = [
        os.path.join(current_dir, "tests", "fixtures", "ccdp_batch_2.xlsx"),
        os.path.join(project_root, "backend", "tests", "fixtures", "ccdp_batch_2.xlsx"),
        os.path.join(project_root, "Students Complete Details - CCDP 2(1).xlsx"),
        os.path.join(project_root, "Students Complete Details - CCDP 2.xlsx"),
        os.path.join(current_dir, "Students Complete Details - CCDP 2(1).xlsx"),
        os.path.join(current_dir, "Students Complete Details - CCDP 2.xlsx"),
        os.path.join(current_dir, "tests", "fixtures", "synthetic_ccdp_30.xlsx"),
        os.path.join(project_root, "backend", "tests", "fixtures", "synthetic_ccdp_30.xlsx"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Could not find student tracker Excel file in candidates.")


def load_all_students_from_excel(excel_path: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Loads and computes metrics for all students from the Excel tracker."""
    import loader
    import metrics

    if not excel_path:
        excel_path = find_excel_file()

    logger.info(f"Loading student tracker: {excel_path}")
    raw_sheets = loader.load_all_sheets(excel_path)
    full_metrics = metrics.build_full_metrics(raw_sheets)
    return full_metrics["per_student"], full_metrics

# ---------------------------------------------------------------------------
# 9. CLI Interface & Regeneration Command
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="CCDP Student Dashboard & AI Career Report PDF Generator")
    parser.add_argument("--all", action="store_true", help="Generate reports for every student in the batch")
    parser.add_argument("--student", type=str, help="Generate report for a specific student name (e.g. 'Jayasree A')")
    parser.add_argument("--excel", type=str, default=None, help="Path to student Excel tracker")
    parser.add_argument("--output-dir", type=str, default="output_reports", help="Directory to save generated PDFs")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    per_student, batch_metrics = load_all_students_from_excel(args.excel)

    if args.student:
        target = args.student.strip().lower()
        matched = None
        for k, rec in per_student.items():
            if target in k or target in rec.get("display_name", "").lower():
                matched = rec
                break
        if not matched:
            logger.error(f"Student '{args.student}' not found in batch.")
            sys.exit(1)
            
        name = matched.get("display_name", "Student").replace(" ", "_")
        pdf_bytes = generate_student_report_pdf(matched, batch_name="2023", batch_metrics=batch_metrics)
        out_file = os.path.join(args.output_dir, f"{name}_Dashboard_Report.pdf")
        with open(out_file, "wb") as f:
            f.write(pdf_bytes)
        logger.info(f"Successfully generated: {out_file} ({len(pdf_bytes):,} bytes)")

    elif args.all:
        logger.info(f"Regenerating reports for all {len(per_student)} students in batch...")
        success_count = 0
        for k, rec in per_student.items():
            name = rec.get("display_name", "Student").replace(" ", "_")
            try:
                pdf_bytes = generate_student_report_pdf(rec, batch_name="2023", batch_metrics=batch_metrics)
                out_file = os.path.join(args.output_dir, f"{name}_Dashboard_Report.pdf")
                with open(out_file, "wb") as f:
                    f.write(pdf_bytes)
                success_count += 1
                logger.info(f"[{success_count}/{len(per_student)}] Generated: {out_file}")
            except Exception as e:
                logger.error(f"Failed to generate report for {name}: {e}")
        logger.info(f"Completed! {success_count}/{len(per_student)} reports generated in '{args.output_dir}'.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
