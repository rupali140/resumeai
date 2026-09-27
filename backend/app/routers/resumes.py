import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..config import settings
from ..database import get_db
from ..services.parser import extract_text
from ..services.ai_engine import extract_resume_fields

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.post("/upload", response_model=schemas.ResumeDetail)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    filename = file.filename or "resume"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File exceeds the {settings.MAX_FILE_SIZE_MB}MB limit.")

    raw_text = extract_text(filename, file_bytes)

    # Best-effort structured extraction — don't fail the whole upload if this part errors
    # (e.g. AI key not configured yet); the raw text is still saved either way.
    parsed_data = None
    try:
        parsed_data = extract_resume_fields(raw_text)
    except Exception:
        parsed_data = None

    resume = models.Resume(
        owner_id=current_user.id,
        filename=filename,
        file_type=ext.lstrip("."),
        raw_text=raw_text,
        parsed_data_json=json.dumps(parsed_data) if parsed_data is not None else None,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return schemas.ResumeDetail(
        id=resume.id,
        filename=resume.filename,
        file_type=resume.file_type,
        uploaded_at=resume.uploaded_at,
        parsed_data=parsed_data,
    )


@router.get("", response_model=list[schemas.ResumeOut])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    return (
        db.query(models.Resume)
        .filter(models.Resume.owner_id == current_user.id)
        .order_by(models.Resume.uploaded_at.desc())
        .all()
    )


@router.get("/{resume_id}", response_model=schemas.ResumeDetail)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.id == resume_id, models.Resume.owner_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return schemas.ResumeDetail(
        id=resume.id,
        filename=resume.filename,
        file_type=resume.file_type,
        uploaded_at=resume.uploaded_at,
        parsed_data=json.loads(resume.parsed_data_json) if resume.parsed_data_json else None,
    )


@router.put("/{resume_id}/parsed", response_model=schemas.ResumeDetail)
def update_parsed_data(
    resume_id: int,
    payload: schemas.ResumeParsedUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Lets the user correct fields the AI extracted incorrectly."""
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.id == resume_id, models.Resume.owner_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    resume.parsed_data_json = json.dumps(payload.parsed_data)
    db.commit()
    db.refresh(resume)

    return schemas.ResumeDetail(
        id=resume.id,
        filename=resume.filename,
        file_type=resume.file_type,
        uploaded_at=resume.uploaded_at,
        parsed_data=payload.parsed_data,
    )


@router.delete("/{resume_id}", status_code=204)
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.id == resume_id, models.Resume.owner_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    db.delete(resume)
    db.commit()
    return None
