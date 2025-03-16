from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import base64


class TokenPayload(BaseModel):
    sub: Optional[int] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_recruiter: bool = False


class UserCreate(UserBase):
    password: str


class UserUpdate(UserBase):
    password: Optional[str] = None


class UserInDB(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    hashed_password: str

    class Config:
        from_attributes = True


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SkillBase(BaseModel):
    name: str
    proficiency: Optional[str] = None
    context: Optional[str] = None


class ExperienceBase(BaseModel):
    role: str
    company: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    achievements: Optional[List[str]] = []


class EducationBase(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None
    extras: Optional[str] = None


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: Optional[List[str]] = []
    url: Optional[str] = None


class CertificationBase(BaseModel):
    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None
    expires: Optional[str] = None


class AchievementBase(BaseModel):
    description: Optional[str] = None


class ResumeBase(BaseModel):
    user_id: Optional[int] = None
    full_text: Optional[str] = None
    parsed_sections: Optional[Dict[str, Any]] = {}
    skills: Optional[List[Dict[str, Any]]] = []
    experience: Optional[List[Dict[str, Any]]] = []
    education: Optional[List[Dict[str, Any]]] = []
    projects: Optional[List[Dict[str, Any]]] = []
    certifications: Optional[List[Dict[str, Any]]] = []
    achievements: Optional[List[Dict[str, Any]]] = []
    file_type: Optional[str] = None


class ResumeCreate(ResumeBase):
    pass


class ResumeUpdate(ResumeBase):
    pass


class Resume(ResumeBase):
    id: int
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResumeUpload(BaseModel):
    file_content: Optional[str] = None
    file_type: str
    file_name: str


class SkillRequirement(BaseModel):
    name: str
    importance: Optional[float] = 1.0


class JobBase(BaseModel):
    company_id: Optional[int] = None
    title: str
    description_text: str
    required_skills: Optional[List[Dict[str, Any]]] = []
    preferred_skills: Optional[List[Dict[str, Any]]] = []
    responsibilities: Optional[List[str]] = []
    qualifications: Optional[List[str]] = []
    priority_weights: Optional[Dict[str, float]] = {"skills": 0.6, "experience": 0.3, "education": 0.1}


class JobCreate(JobBase):
    pass


class JobUpdate(JobBase):
    pass


class Job(JobBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApplicationBase(BaseModel):
    job_id: int
    resume_id: int
    full_name: str
    email: str
    phone: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    match_score: Optional[float] = None
    match_details: Optional[Dict[str, Any]] = None
    feedback: Optional[Dict[str, Any]] = None


class Application(ApplicationBase):
    id: int
    match_score: float
    match_details: Dict[str, Any]
    feedback: Dict[str, Any]
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApplicationWithDetails(Application):
    job: Optional[Job] = None
    resume: Optional[Resume] = None


class MatchRequest(BaseModel):
    resume_id: int
    job_id: int


class MatchResponse(BaseModel):
    resume_id: int
    job_id: int
    match_score: float
    match_details: Dict[str, Any]
    feedback: Dict[str, Any]


class SkillMatchSection(BaseModel):
    matched: List[str] = []
    missing: List[str] = []
    match_rate: float = 0.0


class SkillMatch(BaseModel):
    score: float = 0.0
    required: SkillMatchSection = SkillMatchSection()
    preferred: SkillMatchSection = SkillMatchSection()


class ExperienceEntryMatch(BaseModel):
    role: str
    company: str
    match_percentage: float = 0.0
    matching_terms: List[str] = []


class ExperienceMatch(BaseModel):
    score: float = 0.0
    matching_aspects: List[str] = []
    missing_aspects: List[str] = []
    experience_entries: List[Dict[str, Any]] = []


class EducationMatch(BaseModel):
    score: float = 0.0
    matching_aspects: List[str] = []
    missing_aspects: List[str] = []
    highest_education: Optional[str] = None


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