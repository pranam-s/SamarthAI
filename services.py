import asyncio
import json
import logging
import os
import re
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiofiles
from docx import Document
from fastapi import UploadFile
from google import genai
from google.genai import types
from openai import OpenAI
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models import Application as ApplicationModel
from models import Job as JobModel
from models import Resume as ResumeModel
from models import User as UserModel

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(settings.PROMPTS_DIR)


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


class AIService:
    """Handles all AI provider interactions with Google GenAI primary and OpenRouter fallback."""

    def __init__(self):
        self.google_client = None
        self.openrouter_client = None

        if settings.resolved_google_api_key:
            self.google_client = genai.Client(api_key=settings.resolved_google_api_key)

        if settings.OPENROUTER_API_KEY:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )

    @staticmethod
    def parse_json(text: str) -> dict[str, Any]:
        start_idx = text.find("{")
        if start_idx == -1:
            raise ValueError("No JSON object found in response")

        stack: list[str] = []
        in_string = False
        escaped = False

        for i in range(start_idx, len(text)):
            char = text[i]
            if in_string:
                if char == "\\" and not escaped:
                    escaped = True
                elif char == '"' and not escaped:
                    in_string = False
                else:
                    escaped = False
            else:
                if char == '"':
                    in_string = True
                elif char == "{":
                    stack.append(char)
                elif char == "}":
                    if not stack:
                        raise ValueError("Malformed JSON response")
                    stack.pop()
                    if not stack:
                        return json.loads(text[start_idx : i + 1])

        raise ValueError("Malformed JSON response")

    async def _call_google(self, prompt: str, file_path: str | None = None) -> str | None:
        if not self.google_client:
            return None

        try:
            contents: list[Any] = [prompt]
            if file_path:
                mime_type = self._get_mime_type(file_path)
                async with aiofiles.open(file_path, "rb") as uploaded_file:
                    file_bytes = await uploaded_file.read()
                contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))

            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=settings.GOOGLE_THINKING_BUDGET,
                ),
            )
            response = await self.google_client.aio.models.generate_content(
                model=settings.GOOGLE_MODEL,
                contents=contents,
                config=config,
            )
            return response.text
        except Exception:
            logger.exception("Google GenAI call failed")
            return None

    async def _call_openrouter(self, prompt: str) -> str | None:
        if not self.openrouter_client:
            return None

        def _invoke() -> str | None:
            completion = self.openrouter_client.chat.completions.create(
                model=settings.OPENROUTER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": settings.APP_URL,
                    "X-OpenRouter-Title": settings.PROJECT_NAME,
                },
            )
            return completion.choices[0].message.content

        try:
            return await asyncio.to_thread(_invoke)
        except Exception:
            logger.exception("OpenRouter call failed")
            return None

    async def _call_text(self, prompt: str, file_path: str | None = None) -> str | None:
        providers = [settings.AI_PRIMARY_PROVIDER, settings.AI_FALLBACK_PROVIDER]
        for provider in providers:
            if provider == "google":
                text = await self._call_google(prompt, file_path=file_path)
            elif provider == "openrouter":
                text = await self._call_openrouter(prompt)
            else:
                text = None

            if text:
                return text

        return None

    async def call_gemini(self, prompt: str, file_path: str | None = None) -> dict[str, Any] | str:
        text = await self._call_text(prompt, file_path=file_path)
        if not text:
            return {"error": "No provider response available"}

        try:
            return self.parse_json(text)
        except Exception:
            return text

    @staticmethod
    def _get_mime_type(file_path: str) -> str:
        extension = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }
        return mime_map.get(extension, "application/octet-stream")

    async def extract_resume_from_pdf(self, file_path: str) -> str:
        prompt = _load_prompt("extract_pdf")
        response = await self._call_text(prompt, file_path=file_path)
        if response:
            return response
        return self._extract_text_from_pdf_locally(file_path)

    @staticmethod
    def _extract_text_from_pdf_locally(file_path: str) -> str:
        chunks: list[str] = []
        with open(file_path, "rb") as f:
            for page in PdfReader(f).pages:
                chunks.append(page.extract_text() or "")
        return "\n".join(chunks).strip()

    @staticmethod
    def _default_resume_payload(text: str) -> dict[str, Any]:
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        phone_match = re.search(r"(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){8,13}", text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        possible_name = lines[0] if lines else ""

        skill_keywords = [
            "python",
            "java",
            "javascript",
            "typescript",
            "react",
            "node",
            "sql",
            "docker",
            "kubernetes",
            "aws",
            "gcp",
            "azure",
            "fastapi",
            "django",
            "flask",
            "git",
            "linux",
            "pandas",
            "numpy",
            "machine learning",
            "llm",
            "genai",
            "tensorflow",
            "pytorch",
            "postgresql",
            "mongodb",
        ]
        lowered = text.lower()
        found_skills = [
            {"name": skill.title(), "proficiency": "", "context": ""}
            for skill in skill_keywords
            if skill in lowered
        ]

        return {
            "parsed_sections": {
                "summary": lines[1] if len(lines) > 1 else "",
                "contact": {
                    "name": possible_name,
                    "email": email_match.group(0) if email_match else "",
                    "phone": phone_match.group(0) if phone_match else "",
                    "location": "",
                },
            },
            "skills": found_skills,
            "experience": [],
            "education": [],
            "projects": [],
            "certifications": [],
            "achievements": [],
        }

    async def parse_resume(self, text: str) -> dict[str, Any]:
        prompt = _load_prompt("parse_resume").replace("{resume_text}", text)
        response = await self._call_text(prompt)
        if response:
            try:
                parsed = self.parse_json(response)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                logger.warning("Failed to parse AI resume response, using heuristic")
        return self._default_resume_payload(text)

    @staticmethod
    def _default_job_payload(text: str) -> dict[str, Any]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = lines[0] if lines else "Untitled Job"

        keyword_weights = {
            "python": 1.0,
            "fastapi": 1.0,
            "sql": 1.0,
            "docker": 0.8,
            "kubernetes": 0.8,
            "aws": 0.8,
            "react": 0.7,
            "typescript": 0.7,
            "machine learning": 0.8,
            "genai": 0.7,
        }
        lowered = text.lower()
        required_skills = [
            {"name": kw.title(), "importance": imp}
            for kw, imp in keyword_weights.items()
            if kw in lowered
        ]

        return {
            "title": title,
            "required_skills": required_skills,
            "preferred_skills": [],
            "responsibilities": [],
            "qualifications": [],
        }

    async def parse_job_description(self, text: str) -> dict[str, Any]:
        prompt = _load_prompt("parse_job").replace("{job_text}", text)
        response = await self._call_text(prompt)
        if response:
            try:
                parsed = self.parse_json(response)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                logger.warning("Failed to parse AI job response, using heuristic")
        return self._default_job_payload(text)

    @staticmethod
    def _extract_skill_names(skills: Any) -> list[str]:
        if not isinstance(skills, list):
            return []
        values: list[str] = []
        for skill in skills:
            if isinstance(skill, dict) and skill.get("name"):
                values.append(str(skill["name"]).strip().lower())
            elif isinstance(skill, str):
                values.append(skill.strip().lower())
        return values

    def _heuristic_match_score(
        self, resume_data: dict[str, Any], job_data: dict[str, Any]
    ) -> tuple[float, dict[str, Any]]:
        resume_skills = set(self._extract_skill_names(resume_data.get("skills", [])))
        required_skills = set(self._extract_skill_names(job_data.get("required_skills", [])))
        preferred_skills = set(self._extract_skill_names(job_data.get("preferred_skills", [])))

        matched_required = sorted(required_skills & resume_skills)
        missing_required = sorted(required_skills - resume_skills)
        matched_preferred = sorted(preferred_skills & resume_skills)
        missing_preferred = sorted(preferred_skills - resume_skills)

        required_rate = (
            (len(matched_required) / len(required_skills) * 100.0) if required_skills else 100.0
        )
        preferred_rate = (
            (len(matched_preferred) / len(preferred_skills) * 100.0) if preferred_skills else 100.0
        )
        skills_score = round((required_rate * 0.8) + (preferred_rate * 0.2), 2)

        experience_entries = (
            resume_data.get("experience", [])
            if isinstance(resume_data.get("experience"), list)
            else []
        )
        education_entries = (
            resume_data.get("education", [])
            if isinstance(resume_data.get("education"), list)
            else []
        )

        experience_score = 70.0 if experience_entries else 25.0
        education_score = 75.0 if education_entries else 30.0

        overall_match = round(
            (skills_score * 0.6) + (experience_score * 0.3) + (education_score * 0.1), 2
        )

        details = {
            "overall_match": overall_match,
            "sections": {
                "skills": {
                    "score": round(skills_score, 2),
                    "required": {
                        "matched": [s.title() for s in matched_required],
                        "missing": [s.title() for s in missing_required],
                        "match_rate": round(required_rate, 2),
                    },
                    "preferred": {
                        "matched": [s.title() for s in matched_preferred],
                        "missing": [s.title() for s in missing_preferred],
                        "match_rate": round(preferred_rate, 2),
                    },
                },
                "experience": {
                    "score": round(experience_score, 2),
                    "matching_aspects": (
                        ["Relevant experience available"] if experience_entries else []
                    ),
                    "missing_aspects": (
                        [] if experience_entries else ["Add role-specific experience"]
                    ),
                    "experience_entries": [],
                },
                "education": {
                    "score": round(education_score, 2),
                    "matching_aspects": (["Education data available"] if education_entries else []),
                    "missing_aspects": ([] if education_entries else ["Add education details"]),
                    "highest_education": None,
                },
            },
            "weights_applied": {"skills": 0.6, "experience": 0.3, "education": 0.1},
        }
        return overall_match, details

    async def calculate_match_score(
        self, resume_data: dict[str, Any], job_data: dict[str, Any]
    ) -> tuple[float, dict[str, Any]]:
        prompt = (
            _load_prompt("match_score")
            .replace("{resume_data}", json.dumps(resume_data))
            .replace("{job_data}", json.dumps(job_data))
        )

        response = await self._call_text(prompt)
        if response:
            try:
                parsed = self.parse_json(response)
                if isinstance(parsed, dict):
                    return float(parsed.get("overall_match", 0.0)), parsed
            except Exception:
                logger.warning("Failed to parse AI match response, using heuristic")
        return self._heuristic_match_score(resume_data, job_data)

    async def generate_resume_feedback(
        self,
        resume_data: dict[str, Any],
        job_data: dict[str, Any],
        match_details: dict[str, Any],
    ) -> dict[str, Any]:
        skills_section = match_details.get("sections", {}).get("skills", {})
        required_section = skills_section.get("required", {})
        preferred_section = skills_section.get("preferred", {})

        missing_required_skills = required_section.get("missing", [])
        missing_preferred_skills = preferred_section.get("missing", [])

        strengths = [
            f"You match required skill: {skill}" for skill in required_section.get("matched", [])
        ]
        improvements = [f"Add evidence for skill: {skill}" for skill in missing_required_skills[:5]]
        keyword_recommendations = list(
            dict.fromkeys([*missing_required_skills, *missing_preferred_skills])
        )[:10]

        prompt = _load_prompt("feedback").replace("{match_details}", json.dumps(match_details))
        response = await self._call_text(prompt)
        if response:
            try:
                parsed = self.parse_json(response)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                logger.warning("Failed to parse AI feedback response, using heuristic")

        return {
            "strengths": (
                strengths[:5] if strengths else ["Resume contains useful baseline information."]
            ),
            "improvements": (
                improvements
                if improvements
                else ["Add measurable impact in project or role descriptions."]
            ),
            "missing_skills": missing_required_skills[:8],
            "keyword_recommendations": keyword_recommendations,
        }


class ResumeService:
    """Resume file processing and CRUD operations."""

    def __init__(self, ai: AIService):
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        self.ai = ai

    async def process_resume_file(self, file: UploadFile) -> dict[str, Any]:
        filename = file.filename or "resume.txt"
        ext = os.path.splitext(filename)[1].lower()
        unique_name = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

        async with aiofiles.open(file_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                await out.write(chunk)

        if ext == ".pdf":
            text = await self.ai.extract_resume_from_pdf(file_path)
        elif ext == ".docx":
            text = self._extract_text_from_docx(file_path)
        else:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                text = await f.read()

        parsed_data = await self.ai.parse_resume(text)

        return {
            "file_path": file_path,
            "file_type": ext.replace(".", ""),
            "full_text": text,
            "structured_text": text,
            "parsed_data": parsed_data,
        }

    async def process_resume_text(self, text: str) -> dict[str, Any]:
        parsed_data = await self.ai.parse_resume(text)
        return {
            "file_path": None,
            "file_type": "txt",
            "full_text": text,
            "structured_text": text,
            "parsed_data": parsed_data,
        }

    @staticmethod
    def _extract_text_from_docx(file_path: str) -> str:
        return "\n".join(p.text for p in Document(file_path).paragraphs)

    async def create_resume(
        self, db: AsyncSession, user_id: int, resume_data: dict[str, Any]
    ) -> ResumeModel:
        parsed = resume_data["parsed_data"]
        resume = ResumeModel(
            user_id=user_id,
            full_text=resume_data["full_text"],
            parsed_sections=parsed,
            skills=parsed.get("skills", []),
            experience=parsed.get("experience", []),
            education=parsed.get("education", []),
            projects=parsed.get("projects", []),
            certifications=parsed.get("certifications", []),
            achievements=parsed.get("achievements", []),
            file_path=resume_data["file_path"],
            file_type=resume_data["file_type"],
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)
        return resume

    async def get_resumes(
        self,
        db: AsyncSession,
        user_id: int,
        is_recruiter: bool,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ResumeModel]:
        if is_recruiter:
            stmt = select(ResumeModel).offset(skip).limit(limit)
        else:
            stmt = (
                select(ResumeModel).where(ResumeModel.user_id == user_id).offset(skip).limit(limit)
            )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_resume(self, db: AsyncSession, resume_id: int) -> ResumeModel | None:
        result = await db.execute(select(ResumeModel).where(ResumeModel.id == resume_id))
        return result.scalars().first()

    async def delete_resume(self, db: AsyncSession, resume_id: int) -> bool:
        resume = await self.get_resume(db, resume_id)
        if not resume:
            return False
        if resume.file_path and os.path.exists(resume.file_path):
            os.remove(resume.file_path)
        await db.execute(delete(ResumeModel).where(ResumeModel.id == resume_id))
        await db.commit()
        return True


class JobService:
    """Job description processing and CRUD operations."""

    def __init__(self, ai: AIService):
        self.ai = ai

    async def process_job_description(self, text: str) -> dict[str, Any]:
        parsed_data = await self.ai.parse_job_description(text)
        return {"description_text": text, "parsed_data": parsed_data}

    async def create_job(
        self,
        db: AsyncSession,
        user_id: int,
        job_data: dict[str, Any],
        job_in: dict[str, Any],
    ) -> JobModel:
        parsed = job_data["parsed_data"]
        job = JobModel(
            company_id=user_id,
            title=job_in.get("title") or parsed.get("title", "Untitled Job"),
            description_text=job_data["description_text"],
            required_skills=parsed.get("required_skills", []),
            preferred_skills=parsed.get("preferred_skills", []),
            responsibilities=parsed.get("responsibilities", []),
            qualifications=parsed.get("qualifications", []),
            priority_weights=job_in.get("priority_weights")
            or {"skills": 0.6, "experience": 0.3, "education": 0.1},
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    async def get_jobs(
        self,
        db: AsyncSession,
        user_id: int,
        is_recruiter: bool,
        skip: int = 0,
        limit: int = 100,
    ) -> list[JobModel]:
        if is_recruiter:
            stmt = select(JobModel).where(JobModel.company_id == user_id).offset(skip).limit(limit)
        else:
            stmt = select(JobModel).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_job(self, db: AsyncSession, job_id: int) -> JobModel | None:
        result = await db.execute(select(JobModel).where(JobModel.id == job_id))
        return result.scalars().first()

    async def update_job(
        self, db: AsyncSession, job_id: int, job_data: dict[str, Any]
    ) -> JobModel | None:
        job = await self.get_job(db, job_id)
        if not job:
            return None
        for key, value in job_data.items():
            setattr(job, key, value)
        await db.commit()
        await db.refresh(job)
        return job

    async def delete_job(self, db: AsyncSession, job_id: int) -> bool:
        job = await self.get_job(db, job_id)
        if not job:
            return False
        await db.execute(delete(JobModel).where(JobModel.id == job_id))
        await db.commit()
        return True

    async def get_recommendations(
        self, resume_id: int, db: AsyncSession, current_user: UserModel, limit: int = 5
    ) -> list[JobModel]:
        resume = await resume_service.get_resume(db, resume_id)
        if not resume:
            return []

        jobs = await self.get_jobs(db, current_user.id, current_user.is_recruiter, limit=100)
        scored: list[tuple[JobModel, float]] = []

        for job in jobs:
            score, _ = await self.ai.calculate_match_score(
                resume.parsed_sections,
                {
                    "title": job.title,
                    "required_skills": job.required_skills,
                    "preferred_skills": job.preferred_skills,
                    "responsibilities": job.responsibilities,
                    "qualifications": job.qualifications,
                },
            )
            scored.append((job, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [j for j, _ in scored[:limit]]

    async def get_resume_improvement(
        self, resume_id: int, db: AsyncSession, current_user: UserModel
    ) -> dict[str, Any]:
        resume = await resume_service.get_resume(db, resume_id)
        if not resume:
            return {}

        prompt = _load_prompt("improve_resume").replace("{resume_text}", resume.full_text or "")
        response = await self.ai.call_gemini(prompt)
        if isinstance(response, dict) and "error" not in response:
            return response

        return {
            "format": ["Use consistent section headings and spacing."],
            "bullet_points": ["Begin bullets with impact verbs and include quantifiable outcomes."],
            "keywords": ["Collaboration", "Problem Solving", "Delivery"],
            "skills": [
                skill.get("name") for skill in (resume.skills or [])[:5] if isinstance(skill, dict)
            ],
        }

    async def get_resume_quality_score(
        self, resume_id: int, db: AsyncSession, current_user: UserModel
    ) -> dict[str, Any]:
        resume = await resume_service.get_resume(db, resume_id)
        if not resume:
            return {}

        has_quantifiable = False
        experience_score = 0
        for exp in resume.experience or []:
            achievements = exp.get("achievements", []) if isinstance(exp, dict) else []
            for achievement in achievements:
                if re.search(
                    r"\d+%|\d+x|\$\d+|increased|decreased|improved|reduced|saved|generated",
                    str(achievement),
                    re.IGNORECASE,
                ):
                    has_quantifiable = True
                    experience_score += 10

        skills_score = min(100, len(resume.skills or []) * 7)
        education_score = min(100, len(resume.education or []) * 30)
        overall = round(
            (min(100, experience_score) * 0.5) + (skills_score * 0.3) + (education_score * 0.2),
            2,
        )

        suggestions: list[str] = []
        if not has_quantifiable:
            suggestions.append("Add measurable outcomes in experience bullets.")
        if skills_score < 60:
            suggestions.append("Expand skills with proficiency and role context.")
        if education_score < 60:
            suggestions.append("Add education details such as field and achievements.")

        return {
            "overall_score": overall,
            "sections": {
                "experience": min(100, experience_score),
                "skills": skills_score,
                "education": education_score,
            },
            "suggestions": suggestions,
        }

    async def get_market_analysis(
        self, db: AsyncSession, current_user: UserModel
    ) -> dict[str, Any]:
        jobs = await self.get_jobs(db, current_user.id, current_user.is_recruiter, limit=1000)

        required_counter: Counter[str] = Counter()
        preferred_counter: Counter[str] = Counter()

        for job in jobs:
            for skill in job.required_skills or []:
                if isinstance(skill, dict) and skill.get("name"):
                    required_counter[str(skill["name"]).lower()] += 1
            for skill in job.preferred_skills or []:
                if isinstance(skill, dict) and skill.get("name"):
                    preferred_counter[str(skill["name"]).lower()] += 1

        return {
            "total_jobs_analyzed": len(jobs),
            "top_required_skills": [
                {"name": name, "count": count} for name, count in required_counter.most_common(10)
            ],
            "top_preferred_skills": [
                {"name": name, "count": count} for name, count in preferred_counter.most_common(10)
            ],
            "analysis_date": datetime.now(UTC).isoformat(),
        }

    async def analyze_skills_gap(
        self, resume_id: int, job_id: int, db: AsyncSession, current_user: UserModel
    ) -> dict[str, Any]:
        """Analyse the gap between a resume's skills and a job's requirements."""
        resume = await resume_service.get_resume(db, resume_id)
        if not resume:
            return {}

        job = await self.get_job(db, job_id)
        if not job:
            return {}

        resume_skills = set(self.ai._extract_skill_names(resume.skills or []))
        required_skills_raw = job.required_skills or []
        preferred_skills_raw = job.preferred_skills or []
        required_skills = set(self.ai._extract_skill_names(required_skills_raw))
        preferred_skills = set(self.ai._extract_skill_names(preferred_skills_raw))

        matched = sorted(resume_skills & (required_skills | preferred_skills))
        missing_req = sorted(required_skills - resume_skills)
        missing_pref = sorted(preferred_skills - resume_skills)

        total_target = len(required_skills | preferred_skills)
        gap_score = round((len(matched) / total_target * 100.0) if total_target else 100.0, 2)

        # Build importance lookup from raw skills
        importance_map: dict[str, float] = {}
        for s in required_skills_raw:
            if isinstance(s, dict) and s.get("name"):
                importance_map[str(s["name"]).strip().lower()] = float(s.get("importance", 1.0))
        for s in preferred_skills_raw:
            if isinstance(s, dict) and s.get("name"):
                importance_map[str(s["name"]).strip().lower()] = float(s.get("importance", 0.5))

        missing_required_items = [
            {
                "skill": s.title(),
                "status": "missing_required",
                "importance": importance_map.get(s, 1.0),
                "learning_suggestion": f"Consider learning {s.title()} through official docs or courses.",
            }
            for s in missing_req
        ]
        missing_preferred_items = [
            {
                "skill": s.title(),
                "status": "missing_preferred",
                "importance": importance_map.get(s, 0.5),
                "learning_suggestion": f"Explore {s.title()} to strengthen your profile.",
            }
            for s in missing_pref
        ]

        learning_path: list[str] = []
        # Prioritise missing required by importance
        ordered = sorted(missing_required_items, key=lambda x: x["importance"], reverse=True)
        for item in ordered[:5]:
            learning_path.append(f"Learn {item['skill']} (high priority)")
        for item in missing_preferred_items[:3]:
            learning_path.append(f"Explore {item['skill']} (nice-to-have)")

        summary = (
            f"You match {len(matched)} of {total_target} target skills "
            f"({gap_score:.0f}% coverage). "
            f"{len(missing_req)} required and {len(missing_pref)} preferred skills are missing."
        )

        # Try AI-enhanced analysis
        try:
            prompt = (
                _load_prompt("skills_gap")
                .replace("{resume_skills}", json.dumps(sorted(resume_skills)))
                .replace("{required_skills}", json.dumps(sorted(required_skills)))
                .replace("{preferred_skills}", json.dumps(sorted(preferred_skills)))
            )
            response = await self.ai._call_text(prompt)
            if response:
                parsed = self.ai.parse_json(response)
                if isinstance(parsed, dict):
                    return {
                        "resume_id": resume_id,
                        "job_id": job_id,
                        "gap_score": parsed.get("gap_score", gap_score),
                        "matched_skills": parsed.get(
                            "matched_skills", [s.title() for s in matched]
                        ),
                        "missing_required": parsed.get("missing_required", missing_required_items),
                        "missing_preferred": parsed.get(
                            "missing_preferred", missing_preferred_items
                        ),
                        "learning_path": parsed.get("learning_path", learning_path),
                        "summary": parsed.get("summary", summary),
                    }
        except Exception:
            logger.warning("AI skills gap analysis failed, using heuristic")

        return {
            "resume_id": resume_id,
            "job_id": job_id,
            "gap_score": gap_score,
            "matched_skills": [s.title() for s in matched],
            "missing_required": missing_required_items,
            "missing_preferred": missing_preferred_items,
            "learning_path": learning_path,
            "summary": summary,
        }


class MatchingService:
    """Resume-to-job matching and application management."""

    def __init__(self, ai: AIService):
        self.ai = ai

    async def match_resume_to_job(
        self, resume_data: dict[str, Any], job_data: dict[str, Any]
    ) -> tuple[float, dict[str, Any], dict[str, Any]]:
        score, match_details = await self.ai.calculate_match_score(resume_data, job_data)
        feedback = await self.ai.generate_resume_feedback(resume_data, job_data, match_details)
        return score, match_details, feedback

    async def create_application(
        self,
        db: AsyncSession,
        application_data: dict[str, Any],
        match_score: float,
        match_details: dict[str, Any],
        feedback: dict[str, Any],
    ) -> ApplicationModel:
        application = ApplicationModel(
            job_id=application_data["job_id"],
            resume_id=application_data["resume_id"],
            full_name=application_data["full_name"],
            email=application_data["email"],
            phone=application_data.get("phone"),
            match_score=match_score,
            match_details=match_details,
            feedback=feedback,
            status="New",
        )
        db.add(application)
        await db.commit()
        await db.refresh(application)
        return application

    async def get_applications(
        self,
        db: AsyncSession,
        user_id: int,
        is_recruiter: bool,
        job_id: int | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ApplicationModel]:
        query = select(ApplicationModel)

        if job_id:
            query = query.where(ApplicationModel.job_id == job_id)
        if status:
            query = query.where(ApplicationModel.status == status)

        if is_recruiter:
            recruiter_jobs = select(JobModel.id).where(JobModel.company_id == user_id)
            query = query.where(ApplicationModel.job_id.in_(recruiter_jobs.scalar_subquery()))
        else:
            user_resumes = select(ResumeModel.id).where(ResumeModel.user_id == user_id)
            query = query.where(ApplicationModel.resume_id.in_(user_resumes.scalar_subquery()))

        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_application(
        self, db: AsyncSession, application_id: int
    ) -> tuple[ApplicationModel, JobModel, ResumeModel] | None:
        query = (
            select(ApplicationModel, JobModel, ResumeModel)
            .join(JobModel, ApplicationModel.job_id == JobModel.id)
            .join(ResumeModel, ApplicationModel.resume_id == ResumeModel.id)
            .where(ApplicationModel.id == application_id)
        )
        result = await db.execute(query)
        row = result.first()
        if row:
            return row[0], row[1], row[2]
        return None

    async def update_application_status(
        self, db: AsyncSession, application_id: int, status: str
    ) -> ApplicationModel | None:
        application = await db.get(ApplicationModel, application_id)
        if not application:
            return None
        application.status = status
        if status != "New":
            application.reviewed_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(application)
        return application


class UserService:
    """User account management."""

    async def create_user(
        self, db: AsyncSession, user_data: dict[str, Any], hashed_password: str
    ) -> UserModel:
        user = UserModel(
            email=user_data["email"],
            hashed_password=hashed_password,
            full_name=user_data.get("full_name", ""),
            is_recruiter=user_data.get("is_recruiter", False),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def get_user_by_email(self, db: AsyncSession, email: str) -> UserModel | None:
        result = await db.execute(select(UserModel).where(UserModel.email == email))
        return result.scalars().first()

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> UserModel | None:
        return await db.get(UserModel, user_id)


ai_service = AIService()
resume_service = ResumeService(ai_service)
job_service = JobService(ai_service)
matching_service = MatchingService(ai_service)
user_service = UserService()
