from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str | None] = mapped_column(String, default=None)
    bio: Mapped[str | None] = mapped_column(Text, default=None)
    location: Mapped[str | None] = mapped_column(String, default=None)
    profile_picture_url: Mapped[str | None] = mapped_column(String, default=None)
    is_recruiter: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), default=None
    )

    resumes: Mapped[list["Resume"]] = relationship(back_populates="owner", lazy="selectin")
    jobs: Mapped[list["Job"]] = relationship(back_populates="company", lazy="selectin")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    full_text: Mapped[str | None] = mapped_column(Text, default=None)
    parsed_sections: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    skills: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    experience: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    education: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    projects: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    certifications: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    achievements: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    file_path: Mapped[str | None] = mapped_column(String, default=None)
    file_type: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), default=None
    )

    owner: Mapped["User"] = relationship(back_populates="resumes", lazy="selectin")
    applications: Mapped[list["Application"]] = relationship(
        back_populates="resume", lazy="selectin"
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String, index=True)
    description_text: Mapped[str | None] = mapped_column(Text, default=None)
    location: Mapped[str | None] = mapped_column(String, default=None)
    salary_min: Mapped[int | None] = mapped_column(Integer, default=None)
    salary_max: Mapped[int | None] = mapped_column(Integer, default=None)
    job_type: Mapped[str | None] = mapped_column(
        String, default=None
    )  # full-time/part-time/contract/internship
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    experience_level: Mapped[str | None] = mapped_column(
        String, default=None
    )  # entry/mid/senior/lead
    required_skills: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    preferred_skills: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    responsibilities: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    qualifications: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    priority_weights: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), default=None
    )

    company: Mapped["User"] = relationship(back_populates="jobs", lazy="selectin")
    applications: Mapped[list["Application"]] = relationship(back_populates="job", lazy="selectin")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"))
    full_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String, default=None)
    cover_letter: Mapped[str | None] = mapped_column(Text, default=None)
    match_score: Mapped[float] = mapped_column(default=0.0)
    match_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    feedback: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    status: Mapped[str] = mapped_column(String, default="New")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    job: Mapped["Job"] = relationship(back_populates="applications", lazy="selectin")
    resume: Mapped["Resume"] = relationship(back_populates="applications", lazy="selectin")
