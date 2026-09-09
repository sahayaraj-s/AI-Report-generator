"""
Job role matching service for Skill Bay Academy (Kauvery Hospital CCDP).
Matches students with positions across Kauvery Hospital 12 Units and partner organisations
based on structured skill benchmarks, fit tiers, and department requirements.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from app.models import JobRoleModel


# 12 Kauvery Hospital Units
KAUVERY_UNITS = [
    "Kauvery Hospital - Trichy (Tennur)",
    "Kauvery Hospital - Trichy (Cantonment)",
    "Kauvery Hospital - Trichy (Heartcity)",
    "Kauvery Hospital - Chennai (Alwarpet)",
    "Kauvery Hospital - Chennai (Vadapalani)",
    "Kauvery Hospital - Chennai (Radial Road)",
    "Kauvery Hospital - Salem",
    "Kauvery Hospital - Hosur",
    "Kauvery Hospital - Tirunelveli",
    "Kauvery Hospital - Bengaluru (Electronic City)",
    "Kauvery Hospital - Bengaluru (Marathahalli)",
    "Kauvery Hospital - Karaikudi",
    "Kauvery Corporate / Central Office",
    "External Partner Organisation",
]

# Standard Placement Departments
DEPARTMENTS = [
    "Patient Care & Customer Relations",
    "Front Office, Admissions & Helpdesk",
    "Billing, Cashless & Health Insurance",
    "Hospital Administration & Operations",
    "IT, Systems & Healthcare Informatics",
    "Medical Records (MRD) & Quality Assurance",
    "Nursing & Clinical Operations Support",
    "Diagnostic Services & Lab Support",
    "Pharmacy Operations & Supply Chain",
    "HR, Training & Development",
    "Biomedical & Facility Management",
    "Corporate & Allied Services",
]


@dataclass
class SkillCriteria:
    skill: str
    min_score: float = 15.0    # e.g. 15
    max_score: float = 25.0    # e.g. 25

    @property
    def benchmark_pct(self) -> float:
        """What % of max_score is required? e.g. 15/25 = 60%"""
        if self.max_score <= 0:
            return 0.0
        return round((self.min_score / self.max_score) * 100, 1)


@dataclass
class JobRole:
    id: int | None
    name: str
    skill_criteria: list[SkillCriteria] = field(default_factory=list)
    min_score: float = 0.0
    demand_level: str = "Medium"
    openings: int = 0
    is_active: bool = True
    company_name: str | None = None
    kauvery_unit: str | None = None
    department: str | None = None

    @property
    def required_skills(self) -> list[str]:
        return [sc.skill for sc in self.skill_criteria]


def _parse_skill_criteria(raw: str) -> list[SkillCriteria]:
    """Parse required_skills JSON — handles both simple and structured formats."""
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if isinstance(item, str):
            result.append(SkillCriteria(skill=item, min_score=15.0, max_score=25.0))
        elif isinstance(item, dict):
            result.append(SkillCriteria(
                skill=item.get("skill", ""),
                min_score=float(item.get("min_score", 15.0)),
                max_score=float(item.get("max_score", 25.0)),
            ))
    return [sc for sc in result if sc.skill]


def get_all_job_roles(db: Session | None = None) -> list[JobRole]:
    """Return all job roles from the database."""
    if db is None:
        return []
    db_roles = db.query(JobRoleModel).all()
    out = []
    for r in db_roles:
        criteria = _parse_skill_criteria(r.required_skills or "[]")
        out.append(JobRole(
            id=r.id,
            name=r.name,
            skill_criteria=criteria,
            min_score=r.min_score or 0.0,
            demand_level=r.demand_level or "Medium",
            openings=r.openings or 0,
            is_active=r.is_active if r.is_active is not None else True,
            company_name=r.company_name,
            kauvery_unit=r.kauvery_unit or "Kauvery Hospital - Trichy (Tennur)",
            department=r.department or "Hospital Administration & Operations",
        ))
    return out


def get_active_job_roles(db: Session) -> list[JobRole]:
    return [r for r in get_all_job_roles(db) if r.is_active]


def _normalize(name: str) -> str:
    return name.strip().lower()


def _skill_match(student_skill_name: str, criteria_skill_name: str) -> bool:
    """Fuzzy match between student skill column name and role skill criteria."""
    s = _normalize(student_skill_name)
    c = _normalize(criteria_skill_name)
    if s == c or c in s or s in c:
        return True
    # Synonyms in CCDP
    comm_words = {"comm", "communication", "verbal", "english", "presentation"}
    it_words = {"office", "ms office", "excel", "word", "it", "computer"}
    soft_words = {"soft", "interpersonal", "teamwork", "etiquette"}
    analytical_words = {"analytical", "aptitude", "problem", "reasoning", "logic"}

    if any(w in s for w in comm_words) and any(w in c for w in comm_words):
        return True
    if any(w in s for w in it_words) and any(w in c for w in it_words):
        return True
    if any(w in s for w in soft_words) and any(w in c for w in soft_words):
        return True
    if any(w in s for w in analytical_words) and any(w in c for w in analytical_words):
        return True
    return False


def classify_fit(pct: float) -> str:
    """Classify suitability percentage into a fit tier."""
    if pct >= 75:
        return "Perfect Match"
    if pct >= 55:
        return "Medium Fit"
    if pct >= 35:
        return "Low Fit"
    return "Not Eligible"


def match_job_roles(skill_scores: dict, overall_score: float, top_n: int = 4, db: Session | None = None):
    """
    skill_scores: {skill_name: score_0_to_100}
    Returns a list of {role, confidence, fit_tier, matched_skills, skill_gaps, openings, company_name, kauvery_unit, department}.
    """
    roles = get_all_job_roles(db)
    if not roles:
        # Provide default Kauvery roles if database has none
        roles = _get_default_kauvery_roles()

    normalized_scores = {_normalize(k): v for k, v in skill_scores.items()}
    results = []

    for role in roles:
        if not role.is_active:
            continue

        matched = []
        skill_gaps = []
        total_benchmark = 0.0
        total_achieved = 0.0

        for crit in role.skill_criteria:
            crit_norm = _normalize(crit.skill)
            found_score = None
            found_name = None
            for skill_name, score in normalized_scores.items():
                if _skill_match(skill_name, crit_norm):
                    found_score = score
                    found_name = skill_name
                    break

            if found_score is not None:
                # Score on criteria scale
                achieved = (found_score / 100.0) * crit.max_score
                total_benchmark += crit.min_score
                total_achieved += achieved
                if achieved >= crit.min_score:
                    matched.append(found_name or crit.skill)
                else:
                    skill_gaps.append({
                        "skill": crit.skill,
                        "required": f"{crit.min_score}/{crit.max_score}",
                        "achieved": round(achieved, 1),
                    })
            else:
                total_benchmark += crit.min_score
                skill_gaps.append({
                    "skill": crit.skill,
                    "required": f"{crit.min_score}/{crit.max_score}",
                    "achieved": 0,
                })

        if total_benchmark > 0:
            criteria_pct = (total_achieved / total_benchmark) * 100.0
        else:
            n = len(role.skill_criteria)
            criteria_pct = (len(matched) / n * 100.0) if n > 0 else 70.0

        # Weighted confidence: 65% criteria + 25% overall score + 10% base
        confidence = criteria_pct * 0.65 + overall_score * 0.25 + 10.0
        confidence = round(min(max(confidence, 10.0), 99.0), 1)
        fit_tier = classify_fit(criteria_pct)

        results.append({
            "role": role.name,
            "confidence": confidence,
            "fit_tier": fit_tier,
            "criteria_pct": round(min(criteria_pct, 100.0), 1),
            "matched_skills": matched,
            "skill_gaps": skill_gaps,
            "openings": role.openings,
            "company_name": role.company_name or "Kauvery Hospital",
            "kauvery_unit": role.kauvery_unit,
            "department": role.department,
        })

    results.sort(key=lambda r: r["confidence"], reverse=True)
    return results[:top_n]


def get_role_candidates(role: JobRole, db: Session) -> list[dict]:
    """Get students matched to this role classified by fit tier."""
    from app.models import Student, StudentScore

    students = db.query(Student).all()
    candidates = []

    for student in students:
        skill_scores_raw = (
            db.query(StudentScore).filter_by(student_id=student.id).all()
        )
        skill_scores = {ss.skill.name: ss.score for ss in skill_scores_raw}
        normalized_scores = {_normalize(k): v for k, v in skill_scores.items()}

        matched = []
        skill_gaps = []
        total_benchmark = 0.0
        total_achieved = 0.0

        for crit in role.skill_criteria:
            crit_norm = _normalize(crit.skill)
            found_score = None
            found_name = None
            for skill_name, score in normalized_scores.items():
                if _skill_match(skill_name, crit_norm):
                    found_score = score
                    found_name = skill_name
                    break

            if found_score is not None:
                achieved = (found_score / 100.0) * crit.max_score
                total_benchmark += crit.min_score
                total_achieved += achieved
                if achieved >= crit.min_score:
                    matched.append(found_name or crit.skill)
                else:
                    skill_gaps.append({
                        "skill": crit.skill,
                        "required": f"{crit.min_score}/{crit.max_score}",
                        "achieved": round(achieved, 1),
                    })
            else:
                total_benchmark += crit.min_score
                skill_gaps.append({
                    "skill": crit.skill,
                    "required": f"{crit.min_score}/{crit.max_score}",
                    "achieved": 0,
                })

        if total_benchmark > 0:
            criteria_pct = (total_achieved / total_benchmark) * 100.0
        else:
            n = len(role.skill_criteria)
            criteria_pct = (len(matched) / n * 100.0) if n > 0 else 70.0

        confidence = criteria_pct * 0.65 + student.overall_score * 0.25 + 10.0
        confidence = round(min(max(confidence, 10.0), 99.0), 1)
        fit_tier = classify_fit(criteria_pct)

        if confidence >= 25.0:
            candidates.append({
                "student_id": student.id,
                "name": student.name,
                "roll_number": student.roll_number,
                "batch": student.batch.name if student.batch else None,
                "course": student.course.name if student.course else None,
                "overall_score": student.overall_score,
                "confidence": confidence,
                "criteria_pct": round(min(criteria_pct, 100.0), 1),
                "fit_tier": fit_tier,
                "matched_skills": matched,
                "skill_gaps": skill_gaps,
            })

    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    return candidates


def _get_default_kauvery_roles() -> list[JobRole]:
    """Default Kauvery Hospital CCDP Placement Roles."""
    return [
        JobRole(
            id=1,
            name="Patient Care Coordinator",
            skill_criteria=[
                SkillCriteria("Communication Skills", 18.0, 25.0),
                SkillCriteria("Soft Skills", 16.0, 25.0),
                SkillCriteria("MS Office & IT", 14.0, 25.0),
            ],
            demand_level="High",
            openings=6,
            is_active=True,
            company_name="Kauvery Hospital",
            kauvery_unit="Kauvery Hospital - Trichy (Tennur)",
            department="Patient Care & Customer Relations",
        ),
        JobRole(
            id=2,
            name="Front Office & Helpdesk Executive",
            skill_criteria=[
                SkillCriteria("Communication Skills", 18.0, 25.0),
                SkillCriteria("MS Office & IT", 15.0, 25.0),
                SkillCriteria("Soft Skills", 15.0, 25.0),
            ],
            demand_level="High",
            openings=5,
            is_active=True,
            company_name="Kauvery Hospital",
            kauvery_unit="Kauvery Hospital - Chennai (Alwarpet)",
            department="Front Office, Admissions & Helpdesk",
        ),
        JobRole(
            id=3,
            name="Billing & Health Insurance Executive",
            skill_criteria=[
                SkillCriteria("MS Office & IT", 18.0, 25.0),
                SkillCriteria("Analytical Skills", 16.0, 25.0),
                SkillCriteria("Communication Skills", 14.0, 25.0),
            ],
            demand_level="High",
            openings=4,
            is_active=True,
            company_name="Kauvery Hospital",
            kauvery_unit="Kauvery Hospital - Chennai (Vadapalani)",
            department="Billing, Cashless & Health Insurance",
        ),
        JobRole(
            id=4,
            name="Hospital Operations Trainee",
            skill_criteria=[
                SkillCriteria("Leadership Skills", 16.0, 25.0),
                SkillCriteria("Problem Solving", 15.0, 25.0),
                SkillCriteria("Communication Skills", 15.0, 25.0),
            ],
            demand_level="Medium",
            openings=8,
            is_active=True,
            company_name="Kauvery Hospital",
            kauvery_unit="Kauvery Hospital - Salem",
            department="Hospital Administration & Operations",
        ),
        JobRole(
            id=5,
            name="Healthcare IT & Systems Assistant",
            skill_criteria=[
                SkillCriteria("MS Office & IT", 20.0, 25.0),
                SkillCriteria("Analytical Skills", 16.0, 25.0),
                SkillCriteria("Problem Solving", 15.0, 25.0),
            ],
            demand_level="Medium",
            openings=3,
            is_active=True,
            company_name="Kauvery Hospital",
            kauvery_unit="Kauvery Hospital - Bengaluru (Electronic City)",
            department="IT, Systems & Healthcare Informatics",
        ),
    ]


def auto_detect_roles_from_skills(detected_skills: list[str]) -> list[dict]:
    """Generates suggested Kauvery Hospital & corporate job role templates."""
    return [
        {
            "name": "Patient Care Coordinator",
            "kauvery_unit": "Kauvery Hospital - Trichy (Tennur)",
            "department": "Patient Care & Customer Relations",
            "required_skills": [
                {"skill": "Communication Skills", "min_score": 18, "max_score": 25},
                {"skill": "Soft Skills", "min_score": 16, "max_score": 25},
                {"skill": "MS Office & IT", "min_score": 14, "max_score": 25},
            ],
            "demand_level": "High",
            "openings": 6,
            "is_active": True,
            "company_name": "Kauvery Hospital",
        },
        {
            "name": "Front Office & Helpdesk Executive",
            "kauvery_unit": "Kauvery Hospital - Chennai (Alwarpet)",
            "department": "Front Office, Admissions & Helpdesk",
            "required_skills": [
                {"skill": "Communication Skills", "min_score": 18, "max_score": 25},
                {"skill": "MS Office & IT", "min_score": 15, "max_score": 25},
            ],
            "demand_level": "High",
            "openings": 5,
            "is_active": True,
            "company_name": "Kauvery Hospital",
        },
        {
            "name": "Billing & Health Insurance Executive",
            "kauvery_unit": "Kauvery Hospital - Chennai (Vadapalani)",
            "department": "Billing, Cashless & Health Insurance",
            "required_skills": [
                {"skill": "MS Office & IT", "min_score": 18, "max_score": 25},
                {"skill": "Analytical Skills", "min_score": 16, "max_score": 25},
            ],
            "demand_level": "High",
            "openings": 4,
            "is_active": True,
            "company_name": "Kauvery Hospital",
        },
        {
            "name": "Hospital Operations Trainee",
            "kauvery_unit": "Kauvery Hospital - Salem",
            "department": "Hospital Administration & Operations",
            "required_skills": [
                {"skill": "Leadership Skills", "min_score": 16, "max_score": 25},
                {"skill": "Problem Solving", "min_score": 15, "max_score": 25},
            ],
            "demand_level": "Medium",
            "openings": 8,
            "is_active": True,
            "company_name": "Kauvery Hospital",
        },
    ]
