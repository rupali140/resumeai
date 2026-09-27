import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    resumes = relationship("Resume", back_populates="owner", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="resumes")
    analyses = relationship("Analysis", back_populates="resume", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_title = Column(String, nullable=True)
    job_description = Column(Text, nullable=False)

    ats_score = Column(Integer, nullable=False)
    keyword_match = Column(Integer, nullable=False)
    skills_match = Column(Integer, nullable=False)
    experience_relevance = Column(Integer, nullable=False)
    education_match = Column(Integer, nullable=False)
    formatting_score = Column(Integer, nullable=False)

    matched_skills_json = Column(Text, nullable=False)   # JSON string list
    missing_skills_json = Column(Text, nullable=False)   # JSON string list of {name,priority,category}
    matched_keywords_json = Column(Text, nullable=False)
    missing_keywords_json = Column(Text, nullable=False)
    suggestions_json = Column(Text, nullable=False)       # JSON string list of {category,text}

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    resume = relationship("Resume", back_populates="analyses")
