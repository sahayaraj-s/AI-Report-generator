"""
metrics.py - Pure computation layer (no LLM, no DB, no Excel reading)
======================================================================
Takes the student dict from loader.py and computes all derived metrics:
- Per-student: total score, overall %, class rank, per-subject %, attendance %
- Batch-level: class average per subject, class rank by salary among placed students
- Typing speed: vs class average, class range (min-max)
"""
from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Per-student assessment metrics
# ---------------------------------------------------------------------------

def compute_assessment_metrics(students: dict, max_marks: dict, total_max_benchmark: float = 265.0) -> tuple[dict, dict, float]:
    per_student = {}

    for cn, rec in students.items():
        scores = rec.get("assessment_scores", {})
        att = rec.get("attendance", {})

        total_score = 0.0
        missing_subjects_max = 0.0
        per_subject_pct = {}

        for subject, mx in max_marks.items():
            if subject in scores and isinstance(scores[subject], (int, float)):
                raw_score = scores[subject]
                pct = round((raw_score / mx) * 100, 1) if mx > 0 else 0.0
                per_subject_pct[subject] = pct
                total_score += raw_score
            else:
                # Exclude missing subject from student total and average
                missing_subjects_max += mx

        # If benchmark is provided (e.g. 265.0), subtract missing subjects (Kasthuri R -> 245.0)
        if total_max_benchmark:
            student_total_max = round(total_max_benchmark - missing_subjects_max, 1)
        else:
            student_total_max = round(sum(max_marks.values()) - missing_subjects_max, 1)

        overall_pct = round((total_score / student_total_max) * 100, 1) if student_total_max > 0 else 0.0

        present = att.get("present", 0)
        total_days = att.get("total_trackable", 0)
        att_pct = att.get("pct", 0.0)

        per_student[cn] = {
            "total_score": round(total_score, 1),
            "total_max": student_total_max,
            "overall_pct": overall_pct,
            "per_subject_pct": per_subject_pct,
            "attendance_pct": att_pct,
            "present_days": present,
            "total_trackable_days": total_days,
        }

    # Class rank by total_score descending
    ranked = sorted(per_student.keys(), key=lambda cn: per_student[cn]["total_score"], reverse=True)
    for rank_idx, cn in enumerate(ranked, 1):
        per_student[cn]["class_rank"] = rank_idx

    # Class average % per subject
    subject_pct_lists: dict = {}
    for cn, data in per_student.items():
        for subj, pct in data["per_subject_pct"].items():
            subject_pct_lists.setdefault(subj, []).append(pct)

    class_avg_pct_per_subject = {
        subj: round(sum(vals) / len(vals), 1)
        for subj, vals in subject_pct_lists.items()
    }

    # Overall class average %
    if total_max_benchmark and per_student:
        total_batch_score = sum(d["total_score"] for d in per_student.values())
        class_avg_overall_pct = round((total_batch_score / (total_max_benchmark * len(per_student))) * 100, 1)
    else:
        pcts = [d["overall_pct"] for d in per_student.values()]
        class_avg_overall_pct = round(sum(pcts) / len(pcts), 1) if pcts else 0.0

    return per_student, class_avg_pct_per_subject, class_avg_overall_pct


# ---------------------------------------------------------------------------
# Skill matrix metrics
# ---------------------------------------------------------------------------

def compute_skill_matrix_metrics(students: dict) -> tuple[dict, dict, dict]:
    per_student = {}
    skill_lists: dict = {}
    typing_values = []

    for cn, rec in students.items():
        sm = rec.get("skill_matrix", {})
        typing_wpm = None
        skill_scores = {}

        for col, val in sm.items():
            if not isinstance(val, (int, float)):
                continue
            col_n = col.lower()
            if "typing" in col_n or "wpm" in col_n:
                typing_wpm = val
                typing_values.append(val)
            else:
                skill_scores[col] = val
                skill_lists.setdefault(col, []).append(val)

        per_student[cn] = {"typing_wpm": typing_wpm, "skill_scores": skill_scores}

    class_skill_averages = {
        skill: round(sum(vals) / len(vals), 2)
        for skill, vals in skill_lists.items()
    }

    typing_stats = {
        "avg": round(sum(typing_values) / len(typing_values), 1) if typing_values else None,
        "min": round(min(typing_values), 1) if typing_values else None,
        "max": round(max(typing_values), 1) if typing_values else None,
    }

    return per_student, class_skill_averages, typing_stats


# ---------------------------------------------------------------------------
# Placement salary rank
# ---------------------------------------------------------------------------

def compute_placement_ranks(students: dict, total_cohort: int = 30) -> dict:
    """
    Among placed students only, rank by salary using competition ranking with ties (1, 1, 3, 3, 5...).
    Returns {canonical_name -> {'rank': int, 'display': str}}.
    """
    placed = [
        (cn, rec["placement"]["salary_num"])
        for cn, rec in students.items()
        if rec.get("placement") and rec["placement"].get("salary_num", 0) > 0
    ]
    placed_sorted = sorted(placed, key=lambda x: x[1], reverse=True)

    ranks = {}
    i = 0
    while i < len(placed_sorted):
        sal = placed_sorted[i][1]
        tied_group = [placed_sorted[j][0] for j in range(i, len(placed_sorted)) if placed_sorted[j][1] == sal]
        rank_num = i + 1
        is_tied = len(tied_group) > 1

        suffix = "th"
        if rank_num % 10 == 1 and rank_num % 100 != 11:
            suffix = "st"
        elif rank_num % 10 == 2 and rank_num % 100 != 12:
            suffix = "nd"
        elif rank_num % 10 == 3 and rank_num % 100 != 13:
            suffix = "rd"

        tied_str = " (Tied)" if is_tied else ""
        disp = f"{rank_num}{suffix} of {total_cohort}{tied_str}"

        for cn in tied_group:
            ranks[cn] = {
                "rank": rank_num,
                "display": disp,
            }
        i += len(tied_group)

    return ranks


# ---------------------------------------------------------------------------
# Strengths and weaknesses (from per-subject %)
# ---------------------------------------------------------------------------

def compute_strengths_weaknesses(per_subject_pct: dict, class_avg: dict) -> tuple:
    strengths = []
    weaknesses = []
    for subj, pct in per_subject_pct.items():
        avg = class_avg.get(subj, 0)
        gap = pct - avg
        if gap > 5:
            strengths.append((subj, gap))
        elif gap < -5:
            weaknesses.append((subj, abs(gap)))

    strengths.sort(key=lambda x: x[1], reverse=True)
    weaknesses.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in strengths], [w[0] for w in weaknesses]


# ---------------------------------------------------------------------------
# Build full metrics bundle
# ---------------------------------------------------------------------------

def build_full_metrics(loader_result: dict) -> dict:
    students = loader_result["students"]
    max_marks = loader_result["max_marks"]
    total_max_benchmark = loader_result.get("total_max") or 265.0

    assess_metrics, class_avg_subj, class_avg_overall = compute_assessment_metrics(
        students, max_marks, total_max_benchmark
    )
    skill_metrics, class_skill_avgs, typing_stats = compute_skill_matrix_metrics(students)
    placement_ranks = compute_placement_ranks(students, total_cohort=len(students))

    combined = {}
    for cn, rec in students.items():
        am = assess_metrics.get(cn, {})
        sm = skill_metrics.get(cn, {})

        strengths, weaknesses = compute_strengths_weaknesses(
            am.get("per_subject_pct", {}),
            class_avg_subj,
        )

        placement_info = rec.get("placement")
        if placement_info:
            pr = placement_ranks.get(cn, {})
            placement_info["cohort_rank"] = pr.get("display", "")
            placement_info["salary_rank"] = pr.get("rank")

        combined[cn] = {
            # Identity
            "canonical_name": cn,
            "display_name": rec.get("display_name", cn),
            "profile": rec.get("profile", {}),
            # Assessment
            "assessment_scores": rec.get("assessment_scores", {}),
            "max_marks": max_marks,
            "total_score": am.get("total_score", 0.0),
            "total_max": am.get("total_max", 0.0),
            "overall_pct": am.get("overall_pct", 0.0),
            "per_subject_pct": am.get("per_subject_pct", {}),
            "class_rank": am.get("class_rank", 0),
            "class_size": len(students),
            # Class-level stats
            "class_avg_pct_per_subject": class_avg_subj,
            "class_avg_overall_pct": class_avg_overall,
            # Attendance
            "attendance_pct": am.get("attendance_pct", 0.0),
            "present_days": am.get("present_days", 0),
            "total_trackable_days": am.get("total_trackable_days", 0),
            # Skill matrix
            "typing_wpm": sm.get("typing_wpm"),
            "skill_scores": sm.get("skill_scores", {}),
            "class_skill_averages": class_skill_avgs,
            "typing_stats": typing_stats,
            # Placement
            "placement": rec.get("placement"),
            "placement_rank": placement_ranks.get(cn, {}).get("rank"),
            "cohort_rank": placement_ranks.get(cn, {}).get("display"),
            # Supplementary
            "other_skills": rec.get("other_skills", {}),
            "hostelite": rec.get("hostelite"),
            "parent_meet": rec.get("parent_meet"),
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
        "max_marks": max_marks,
        "student_count": len(combined),
        "dq_warnings": loader_result.get("dq_warnings", []),
        "manifest": loader_result.get("manifest", {}),
    }
