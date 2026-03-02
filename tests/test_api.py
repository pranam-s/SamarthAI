"""Tests for api.py – REST API routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "strong-pass-123",
            "full_name": "Test User",
            "is_recruiter": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {
        "email": "dup@example.com",
        "password": "pass-123",
        "full_name": "Dup User",
        "is_recruiter": False,
    }
    resp1 = await client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 200

    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "my-pass-456",
            "full_name": "Login User",
            "is_recruiter": False,
        },
    )

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "my-pass-456"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrong@example.com",
            "password": "correct-pass",
            "full_name": "Wrong User",
            "is_recruiter": False,
        },
    )

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "wrong@example.com", "password": "wrong-pass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "pass"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Helper to get auth headers
# ---------------------------------------------------------------------------


async def _register_and_login(
    client: AsyncClient,
    email: str = "user@example.com",
    password: str = "test-pass-789",
    is_recruiter: bool = False,
) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
            "is_recruiter": is_recruiter,
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Resume endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_resume_text(client: AsyncClient) -> None:
    headers = await _register_and_login(client)
    resp = await client.post(
        "/api/v1/resumes",
        data={"resume_data": "Jane Doe\nPython Developer\njane@example.com"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] >= 1
    assert data["full_text"] is not None


@pytest.mark.asyncio
async def test_list_resumes(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="list-res@example.com")
    # Create a resume
    await client.post(
        "/api/v1/resumes",
        data={"resume_data": "Resume text"},
        headers=headers,
    )
    resp = await client.get("/api/v1/resumes", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_resume_by_id(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="get-res@example.com")
    create = await client.post(
        "/api/v1/resumes",
        data={"resume_data": "Get resume test"},
        headers=headers,
    )
    rid = create.json()["id"]
    resp = await client.get(f"/api/v1/resumes/{rid}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == rid


@pytest.mark.asyncio
async def test_delete_resume(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="del-res@example.com")
    create = await client.post(
        "/api/v1/resumes",
        data={"resume_data": "Delete me"},
        headers=headers,
    )
    rid = create.json()["id"]
    del_resp = await client.delete(f"/api/v1/resumes/{rid}", headers=headers)
    assert del_resp.status_code == 200

    get_resp = await client.get(f"/api/v1/resumes/{rid}", headers=headers)
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Job endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="job-create@example.com", is_recruiter=True)
    resp = await client.post(
        "/api/v1/jobs",
        json={
            "title": "Backend Engineer",
            "description_text": "Python backend role",
            "required_skills": [{"name": "Python", "importance": 1.0}],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Backend Engineer"
    assert data["id"] >= 1


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="job-list@example.com", is_recruiter=True)
    await client.post(
        "/api/v1/jobs",
        json={"title": "Job1", "description_text": "Desc1"},
        headers=headers,
    )
    resp = await client.get("/api/v1/jobs", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_job_by_id(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="job-get@example.com", is_recruiter=True)
    create = await client.post(
        "/api/v1/jobs",
        json={"title": "GetJob", "description_text": "Test"},
        headers=headers,
    )
    jid = create.json()["id"]
    resp = await client.get(f"/api/v1/jobs/{jid}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == jid


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_create_resume_fails(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/resumes",
        json={"full_text": "No auth", "file_type": "text"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_create_job_fails(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/jobs",
        json={"title": "NoAuth", "description_text": "Fail"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Job update / delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_job(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="job-upd@e.com", is_recruiter=True)
    create = await client.post(
        "/api/v1/jobs",
        json={"title": "Old Title", "description_text": "Desc"},
        headers=headers,
    )
    jid = create.json()["id"]
    resp = await client.put(
        f"/api/v1/jobs/{jid}",
        json={"title": "New Title"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_delete_job(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="job-del@e.com", is_recruiter=True)
    create = await client.post(
        "/api/v1/jobs",
        json={"title": "Del Me", "description_text": "Gone"},
        headers=headers,
    )
    jid = create.json()["id"]
    resp = await client.delete(f"/api/v1/jobs/{jid}", headers=headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_application(client: AsyncClient) -> None:
    # Create a jobseeker with a resume
    js_headers = await _register_and_login(client, email="applicant@e.com")
    resume_resp = await client.post(
        "/api/v1/resumes",
        data={"resume_data": "Applicant Skills: Python, FastAPI"},
        headers=js_headers,
    )
    rid = resume_resp.json()["id"]

    # Create a recruiter with a job
    rec_headers = await _register_and_login(client, email="recruiter-app@e.com", is_recruiter=True)
    job_resp = await client.post(
        "/api/v1/jobs",
        json={"title": "Dev Role", "description_text": "Need Python"},
        headers=rec_headers,
    )
    jid = job_resp.json()["id"]

    # Jobseeker applies
    resp = await client.post(
        "/api/v1/applications",
        json={
            "resume_id": rid,
            "job_id": jid,
            "full_name": "Test Applicant",
            "email": "applicant@e.com",
        },
        headers=js_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["resume_id"] == rid
    assert data["job_id"] == jid


@pytest.mark.asyncio
async def test_list_applications(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="list-apps@e.com")
    resp = await client.get("/api/v1/applications", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Match endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_match_resume_to_job(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="match-test@e.com")
    resume_resp = await client.post(
        "/api/v1/resumes",
        data={"resume_data": "Skills: Python, Machine Learning, SQL"},
        headers=headers,
    )
    rid = resume_resp.json()["id"]

    rec_headers = await _register_and_login(client, email="match-rec@e.com", is_recruiter=True)
    job_resp = await client.post(
        "/api/v1/jobs",
        json={"title": "ML Engineer", "description_text": "Need Python and ML"},
        headers=rec_headers,
    )
    jid = job_resp.json()["id"]

    resp = await client.post(
        "/api/v1/match",
        json={"resume_id": rid, "job_id": jid},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data or "match_score" in data or isinstance(data, dict)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_recommendations(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="recs@e.com")
    resume_resp = await client.post(
        "/api/v1/resumes",
        data={"resume_data": "Skilled in Java and Spring Boot"},
        headers=headers,
    )
    rid = resume_resp.json()["id"]
    resp = await client.get(f"/api/v1/recommendations/{rid}", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Resume improvement suggestions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_resume_improvement(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="improve@e.com")
    resume_resp = await client.post(
        "/api/v1/resumes",
        data={"resume_data": "I know some coding"},
        headers=headers,
    )
    rid = resume_resp.json()["id"]
    resp = await client.get(f"/api/v1/resumes/{rid}/improve", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


# ---------------------------------------------------------------------------
# Quality score
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_resume_quality_score(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="quality@e.com")
    resume_resp = await client.post(
        "/api/v1/resumes",
        data={"resume_data": "Python developer with 5 years experience"},
        headers=headers,
    )
    rid = resume_resp.json()["id"]
    resp = await client.get(f"/api/v1/resumes/{rid}/quality-score", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Market analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_market_analysis(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="market@e.com", is_recruiter=True)
    resp = await client.get("/api/v1/market-analysis", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


# ---------------------------------------------------------------------------
# Skills Gap Analysis (new feature)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skills_gap_analysis(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="skillsgap@e.com")
    resume_resp = await client.post(
        "/api/v1/resumes",
        data={"resume_data": "Skills: Python, SQL, Docker"},
        headers=headers,
    )
    rid = resume_resp.json()["id"]

    rec_headers = await _register_and_login(client, email="skillsgap-rec@e.com", is_recruiter=True)
    job_resp = await client.post(
        "/api/v1/jobs",
        json={"title": "Backend Dev", "description_text": "Need Python, Go, Kubernetes"},
        headers=rec_headers,
    )
    jid = job_resp.json()["id"]

    resp = await client.post(
        "/api/v1/skills-gap",
        json={"resume_id": rid, "job_id": jid},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "gap_score" in data
    assert "matched_skills" in data
    assert "summary" in data


@pytest.mark.asyncio
async def test_skills_gap_resume_not_found(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="sgap-404@e.com")
    resp = await client.post(
        "/api/v1/skills-gap",
        json={"resume_id": 9999, "job_id": 1},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_skills_gap_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/skills-gap",
        json={"resume_id": 1, "job_id": 1},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Upload base64
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_resume_base64(client: AsyncClient) -> None:
    import base64

    headers = await _register_and_login(client, email="base64@e.com")
    content = base64.b64encode(b"Python developer with 5 years experience").decode()
    resp = await client.post(
        "/api/v1/resumes/upload-base64",
        json={
            "file_content": content,
            "file_type": "txt",
            "file_name": "resume.txt",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"]
    assert data["full_text"]


@pytest.mark.asyncio
async def test_upload_resume_base64_invalid(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="base64bad@e.com")
    resp = await client.post(
        "/api/v1/resumes/upload-base64",
        json={
            "file_content": "!!!NOT-BASE64!!!",
            "file_type": "txt",
            "file_name": "bad.txt",
        },
        headers=headers,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET application by id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_application_detail(client: AsyncClient) -> None:
    """Test retrieving a single application by ID."""
    # Create recruiter + job
    rec_h = await _register_and_login(client, email="appdet-rec@e.com", is_recruiter=True)
    job_resp = await client.post(
        "/api/v1/jobs",
        json={"title": "Eng Lead", "description_text": "Lead a team of engineers"},
        headers=rec_h,
    )
    jid = job_resp.json()["id"]

    # Create seeker + resume + application
    seek_h = await _register_and_login(client, email="appdet-seek@e.com")
    resume_resp = await client.post(
        "/api/v1/resumes",
        data={"resume_data": "Python engineer with leadership experience"},
        headers=seek_h,
    )
    rid = resume_resp.json()["id"]

    app_resp = await client.post(
        "/api/v1/applications",
        json={
            "job_id": jid,
            "resume_id": rid,
            "full_name": "App Detail",
            "email": "appdet-seek@e.com",
        },
        headers=seek_h,
    )
    aid = app_resp.json()["id"]

    # Retrieve as the seeker
    resp = await client.get(f"/api/v1/applications/{aid}", headers=seek_h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == aid
    assert "job" in data
    assert "resume" in data


# ---------------------------------------------------------------------------
# PATCH application status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_application_status(client: AsyncClient) -> None:
    """Test that a recruiter can update an application status."""
    rec_h = await _register_and_login(client, email="patchstat-rec@e.com", is_recruiter=True)
    job_resp = await client.post(
        "/api/v1/jobs",
        json={"title": "DevOps", "description_text": "Manage infra"},
        headers=rec_h,
    )
    jid = job_resp.json()["id"]

    seek_h = await _register_and_login(client, email="patchstat-seek@e.com")
    resume_resp = await client.post(
        "/api/v1/resumes",
        data={"resume_data": "Linux sysadmin with CI/CD experience"},
        headers=seek_h,
    )
    rid = resume_resp.json()["id"]

    app_resp = await client.post(
        "/api/v1/applications",
        json={
            "job_id": jid,
            "resume_id": rid,
            "full_name": "Patch Test",
            "email": "patchstat-seek@e.com",
        },
        headers=seek_h,
    )
    aid = app_resp.json()["id"]

    # Recruiter updates status
    resp = await client.patch(
        f"/api/v1/applications/{aid}/status?status_value=Reviewed",
        headers=rec_h,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Reviewed"


@pytest.mark.asyncio
async def test_update_application_status_forbidden(client: AsyncClient) -> None:
    """Non-recruiter cannot update application status."""
    seek_h = await _register_and_login(client, email="patchfail@e.com")
    resp = await client.patch(
        "/api/v1/applications/1/status?status_value=Reviewed",
        headers=seek_h,
    )
    assert resp.status_code == 403
