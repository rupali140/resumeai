import json
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics", response_model=schemas.AnalyticsOut)
def analytics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    rows = (
        db.query(models.Analysis)
        .join(models.Resume)
        .filter(models.Resume.owner_id == current_user.id)
        .order_by(models.Analysis.created_at.asc())
        .all()
    )

    resumes_analyzed = len(rows)
    average_score = round(sum(r.ats_score for r in rows) / resumes_analyzed, 1) if resumes_analyzed else None

    score_trend = [
        schemas.ScorePoint(date=r.created_at, ats_score=r.ats_score, job_title=r.job_title)
        for r in rows
    ]

    skill_counter = Counter()
    for r in rows:
        try:
            missing = json.loads(r.missing_skills_json)
        except (TypeError, json.JSONDecodeError):
            missing = []
        for skill in missing:
            name = skill.get("name") if isinstance(skill, dict) else skill
            if name:
                skill_counter[name] += 1

    most_common_missing_skills = [
        schemas.SkillFrequency(name=name, count=count)
        for name, count in skill_counter.most_common(8)
    ]

    return schemas.AnalyticsOut(
        resumes_analyzed=resumes_analyzed,
        average_score=average_score,
        score_trend=score_trend,
        most_common_missing_skills=most_common_missing_skills,
    )
