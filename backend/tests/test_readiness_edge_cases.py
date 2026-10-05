import pytest
from app.services.analytics import compute_analytics_from_records

def test_all_students_above_cutoff():
    records = [
        {
            "name": f"Top Student {i}",
            "skill_scores": {"Basic English": 90.0, "Healthcare Operations": 88.0},
            "attendance_pct": 95.0,
            "attendance_status": "tracked",
        }
        for i in range(10)
    ]
    res = compute_analytics_from_records(records)
    assert res["total_students"] == 10
    assert res["placement_ready"] == 10
    assert res["placement_ready_pct"] == 100.0
    assert res["need_training"] == 0

def test_no_students_above_cutoff():
    records = [
        {
            "name": f"Struggling Student {i}",
            "skill_scores": {"Basic English": 20.0, "Healthcare Operations": 25.0},
            "attendance_pct": 30.0,
            "attendance_status": "tracked",
        }
        for i in range(10)
    ]
    res = compute_analytics_from_records(records)
    assert res["total_students"] == 10
    assert res["placement_ready"] == 0
    assert res["placement_ready_pct"] == 0.0
    assert res["need_training"] == 10
    assert res["need_training_critical"] == 10

def test_mixed_students_readiness():
    records = [
        {"name": "Ready 1", "skill_scores": {"Basic English": 85.0}, "attendance_pct": 90.0},
        {"name": "Ready 2", "skill_scores": {"Basic English": 80.0}, "attendance_pct": 85.0},
        {"name": "Not Ready 1", "skill_scores": {"Basic English": 30.0}, "attendance_pct": 40.0},
        {"name": "Not Ready 2", "skill_scores": {"Basic English": 25.0}, "attendance_pct": 35.0},
    ]
    res = compute_analytics_from_records(records)
    assert res["total_students"] == 4
    assert res["placement_ready"] == 2
    assert res["placement_ready_pct"] == 50.0

def test_empty_cohort_readiness():
    res = compute_analytics_from_records([])
    assert res["total_students"] == 0
    assert res["placement_ready"] == 0
    assert res["placement_ready_pct"] == 0.0
    assert res["average_score"] == 0.0
    assert res["average_attendance"] is None
