"""
Deterministic scoring engine for Skill Bay Academy (Kauvery Hospital CCDP).
Uses absolute scale normalization (no cross-student min-max scaling)
so every student's score reflects their actual performance accurately.
"""
from __future__ import annotations
import math


def normalize_score(raw_value: float, max_scale: float = 100.0) -> float:
    """Normalize a raw score against its maximum scale (e.g. 8.5/10 -> 85.0)."""
    try:
        val = float(raw_value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(val) or val < 0:
        return 0.0
    if max_scale <= 0:
        return min(max(val, 0.0), 100.0)
    score_100 = (val / max_scale) * 100.0
    return round(min(max(score_100, 0.0), 100.0), 1)


def overall_score(
    skill_scores: dict,
    attendance_pct: float,
    skill_weight: float = 0.75,
    att_weight: float = 0.25,
) -> float:
    """
    Weighted blend: skills 75% (default), attendance 25% (default).
    Weights are configurable via admin settings (must sum to 1.0).
    """
    if not skill_scores:
        skill_component = 0.0
    else:
        skill_component = sum(skill_scores.values()) / len(skill_scores)
    return round(skill_component * skill_weight + attendance_pct * att_weight, 1)


def placement_readiness_pct(overall: float, attendance_pct: float, top_role_confidence: float) -> float:
    """Blend of overall score, attendance, and how strong the best-fit role match is."""
    val = overall * 0.55 + attendance_pct * 0.15 + top_role_confidence * 0.30
    return round(min(max(val, 0.0), 99.0), 1)


def strengths_and_weaknesses(skill_scores: dict, threshold_strong=70.0, threshold_weak=60.0):
    """
    Identifies genuine strengths and areas needing development.
    Guarantees meaningful feedback even for top or struggling students.
    """
    if not skill_scores:
        return [], []

    sorted_skills = sorted(skill_scores.items(), key=lambda item: item[1], reverse=True)

    strengths = [k for k, v in sorted_skills if v >= threshold_strong]
    weaknesses = [k for k, v in sorted_skills if v < threshold_weak]
    weaknesses.reverse()

    if not strengths and sorted_skills:
        strengths = [sorted_skills[0][0]]
    if not weaknesses and len(sorted_skills) > 1 and sorted_skills[-1][1] < 85:
        weaknesses = [sorted_skills[-1][0]]

    return strengths[:4], weaknesses[:4]


SALARY_BANDS_LPA = [
    (85, "₹4.5–7.0 LPA"),
    (70, "₹3.5–5.0 LPA"),
    (55, "₹2.8–3.8 LPA"),
    (40, "₹2.2–2.8 LPA"),
    (0, "₹1.8–2.4 LPA"),
]


def predict_salary_band(overall: float) -> str:
    for threshold, band in SALARY_BANDS_LPA:
        if overall >= threshold:
            return band
    return SALARY_BANDS_LPA[-1][1]


def interview_readiness_label(overall: float) -> str:
    if overall >= 80:
        return "Excellent — Ready for Kauvery Hospital & Partner Interviews"
    if overall >= 65:
        return "Good — Ready with Light Mock Interview Practice"
    if overall >= 50:
        return "Developing — Needs 1-2 Weeks of Focused Competency Prep"
    return "Needs Training — Foundational CCDP Gap Remediation Required"
