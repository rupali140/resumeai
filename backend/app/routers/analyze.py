import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..services.ai_engine import analyze_resume

router = APIRouter(prefix="/api", tags=["analysis"])


def _row_to_out(row: models.Analysis) -> schemas.AnalysisOut:
    return schemas.AnalysisOut(
        id=row.id,
        resume_id=row.resume_id,
        job_title=row.job_title,
        ats_score=row.ats_score,
        keyword_match=row.keyword_match,
        skills_match=row.skills_match,
        experience_relevance=row.experience_relevance,
        education_match=row.education_match,
        formatting_score=row.formatting_score,
        matched_skills=json.loads(row.matched_skills_json),
        missing_skills=json.loads(row.missing_skills_json),
        matched_keywords=json.loads(row.matched_keywords_json),
        missing_keywords=json.loads(row.missing_keywords_json),
        suggestions=json.loads(row.suggestions_json),
        created_at=row.created_at,
    )


@router.post("/analyze", response_model=schemas.AnalysisOut)
def analyze(
    payload: schemas.AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.id == payload.resume_id, models.Resume.owner_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    if not payload.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    result = analyze_resume(resume.raw_text, payload.job_description, payload.job_title)

    analysis = models.Analysis(
        resume_id=resume.id,
        job_title=payload.job_title,
        job_description=payload.job_description,
        ats_score=result["ats_score"],
        keyword_match=result["keyword_match"],
        skills_match=result["skills_match"],
        experience_relevance=result["experience_relevance"],
        education_match=result["education_match"],
        formatting_score=result["formatting_score"],
        matched_skills_json=json.dumps(result["matched_skills"]),
        missing_skills_json=json.dumps(result["missing_skills"]),
        matched_keywords_json=json.dumps(result["matched_keywords"]),
        missing_keywords_json=json.dumps(result["missing_keywords"]),
        suggestions_json=json.dumps(result["suggestions"]),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return _row_to_out(analysis)


@router.get("/analysis/{analysis_id}", response_model=schemas.AnalysisOut)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    row = (
        db.query(models.Analysis)
        .join(models.Resume)
        .filter(models.Analysis.id == analysis_id, models.Resume.owner_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return _row_to_out(row)


@router.get("/history", response_model=list[schemas.AnalysisSummary])
def history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    rows = (
        db.query(models.Analysis)
        .join(models.Resume)
        .filter(models.Resume.owner_id == current_user.id)
        .order_by(models.Analysis.created_at.desc())
        .all()
    )
    return rows


@router.delete("/analysis/{analysis_id}", status_code=204)
def delete_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    row = (
        db.query(models.Analysis)
        .join(models.Resume)
        .filter(models.Analysis.id == analysis_id, models.Resume.owner_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    db.delete(row)
    db.commit()
    return None
