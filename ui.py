from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from api import get_current_user
from core.config import settings
from core.i18n import normalize_locale, translate
from core.security import (
    create_access_token,
    create_csrf_token,
    decode_access_token,
    verify_csrf_token,
    verify_password,
)
from db.database import get_db
from models import User
from schemas import TokenPayload
from services import job_service, matching_service, resume_service, user_service

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Helper for template context
async def get_user_context(request: Request, current_user: User | None = None):
    locale_cookie = request.cookies.get("locale")
    locale_header = request.headers.get("accept-language")
    locale = normalize_locale(locale_cookie or locale_header or settings.DEFAULT_LOCALE)

    csrf_token = create_csrf_token(current_user.id) if current_user else ""

    return {
        "request": request,
        "user": current_user,
        "app_name": settings.PROJECT_NAME,
        "now": datetime.now(),
        "locale": locale,
        "supported_locales": settings.SUPPORTED_LOCALES,
        "csrf_token": csrf_token,
        "t": lambda key: translate(locale, key),
    }


def validate_csrf_or_400(current_user: User, csrf_token: str):
    if not verify_csrf_token(csrf_token, current_user.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid CSRF token")

async def get_optional_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User | None:
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not token:
        return None

    if token.startswith("Bearer "):
        token = token.replace("Bearer ", "", 1)

    try:
        payload = decode_access_token(token)
        token_data = TokenPayload(**payload)
        user = await user_service.get_user_by_id(db, token_data.sub)
        if not user or not user.is_active:
            return None
        return user
    except Exception:
        return None

# Home page
@router.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: Annotated[User | None, Depends(get_optional_user)]):
    context = await get_user_context(request, current_user)
    context["active_page"] = "home"
    return templates.TemplateResponse("index.html", context)

# Auth routes
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    context = await get_user_context(request)
    context["active_page"] = "login"
    return templates.TemplateResponse("auth/login.html", context)

@router.post("/login")
async def login_submit(
    request: Request,
    db: AsyncSession = Depends(get_db), 
    email: str = Form(...), 
    password: str = Form(...)
):
    user = await user_service.get_user_by_email(db, email)
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        context = await get_user_context(request)
        context["error"] = "Invalid email or password"
        return templates.TemplateResponse("auth/login.html", context, status_code=400)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.id, expires_delta=access_token_expires)
    
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    context = await get_user_context(request)
    context["active_page"] = "register"
    return templates.TemplateResponse("auth/register.html", context)

@router.post("/register")
async def register_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    is_recruiter: bool = Form(False)
):
    user = await user_service.get_user_by_email(db, email)
    if user:
        context = await get_user_context(request)
        context["error"] = "Email already registered"
        return templates.TemplateResponse("auth/register.html", context, status_code=400)
    
    user_data = {
        "email": email,
        "full_name": full_name,
        "is_recruiter": is_recruiter
    }
    
    from core.security import get_password_hash
    hashed_password = get_password_hash(password)
    await user_service.create_user(db, user_data, hashed_password)
    
    return RedirectResponse(url="/login?registered=true", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME)
    return response


@router.post("/set-locale")
async def set_locale(locale: str = Form(...), redirect_to: str = Form("/")):
    selected = normalize_locale(locale)
    response = RedirectResponse(url=redirect_to or "/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="locale",
        value=selected,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * 365,
    )
    return response

# Dashboard routes
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    context = await get_user_context(request, current_user)
    context["active_page"] = "dashboard"
    
    if current_user.is_recruiter:
        # Recruiter dashboard
        jobs = await job_service.get_jobs(db, current_user.id, current_user.is_recruiter, limit=5)
        applications = await matching_service.get_applications(db, current_user.id, current_user.is_recruiter, limit=10)
        
        context["jobs"] = jobs
        context["applications"] = applications
        context["stats"] = {
            "jobs_count": len(jobs),
            "new_applications": sum(1 for app in applications if app.status == "New"),
            "shortlisted": sum(1 for app in applications if app.status == "Shortlisted")
        }
        
        return templates.TemplateResponse("dashboard/recruiter.html", context)
    else:
        # Job seeker dashboard
        resumes = await resume_service.get_resumes(db, current_user.id, current_user.is_recruiter, limit=5)
        applications = await matching_service.get_applications(db, current_user.id, current_user.is_recruiter, limit=10)
        jobs = await job_service.get_jobs(db, current_user.id, current_user.is_recruiter, limit=5)
        
        context["resumes"] = resumes
        context["applications"] = applications
        context["jobs"] = jobs
        context["stats"] = {
            "resumes_count": len(resumes),
            "applications_count": len(applications),
            "pending_applications": sum(1 for app in applications if app.status == "New")
        }
        
        if resumes:
            # Get job recommendations for the first resume
            recommendations = await job_service.get_jobs(db, current_user.id, current_user.is_recruiter, limit=3)
            context["recommendations"] = recommendations
        
        return templates.TemplateResponse("dashboard/jobseeker.html", context)

# Resume routes
@router.get("/resumes", response_class=HTMLResponse)
async def resumes(
    request: Request, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    context = await get_user_context(request, current_user)
    context["active_page"] = "resumes"
    resumes = await resume_service.get_resumes(db, current_user.id, current_user.is_recruiter)
    context["resumes"] = resumes
    return templates.TemplateResponse("resumes/index.html", context)

@router.get("/resumes/create", response_class=HTMLResponse)
async def create_resume_page(request: Request, current_user: User = Depends(get_current_user)):
    context = await get_user_context(request, current_user)
    context["active_page"] = "resumes"
    return templates.TemplateResponse("resumes/create.html", context)

@router.post("/resumes/create")
async def create_resume_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    resume_text: str | None = Form(None),
    resume_file: UploadFile | None = File(None),
    csrf_token: str = Form(...),
):
    validate_csrf_or_400(current_user, csrf_token)

    if not resume_file and not resume_text:
        context = await get_user_context(request, current_user)
        context["error"] = "Either file or text must be provided"
        return templates.TemplateResponse("resumes/create.html", context, status_code=400)
    
    try:
        if resume_file:
            result = await resume_service.process_resume_file(resume_file)
        else:
            result = await resume_service.process_resume_text(resume_text)
        
        resume = await resume_service.create_resume(db, current_user.id, result)
        return RedirectResponse(url=f"/resumes/{resume.id}", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        context = await get_user_context(request, current_user)
        context["error"] = f"Error processing resume: {str(e)}"
        return templates.TemplateResponse("resumes/create.html", context, status_code=400)

@router.get("/resumes/{id}", response_class=HTMLResponse)
async def resume_detail(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    resume = await resume_service.get_resume(db, id)
    if not resume:
        return RedirectResponse(url="/resumes", status_code=status.HTTP_303_SEE_OTHER)
    
    if not current_user.is_recruiter and resume.user_id != current_user.id:
        return RedirectResponse(url="/resumes", status_code=status.HTTP_303_SEE_OTHER)
    
    context = await get_user_context(request, current_user)
    context["active_page"] = "resumes"
    context["resume"] = resume
    
    # Get improvement suggestions
    improvement = await job_service.get_resume_improvement(id, db, current_user)
    context["improvement"] = improvement
    
    # Get quality score
    quality_score = await job_service.get_resume_quality_score(id, db, current_user)
    context["quality_score"] = quality_score
    
    # Get job recommendations if not recruiter
    if not current_user.is_recruiter:
        recommendations = await job_service.get_recommendations(resume.id, db, current_user)
        context["recommendations"] = recommendations
    
    return templates.TemplateResponse("resumes/detail.html", context)


@router.post("/resumes/{id}/delete")
async def delete_resume_submit(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    csrf_token: str = Form(...),
):
    validate_csrf_or_400(current_user, csrf_token)

    resume = await resume_service.get_resume(db, id)
    if not resume:
        return RedirectResponse(url="/resumes", status_code=status.HTTP_303_SEE_OTHER)

    if resume.user_id != current_user.id and not current_user.is_recruiter:
        return RedirectResponse(url="/resumes", status_code=status.HTTP_303_SEE_OTHER)

    await resume_service.delete_resume(db, id)
    return RedirectResponse(url="/resumes", status_code=status.HTTP_303_SEE_OTHER)

# Job routes
@router.get("/jobs", response_class=HTMLResponse)
async def jobs(
    request: Request, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    context = await get_user_context(request, current_user)
    context["active_page"] = "jobs"
    jobs = await job_service.get_jobs(db, current_user.id, current_user.is_recruiter)
    context["jobs"] = jobs
    return templates.TemplateResponse("jobs/index.html", context)

@router.get("/jobs/create", response_class=HTMLResponse)
async def create_job_page(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user.is_recruiter:
        return RedirectResponse(url="/jobs", status_code=status.HTTP_303_SEE_OTHER)
    
    context = await get_user_context(request, current_user)
    context["active_page"] = "jobs"
    return templates.TemplateResponse("jobs/create.html", context)

@router.post("/jobs/create")
async def create_job_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    title: str = Form(...),
    description_text: str = Form(...),
    csrf_token: str = Form(...),
):
    validate_csrf_or_400(current_user, csrf_token)

    if not current_user.is_recruiter:
        return RedirectResponse(url="/jobs", status_code=status.HTTP_303_SEE_OTHER)
    
    try:
        result = await job_service.process_job_description(description_text)
        job = await job_service.create_job(db, current_user.id, result, {"title": title, "description_text": description_text})
        return RedirectResponse(url=f"/jobs/{job.id}", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        context = await get_user_context(request, current_user)
        context["error"] = f"Error processing job: {str(e)}"
        context["title"] = title
        context["description_text"] = description_text
        return templates.TemplateResponse("jobs/create.html", context, status_code=400)

@router.get("/jobs/{id}", response_class=HTMLResponse)
async def job_detail(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = await job_service.get_job(db, id)
    if not job:
        return RedirectResponse(url="/jobs", status_code=status.HTTP_303_SEE_OTHER)
    
    context = await get_user_context(request, current_user)
    context["active_page"] = "jobs"
    context["job"] = job
    
    # Get applications if recruiter and this is their job
    if current_user.is_recruiter and job.company_id == current_user.id:
        applications = await matching_service.get_applications(db, current_user.id, True, job.id)
        context["applications"] = applications
    
    # Get resumes if job seeker for applying
    if not current_user.is_recruiter:
        resumes = await resume_service.get_resumes(db, current_user.id, False)
        context["resumes"] = resumes
        
        # Check if user already applied
        applications = await matching_service.get_applications(db, current_user.id, False, job.id)
        context["user_applications"] = applications
    
    return templates.TemplateResponse("jobs/detail.html", context)

# Application routes
@router.get("/applications", response_class=HTMLResponse)
async def applications(
    request: Request, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    context = await get_user_context(request, current_user)
    context["active_page"] = "applications"
    applications = await matching_service.get_applications(db, current_user.id, current_user.is_recruiter)
    
    # Get additional data for display
    for app in applications:
        job = await job_service.get_job(db, app.job_id)
        resume = await resume_service.get_resume(db, app.resume_id)
        app.job_title = job.title if job else "Unknown Job"
        app.resume_name = resume.parsed_sections.get("contact", {}).get("name", "Unnamed Resume") if resume else "Unknown Resume"
    
    context["applications"] = applications
    return templates.TemplateResponse("applications/index.html", context)

@router.post("/applications/create")
async def create_application(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    job_id: int = Form(...),
    resume_id: int = Form(...),
    csrf_token: str = Form(...),
):
    validate_csrf_or_400(current_user, csrf_token)

    if current_user.is_recruiter:
        return RedirectResponse(url="/jobs", status_code=status.HTTP_303_SEE_OTHER)
    
    # Check if job and resume exist
    job = await job_service.get_job(db, job_id)
    resume = await resume_service.get_resume(db, resume_id)
    
    if not job or not resume:
        return RedirectResponse(url="/jobs", status_code=status.HTTP_303_SEE_OTHER)
    
    if resume.user_id != current_user.id:
        return RedirectResponse(url="/jobs", status_code=status.HTTP_303_SEE_OTHER)
    
    # Check if already applied
    applications = await matching_service.get_applications(db, current_user.id, False, job_id)
    for app in applications:
        if app.resume_id == resume_id:
            return RedirectResponse(url=f"/jobs/{job_id}?already_applied=true", status_code=status.HTTP_303_SEE_OTHER)
    
    # Get user information from resume
    contact_info = resume.parsed_sections.get("contact", {})
    
    # Create application
    application_data = {
        "job_id": job_id,
        "resume_id": resume_id,
        "full_name": contact_info.get("name", current_user.full_name),
        "email": contact_info.get("email", current_user.email),
        "phone": contact_info.get("phone", "")
    }
    
    # Match resume to job
    score, match_details, feedback = await matching_service.match_resume_to_job(
        resume.parsed_sections,
        {
            "title": job.title,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "responsibilities": job.responsibilities,
            "qualifications": job.qualifications
        }
    )
    
    application = await matching_service.create_application(db, application_data, score, match_details, feedback)
    return RedirectResponse(url=f"/applications/{application.id}", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/applications/{id}", response_class=HTMLResponse)
async def application_detail(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    application_data = await matching_service.get_application(db, id)
    if not application_data:
        return RedirectResponse(url="/applications", status_code=status.HTTP_303_SEE_OTHER)
    
    application, job, resume = application_data
    
    # Check permissions
    if (current_user.is_recruiter and job.company_id != current_user.id) or \
       (not current_user.is_recruiter and resume.user_id != current_user.id):
        return RedirectResponse(url="/applications", status_code=status.HTTP_303_SEE_OTHER)
    
    context = await get_user_context(request, current_user)
    context["active_page"] = "applications"
    context["application"] = application
    context["job"] = job
    context["resume"] = resume
    context["match_score"] = application.match_score
    context["match_details"] = application.match_details
    context["feedback"] = application.feedback
    
    return templates.TemplateResponse("applications/detail.html", context)

@router.post("/applications/{id}/update-status")
async def update_application_status(
    id: int,
    status_value: str = Form(..., alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    csrf_token: str = Form(...),
):
    validate_csrf_or_400(current_user, csrf_token)

    if not current_user.is_recruiter:
        return RedirectResponse(url="/applications", status_code=status.HTTP_303_SEE_OTHER)
    
    application_data = await matching_service.get_application(db, id)
    if not application_data:
        return RedirectResponse(url="/applications", status_code=status.HTTP_303_SEE_OTHER)
    
    application, job, _ = application_data
    
    if job.company_id != current_user.id:
        return RedirectResponse(url="/applications", status_code=status.HTTP_303_SEE_OTHER)
    
    valid_statuses = ["New", "Reviewed", "Shortlisted", "Rejected"]
    if status_value not in valid_statuses:
        return RedirectResponse(url=f"/applications/{id}", status_code=status.HTTP_303_SEE_OTHER)
    
    await matching_service.update_application_status(db, id, status_value)
    return RedirectResponse(url=f"/applications/{id}", status_code=status.HTTP_303_SEE_OTHER)

# Analysis routes
@router.get("/analysis", response_class=HTMLResponse)
async def market_analysis(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_recruiter:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    
    context = await get_user_context(request, current_user)
    context["active_page"] = "analysis"
    
    analysis = await job_service.get_market_analysis(db, current_user)
    context["analysis"] = analysis
    
    return templates.TemplateResponse("analysis/index.html", context)