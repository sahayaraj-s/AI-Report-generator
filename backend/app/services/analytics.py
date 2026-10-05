"""
analytics.py - Unified Single Source of Truth for Placement Analytics
====================================================================
Computes:
- Consolidated student roster
- Skill scores (only genuine skills, normalized 0-100)
- Overall blended score (configurable weights, default 75% skill + 25% attendance)
- Placement readiness % and qualification (readiness cutoff from settings)
- Performance tiers (Tier 1-4 from settings)
- Attendance stats (parsed strictly from P/A cells; N/A when absent, never silent 75%)
- Typing stats (WPM vs target)
- Placement status (Placed vs Placement Ready are strictly separate concepts)
- Role fit and Kauvery unit fulfillment matrix
- Full dashboard KPIs, radar, histogram, remediation, and funnel
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Sequence
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    AnalysisResult,
    Batch,
    Course,
    Institute,
    JobRoleModel,
    Skill,
    Student,
    StudentScore,
    Upload,
)
from app.services.column_classifier import classify_column
from app.services.job_roles import match_job_roles, get_all_job_roles
from app.services import scoring


# ---------------------------------------------------------------------------
# Filter Object
# ---------------------------------------------------------------------------

@dataclass
class AnalyticsFilters:
    batch: str = ""
    course: str = ""
    tier: str = ""  # "tier_1", "tier_2", "tier_3", "tier_4"
    readiness: str = ""  # "ready", "needs_training"
    placed: str = ""  # "placed", "unplaced", "all"
    min_score: float | None = None
    max_score: float | None = None
    min_attendance: float | None = None
    search: str = ""
    sort_by: str = "overall_score"  # "name", "overall_score", "attendance_pct", "rank"
    sort_dir: str = "desc"  # "asc", "desc"


# ---------------------------------------------------------------------------
# Central Threshold Settings
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS = {
    "skill_weight": 0.75,
    "att_weight": 0.25,
    "readiness_cutoff": 55.0,
    "readiness_target_pct": 80.0,
    "attendance_target_pct": 85.0,
    "score_benchmark": 75.0,
    "typing_target_wpm": 30.0,
    "tier_1_cutoff": 80.0,
    "tier_2_cutoff": 60.0,
    "tier_3_cutoff": 40.0,
    "fit_perfect_cutoff": 75.0,
    "fit_medium_cutoff": 55.0,
    "fit_low_cutoff": 35.0,
}


def get_threshold_settings(db: Session | None = None) -> dict:
    cfg = dict(DEFAULT_THRESHOLDS)
    if db is not None:
        inst = db.query(Institute).first()
        if inst:
            if inst.skill_weight_pct is not None:
                cfg["skill_weight"] = round(inst.skill_weight_pct / 100.0, 4)
            if inst.attendance_weight_pct is not None:
                cfg["att_weight"] = round(inst.attendance_weight_pct / 100.0, 4)
            if inst.readiness_cutoff is not None:
                cfg["readiness_cutoff"] = float(inst.readiness_cutoff)
            if inst.readiness_target_pct is not None:
                cfg["readiness_target_pct"] = float(inst.readiness_target_pct)
            if inst.attendance_target_pct is not None:
                cfg["attendance_target_pct"] = float(inst.attendance_target_pct)
            if inst.score_benchmark is not None:
                cfg["score_benchmark"] = float(inst.score_benchmark)
            if inst.typing_target_wpm is not None:
                cfg["typing_target_wpm"] = float(inst.typing_target_wpm)
            if inst.tier_1_cutoff is not None:
                cfg["tier_1_cutoff"] = float(inst.tier_1_cutoff)
            if inst.tier_2_cutoff is not None:
                cfg["tier_2_cutoff"] = float(inst.tier_2_cutoff)
            if inst.tier_3_cutoff is not None:
                cfg["tier_3_cutoff"] = float(inst.tier_3_cutoff)
            if inst.fit_perfect_cutoff is not None:
                cfg["fit_perfect_cutoff"] = float(inst.fit_perfect_cutoff)
            if inst.fit_medium_cutoff is not None:
                cfg["fit_medium_cutoff"] = float(inst.fit_medium_cutoff)
            if inst.fit_low_cutoff is not None:
                cfg["fit_low_cutoff"] = float(inst.fit_low_cutoff)
    return cfg


# ---------------------------------------------------------------------------
# Individual Student Computations
# ---------------------------------------------------------------------------

def compute_student_metrics(
    raw_data: dict,
    cfg: dict,
    db: Session | None = None,
) -> dict:
    """
    Computes all normalized metrics for a single student dict.
    Input raw_data format (from DB or consolidator):
      - name, roll_number, email, phone
      - course, batch
      - skill_scores: {skill_name: 0-100}
      - assessment_scores: {subject: raw_score}
      - attendance_pct: float | None
      - attendance_status: "tracked" | "N/A"
      - attendance_reason: str | None
      - is_placed: bool
      - placement_company: str | None
      - placement_designation: str | None
      - placement_salary: str | None
      - placement_salary_num: float
      - typing_wpm: float | None
      - compliance: dict
    """
    # 1. Genuine skills only (exclude compliance, metric, derived, admin/PII)
    raw_skills = raw_data.get("skill_scores") or {}
    genuine_skills = {}
    for k, v in raw_skills.items():
        if classify_column(k) == "skill":
            try:
                fv = float(v)
                genuine_skills[k] = round(min(max(fv, 0.0), 100.0), 1)
            except (TypeError, ValueError):
                pass

    if genuine_skills:
        skill_mean = round(sum(genuine_skills.values()) / len(genuine_skills), 1)
    else:
        skill_mean = 0.0

    # 2. Attendance
    att_pct = raw_data.get("attendance_pct")
    att_status = raw_data.get("attendance_status", "tracked")
    att_reason = raw_data.get("attendance_reason")

    if att_pct is not None:
        try:
            att_pct = round(max(0.0, min(float(att_pct), 100.0)), 1)
            att_status = "tracked"
            att_reason = None
        except (TypeError, ValueError):
            att_pct = None
            att_status = "N/A"
            att_reason = "Invalid attendance value"
    else:
        att_status = "N/A"
        att_reason = att_reason or "No attendance recorded"

    # 3. Overall Score: 75% skill + 25% attendance if attendance is tracked
    sw = cfg["skill_weight"]
    aw = cfg["att_weight"]
    if att_pct is not None and att_status == "tracked":
        overall = round(skill_mean * sw + att_pct * aw, 1)
    else:
        # Never invent 75% attendance; if attendance is N/A, overall reflects skill performance
        overall = skill_mean

    # 4. Role Matching
    role_matches = match_job_roles(genuine_skills, overall, top_n=3, db=db)
    top_role = role_matches[0] if role_matches else None
    top_conf = top_role["confidence"] if top_role else 0.0
    best_role_name = top_role["role"] if top_role else "Kauvery Hospital Placement"
    fit_tier = top_role["fit_tier"] if top_role else "Developing"

    # 5. Readiness (Score-based qualification)
    readiness_pct = scoring.placement_readiness_pct(
        overall=overall,
        attendance_pct=att_pct if att_pct is not None else overall,
        top_role_confidence=top_conf,
    )
    is_placement_ready = readiness_pct >= cfg["readiness_cutoff"]

    # 6. Performance Tier
    if overall >= cfg["tier_1_cutoff"]:
        tier_code = "tier_1"
        tier_label = f"Tier 1: High Distinction (≥{int(cfg['tier_1_cutoff'])}%)"
        tier_short = f"Tier 1 (≥{int(cfg['tier_1_cutoff'])}%)"
    elif overall >= cfg["tier_2_cutoff"]:
        tier_code = "tier_2"
        tier_label = f"Tier 2: Placement Ready ({int(cfg['tier_2_cutoff'])}-{int(cfg['tier_1_cutoff'])-1}%)"
        tier_short = f"Tier 2 ({int(cfg['tier_2_cutoff'])}-{int(cfg['tier_1_cutoff'])-1}%)"
    elif overall >= cfg["tier_3_cutoff"]:
        tier_code = "tier_3"
        tier_label = f"Tier 3: Moderate Support ({int(cfg['tier_3_cutoff'])}-{int(cfg['tier_2_cutoff'])-1}%)"
        tier_short = f"Tier 3 ({int(cfg['tier_3_cutoff'])}-{int(cfg['tier_2_cutoff'])-1}%)"
    else:
        tier_code = "tier_4"
        tier_label = f"Tier 4: Critical Remediation (<{int(cfg['tier_3_cutoff'])}%)"
        tier_short = f"Tier 4 (<{int(cfg['tier_3_cutoff'])}%)"

    # 7. Actual Placement Status
    is_placed = bool(raw_data.get("is_placed", False))
    placement_company = raw_data.get("placement_company")
    placement_designation = raw_data.get("placement_designation")
    placement_salary = raw_data.get("placement_salary")
    placement_salary_num = float(raw_data.get("placement_salary_num") or 0.0)

    # 8. Typing and Compliance
    typing_wpm = raw_data.get("typing_wpm")
    if typing_wpm is not None:
        try:
            typing_wpm = round(float(typing_wpm), 1)
        except (TypeError, ValueError):
            typing_wpm = None

    compliance = raw_data.get("compliance") or {}

    strengths, weaknesses = scoring.strengths_and_weaknesses(genuine_skills)

    return {
        "id": raw_data.get("id"),
        "name": raw_data.get("name") or raw_data.get("display_name") or "Unknown Student",
        "roll_number": raw_data.get("roll_number") or "-",
        "email": raw_data.get("email") or "-",
        "phone": raw_data.get("phone") or "-",
        "course": raw_data.get("course") or "CCDP (Career & Competency Development Program)",
        "batch": raw_data.get("batch") or "CCDP 2",
        "skill_scores": genuine_skills,
        "skill_mean": skill_mean,
        "attendance_pct": att_pct,
        "attendance_status": att_status,
        "attendance_reason": att_reason,
        "overall_score": overall,
        "placement_readiness_pct": readiness_pct,
        "placement_ready": is_placement_ready,
        "tier_code": tier_code,
        "tier_label": tier_label,
        "tier_short": tier_short,
        "is_placed": is_placed,
        "placement_company": placement_company,
        "placement_designation": placement_designation,
        "placement_salary": placement_salary,
        "placement_salary_num": placement_salary_num,
        "typing_wpm": typing_wpm,
        "compliance": compliance,
        "best_role": best_role_name,
        "fit_tier": fit_tier,
        "role_matches": role_matches,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


# ---------------------------------------------------------------------------
# Filter Engine
# ---------------------------------------------------------------------------

def apply_student_filters(students: list[dict], filters: AnalyticsFilters | None) -> list[dict]:
    if not filters:
        filters = AnalyticsFilters()

    res = students
    if filters.batch:
        res = [s for s in res if s["batch"].lower() == filters.batch.lower()]
    if filters.course:
        res = [s for s in res if s["course"].lower() == filters.course.lower()]
    if filters.tier:
        res = [s for s in res if s["tier_code"] == filters.tier]
    if filters.readiness == "ready":
        res = [s for s in res if s["placement_ready"]]
    elif filters.readiness == "needs_training":
        res = [s for s in res if not s["placement_ready"]]
    if filters.placed in ("placed", "true", "1"):
        res = [s for s in res if s["is_placed"]]
    elif filters.placed in ("unplaced", "false", "0"):
        res = [s for s in res if not s["is_placed"]]
    if filters.min_score is not None:
        res = [s for s in res if s["overall_score"] >= filters.min_score]
    if filters.max_score is not None:
        res = [s for s in res if s["overall_score"] <= filters.max_score]
    if filters.min_attendance is not None:
        res = [s for s in res if s["attendance_pct"] is not None and s["attendance_pct"] >= filters.min_attendance]
    if filters.search:
        term = filters.search.lower()
        res = [
            s for s in res
            if term in s["name"].lower()
            or term in s["roll_number"].lower()
            or term in s["email"].lower()
            or term in (s["best_role"] or "").lower()
            or term in (s["placement_company"] or "").lower()
        ]

    # Sorting
    reverse = filters.sort_dir == "desc"
    if filters.sort_by == "name":
        res = sorted(res, key=lambda s: s["name"].lower(), reverse=reverse)
    elif filters.sort_by == "attendance_pct":
        res = sorted(res, key=lambda s: s["attendance_pct"] if s["attendance_pct"] is not None else -1, reverse=reverse)
    elif filters.sort_by == "placement_readiness_pct":
        res = sorted(res, key=lambda s: s["placement_readiness_pct"], reverse=reverse)
    else:  # overall_score
        res = sorted(res, key=lambda s: s["overall_score"], reverse=reverse)

    # Compute ranks
    for rank_idx, s in enumerate(res, 1):
        s["rank"] = rank_idx

    return res


# ---------------------------------------------------------------------------
# Cohort Aggregate Calculations
# ---------------------------------------------------------------------------

def aggregate_cohort(
    students: list[dict],
    all_students_in_batch: list[dict],
    cfg: dict,
    active_roles: list[JobRoleModel] | None = None,
    all_batches: list[str] | None = None,
    all_courses: list[str] | None = None,
) -> dict:
    total_students = len(students)
    ready_count = sum(1 for s in students if s["placement_ready"])
    ready_pct = round((ready_count / total_students) * 100.0, 1) if total_students else 0.0

    placed_count = sum(1 for s in students if s["is_placed"])
    placed_pct = round((placed_count / total_students) * 100.0, 1) if total_students else 0.0

    scores = [s["overall_score"] for s in students]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    tracked_att = [s["attendance_pct"] for s in students if s["attendance_pct"] is not None]
    avg_attendance = round(sum(tracked_att) / len(tracked_att), 1) if tracked_att else None

    # Tiers
    tier_counts = {"tier_1": 0, "tier_2": 0, "tier_3": 0, "tier_4": 0}
    for s in students:
        tier_counts[s["tier_code"]] = tier_counts.get(s["tier_code"], 0) + 1

    score_tier_distribution = [
        {
            "tier": f"Tier 1: High Distinction (≥{int(cfg['tier_1_cutoff'])}%)",
            "short_label": f"Tier 1 (≥{int(cfg['tier_1_cutoff'])}%)",
            "code": "tier_1",
            "count": tier_counts["tier_1"],
            "pct": round((tier_counts["tier_1"] / total_students) * 100.0, 1) if total_students else 0.0,
            "color": "#22C55E",
            "badge_tone": "success",
        },
        {
            "tier": f"Tier 2: Placement Ready ({int(cfg['tier_2_cutoff'])}-{int(cfg['tier_1_cutoff'])-1}%)",
            "short_label": f"Tier 2 ({int(cfg['tier_2_cutoff'])}-{int(cfg['tier_1_cutoff'])-1}%)",
            "code": "tier_2",
            "count": tier_counts["tier_2"],
            "pct": round((tier_counts["tier_2"] / total_students) * 100.0, 1) if total_students else 0.0,
            "color": "#8B1D55",
            "badge_tone": "brand",
        },
        {
            "tier": f"Tier 3: Moderate Support ({int(cfg['tier_3_cutoff'])}-{int(cfg['tier_2_cutoff'])-1}%)",
            "short_label": f"Tier 3 ({int(cfg['tier_3_cutoff'])}-{int(cfg['tier_2_cutoff'])-1}%)",
            "code": "tier_3",
            "count": tier_counts["tier_3"],
            "pct": round((tier_counts["tier_3"] / total_students) * 100.0, 1) if total_students else 0.0,
            "color": "#EFBC19",
            "badge_tone": "warning",
        },
        {
            "tier": f"Tier 4: Critical Remediation (<{int(cfg['tier_3_cutoff'])}%)",
            "short_label": f"Tier 4 (<{int(cfg['tier_3_cutoff'])}%)",
            "code": "tier_4",
            "count": tier_counts["tier_4"],
            "pct": round((tier_counts["tier_4"] / total_students) * 100.0, 1) if total_students else 0.0,
            "color": "#EF4444",
            "badge_tone": "danger",
        },
    ]

    # Typing stats
    typing_vals = [s["typing_wpm"] for s in students if s["typing_wpm"] is not None]
    typing_avg = round(sum(typing_vals) / len(typing_vals), 1) if typing_vals else None
    typing_target = cfg["typing_target_wpm"]
    typing_stats = {
        "avg": typing_avg,
        "min": min(typing_vals) if typing_vals else None,
        "max": max(typing_vals) if typing_vals else None,
        "target": typing_target,
        "above_target_count": sum(1 for v in typing_vals if v >= typing_target),
        "total_tested": len(typing_vals),
    }

    # Skill aggregates & radar
    all_skill_names = set()
    for s in students:
        all_skill_names.update(s["skill_scores"].keys())

    skill_rows = []
    benchmark = cfg["score_benchmark"]
    for sname in sorted(all_skill_names):
        vals = [s["skill_scores"][sname] for s in students if sname in s["skill_scores"]]
        if vals:
            s_avg = round(sum(vals) / len(vals), 1)
            s_min = round(min(vals), 1)
            s_max = round(max(vals), 1)
            gap = round(max(0.0, benchmark - s_avg), 1)
            affected_count = sum(1 for v in vals if v < 60.0)
            at_risk = [s["name"] for s in students if sname in s["skill_scores"] and s["skill_scores"][sname] < 50.0][:5]
            skill_rows.append({
                "skill": sname,
                "average_score": s_avg,
                "min_score": s_min,
                "max_score": s_max,
                "benchmark": benchmark,
                "gap": gap,
                "affected_students_count": affected_count,
                "at_risk_students": at_risk,
            })

    skill_distribution = sorted(skill_rows, key=lambda r: r["skill"])
    weak_skill_heatmap = sorted(skill_rows, key=lambda r: r["average_score"])[:8]
    priority_remediation = sorted(skill_rows, key=lambda r: r["gap"], reverse=True)

    # Competency radar (top 10 genuine skills)
    competency_radar = [
        {
            "skill": r["skill"],
            "score": r["average_score"],
            "benchmark": benchmark,
            "full_mark": 100,
        }
        for r in skill_distribution[:10]
    ]

    # Histogram: 5 score bins
    histogram_bins = [
        {"bin": "0–20%", "count": sum(1 for s in scores if s < 20)},
        {"bin": "21–40%", "count": sum(1 for s in scores if 20 <= s < 40)},
        {"bin": "41–60%", "count": sum(1 for s in scores if 40 <= s < 60)},
        {"bin": "61–80%", "count": sum(1 for s in scores if 60 <= s < 80)},
        {"bin": "81–100%", "count": sum(1 for s in scores if s >= 80)},
    ]

    # Placement Funnel
    placement_funnel = [
        {"stage": "Enrolled", "count": total_students, "pct": 100.0},
        {"stage": "Placement Ready", "count": ready_count, "pct": ready_pct},
        {"stage": "Placed", "count": placed_count, "pct": placed_pct},
    ]

    # Placed company breakdown
    placed_companies: dict[str, int] = {}
    for s in students:
        if s["is_placed"] and s["placement_company"]:
            c = s["placement_company"]
            placed_companies[c] = placed_companies.get(c, 0) + 1

    company_breakdown = [
        {"company": c, "placed_count": count}
        for c, count in sorted(placed_companies.items(), key=lambda x: x[1], reverse=True)
    ]

    # Kauvery Unit Fulfillment Matrix
    kauvery_unit_matrix = []
    total_openings_count = 0
    recruiter_units = set()

    roles_to_eval = active_roles or []
    for r in roles_to_eval:
        unit = getattr(r, "kauvery_unit", None) or getattr(r, "company_name", "Kauvery Hospital")
        dept = getattr(r, "department", "Hospital Operations")
        openings = int(getattr(r, "openings", 0) or 0)
        total_openings_count += openings
        recruiter_units.add(unit)

        min_sc = float(getattr(r, "min_score", 50.0) or 50.0)
        matched_candidates = sum(1 for s in students if s["overall_score"] >= min_sc)
        fulfillment = round(min(100.0, (matched_candidates / max(openings, 1)) * 100.0), 1) if openings > 0 else 100.0

        kauvery_unit_matrix.append({
            "id": getattr(r, "id", 0),
            "role_name": getattr(r, "name", "Hospital Trainee"),
            "kauvery_unit": unit,
            "department": dept,
            "openings": openings,
            "demand_level": getattr(r, "demand_level", "Medium"),
            "matched_candidates": matched_candidates,
            "min_score": min_sc,
            "fulfillment_rate": fulfillment,
        })

    # Professional Compliance Card summary
    compliance_counts: dict[str, int] = {}
    for s in students:
        for k, v in s.get("compliance", {}).items():
            if v and str(v).lower() not in ("no", "none", "-", "nan"):
                compliance_counts[k] = compliance_counts.get(k, 0) + 1

    professional_compliance = [
        {"item": k, "recorded_count": v, "pct": round((v / total_students) * 100.0, 1) if total_students else 0.0}
        for k, v in sorted(compliance_counts.items())
    ]

    # Course comparison within current batch
    course_groups: dict[str, list[dict]] = {}
    for s in students:
        course_groups.setdefault(s["course"], []).append(s)
    course_comparison = [
        {
            "course": cname,
            "average_score": round(sum(s["overall_score"] for s in st_list) / len(st_list), 1),
            "student_count": len(st_list),
            "ready_count": sum(1 for s in st_list if s["placement_ready"]),
        }
        for cname, st_list in course_groups.items()
    ]

    # Top performers leaderboard
    sorted_by_score = sorted(students, key=lambda s: s["overall_score"], reverse=True)
    leaderboard = sorted_by_score[:8]
    top_performer = sorted_by_score[0]["name"] if sorted_by_score else None

    # Lists for slicers
    batches_out = all_batches if all_batches is not None else sorted(list({s["batch"] for s in all_students_in_batch}))
    courses_out = all_courses if all_courses is not None else sorted(list({s["course"] for s in all_students_in_batch}))

    return {
        "batch_list": batches_out,
        "course_list": courses_out,
        "total_students": total_students,
        "placement_ready": ready_count,
        "placement_ready_pct": ready_pct,
        "need_training": total_students - ready_count,
        "need_training_critical": tier_counts["tier_4"],
        "need_training_moderate": tier_counts["tier_3"],
        "placed_count": placed_count,
        "placed_pct": placed_pct,
        "average_score": avg_score,
        "average_attendance": avg_attendance,
        "attendance_tracked_count": len(tracked_att),
        "attendance_na_count": total_students - len(tracked_att),
        "top_performer": top_performer,
        "recruiters_partnered": len(recruiter_units),
        "total_openings": total_openings_count,
        "target_metrics": {
            "placement_target_pct": cfg["readiness_target_pct"],
            "attendance_target_pct": cfg["attendance_target_pct"],
            "score_target": cfg["score_benchmark"],
            "readiness_cutoff": cfg["readiness_cutoff"],
            "typing_target_wpm": cfg["typing_target_wpm"],
        },
        "score_tier_distribution": score_tier_distribution,
        "competency_radar": competency_radar,
        "skill_distribution": skill_distribution,
        "course_comparison": course_comparison,
        "monthly_progress": [],  # Cleanly empty unless real multi-batch/date tracking exists
        "weak_skill_heatmap": weak_skill_heatmap,
        "priority_remediation": priority_remediation,
        "score_distribution_histogram": histogram_bins,
        "placement_funnel": placement_funnel,
        "company_breakdown": company_breakdown,
        "kauvery_unit_matrix": kauvery_unit_matrix,
        "professional_compliance": professional_compliance,
        "typing_stats": typing_stats,
        "leaderboard": leaderboard,
        "students": students,
    }


# ---------------------------------------------------------------------------
# Consumers: DB & In-Memory Adapters
# ---------------------------------------------------------------------------

def load_students_from_db(db: Session) -> list[dict]:
    """Extracts raw student dictionaries from DB for compute_student_metrics."""
    db_students = db.query(Student).all()
    out = []
    for s in db_students:
        scores_dict = {}
        for sc in s.scores:
            scores_dict[sc.skill.name] = sc.score

        comp_dict = {}
        if s.compliance_json:
            try:
                comp_dict = json.loads(s.compliance_json)
            except Exception:
                pass

        out.append({
            "id": s.id,
            "name": s.name,
            "roll_number": s.roll_number,
            "email": s.email,
            "phone": s.phone,
            "course": s.course.name if s.course else "CCDP (Career & Competency Development Program)",
            "batch": s.batch.name if s.batch else "CCDP 2",
            "skill_scores": scores_dict,
            "attendance_pct": s.attendance_pct,
            "attendance_status": getattr(s, "attendance_status", "tracked") or "tracked",
            "attendance_reason": getattr(s, "attendance_reason", None),
            "is_placed": getattr(s, "is_placed", False),
            "placement_company": getattr(s, "placement_company", None),
            "placement_designation": getattr(s, "placement_designation", None),
            "placement_salary": getattr(s, "placement_salary", None),
            "placement_salary_num": getattr(s, "placement_salary_num", 0.0),
            "typing_wpm": getattr(s, "typing_wpm", None),
            "compliance": comp_dict,
        })
    return out


def compute_analytics(db: Session, filters: AnalyticsFilters | None = None) -> dict:
    """
    Primary API entry point for Dashboard, Reports, and Chat Tools using the database.
    """
    cfg = get_threshold_settings(db)
    raw_list = load_students_from_db(db)
    all_computed = [compute_student_metrics(r, cfg, db=db) for r in raw_list]
    filtered = apply_student_filters(all_computed, filters)

    active_roles = db.query(JobRoleModel).filter(JobRoleModel.is_active.is_(True)).all()
    all_batches = sorted(list({b.name for b in db.query(Batch).all() if b.name}))
    all_courses = sorted(list({c.name for c in db.query(Course).all() if c.name}))

    return aggregate_cohort(
        students=filtered,
        all_students_in_batch=all_computed,
        cfg=cfg,
        active_roles=active_roles,
        all_batches=all_batches,
        all_courses=all_courses,
    )


def compute_analytics_from_records(
    records: list[dict],
    settings_dict: dict | None = None,
    filters: AnalyticsFilters | None = None,
    db: Session | None = None,
) -> dict:
    """
    Entry point for Upload Live Preview (guarantees identical logic before save).
    """
    cfg = dict(DEFAULT_THRESHOLDS)
    if settings_dict:
        cfg.update(settings_dict)
    elif db:
        cfg = get_threshold_settings(db)

    all_computed = [compute_student_metrics(r, cfg, db=db) for r in records]
    filtered = apply_student_filters(all_computed, filters)

    active_roles = db.query(JobRoleModel).filter(JobRoleModel.is_active.is_(True)).all() if db else None

    return aggregate_cohort(
        students=filtered,
        all_students_in_batch=all_computed,
        cfg=cfg,
        active_roles=active_roles,
    )


# ---------------------------------------------------------------------------
# Specialized Tool Queries for LLM & Chat
# ---------------------------------------------------------------------------

def get_cohort_summary(db: Session, filters: AnalyticsFilters | None = None) -> dict:
    data = compute_analytics(db, filters)
    return {
        "total_students": data["total_students"],
        "placement_ready_count": data["placement_ready"],
        "placement_ready_pct": data["placement_ready_pct"],
        "placed_count": data["placed_count"],
        "placed_pct": data["placed_pct"],
        "average_score": data["average_score"],
        "average_attendance": data["average_attendance"],
        "tier_distribution": {t["code"]: t["count"] for t in data["score_tier_distribution"]},
        "top_performers": [
            {"rank": s["rank"], "name": s["name"], "score": s["overall_score"], "role": s["best_role"]}
            for s in data["leaderboard"][:5]
        ],
        "top_skills": [
            {"skill": s["skill"], "score": s["average_score"]}
            for s in data["skill_distribution"][:5]
        ],
    }


def list_students(
    db: Session,
    filters: AnalyticsFilters | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    data = compute_analytics(db, filters)
    all_matched = data["students"]
    paged = all_matched[offset: offset + limit]
    return {
        "total": len(all_matched),
        "limit": limit,
        "offset": offset,
        "students": [
            {
                "rank": s.get("rank"),
                "name": s["name"],
                "roll_number": s["roll_number"],
                "course": s["course"],
                "batch": s["batch"],
                "overall_score": s["overall_score"],
                "attendance_pct": s["attendance_pct"],
                "placement_ready": s["placement_ready"],
                "is_placed": s["is_placed"],
                "placement_company": s["placement_company"],
                "placement_designation": s["placement_designation"],
                "placement_salary": s["placement_salary"],
                "best_role": s["best_role"],
                "fit_tier": s["fit_tier"],
                "tier": s["tier_code"],
            }
            for s in paged
        ],
    }


def get_student_profile(db: Session, student_ref: int | str) -> dict | None:
    data = compute_analytics(db)
    target = None
    ref_str = str(student_ref).strip().lower()

    for s in data["students"]:
        if str(s.get("id")) == ref_str:
            target = s
            break
        if s["name"].lower() == ref_str or ref_str in s["name"].lower():
            target = s
            break
        if s["roll_number"].lower() == ref_str:
            target = s
            break

    if not target:
        return None

    # Safe return (exclude phone, email, contact PII from model payload)
    return {
        "id": target.get("id"),
        "name": target["name"],
        "roll_number": target["roll_number"],
        "course": target["course"],
        "batch": target["batch"],
        "rank": target.get("rank"),
        "overall_score": target["overall_score"],
        "attendance_pct": target["attendance_pct"],
        "attendance_status": target["attendance_status"],
        "placement_ready": target["placement_ready"],
        "placement_readiness_pct": target["placement_readiness_pct"],
        "tier": target["tier_label"],
        "is_placed": target["is_placed"],
        "placement_company": target["placement_company"],
        "placement_designation": target["placement_designation"],
        "placement_salary": target["placement_salary"],
        "typing_wpm": target["typing_wpm"],
        "skill_scores": target["skill_scores"],
        "strengths": target["strengths"],
        "weaknesses": target["weaknesses"],
        "best_role": target["best_role"],
        "fit_tier": target["fit_tier"],
        "role_matches": target["role_matches"],
        "compliance": target["compliance"],
    }


def compare_students(db: Session, refs: list[int | str]) -> list[dict]:
    profiles = []
    for r in refs:
        p = get_student_profile(db, r)
        if p:
            profiles.append(p)
    return profiles


def get_skill_stats(db: Session, skill: str | None = None, filters: AnalyticsFilters | None = None) -> dict:
    data = compute_analytics(db, filters)
    dist = data["skill_distribution"]
    if skill:
        skill_clean = skill.strip().lower()
        matched = [s for s in dist if skill_clean in s["skill"].lower()]
        return {"matched_skills": matched, "benchmark": data["target_metrics"]["score_target"]}
    return {
        "skills": dist,
        "radar": data["competency_radar"],
        "priority_remediation": data["priority_remediation"],
        "benchmark": data["target_metrics"]["score_target"],
    }


def get_attendance_stats(db: Session, filters: AnalyticsFilters | None = None) -> dict:
    data = compute_analytics(db, filters)
    students = data["students"]
    tracked = [s["attendance_pct"] for s in students if s["attendance_pct"] is not None]
    return {
        "average_attendance": data["average_attendance"],
        "target_attendance": data["target_metrics"]["attendance_target_pct"],
        "tracked_students_count": len(tracked),
        "unrecorded_students_count": len(students) - len(tracked),
        "above_90_pct": sum(1 for a in tracked if a >= 90.0),
        "between_80_90_pct": sum(1 for a in tracked if 80.0 <= a < 90.0),
        "below_80_pct": sum(1 for a in tracked if a < 80.0),
    }


def get_typing_stats(db: Session, filters: AnalyticsFilters | None = None) -> dict:
    data = compute_analytics(db, filters)
    return data["typing_stats"]


def get_placement_stats(db: Session, group_by: str = "company", filters: AnalyticsFilters | None = None) -> dict:
    data = compute_analytics(db, filters)
    students = data["students"]
    placed_students = [s for s in students if s["is_placed"]]
    unplaced_students = [s for s in students if not s["is_placed"]]

    top_packages = sorted(
        [
            {
                "name": s["name"],
                "company": s["placement_company"],
                "designation": s["placement_designation"],
                "salary": s["placement_salary"],
                "salary_num": s["placement_salary_num"],
            }
            for s in placed_students
        ],
        key=lambda x: x["salary_num"],
        reverse=True,
    )[:5]

    return {
        "total_students": len(students),
        "placed_count": len(placed_students),
        "placed_pct": data["placed_pct"],
        "unplaced_count": len(unplaced_students),
        "company_breakdown": data["company_breakdown"],
        "top_packages": top_packages,
        "unplaced_sample": [
            {"name": s["name"], "overall_score": s["overall_score"], "rank": s.get("rank")}
            for s in unplaced_students[:10]
        ],
    }


def get_job_role_matches(db: Session, student_ref: int | str | None = None, role: str | None = None) -> dict:
    if student_ref:
        profile = get_student_profile(db, student_ref)
        if not profile:
            return {"error": f"Student '{student_ref}' not found"}
        return {
            "student_name": profile["name"],
            "overall_score": profile["overall_score"],
            "best_role": profile["best_role"],
            "fit_tier": profile["fit_tier"],
            "all_role_matches": profile["role_matches"],
        }
    data = compute_analytics(db)
    matrix = data["kauvery_unit_matrix"]
    if role:
        role_clean = role.strip().lower()
        filtered_matrix = [m for m in matrix if role_clean in m["role_name"].lower()]
        return {"matched_roles": filtered_matrix}
    return {"kauvery_unit_matrix": matrix}


def get_unit_fulfillment(db: Session, filters: AnalyticsFilters | None = None) -> list[dict]:
    data = compute_analytics(db, filters)
    return data["kauvery_unit_matrix"]


def build_chart(
    db: Session,
    kind: str,
    metric: str,
    group_by: str = "tier",
    filters: AnalyticsFilters | None = None,
    limit: int = 10,
) -> dict:
    data = compute_analytics(db, filters)
    kind_lower = kind.lower()

    if metric == "tier" or group_by == "tier":
        chart_data = [
            {"name": t["short_label"], "value": t["count"], "pct": t["pct"]}
            for t in data["score_tier_distribution"]
        ]
        return {
            "kind": "bar" if kind_lower not in ("pie", "donut") else kind_lower,
            "title": "Performance Tier Distribution",
            "data": chart_data,
            "xKey": "name",
            "yKey": "value",
        }

    if metric == "skills" or group_by == "skill":
        chart_data = [
            {"skill": s["skill"], "score": s["average_score"], "benchmark": s["benchmark"]}
            for s in data["competency_radar"][:limit]
        ]
        return {
            "kind": "radar" if kind_lower == "radar" else "bar",
            "title": "Skill Competency Benchmark Comparison",
            "data": chart_data,
            "xKey": "skill",
            "yKey": "score",
        }

    if metric == "funnel" or metric == "placement":
        return {
            "kind": "bar",
            "title": "Placement Funnel Progression",
            "data": data["placement_funnel"],
            "xKey": "stage",
            "yKey": "count",
        }

    # Default to score distribution histogram
    return {
        "kind": "bar",
        "title": "Score Distribution Histogram",
        "data": data["score_distribution_histogram"],
        "xKey": "bin",
        "yKey": "count",
    }


def generate_report(db: Session, kind: str, ref: int | str | None = None) -> dict:
    if ref:
        profile = get_student_profile(db, ref)
        if not profile:
            return {"error": f"Student '{ref}' not found"}
        return {
            "kind": "student_report",
            "student": profile,
            "pdf_url": f"/api/reports/student/{profile['id']}/pdf",
        }
    data = compute_analytics(db)
    return {
        "kind": "executive_report",
        "summary": {
            "total_students": data["total_students"],
            "placement_ready": data["placement_ready"],
            "placement_ready_pct": data["placement_ready_pct"],
            "placed_count": data["placed_count"],
            "average_score": data["average_score"],
        },
        "pdf_url": "/api/reports/batch/executive/pdf",
    }

