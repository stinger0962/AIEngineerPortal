"""AI Resume Builder endpoint."""
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import User, AIFeedback
from app.schemas.portal import ResumeInput, ResumeOutput
from app.services.ai_service import AIService
from app.services.adaptive_service import build_mastery_profile
from app.services.learning_service import list_paths
from app.core.config import get_settings

router = APIRouter(prefix="/resume", tags=["resume"])


def _get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1)) or 1


@router.post("/generate", response_model=ResumeOutput)
def generate_resume(
    payload: ResumeInput,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    svc = AIService()

    if not svc.is_available:
        raise HTTPException(503, "AI not available")

    user_id = _get_user_id(db)

    # Gather portal learning data if requested
    portal_context = ""
    if payload.include_portal_data:
        mastery = build_mastery_profile(db)
        paths = list_paths(db, user_id)

        portal_context = "\n## Portal Learning Data\n"
        portal_context += f"Learning paths completed: {sum(1 for p in paths if p.get('completion_pct', 0) >= 80)}/{len(paths)}\n"
        for p in paths:
            portal_context += f"- {p.get('title', '')}: {p.get('completion_pct', 0)}% complete\n"

        portal_context += "\nMastery scores:\n"
        for m in mastery:
            portal_context += f"- {m.get('area_title', '')}: {m.get('mastery_score', 0)}/100\n"

    # Build prompt
    system = (
        "You are a professional resume writer specializing in AI engineering roles. "
        "Generate a polished, ATS-friendly resume in markdown format.\n\n"
        "## Guidelines\n"
        "- Target role: AI Engineer (application-level, not ML research)\n"
        "- Emphasize: agent orchestration, RAG systems, LLM integration, evaluation, deployment\n"
        "- Use action verbs and quantify impact where possible\n"
        "- Keep it concise (1-2 pages when printed)\n"
        "- Include a strong professional summary\n"
        "- Skills section should highlight AI engineering tools and patterns\n"
        "- Projects should tell a story: what, why, how, impact\n\n"
        "## Output format\n"
        "Return valid JSON with these fields:\n"
        '{"summary": "professional summary paragraph", '
        '"skills": ["skill1", "skill2"], '
        '"work_experience": [{"company": "", "role": "", "dates": "", "bullets": ["..."]}], '
        '"projects": [{"title": "", "description": "", "tech_stack": [""], "impact": ""}], '
        '"education": [{"school": "", "degree": "", "year": ""}], '
        '"certifications": ["..."], '
        '"ai_engineering_highlights": ["achievement from learning data"], '
        '"resume_md": "full resume as clean markdown"}'
    )

    user_msg = f"Generate a resume for this AI engineer candidate:\n\n"
    user_msg += f"Name: {payload.full_name}\n"
    user_msg += f"Target Role: {payload.target_role}\n"
    user_msg += f"Years of Experience: {payload.years_experience}\n"
    user_msg += f"Current Role: {payload.current_role}\n"

    if payload.summary_override:
        user_msg += f"\nCustom Summary: {payload.summary_override}\n"

    if payload.work_experience:
        user_msg += "\n## Work Experience\n"
        for exp in payload.work_experience:
            user_msg += f"- {exp.get('role', '')} at {exp.get('company', '')} ({exp.get('dates', '')})\n"
            for bullet in exp.get('bullets', []):
                user_msg += f"  - {bullet}\n"

    if payload.education:
        user_msg += "\n## Education\n"
        for edu in payload.education:
            user_msg += f"- {edu.get('degree', '')} from {edu.get('school', '')} ({edu.get('year', '')})\n"

    if payload.projects_override:
        user_msg += "\n## Additional Projects\n"
        for proj in payload.projects_override:
            user_msg += f"- {proj.get('title', '')}: {proj.get('description', '')}\n"

    if payload.skills_override:
        user_msg += f"\n## Additional Skills\n{', '.join(payload.skills_override)}\n"

    user_msg += portal_context

    import time, json, anthropic
    start = time.time()
    try:
        response = svc.client.messages.create(
            model=svc.model,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
    except (anthropic.APITimeoutError, anthropic.APIConnectionError):
        raise HTTPException(502, "Resume generation failed — try again")

    latency_ms = int((time.time() - start) * 1000)
    raw = response.content[0].text

    # Parse JSON
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(502, "Failed to parse resume — try again")

    # Track cost
    feedback = AIFeedback(
        user_id=user_id,
        feature="resume",
        reference_id=None,
        user_input_hash=None,
        prompt_template=system[:200],
        response_json=data,
        model=svc.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        latency_ms=latency_ms,
    )
    db.add(feedback)
    db.commit()

    return ResumeOutput(
        summary=data.get("summary", ""),
        skills=data.get("skills", []),
        work_experience=data.get("work_experience", []),
        projects=data.get("projects", []),
        education=data.get("education", []),
        certifications=data.get("certifications", []),
        ai_engineering_highlights=data.get("ai_engineering_highlights", []),
        resume_md=data.get("resume_md", ""),
        model=svc.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
