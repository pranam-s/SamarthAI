from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

# Password policy lives in the I/O contract layer. Do not move it into
# core.security: schemas must stay import-light because pytest-cov imports
# --cov targets before the test sys.path is configured, and pulling in
# bcrypt here aborts the interpreter (PyO3 double-init, audit A-25).
MIN_PASSWORD_LENGTH = 8


class TokenPayload(BaseModel):
    sub: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    is_recruiter: bool = False
    phone: str | None = None
    bio: str | None = None
    location: str | None = None
    profile_picture_url: str | None = None


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def password_meets_minimum_length(cls, value: str) -> str:
        """Enforce the shared password policy on every registration path."""
        if len(value) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        return value


class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    hashed_password: str


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None


class ResumeBase(BaseModel):
    user_id: int | None = None
    full_text: str | None = None
    parsed_sections: dict[str, Any] | None = {}
    skills: list[dict[str, Any]] | None = []
    experience: list[dict[str, Any]] | None = []
    education: list[dict[str, Any]] | None = []
    projects: list[dict[str, Any]] | None = []
    certifications: list[dict[str, Any]] | None = []
    achievements: list[dict[str, Any]] | None = []
    file_type: str | None = None


class Resume(ResumeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ResumeUpload(BaseModel):
    file_content: str | None = None
    file_type: str
    file_name: str


class SkillRequirement(BaseModel):
    name: str
    importance: float | None = 1.0


class JobBase(BaseModel):
    company_id: int | None = None
    title: str
    description_text: str | None = None
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    job_type: Literal["full-time", "part-time", "contract", "internship"] | None = None
    is_remote: bool = False
    experience_level: Literal["entry", "mid", "senior", "lead"] | None = None
    required_skills: list[dict[str, Any]] | None = []
    preferred_skills: list[dict[str, Any]] | None = []
    responsibilities: list[str] | None = []
    qualifications: list[str] | None = []
    priority_weights: dict[str, float] | None = {"skills": 0.6, "experience": 0.3, "education": 0.1}


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    company_id: int | None = None
    title: str | None = None
    description_text: str | None = None
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    job_type: Literal["full-time", "part-time", "contract", "internship"] | None = None
    is_remote: bool | None = None
    experience_level: Literal["entry", "mid", "senior", "lead"] | None = None
    required_skills: list[dict[str, Any]] | None = None
    preferred_skills: list[dict[str, Any]] | None = None
    responsibilities: list[str] | None = None
    qualifications: list[str] | None = None
    priority_weights: dict[str, float] | None = None


class Job(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime | None = None


class ApplicationBase(BaseModel):
    job_id: int
    resume_id: int
    full_name: str
    email: str
    phone: str | None = None
    cover_letter: str | None = None


class ApplicationCreate(ApplicationBase):
    pass


class Application(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_score: float = 0.0
    match_details: dict[str, Any] | None = None
    feedback: dict[str, Any] | None = None
    status: str
    created_at: datetime
    reviewed_at: datetime | None = None


class ApplicationWithDetails(Application):
    job: Job | None = None
    resume: Resume | None = None


class MatchRequest(BaseModel):
    resume_id: int
    job_id: int


class MatchResponse(BaseModel):
    resume_id: int
    job_id: int
    match_score: float
    match_details: dict[str, Any]
    feedback: dict[str, Any]


class SkillMatchSection(BaseModel):
    matched: list[str] = []
    missing: list[str] = []
    match_rate: float = 0.0


class SkillMatch(BaseModel):
    score: float = 0.0
    required: SkillMatchSection = SkillMatchSection()
    preferred: SkillMatchSection = SkillMatchSection()


class ExperienceEntryMatch(BaseModel):
    role: str
    company: str
    match_percentage: float = 0.0
    matching_terms: list[str] = []


class ExperienceMatch(BaseModel):
    score: float = 0.0
    matching_aspects: list[str] = []
    missing_aspects: list[str] = []
    experience_entries: list[dict[str, Any]] = []


class EducationMatch(BaseModel):
    score: float = 0.0
    matching_aspects: list[str] = []
    missing_aspects: list[str] = []
    highest_education: str | None = None


class MatchSections(BaseModel):
    skills: SkillMatch = SkillMatch()
    experience: ExperienceMatch = ExperienceMatch()
    education: EducationMatch = EducationMatch()


class MatchWeights(BaseModel):
    skills: float = 0.6
    experience: float = 0.3
    education: float = 0.1


class MatchDetails(BaseModel):
    overall_match: float = 0.0
    sections: MatchSections = MatchSections()
    weights_applied: MatchWeights = MatchWeights()


# ---------------------------------------------------------------------------
# Skills Gap Analysis (new feature)
# ---------------------------------------------------------------------------


class SkillsGapRequest(BaseModel):
    resume_id: int
    job_id: int


class SkillGapItem(BaseModel):
    skill: str
    status: str  # "matched", "missing_required", "missing_preferred"
    importance: float = 0.0
    learning_suggestion: str = ""


class SkillsGapResponse(BaseModel):
    resume_id: int
    job_id: int
    gap_score: float  # 0-100, higher = better coverage
    matched_skills: list[str] = []
    missing_required: list[SkillGapItem] = []
    missing_preferred: list[SkillGapItem] = []
    learning_path: list[str] = []
    summary: str = ""
