import base64
import io
import logging
from datetime import timedelta
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import ALGORITHM, create_access_token, get_password_hash, verify_password
from db.database import get_db
from models import User
from schemas import (
    Application,
    ApplicationCreate,
    ApplicationWithDetails,
    Job,
    JobCreate,
    JobUpdate,
    MatchRequest,
    MatchResponse,
    Resume,
    ResumeUpload,
    SkillsGapRequest,
    SkillsGapResponse,
    Token,
    TokenPayload,
    UserCreate,
)
from schemas import User as UserSchema
from services import job_service, matching_service, resume_service, user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_V1_STR)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    raw_cookie_token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    selected_token = token or raw_cookie_token

    if not selected_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    if selected_token.startswith("Bearer "):
        selected_token = selected_token.replace("Bearer ", "", 1)

    try:
        payload = jwt.decode(selected_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)
    except (jwt.InvalidTokenError, ValidationError) as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        ) from err

    if token_data.sub is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    try:
        user_id = int(token_data.sub)
    except (ValueError, TypeError) as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        ) from err

    user = await user_service.get_user_by_id(db, user_id)
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
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
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
        "access_token": create_access_token(user.id, expires_delta=access_token_expires),
        "token_type": "bearer",
    }


@router.post("/auth/register", response_model=UserSchema)
async def register_user(user_in: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]) -> Any:
    user = await user_service.get_user_by_email(db, user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    user_data = user_in.model_dump()
    hashed_password = get_password_hash(user_in.password)
    user = await user_service.create_user(db, user_data, hashed_password)
    return user


@router.get("/auth/me", response_model=UserSchema)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    """Return the profile of the currently authenticated user."""
    return current_user


@router.post("/resumes", response_model=Resume)
async def create_resume(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile | None = File(None),
    resume_data: Annotated[str | None, Form()] = None,
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
    resume_upload: ResumeUpload,
) -> Any:
    if not resume_upload.file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content must be provided",
        )

    try:
        file_content = base64.b64decode(resume_upload.file_content)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 encoding",
        ) from err

    file = UploadFile(filename=resume_upload.file_name, file=io.BytesIO(file_content))
    result = await resume_service.process_resume_file(file)
    resume = await resume_service.create_resume(db, current_user.id, result)
    return resume


@router.get("/resumes", response_model=list[Resume])
async def read_resumes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    return await resume_service.get_resumes(
        db, current_user.id, current_user.is_recruiter, skip, limit
    )


@router.get("/resumes/{id}", response_model=Resume)
async def read_resume(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    resume = await resume_service.get_resume(db, id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if not current_user.is_recruiter and resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return resume


@router.delete("/resumes/{id}")
async def delete_resume(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    resume = await resume_service.get_resume(db, id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if not current_user.is_recruiter and resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    await resume_service.delete_resume(db, id)
    return None


@router.post("/jobs", response_model=Job)
async def create_job(
    job_in: JobCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    if not current_user.is_recruiter:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    result = await job_service.process_job_description(job_in.description_text)
    job = await job_service.create_job(db, current_user.id, result, job_in.model_dump())
    return job


@router.get("/jobs", response_model=list[Job])
async def read_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    return await job_service.get_jobs(db, current_user.id, current_user.is_recruiter, skip, limit)


@router.get("/jobs/{id}", response_model=Job)
async def read_job(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    job = await job_service.get_job(db, id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.company_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    job_data = job_in.model_dump(exclude_unset=True)
    if "description_text" in job_data and job_data["description_text"] != job.description_text:
        result = await job_service.process_job_description(job_data["description_text"])
        job_data["description_text"] = result["description_text"]
        job_data["required_skills"] = result["parsed_data"].get(
            "required_skills", job.required_skills
        )
        job_data["preferred_skills"] = result["parsed_data"].get(
            "preferred_skills", job.preferred_skills
        )
        job_data["responsibilities"] = result["parsed_data"].get(
            "responsibilities", job.responsibilities
        )
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.company_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

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
            "qualifications": job.qualifications,
        },
    )

    application = await matching_service.create_application(
        db, application_in.model_dump(), score, match_details, feedback
    )
    return application


@router.get("/applications", response_model=list[Application])
async def read_applications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
    job_id: int | None = None,
    status_filter: str | None = None,
) -> Any:
    return await matching_service.get_applications(
        db, current_user.id, current_user.is_recruiter, job_id, status_filter, skip, limit
    )


@router.get("/applications/{id}", response_model=ApplicationWithDetails)
async def read_application(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    application_data = await matching_service.get_application(db, id)
    if not application_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    application, job, resume = application_data

    if (current_user.is_recruiter and job.company_id != current_user.id) or (
        not current_user.is_recruiter and resume.user_id != current_user.id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    result = ApplicationWithDetails.model_validate(application)
    result.job = Job.model_validate(job)
    result.resume = Resume.model_validate(resume)
    return result


@router.patch("/applications/{id}/status", response_model=Application)
async def update_application_status(
    id: int,
    status_value: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    if not current_user.is_recruiter:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    valid_statuses = ["New", "Reviewed", "Shortlisted", "Rejected"]
    if status_value not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    application_data = await matching_service.get_application(db, id)
    if not application_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    application, job, _ = application_data
    if job.company_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    updated = await matching_service.update_application_status(db, id, status_value)
    return updated


@router.post("/match", response_model=MatchResponse)
async def match_resume_to_job(
    match_request: MatchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    job = await job_service.get_job(db, match_request.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    resume = await resume_service.get_resume(db, match_request.resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

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
            "qualifications": job.qualifications,
        },
    )

    return {
        "resume_id": match_request.resume_id,
        "job_id": match_request.job_id,
        "match_score": score,
        "match_details": match_details,
        "feedback": feedback,
    }


@router.get("/recommendations/{resume_id}", response_model=list[Job])
async def get_job_recommendations(
    resume_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 5,
) -> Any:
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if resume.user_id != current_user.id and not current_user.is_recruiter:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return await job_service.get_recommendations(resume_id, db, current_user, limit)


@router.get("/resumes/{id}/improve", response_model=dict[str, Any])
async def get_resume_improvement(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    resume = await resume_service.get_resume(db, id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if resume.user_id != current_user.id and not current_user.is_recruiter:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return await job_service.get_resume_improvement(id, db, current_user)


@router.get("/market-analysis", response_model=dict[str, Any])
async def get_job_market_analysis(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    if not current_user.is_recruiter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters can access market analysis",
        )
    return await job_service.get_market_analysis(db, current_user)


@router.get("/resumes/{id}/quality-score", response_model=dict[str, Any])
async def get_resume_quality_score(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    resume = await resume_service.get_resume(db, id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if resume.user_id != current_user.id and not current_user.is_recruiter:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return await job_service.get_resume_quality_score(id, db, current_user)


@router.post("/skills-gap", response_model=SkillsGapResponse)
async def analyze_skills_gap(
    request: SkillsGapRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    resume = await resume_service.get_resume(db, request.resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if resume.user_id != current_user.id and not current_user.is_recruiter:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    job = await job_service.get_job(db, request.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    result = await job_service.analyze_skills_gap(
        request.resume_id, request.job_id, db, current_user
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Skills gap analysis failed",
        )
    return result
