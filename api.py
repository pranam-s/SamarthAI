import base64
import io
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Annotated
from collections import Counter
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import create_access_token, verify_password, get_password_hash, ALGORITHM
from db.database import get_db
from models import User
from schemas import (
    Token, TokenPayload, UserCreate, User as UserSchema, Resume, ResumeUpload,
    Job, JobCreate, JobUpdate, Application, ApplicationCreate, ApplicationWithDetails,
    MatchRequest, MatchResponse
)
from services import resume_service, job_service, matching_service, user_service, ai_service

router = APIRouter(prefix=settings.API_V1_STR)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)], token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    user = await user_service.get_user_by_id(db, token_data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


@router.post("/auth/login", response_model=Token)
async def login_access_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Any:
    user = await user_service.get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/auth/register", response_model=UserSchema)
async def register_user(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    user = await user_service.get_user_by_email(db, user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    user_data = user_in.dict()
    hashed_password = get_password_hash(user_in.password)
    user = await user_service.create_user(db, user_data, hashed_password)
    return user


@router.post("/resumes", response_model=Resume)
async def create_resume(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: Annotated[UploadFile, Form()]=None,
    resume_data: Annotated[Optional[str], Form()]=None
) -> Any:
    if file is None and resume_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either file or resume_data must be provided",
        )

    if file:
        result = await resume_service.process_resume_file(file)
    else:
        result = await resume_service.process_resume_text(resume_data)

    resume = await resume_service.create_resume(db, current_user.id, result)
    return resume


@router.post("/resumes/upload-base64", response_model=Resume)
async def create_resume_base64(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    resume_upload: ResumeUpload
) -> Any:
    if not resume_upload.file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content must be provided",
        )

    try:
        file_content = base64.b64decode(resume_upload.file_content)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 encoding",
        )
    
    file = UploadFile(
        filename=resume_upload.file_name,
        file=io.BytesIO(file_content)
    )
    
    result = await resume_service.process_resume_file(file)
    resume = await resume_service.create_resume(db, current_user.id, result)
    return resume


@router.get("/resumes", response_model=List[Resume])
async def read_resumes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100
) -> Any:
    resumes = await resume_service.get_resumes(db, current_user.id, current_user.is_recruiter, skip, limit)
    return resumes


@router.get("/resumes/{id}", response_model=Resume)
async def read_resume(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    resume = await resume_service.get_resume(db, id)
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    
    if not current_user.is_recruiter and resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return resume


@router.delete("/resumes/{id}")
async def delete_resume(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    resume = await resume_service.get_resume(db, id)
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    
    if not current_user.is_recruiter and resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    await resume_service.delete_resume(db, id)
    return None


@router.post("/jobs", response_model=Job)
async def create_job(
    job_in: JobCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    if not current_user.is_recruiter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    result = await job_service.process_job_description(job_in.description_text)
    job = await job_service.create_job(db, current_user.id, result, job_in.dict())
    return job


@router.get("/jobs", response_model=List[Job])
async def read_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100
) -> Any:
    jobs = await job_service.get_jobs(db, current_user.id, current_user.is_recruiter, skip, limit)
    return jobs


@router.get("/jobs/{id}", response_model=Job)
async def read_job(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    job = await job_service.get_job(db, id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    return job


@router.put("/jobs/{id}", response_model=Job)
async def update_job(
    id: int,
    job_in: JobUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    job = await job_service.get_job(db, id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    if job.company_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    job_data = job_in.dict(exclude_unset=True)
    
    if "description_text" in job_data and job_data["description_text"] != job.description_text:
        result = await job_service.process_job_description(job_data["description_text"])
        
        job_data["description_text"] = result["description_text"]
        job_data["required_skills"] = result["parsed_data"].get("required_skills", job.required_skills)
        job_data["preferred_skills"] = result["parsed_data"].get("preferred_skills", job.preferred_skills)
        job_data["responsibilities"] = result["parsed_data"].get("responsibilities", job.responsibilities)
        job_data["qualifications"] = result["parsed_data"].get("qualifications", job.qualifications)
    
    updated_job = await job_service.update_job(db, id, job_data)
    return updated_job


@router.delete("/jobs/{id}")
async def delete_job(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    job = await job_service.get_job(db, id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    if job.company_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    await job_service.delete_job(db, id)
    return None


@router.post("/applications", response_model=Application)
async def create_application(
    application_in: ApplicationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    if current_user.is_recruiter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiters cannot apply to jobs",
        )
    
    job = await job_service.get_job(db, application_in.job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    resume = await resume_service.get_resume(db, application_in.resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found or doesn't belong to you",
        )
    
    score, match_details, feedback = await matching_service.match_resume_to_job(
        resume.parsed_sections,
        {
            "title": job.title,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "responsibilities": job.responsibilities,
            "qualifications": job.qualifications
        },
    )
    
    application = await matching_service.create_application(
        db, 
        application_in.dict(), 
        score, 
        match_details, 
        feedback
    )
    return application


@router.get("/applications", response_model=List[Application])
async def read_applications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
    job_id: Optional[int] = None,
    status: Optional[str] = None
) -> Any:
    applications = await matching_service.get_applications(
        db, 
        current_user.id, 
        current_user.is_recruiter,
        job_id,
        status,
        skip, 
        limit
    )
    return applications


@router.get("/applications/{id}", response_model=ApplicationWithDetails)
async def read_application(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    application_data = await matching_service.get_application(db, id)
    
    if not application_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    application, job, resume = application_data
    
    if (current_user.is_recruiter and job.company_id != current_user.id) or \
       (not current_user.is_recruiter and resume.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    application_with_details = ApplicationWithDetails.from_orm(application)
    application_with_details.job = Job.from_orm(job)
    application_with_details.resume = Resume.from_orm(resume)
    
    return application_with_details


@router.patch("/applications/{id}/status", response_model=Application)
async def update_application_status(
    id: int,
    status: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    if not current_user.is_recruiter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    valid_statuses = ["New", "Reviewed", "Shortlisted", "Rejected"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )
    
    application_data = await matching_service.get_application(db, id)
    
    if not application_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    application, job, _ = application_data
    
    if job.company_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    updated_application = await matching_service.update_application_status(db, id, status)
    return updated_application


@router.post("/match", response_model=MatchResponse)
async def match_resume_to_job(
    match_request: MatchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    job = await job_service.get_job(db, match_request.job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    resume = await resume_service.get_resume(db, match_request.resume_id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    
    if not current_user.is_recruiter and resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this resume",
        )
    
    score, match_details, feedback = await matching_service.match_resume_to_job(
        resume.parsed_sections,
        {
            "title": job.title,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "responsibilities": job.responsibilities,
            "qualifications": job.qualifications
        },
    )
    
    return {
        "resume_id": match_request.resume_id,
        "job_id": match_request.job_id,
        "match_score": score,
        "match_details": match_details,
        "feedback": feedback
    }

@router.get("/recommendations/{resume_id}", response_model=List[Job])
async def get_job_recommendations(
    resume_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 5
) -> Any:
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    if resume.user_id != current_user.id and not current_user.is_recruiter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    jobs = await job_service.get_jobs(db, current_user.id, current_user.is_recruiter, limit=100)
    job_scores = []
    for job in jobs:
        score, _ = await ai_service.calculate_match_score(
            resume.parsed_sections,
            {
                "title": job.title,
                "required_skills": job.required_skills,
                "preferred_skills": job.preferred_skills,
                "responsibilities": job.responsibilities,
                "qualifications": job.qualifications
            },
    )
        job_scores.append((job, score))
    job_scores.sort(key=lambda x: x[1], reverse=True)
    top_jobs = [job for job, _ in job_scores[:limit]]
    return top_jobs

@router.get("/resumes/{id}/improve", response_model=Dict[str, Any])
async def get_resume_improvement(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    resume = await resume_service.get_resume(db, id)
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    
    if resume.user_id != current_user.id and not current_user.is_recruiter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    prompt = f"""
    Analyze this resume and provide specific improvements. Structure your response as a JSON object with the following fields:
    
    1. "format": Array of suggestions for better formatting and structure
    2. "bullet_points": Array of suggestions for creating more impactful bullet points
    3. "keywords": Array of industry-specific keywords to add
    4. "skills": Array of skills that should be highlighted more prominently
    
    Resume:
    {resume.full_text}
    """
    
    improvement_suggestions = await ai_service.call_gemini(prompt)
    return improvement_suggestions

@router.get("/market-analysis", response_model=Dict[str, Any])
async def get_job_market_analysis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    if not current_user.is_recruiter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters can access market analysis",
        )
    
    jobs = await job_service.get_jobs(db, current_user.id, current_user.is_recruiter, limit=1000)
    
    all_required_skills = []
    all_preferred_skills = []
    
    for job in jobs:
        for skill in job.required_skills or []:
            all_required_skills.append(skill.get("name", "").lower())
        for skill in job.preferred_skills or []:
            all_preferred_skills.append(skill.get("name", "").lower())
    
    required_skill_counts = Counter(all_required_skills)
    preferred_skill_counts = Counter(all_preferred_skills)
    
    top_required = required_skill_counts.most_common(10)
    top_preferred = preferred_skill_counts.most_common(10)
    
    return {
        "total_jobs_analyzed": len(jobs),
        "top_required_skills": [{"name": name, "count": count} for name, count in top_required],
        "top_preferred_skills": [{"name": name, "count": count} for name, count in top_preferred],
        "analysis_date": datetime.utcnow().isoformat()
    }

@router.get("/resumes/{id}/quality-score", response_model=Dict[str, Any])
async def get_resume_quality_score(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    resume = await resume_service.get_resume(db, id)
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    
    if resume.user_id != current_user.id and not current_user.is_recruiter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    quality_score = {
        "overall_score": 0,
        "sections": {},
        "suggestions": []
    }
    
    has_quantifiable = False
    experience_score = 0
    if resume.experience:
        for exp in resume.experience:
            achievements = exp.get("achievements", [])
            for achievement in achievements:
                if re.search(r'\d+%|\d+x|\$\d+|\d+ percent|increased|decreased|improved|reduced|saved|generated', achievement, re.IGNORECASE):
                    has_quantifiable = True
                    experience_score += 10
    
    quality_score["sections"]["experience"] = min(100, experience_score)
    
    skills_score = 0
    if resume.skills:
        skills_score += min(50, len(resume.skills) * 5)
        
        has_proficiency = any(skill.get("proficiency") for skill in resume.skills)
        if has_proficiency:
            skills_score += 25
        
        has_context = any(skill.get("context") for skill in resume.skills)
        if has_context:
            skills_score += 25
    
    quality_score["sections"]["skills"] = min(100, skills_score)
    
    education_score = 0
    if resume.education:
        education_score += min(50, len(resume.education) * 25)
        
        for edu in resume.education:
            if edu.get("gpa"):
                education_score += 25
                break
        
        for edu in resume.education:
            if edu.get("field_of_study"):
                education_score += 25
                break
    
    quality_score["sections"]["education"] = min(100, education_score)
    
    section_scores = [
        quality_score["sections"].get("experience", 0) * 0.5,
        quality_score["sections"].get("skills", 0) * 0.3,
        quality_score["sections"].get("education", 0) * 0.2
    ]
    quality_score["overall_score"] = sum(section_scores)
    
    if not has_quantifiable:
        quality_score["suggestions"].append("Add quantifiable achievements to your experience (e.g., percentages, amounts)")
    
    if "skills" in quality_score["sections"] and quality_score["sections"]["skills"] < 60:
        quality_score["suggestions"].append("Add more skills with proficiency levels and context")
    
    if "education" in quality_score["sections"] and quality_score["sections"]["education"] < 60:
        quality_score["suggestions"].append("Provide more details in your education section, such as GPA and field of study")
    
    return quality_score
