from pydantic import BaseModel, EmailStr
from typing import List, Optional
import datetime


# ---- Auth ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    name: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- Resumes ----
class ResumeOut(BaseModel):
    id: int
    filename: str
    file_type: str
    uploaded_at: datetime.datetime

    class Config:
        from_attributes = True


class ResumeDetail(ResumeOut):
    parsed_data: Optional[dict] = None


class ResumeParsedUpdate(BaseModel):
    parsed_data: dict


# ---- Bullet optimizer ----
class BulletOptimizeRequest(BaseModel):
    bullet: str


class BulletOptimizeResponse(BaseModel):
    original: str
    improved: str
    explanation: str


# ---- Analytics ----
class ScorePoint(BaseModel):
    date: datetime.datetime
    ats_score: int
    job_title: Optional[str] = None


class SkillFrequency(BaseModel):
    name: str
    count: int


class AnalyticsOut(BaseModel):
    resumes_analyzed: int
    average_score: Optional[float] = None
    score_trend: List[ScorePoint]
    most_common_missing_skills: List[SkillFrequency]


# ---- Analysis ----
class AnalyzeRequest(BaseModel):
    resume_id: int
    job_title: Optional[str] = None
    job_description: str


class SkillItem(BaseModel):
    name: str
    category: Optional[str] = "General"
    priority: Optional[str] = "Medium"  # High / Medium / Low


class SuggestionItem(BaseModel):
    category: str  # Critical / Important / Recommended
    text: str


class AnalysisOut(BaseModel):
    id: int
    resume_id: int
    job_title: Optional[str]
    ats_score: int
    keyword_match: int
    skills_match: int
    experience_relevance: int
    education_match: int
    formatting_score: int
    matched_skills: List[str]
    missing_skills: List[SkillItem]
    matched_keywords: List[str]
    missing_keywords: List[str]
    suggestions: List[SuggestionItem]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class AnalysisSummary(BaseModel):
    id: int
    job_title: Optional[str]
    ats_score: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True
