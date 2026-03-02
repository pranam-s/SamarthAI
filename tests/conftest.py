from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.database import Base, get_db  # noqa: E402
from main import app  # noqa: E402

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
_TestSession = async_sessionmaker(_test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a clean async DB session backed by an in-memory SQLite database."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _TestSession() as session:
        yield session

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTP test client with dependency overrides."""

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_resume_text() -> str:
    return (
        "Jane Doe\nBackend Engineer\nEmail: jane@example.com\n"
        "Phone: +91 9999999999\nPython FastAPI SQL Docker Kubernetes\n"
        "Experience: 5 years at TechCorp as Senior Developer\n"
        "Education: B.Tech Computer Science, IIT Delhi\n"
        "Projects: E-commerce Platform using React and Node.js\n"
        "Certifications: AWS Solutions Architect"
    )


@pytest.fixture
def sample_parsed_resume() -> dict:
    return {
        "parsed_sections": {
            "contact": {"name": "Jane Doe", "email": "jane@example.com", "phone": "+91 9999999999"},
            "summary": "Backend Engineer",
        },
        "skills": [
            {"name": "Python", "proficiency": "expert"},
            {"name": "FastAPI", "proficiency": "advanced"},
            {"name": "SQL", "proficiency": "advanced"},
            {"name": "Docker", "proficiency": "intermediate"},
            {"name": "Kubernetes", "proficiency": "intermediate"},
        ],
        "experience": [
            {
                "role": "Senior Developer",
                "company": "TechCorp",
                "start_date": "2019",
                "end_date": "Present",
            }
        ],
        "education": [
            {
                "institution": "IIT Delhi",
                "degree": "B.Tech",
                "field_of_study": "Computer Science",
            }
        ],
        "projects": [{"name": "E-commerce Platform", "technologies": ["React", "Node.js"]}],
        "certifications": [{"name": "AWS Solutions Architect"}],
    }


@pytest.fixture
def sample_parsed_job() -> dict:
    return {
        "title": "Senior Backend Engineer",
        "required_skills": [
            {"name": "Python", "importance": 1.0},
            {"name": "FastAPI", "importance": 0.9},
            {"name": "PostgreSQL", "importance": 0.8},
        ],
        "preferred_skills": [
            {"name": "Docker", "importance": 0.7},
            {"name": "Redis", "importance": 0.5},
        ],
        "responsibilities": ["Design and build APIs", "Mentor junior developers"],
        "qualifications": ["5+ years Python experience", "B.Tech or equivalent"],
    }
