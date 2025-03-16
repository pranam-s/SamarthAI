import asyncio
import base64
import json
import os
import uuid
from typing import Dict, List, Optional, Any, Tuple, BinaryIO, Set
import io
from pydantic import BaseModel
import httpx
import numpy as np
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select as future_select
import aiofiles
import PyPDF2
from docx import Document
from google import genai
from google.genai import types

from core.config import settings
from schemas import Resume, Job, JobBase, ResumeBase, MatchDetails
from models import Resume as ResumeModel
from models import Job as JobModel
from models import Application as ApplicationModel
from models import User as UserModel


class AIService:
    def __init__(self):
        self.model = settings.GEMINI_MODEL
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def call_gemini(self, prompt: str, file_path: str = None) -> dict:
        try:
            contents = [prompt]

            if file_path:
                mime_type = self._get_mime_type(file_path)
                async with aiofiles.open(file_path, 'rb') as f:
                    file_data = await f.read()
                contents.append(types.Part.from_bytes(data=file_data, mime_type=mime_type))

            config = types.GenerateContentConfig()
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )

            if response.text:
                try:
                    return self.parse_json(response.text)
                except :
                    return response.text
            else:
                return {"error": "No text response from the model."}

        except Exception as e:
            return {"error": f"Gemini API call failed: {str(e)}"}

    def parse_json(self, text):
        start_idx = text.find('{')
        if start_idx == -1:
            raise ValueError("No JSON object found in the input string")
        stack = []
        in_string = False
        escaped = False
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            if in_string:
                if char == '\\' and not escaped:
                    escaped = True
                elif char == '"' and not escaped:
                    in_string = False
                else:
                    escaped = False
            else:
                if char == '"':
                    in_string = True
                elif char == '{':
                    stack.append('{')
                elif char == '}':
                    if not stack:
                        raise ValueError("Unbalanced braces in the input string")
                    stack.pop()
                
                    if not stack:
                        end_idx = i + 1
                        json_str = text[start_idx:end_idx]
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError as e:
                            raise ValueError(f"Failed to parse JSON: {e}")
        raise ValueError("Unbalanced braces in the input string")

    def _get_mime_type(self, file_path: str) -> str:
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.pdf':
            return 'application/pdf'
        elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            return f'image/{file_extension[1:]}'
        elif file_extension == '.txt':
            return 'text/plain'
        else:
            return 'application/octet-stream'

    async def extract_resume_from_pdf(self, file_path: str) -> str:
        prompt = f"""
    Extract all text from this PDF resume, preserving its structure as much as possible.
    Return only the extracted text, with no additional formatting or analysis.
    """

        response = await self.call_gemini(prompt, file_path=file_path)
        return response

    async def parse_resume(self, text: str) -> Dict[str, Any]:
        prompt = f"""
        Extract the following information from this resume in JSON format:
        
        Resume:
        {text}
        
        Return only a valid JSON object with the following structure:
        {{
            "parsed_sections": {{
                "summary": "string",  // Brief professional summary
                "contact": {{
                    "name": "string",
                    "email": "string",
                    "phone": "string",
                    "location": "string"
                }}
            }},
            "skills": [
                {{
                    "name": "string",  // Skill name
                    "proficiency": "string",  // Expert, Intermediate, Beginner
                    "context": "string"  // Where/how this skill was used
                }}
            ],
            "experience": [
                {{
                    "role": "string",  // Job title
                    "company": "string",  // Company name
                    "start_date": "string",  // Start date (YYYY-MM format)
                    "end_date": "string",  // End date or "Present"
                    "description": "string",  // Job description
                    "achievements": [  // List of accomplishments
                        "string"
                    ]
                }}
            ],
            "education": [
                {{
                    "institution": "string",  // School/university name
                    "degree": "string",  // Degree type (e.g., Bachelor of Science)
                    "field_of_study": "string",  // Major
                    "start_date": "string",  // Start date (YYYY-MM format)
                    "end_date": "string",  // End date (YYYY-MM format)
                    "gpa": "string"  // GPA if mentioned
                }}
            ],
            "projects": [
                {{
                    "name": "string",  // Project title
                    "description": "string",  // Brief description
                    "technologies": [  // Technologies used
                        "string"
                    ],
                    "url": "string"  // Project link if available
                }}
            ],
            "certifications": [
                {{
                    "name": "string",  // Certification name
                    "issuer": "string",  // Issuing organization
                    "date": "string",  // Date obtained
                    "expires": "string"  // Expiration date if applicable
                }}
            ],
            "achievements": [
                {{
                    "description": "string"  // Achievement description
                }}
            ]
        }}
        
        If a field isn't present in the resume, use empty strings for required text fields, empty arrays for lists, and null for optional fields.
        """
        
        response = await self.call_gemini(prompt)
        print(response)
        """if isinstance(response, str):
            try:
                return json.loads(response)
            except:
                return {
                    "parsed_sections": {},
                    "skills": [],
                    "experience": [],
                    "education": [],
                    "projects": [],
                    "certifications": [],
                    "achievements": []
                }"""
        return response

    async def parse_job_description(self, text: str) -> Dict[str, Any]:
        prompt = f"""
        Extract the following information from this job description in JSON format:
        
        Job Description:
        {text}
        
        Return only a valid JSON object with the following structure:
        {{
            "title": "string",  // Job title
            "required_skills": [
                {{
                    "name": "string",  // Skill name
                    "importance": float  // Value between 0-1, default to 1.0 if not specified
                }}
            ],
            "preferred_skills": [
                {{
                    "name": "string",  // Skill name
                    "importance": float  // Value between 0-1, default to 0.5 if not specified
                }}
            ],
            "responsibilities": [  // List of job responsibilities
                "string"
            ],
            "qualifications": [  // List of job qualifications/requirements
                "string"
            ]
        }}
        
        For importance values: assign 1.0 for critical skills, 0.8 for very important skills, 0.6 for important skills. For preferred skills, use 0.5 for nice-to-have skills, and 0.3 for bonus skills.
        
        If a field isn't present, return an empty array. All specified fields must be present in the response.
        """
        
        response = await self.call_gemini(prompt)
        if isinstance(response, str):
            try:
                return json.loads(response)
            except:
                return {
                    "title": "Untitled Job",
                    "required_skills": [],
                    "preferred_skills": [],
                    "responsibilities": [],
                    "qualifications": []
                }
        return response

    async def calculate_match_score(
        self, 
        resume_data: Dict[str, Any], 
        job_data: Dict[str, Any],
    ) -> Tuple[float, Dict[str, Any]]:
        prompt=f"""
        Analyze how well this resume matches the job description.

        Resume:
        {json.dumps(resume_data)}

        Job Description:
        {json.dumps(job_data)}

        Return ONLY a JSON object with this exact structure, the values given are only for demonstration:
        {{
          "overall_match": 75.5,
          "sections": {{
            "skills": {{
              "score": 80.0,
              "required": {{
                "matched": ["Python", "SQL"],
                "missing": ["Kubernetes"],
                "match_rate": 66.7
              }},
              "preferred": {{
                "matched": ["Docker"],
                "missing": ["AWS", "GraphQL"],
                "match_rate": 33.3
              }}
            }},
            "experience": {{
              "score": 70.0,
              "matching_aspects": ["Backend development", "Team leadership"],
              "missing_aspects": ["Enterprise architecture", "CI/CD pipelines"],
              "experience_entries": [
                {{
                  "role": "Software Engineer",
                  "company": "Tech Corp",
                  "match_percentage": 75.0,
                  "matching_terms": ["Python", "development", "leadership"]
                }}
              ]
            }},
            "education": {{
              "score": 85.0,
              "matching_aspects": ["Bachelor's degree in Computer Science"],
              "missing_aspects": [],
              "highest_education": "bachelor"
            }}
          }},
          "weights_applied": {{
            "skills": 0.6,
            "experience": 0.3,
            "education": 0.1
          }}
        }}

        Ensure all fields are present with default values if needed (empty arrays, 0.0 for numbers). 
        For highest_education, use one of: "high school", "associate", "bachelor", "master", "phd", or null if unknown.
        Calculate overall_match as the weighted average of section scores.
        """
        
        response = await self.call_gemini(prompt)
        
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except:
                response = {
                    "overall_match": 0.0,
                    "sections": {
                        "skills": {
                            "score": 0.0,
                            "required": {
                                "matched": [],
                                "missing": [],
                                "match_rate": 0.0
                            },
                            "preferred": {
                                "matched": [],
                                "missing": [],
                                "match_rate": 0.0
                            }
                        },
                        "experience": {
                            "score": 0.0,
                            "matching_aspects": [],
                            "missing_aspects": [],
                            "experience_entries": []
                        },
                        "education": {
                            "score": 0.0,
                            "matching_aspects": [],
                            "missing_aspects": [],
                            "highest_education": None
                        }
                    },
                    "weights_applied": {
                        "skills": 0.6,
                        "experience": 0.3,
                        "education": 0.1
                    }
                }
        
        if not isinstance(response, dict):
            response = {}
        
        overall_match = response.get("overall_match", 0.0)
        
        return overall_match, response

    async def generate_resume_feedback(
        self, 
        resume_data: Dict[str, Any], 
        job_data: Dict[str, Any],
        match_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        missing_required_skills = []
        missing_preferred_skills = []
        missing_responsibilities = []
        education_gaps = []
        
        try:
            if "sections" in match_details:
                if "skills" in match_details["sections"]:
                    if "required" in match_details["sections"]["skills"]:
                        missing_required_skills = match_details["sections"]["skills"]["required"].get("missing", [])
                    if "preferred" in match_details["sections"]["skills"]:
                        missing_preferred_skills = match_details["sections"]["skills"]["preferred"].get("missing", [])
                if "experience" in match_details["sections"]:
                    missing_responsibilities = match_details["sections"]["experience"].get("missing_aspects", [])
                if "education" in match_details["sections"]:
                    education_gaps = match_details["sections"]["education"].get("missing_aspects", [])
        except Exception as e:
            print(f"Error extracting from match details: {str(e)}")
        
        strengths = []
        improvements = []
        keywords = []
        
        try:
            if "sections" in match_details:
                if "skills" in match_details["sections"]:
                    if "required" in match_details["sections"]["skills"]:
                        for skill in match_details["sections"]["skills"]["required"].get("matched", []):
                            strengths.append(f"You have the required skill: {skill}")
                    if "preferred" in match_details["sections"]["skills"]:
                        for skill in match_details["sections"]["skills"]["preferred"].get("matched", []):
                            strengths.append(f"You have the preferred skill: {skill}")
                if "experience" in match_details["sections"]:
                    if match_details["sections"]["experience"].get("score", 0) > 50:
                        strengths.append("Your experience aligns well with job responsibilities")
                if "education" in match_details["sections"]:
                    if match_details["sections"]["education"].get("score", 0) > 50:
                        strengths.append("Your educational background matches the job requirements")
        except Exception as e:
            print(f"Error building strengths from match details: {str(e)}")
        
        for skill in missing_required_skills:
            improvements.append(f"Add the required skill: {skill}")
            keywords.append(skill)
        
        for skill in missing_preferred_skills[:3]: 
            improvements.append(f"Consider adding the preferred skill: {skill}")
            keywords.append(skill)
        
        for resp in missing_responsibilities[:3]: 
            improvements.append(f"Highlight experience related to: {resp}")
            for word in resp.split():
                if len(word) > 4:
                    keywords.append(word)
        
        for qual in education_gaps[:2]: 
            improvements.append(f"Address this qualification: {qual}")
        
        prompt = f"""
        Based on the job match analysis below, provide constructive feedback to improve the resume:
        
        Match Score: {match_details.get('overall_match', 0):.1f}%
        
        Initial Strengths:
        {json.dumps(strengths)}
        
        Initial Improvement Areas:
        {json.dumps(improvements)}
        
        Missing Skills:
        {json.dumps(missing_required_skills + missing_preferred_skills[:3])}
        
        Important Keywords:
        {json.dumps(list(set(keywords)))}
        
        Please provide personalized feedback in JSON format with these fields:
        {{
            "strengths": [
                "String describing a specific strength"
            ],
            "improvements": [
                "String describing a specific, actionable improvement"
            ],
            "missing_skills": [
                "Name of missing skill"
            ],
            "keyword_recommendations": [
                "Keyword to add to resume"
            ]
        }}
        
        Provide 3-5 items in each list. Be specific and actionable in your recommendations.
        """
        
        response = await self.call_gemini(prompt)
        
        if isinstance(response, str):
            try:
                response_json = json.loads(response)
                return response_json
            except json.JSONDecodeError:
                pass
        elif isinstance(response, dict) and not response.get("error"):
            return response
        
        return {
            "strengths": strengths[:5],
            "improvements": improvements[:5],
            "missing_skills": missing_required_skills + missing_preferred_skills[:3],
            "keyword_recommendations": list(set(keywords))[:10]
        }


class ResumeService:
    def __init__(self, ai_service: AIService):
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        self.ai_service = ai_service
        
    async def process_resume_file(self, file: UploadFile) -> Dict[str, Any]:
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):
                await out_file.write(content)
        
        if file_extension.lower() == '.pdf':
            text=await self.ai_service.extract_resume_from_pdf(file_path)
            structured_text = text
        elif file_extension.lower() == '.docx':
            text = await self._extract_text_from_docx(file_path)
            structured_text = text
        else:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                text = await f.read()
            structured_text = text
        
        parsed_data = await self.ai_service.parse_resume(text)
        
        return {
            "file_path": file_path,
            "file_type": file_extension.lower().replace('.', ''),
            "full_text": text,
            "structured_text": structured_text,
            "parsed_data": parsed_data,
        }
    
    async def process_resume_text(self, text: str) -> Dict[str, Any]:
        parsed_data = await self.ai_service.parse_resume(text)
        
        return {
            "file_path": None,
            "file_type": "txt",
            "full_text": text,
            "structured_text": text,
            "parsed_data": parsed_data,
        }
    
    async def _extract_text_from_pdf(self, file_path: str) -> str:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    async def _extract_text_from_docx(self, file_path: str) -> str:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)

    async def create_resume(self, db: AsyncSession, user_id: int, resume_data: Dict[str, Any]) -> ResumeModel:
        resume = ResumeModel(
            user_id=user_id,
            full_text=resume_data["full_text"],
            parsed_sections=resume_data["parsed_data"],
            skills=resume_data["parsed_data"].get("skills", []),
            experience=resume_data["parsed_data"].get("experience", []),
            education=resume_data["parsed_data"].get("education", []),
            projects=resume_data["parsed_data"].get("projects", []),
            certifications=resume_data["parsed_data"].get("certifications", []),
            achievements=resume_data["parsed_data"].get("achievements", []),
            file_path=resume_data["file_path"],
            file_type=resume_data["file_type"]
        )
        
        db.add(resume)
        await db.commit()
        await db.refresh(resume)
        return resume
    
    async def get_resumes(self, db: AsyncSession, user_id: int, is_recruiter: bool, skip: int = 0, limit: int = 100) -> List[ResumeModel]:
        if is_recruiter:
            result = await db.execute(select(ResumeModel).offset(skip).limit(limit))
        else:
            result = await db.execute(select(ResumeModel).where(ResumeModel.user_id == user_id).offset(skip).limit(limit))
        
        return result.scalars().all()
    
    async def get_resume(self, db: AsyncSession, resume_id: int) -> Optional[ResumeModel]:
        result = await db.execute(select(ResumeModel).where(ResumeModel.id == resume_id))
        return result.scalars().first()
    
    async def delete_resume(self, db: AsyncSession, resume_id: int) -> bool:
        resume = await self.get_resume(db, resume_id)
        if resume:
            if resume.file_path and os.path.exists(resume.file_path):
                os.remove(resume.file_path)
            
            await db.execute(delete(ResumeModel).where(ResumeModel.id == resume_id))
            await db.commit()
            return True
        return False


class JobService:
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        
    async def process_job_description(self, text: str) -> Dict[str, Any]:
        parsed_data = await self.ai_service.parse_job_description(text)
        
        return {
            "description_text": text,
            "parsed_data": parsed_data,
        }
    
    async def create_job(self, db: AsyncSession, user_id: int, job_data: Dict[str, Any], job_in: Dict[str, Any]) -> JobModel:
        job = JobModel(
            company_id=user_id,
            title=job_in.get("title") or job_data["parsed_data"].get("title", "Untitled Job"),
            description_text=job_data["description_text"],
            required_skills=job_data["parsed_data"].get("required_skills", []),
            preferred_skills=job_data["parsed_data"].get("preferred_skills", []),
            responsibilities=job_data["parsed_data"].get("responsibilities", []),
            qualifications=job_data["parsed_data"].get("qualifications", []),
            priority_weights=job_in.get("priority_weights") or {"skills": 0.6, "experience": 0.3, "education": 0.1}
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job
    
    async def get_jobs(self, db: AsyncSession, user_id: int, is_recruiter: bool, skip: int = 0, limit: int = 100) -> List[JobModel]:
        if is_recruiter:
            result = await db.execute(select(JobModel).where(JobModel.company_id == user_id).offset(skip).limit(limit))
        else:
            result = await db.execute(select(JobModel).offset(skip).limit(limit))
        
        return result.scalars().all()
    
    async def get_job(self, db: AsyncSession, job_id: int) -> Optional[JobModel]:
        result = await db.execute(select(JobModel).where(JobModel.id == job_id))
        return result.scalars().first()
    
    async def update_job(self, db: AsyncSession, job_id: int, job_data: Dict[str, Any]) -> Optional[JobModel]:
        job = await self.get_job(db, job_id)
        if job:
            for key, value in job_data.items():
                setattr(job, key, value)
            
            await db.commit()
            await db.refresh(job)
            return job
        return None
    
    async def delete_job(self, db: AsyncSession, job_id: int) -> bool:
        job = await self.get_job(db, job_id)
        if job:
            await db.execute(delete(JobModel).where(JobModel.id == job_id))
            await db.commit()
            return True
        return False


class MatchingService:
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        
    async def match_resume_to_job(
        self, 
        resume_data: Dict[str, Any], 
        job_data: Dict[str, Any],
    ) -> Tuple[float, Dict[str, Any], Dict[str, Any]]:
        score, match_details = await self.ai_service.calculate_match_score(
            resume_data, 
            job_data,
        )
        
        feedback = await self.ai_service.generate_resume_feedback(resume_data, job_data, match_details)
        
        return score, match_details, feedback
    
    async def create_application(
        self, 
        db: AsyncSession, 
        application_data: Dict[str, Any], 
        match_score: float,
        match_details: Dict[str, Any],
        feedback: Dict[str, Any]
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
            status="New"
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
        job_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[ApplicationModel]:
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
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_application(self, db: AsyncSession, application_id: int) -> Optional[Tuple[ApplicationModel, JobModel, ResumeModel]]:
        query = select(ApplicationModel, JobModel, ResumeModel) \
            .join(JobModel, ApplicationModel.job_id == JobModel.id) \
            .join(ResumeModel, ApplicationModel.resume_id == ResumeModel.id) \
            .where(ApplicationModel.id == application_id)
        
        result = await db.execute(query)
        row = result.first()
        
        if row:
            return row
        return None
    
    async def update_application_status(
        self, 
        db: AsyncSession, 
        application_id: int, 
        status: str
    ) -> Optional[ApplicationModel]:
        application = await db.get(ApplicationModel, application_id)
        if application:
            application.status = status
            if status != "New":
                application.reviewed_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(application)
            return application
        return None


class UserService:
    async def create_user(self, db: AsyncSession, user_data: Dict[str, Any], hashed_password: str) -> UserModel:
        user = UserModel(
            email=user_data["email"],
            hashed_password=hashed_password,
            full_name=user_data.get("full_name", ""),
            is_recruiter=user_data.get("is_recruiter", False)
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[UserModel]:
        result = await db.execute(select(UserModel).where(UserModel.email == email))
        return result.scalars().first()
    
    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[UserModel]:
        return await db.get(UserModel, user_id)


ai_service = AIService()
resume_service = ResumeService(ai_service)
job_service = JobService(ai_service)
matching_service = MatchingService(ai_service)
user_service = UserService()