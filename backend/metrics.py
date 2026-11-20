"""
metrics.py - Pure computation layer (no LLM, no DB, no Excel reading)
======================================================================
Computes derived metrics with exact decimal arithmetic and competition ranking:
- Per-student: total score, overall %, class rank with ties (1, 2, 2, 4), attendance %, salary rank
- Batch-level: class average per subject (excluding absents), overall class average, typing stats, batch distribution
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Any, Dict, List, Optional, Tuple

def round_half_up(val: float | Decimal, decimals: int = 1) -> float:
    """Rounds float/Decimal using ROUND_HALF_UP to avoid floating-point drift."""
    try:
        d = Decimal(str(val))
        fmt = "0." + "0" * decimals if decimals > 0 else "0"
        return float(d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP))
    except Exception:
        return round(float(val), decimals)

# ---------------------------------------------------------------------------
# Competition Ranking
# ---------------------------------------------------------------------------

def compute_competition_ranks(items: List[Tuple[str, float]], reverse: bool = True) -> Dict[str, Tuple[int, bool]]:
    """
    Computes competition ranks with ties: (1, 2, 2, 4).
    Returns {key: (rank, is_tied)}.
    """
    sorted_items = sorted(items, key=lambda x: x[1], reverse=reverse)
    ranks: Dict[str, Tuple[int, bool]] = {}
    i = 0
    n = len(sorted_items)
    while i < n:
        score = sorted_items[i][1]
        tied_group = [sorted_items[j][0] for j in range(i, n) if sorted_items[j][1] == score]
        rank_num = i + 1
        is_tied = len(tied_group) > 1
        for k in tied_group:
            ranks[k] = (rank_num, is_tied)
        i += len(tied_group)
    return ranks

# ---------------------------------------------------------------------------
# Assessment Metrics
# ---------------------------------------------------------------------------

def compute_assessment_metrics(students: dict, max_marks: dict, total_max_benchmark: Optional[float] = None) -> tuple[dict, dict, float, dict]:
    """
    Computes student scores, totals, percentages, and component class averages.
    Absents are counted as 0 with max marks included, but excluded from component class average.
    """
    per_student = {}
    component_scores_list: Dict[str, List[float]] = {subj: [] for subj in max_marks.keys()}
    
    total_possible_marks = total_max_benchmark or sum(max_marks.values())
    
    for cn, rec in students.items():
        raw_scores = rec.get("assessment_scores") or rec.get("subject_scores") or {}
        if isinstance(raw_scores, list):
            scores = {
                item["component"]: item.get("score_num", item.get("score", 0.0))
                for item in raw_scores
                if isinstance(item, dict) and "component" in item
            }
        elif isinstance(raw_scores, dict):
            scores = raw_scores
        else:
            scores = {}

        att = rec.get("attendance", {})
        absent_subjs = rec.get("absent_subjects", [])
        
        student_total = 0.0
        per_subject_pct = {}
        
        for subject, mx in max_marks.items():
            val = scores.get(subject)
            is_absent = (subject in absent_subjs) or (isinstance(val, str) and val.strip().upper() in ["A", "ABSENT"])
            
            if is_absent:
                score_num = 0.0
                pct = 0.0
            else:
                try:
                    score_num = float(val) if val is not None else 0.0
                except (ValueError, TypeError):
                    score_num = 0.0
                component_scores_list.setdefault(subject, []).append(score_num)
                pct = round_half_up((score_num / mx) * 100.0, 1) if mx > 0 else 0.0
                
            student_total += score_num
            per_subject_pct[subject] = pct
            
        overall_pct = round_half_up((student_total / total_possible_marks) * 100.0, 1) if total_possible_marks > 0 else 0.0
        
        att_pct = rec.get("attendance_pct", att.get("pct", 0.0))
        present = rec.get("present_days", att.get("present", 0))
        total_days = rec.get("total_trackable_days", att.get("total_trackable", 0))
        
        per_student[cn] = {
            "total_score": round_half_up(student_total, 1),
            "total_max": round_half_up(total_possible_marks, 1),
            "overall_pct": overall_pct,
            "per_subject_pct": per_subject_pct,
            "attendance_pct": round_half_up(att_pct, 1),
            "present_days": present,
            "total_trackable_days": total_days,
            "absent_subjects": absent_subjs,
        }
        
    # Competition ranking (1, 2, 2, 4) by total_score descending
    score_tuples = [(cn, data["total_score"]) for cn, data in per_student.items()]
    ranks = compute_competition_ranks(score_tuples, reverse=True)
    for cn, (rank_num, is_tied) in ranks.items():
        per_student[cn]["class_rank"] = rank_num
        per_student[cn]["is_rank_tied"] = is_tied

    # Class average % per subject (excluding absents)
    class_avg_pct_per_subject = {}
    class_avg_score_per_subject = {}
    for subj, mx in max_marks.items():
        scores_for_subj = component_scores_list.get(subj, [])
        if scores_for_subj:
            avg_sc = round_half_up(sum(scores_for_subj) / len(scores_for_subj), 1)
            avg_pct = round_half_up((avg_sc / mx) * 100.0, 1) if mx > 0 else 0.0
        else:
            avg_sc = 0.0
            avg_pct = 0.0
        class_avg_score_per_subject[subj] = avg_sc
        class_avg_pct_per_subject[subj] = avg_pct

    # Overall class average %: mean of overall percentages
    all_overall_pcts = [d["overall_pct"] for d in per_student.values()]
    class_avg_overall_pct = round_half_up(sum(all_overall_pcts) / len(all_overall_pcts), 1) if all_overall_pcts else 0.0
    
    # Statistical distribution (mean, median, std, min, max)
    scores_list = [d["total_score"] for d in per_student.values()]
    sorted_scores = sorted(scores_list)
    n = len(sorted_scores)
    median_score = (sorted_scores[n // 2] if n % 2 != 0 else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2.0) if n else 0.0
    mean_score = sum(scores_list) / n if n else 0.0
    std_score = math.sqrt(sum((x - mean_score) ** 2 for x in scores_list) / n) if n > 1 else 0.0
    
    batch_stats = {
        "mean_score": round_half_up(mean_score, 1),
        "median_score": round_half_up(median_score, 1),
        "std_score": round_half_up(std_score, 1),
        "min_score": round_half_up(min(scores_list), 1) if scores_list else 0.0,
        "max_score": round_half_up(max(scores_list), 1) if scores_list else 0.0,
        "class_avg_score_per_subject": class_avg_score_per_subject,
    }

    return per_student, class_avg_pct_per_subject, class_avg_overall_pct, batch_stats

# ---------------------------------------------------------------------------
# Skill Matrix & Typing Metrics
# ---------------------------------------------------------------------------

def compute_skill_matrix_metrics(students: dict) -> tuple[dict, dict, dict]:
    per_student = {}
    skill_lists: Dict[str, List[float]] = {}
    typing_values: List[float] = []

    for cn, rec in students.items():
        sm = rec.get("skills", rec.get("skill_matrix", {}))
        typing_wpm = rec.get("typing_speed")
        skill_scores = {}

        for col, val in sm.items():
            if not isinstance(val, (int, float)):
                continue
            col_n = col.lower()
            if "typing" in col_n or "wpm" in col_n:
                if typing_wpm is None:
                    typing_wpm = float(val)
            else:
                skill_scores[col] = float(val)
                skill_lists.setdefault(col, []).append(float(val))

        if typing_wpm is not None:
            typing_values.append(float(typing_wpm))

        per_student[cn] = {
            "typing_wpm": int(typing_wpm) if typing_wpm is not None else None,
            "skill_scores": skill_scores,
        }

    class_skill_averages = {
        skill: round_half_up(sum(vals) / len(vals), 1)
        for skill, vals in skill_lists.items()
    }

    typing_stats = {
        "avg": round_half_up(sum(typing_values) / len(typing_values), 1) if typing_values else 0.0,
        "min": round_half_up(min(typing_values), 1) if typing_values else 0.0,
        "max": round_half_up(max(typing_values), 1) if typing_values else 0.0,
        "count": len(typing_values),
    }

    return per_student, class_skill_averages, typing_stats

# ---------------------------------------------------------------------------
# Placement Salary Ranks (Only placed students with valid numeric salary)
# ---------------------------------------------------------------------------

def compute_placement_ranks(students: dict) -> dict:
    """
    Ranks placed students with positive salary using competition ranking with ties.
    Returns {canonical_name -> {'rank': int, 'display': str, 'total_placed': int}}.
    """
    placed_with_salary = []
    for cn, rec in students.items():
        p = rec.get("placement") or {}
        sal_num = p.get("salary_num")
        is_not_joined = p.get("is_not_joined", False)
        if p.get("is_available") and not is_not_joined and sal_num is not None and sal_num > 0:
            placed_with_salary.append((cn, float(sal_num)))

    total_eligible = len(placed_with_salary)
    if not total_eligible:
        return {}

    ranked = compute_competition_ranks(placed_with_salary, reverse=True)
    result = {}

    for cn, (rank_num, is_tied) in ranked.items():
        suffix = "th"
        if rank_num % 10 == 1 and rank_num % 100 != 11:
            suffix = "st"
        elif rank_num % 10 == 2 and rank_num % 100 != 12:
            suffix = "nd"
        elif rank_num % 10 == 3 and rank_num % 100 != 13:
            suffix = "rd"

        tied_str = " (Tied)" if is_tied else ""
        disp = f"{rank_num}{suffix} of {total_eligible}{tied_str}"

        result[cn] = {
            "rank": rank_num,
            "is_tied": is_tied,
            "display": disp,
            "total_placed_with_salary": total_eligible,
        }

    return result

# ---------------------------------------------------------------------------
# Strengths & Weaknesses Determination
# ---------------------------------------------------------------------------

def compute_strengths_weaknesses(per_subject_pct: dict, class_avg_pct: dict) -> tuple[list, list]:
    strengths = []
    weaknesses = []
    for subj, pct in per_subject_pct.items():
        avg = class_avg_pct.get(subj, 0.0)
        gap = pct - avg
        if gap >= 4.0:
            strengths.append((subj, gap))
        elif gap <= -4.0:
            weaknesses.append((subj, abs(gap)))

    strengths.sort(key=lambda x: x[1], reverse=True)
    weaknesses.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in strengths], [w[0] for w in weaknesses]

# ---------------------------------------------------------------------------
# Master Metrics Builder
# ---------------------------------------------------------------------------

def build_full_metrics(loader_result: dict) -> dict:
    students = loader_result.get("students", {})
    
    # Extract max marks from assessment_meta or loader_result
    assess_meta = loader_result.get("assessment_meta", {})
    if assess_meta and "components" in assess_meta:
        max_marks = {c["display_name"]: c["max_marks"] for c in assess_meta["components"]}
        total_batch_max = assess_meta.get("total_batch_max")
    else:
        max_marks = loader_result.get("max_marks", {})
        total_batch_max = loader_result.get("total_max") or sum(max_marks.values())

    assess_metrics, class_avg_subj, class_avg_overall, batch_stats = compute_assessment_metrics(
        students, max_marks, total_batch_max
    )
    skill_metrics, class_skill_avgs, typing_stats = compute_skill_matrix_metrics(students)
    placement_ranks = compute_placement_ranks(students)

    combined = {}
    class_size = len(students)

    for cn, rec in students.items():
        am = assess_metrics.get(cn, {})
        sm = skill_metrics.get(cn, {})

        strengths, weaknesses = compute_strengths_weaknesses(
            am.get("per_subject_pct", {}),
            class_avg_subj,
        )

        placement_info = rec.get("placement") or {}
        pr = placement_ranks.get(cn, {})
        if placement_info.get("is_available"):
            if placement_info.get("is_not_joined"):
                placement_info["cohort_rank"] = "Offer Received · Not Joined"
            elif pr:
                placement_info["cohort_rank"] = pr.get("display", "")
                placement_info["salary_rank"] = pr.get("rank")
            else:
                placement_info["cohort_rank"] = "Placed"
        else:
            placement_info["cohort_rank"] = None

        rank_val = am.get("class_rank", 1)
        is_top_performer = (rank_val <= 3)

        combined[cn] = {
            # Identity
            "canonical_name": cn,
            "display_name": rec.get("display_name", cn),
            "enrolment_no": rec.get("enrolment_no", ""),
            "gender": rec.get("gender", "Not recorded"),
            "age": rec.get("age", "—"),
            "qualification": rec.get("qualification", "Graduate"),
            "college": rec.get("college", "Skill Bay Academy"),
            "home_district": rec.get("home_district", "Not recorded"),
            "hostelite_status": rec.get("hostelite_status", "Not recorded"),
            "parent_meet_status": rec.get("parent_meet_status", "Not recorded"),
            "reference": rec.get("reference", "Direct"),
            # Assessment
            "assessment_scores": rec.get("subject_scores") or rec.get("assessment_scores", {}),
            "max_marks": max_marks,
            "total_score": am.get("total_score", 0.0),
            "total_max": am.get("total_max", total_batch_max),
            "overall_pct": am.get("overall_pct", 0.0),
            "per_subject_pct": am.get("per_subject_pct", {}),
            "class_rank": rank_val,
            "is_rank_tied": am.get("is_rank_tied", False),
            "is_top_performer": is_top_performer,
            "class_size": class_size,
            "absent_subjects": am.get("absent_subjects", []),
            # Class-level stats
            "class_avg_pct_per_subject": class_avg_subj,
            "class_avg_overall_pct": class_avg_overall,
            "batch_stats": batch_stats,
            # Attendance
            "attendance_pct": am.get("attendance_pct", 0.0),
            "present_days": am.get("present_days", 0),
            "total_trackable_days": am.get("total_trackable_days", 0),
            # Skill matrix
            "typing_wpm": sm.get("typing_wpm", 0),
            "skill_scores": sm.get("skill_scores", {}),
            "class_skill_averages": class_skill_avgs,
            "typing_stats": typing_stats,
            # Placement
            "placement": placement_info,
            "placement_rank": pr.get("rank"),
            "cohort_rank": placement_info.get("cohort_rank"),
            # Supplementary
            "other_skills_text": rec.get("other_skills_text", "Not recorded"),
            # Derived
            "strengths": strengths,
            "weaknesses": weaknesses,
        }

    return {
        "per_student": combined,
        "class_avg_pct_per_subject": class_avg_subj,
        "class_avg_overall_pct": class_avg_overall,
        "class_skill_averages": class_skill_avgs,
        "typing_stats": typing_stats,
        "batch_stats": batch_stats,
        "max_marks": max_marks,
        "total_batch_max": total_batch_max,
        "student_count": len(combined),
        "dq_warnings": loader_result.get("warnings", []),
        "manifest": loader_result.get("manifest", {}),
    }
