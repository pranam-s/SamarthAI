from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, JSON, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    is_recruiter = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    full_text = Column(Text)
    parsed_sections = Column(JSON)
    skills = Column(JSON)
    experience = Column(JSON)
    education = Column(JSON)
    projects = Column(JSON)
    certifications = Column(JSON)
    achievements = Column(JSON)
    file_path = Column(String, nullable=True)
    file_type = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, index=True)
    description_text = Column(Text)
    required_skills = Column(JSON)
    preferred_skills = Column(JSON)
    responsibilities = Column(JSON)
    qualifications = Column(JSON)
    priority_weights = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    full_name = Column(String)
    email = Column(String)
    phone = Column(String, nullable=True)
    match_score = Column(Float)
    match_details = Column(JSON)
    feedback = Column(JSON)
    status = Column(String, default="New")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)