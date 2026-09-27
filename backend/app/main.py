from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .config import settings
from .routers import auth, resumes, analyze, optimize, analytics

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ResumeAI API",
    description="AI-powered resume analysis, ATS scoring, and skills-gap engine.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(analyze.router)
app.include_router(optimize.router)
app.include_router(analytics.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
