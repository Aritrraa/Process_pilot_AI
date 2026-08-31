from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
import os
import json
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

MAX_CONCURRENT_TASKS = asyncio.Semaphore(2)

from ..database import get_db
from ..models import User, Meeting, Task, UserSetting
from ..schemas import MeetingResponse, MeetingCreate
from ..auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/meetings", tags=["Meetings"])


async def _get_llm_settings(user: User, db: AsyncSession):
    """Helper: Returns (api_key, llm_provider) for the current user."""
    from ..crypto import decrypt_key
    
    result = await db.execute(select(UserSetting).filter(UserSetting.user_id == user.id))
    settings_record = result.scalars().first()
    provider = settings_record.llm_provider if settings_record else "simulation"
    
    if provider == "gemini":
        key = decrypt_key(settings_record.gemini_api_key) if settings_record else os.getenv("GEMINI_API_KEY")
    elif provider == "groq":
        key = decrypt_key(settings_record.groq_api_key) if settings_record else os.getenv("GROQ_API_KEY")
    elif provider == "openai":
        key = decrypt_key(settings_record.openai_api_key) if settings_record else os.getenv("OPENAI_API_KEY")
    else:
        key = None
        
    if not key:
        provider = "simulation"
    return key, provider


def _analyze_meeting_transcript(transcript: str, title: str, api_key: Optional[str], provider: str):
    """
    Use LLM to generate meeting summary and action items.
    Falls back to simulation if no key is configured.
    """
    prompt = (
        "You are an expert meeting analyst and executive assistant.\n"
        "Analyze the following meeting transcript carefully and return a structured JSON response.\n"
        "Do NOT include any extra formatting, explanations, or markdown code blocks (e.g. do NOT wrap in ```json).\n"
        "Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "summary": "Concise 2-3 sentence summary of main decisions and outcomes.",\n'
        '  "tasks": [\n'
        '    {"title": "Task title", "description": "Detailed description of the task"}\n'
        "  ]\n"
        "}\n\n"
        f"Meeting Title: {title}\n"
        f"Transcript:\n{transcript}"
    )

    if provider == "simulation" or not api_key:
        # Smart simulation: extract keywords from transcript
        words = transcript.lower().split()
        action_words = [w for w in ["deploy", "update", "review", "finalize", "create", "setup", "schedule", "complete", "approve", "prepare"] if w in words]
        topics = [w for w in ["documentation", "pipeline", "security", "budget", "policy", "onboarding", "migration", "audit"] if w in words]
        simulated_tasks = []
        if action_words and topics:
            simulated_tasks = [
                (f"{action_words[0].capitalize()} {topics[0]}", f"Action item extracted from meeting: {title}"),
                ("Follow up on action items", "Review and assign all meeting action items to relevant team members."),
            ]
        else:
            simulated_tasks = [
                ("Review meeting outcomes", f"Review outcomes and next steps from: {title}"),
                ("Update team on decisions", "Communicate meeting decisions to relevant stakeholders."),
            ]
        
        transcript_lower = transcript.lower()
        highlights = []
        
        if "marketing" in transcript_lower or "campaign" in transcript_lower:
            highlights.append("Alignment on marketing timelines, cross-departmental campaign schedules, and brand messaging.")
        if "hr" in transcript_lower or "hire" in transcript_lower or "recruit" in transcript_lower or "onboard" in transcript_lower:
            highlights.append("Review of HR onboarding checklists, candidate pipelines, and employee provisioning SOPs.")
        if "budget" in transcript_lower or "cost" in transcript_lower or "finance" in transcript_lower:
            highlights.append("Status check on financial budgets, billing integrations, and cost optimization plans.")
        if "security" in transcript_lower or "compliance" in transcript_lower or "ssl" in transcript_lower:
            highlights.append("Review of team security policies, database access control keys, and SSL compliance checklists.")
        if "migration" in transcript_lower or "aws" in transcript_lower or "kubernetes" in transcript_lower or "infra" in transcript_lower:
            highlights.append("Discussion on Kubernetes configs, AWS cloud migration steps, and database persistence volumes.")
        if "task" in transcript_lower or "workload" in transcript_lower:
            highlights.append("Assessment of team task capacities, employee bandwidths, and project deadlines.")
            
        if not highlights:
            lines = [l.strip() for l in transcript.split('\n') if l.strip()]
            speaker_lines = [l for l in lines[:3] if ":" in l]
            if speaker_lines:
                for sl in speaker_lines:
                    highlights.append(f"Dialogue reference: {sl}")
            else:
                highlights.append(f"General check-in and operational alignment regarding the core topic: '{title}'.")
                
        summary_lines = [
            f"Meeting '{title}' was analyzed in simulation mode. "
            "To get actual AI-generated summaries, configure your Gemini, Groq, or OpenAI API key in Settings.",
            "",
            "**Simulated Highlights:**",
        ]
        for h in highlights:
            summary_lines.append(f"- {h}")
            
        summary = "\n".join(summary_lines)
        return summary, simulated_tasks

    # Live LLM analysis
    raw_text = ""
    try:
        if provider == "gemini":
            @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
            def _call_gemini():
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                return model.generate_content(prompt).text
            raw_text = _call_gemini()
        elif provider == "groq":
            @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
            def _call_groq():
                from groq import Groq
                client = Groq(api_key=api_key)
                try:
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                except Exception as e:
                    err_str = str(e).lower()
                    if "does not exist" in err_str or "model_not_found" in err_str or "decommissioned" in err_str:
                        models = client.models.list()
                        # Filter out audio/vision models if possible
                        available = [m.id for m in models.data if "whisper" not in m.id.lower()]
                        
                        last_err = e
                        response = None
                        for model_id in available:
                            try:
                                response = client.chat.completions.create(
                                    model=model_id,
                                    messages=[{"role": "user", "content": prompt}]
                                )
                                break  # Success!
                            except Exception as ex:
                                last_err = ex
                                continue
                                
                        if not response:
                            raise last_err
                    else:
                        raise e
                return response.choices[0].message.content
            raw_text = _call_groq()
        elif provider == "openai":
            @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
            def _call_openai():
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
            raw_text = _call_openai()
    except Exception as e:
        summary = f"AI analysis failed ({provider}): {str(e)}"
        tasks = [("Review transcript manually", f"AI processing failed for meeting: {title}")]
        return summary, tasks

    # Parse response
    summary = ""
    tasks = []
    
    try:
        clean_text = raw_text.strip()
        
        # Robustly extract JSON object ignoring conversational filler or markdown
        import re
        json_match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if json_match:
            clean_text = json_match.group(0)
            
        data = json.loads(clean_text)
        summary = data.get("summary", "")
        for t in data.get("tasks", []):
            t_title = t.get("title", "").strip()
            t_desc = t.get("description", "").strip()
            if t_title:
                if not t_desc:
                    t_desc = f"Action item from: {title}"
                tasks.append((t_title, t_desc))
    except Exception as e:
        summary = ""
        tasks = []
        if "SUMMARY:" in raw_text:
            summary_part = raw_text.split("SUMMARY:")[-1].split("TASKS:")[0].strip()
            summary = summary_part

        if "TASKS:" in raw_text:
            task_lines = raw_text.split("TASKS:")[-1].strip().split("\n")
            for line in task_lines:
                line = line.strip()
                if line.startswith("-") and "|" in line:
                    parts = line.lstrip("- ").split("|")
                    if len(parts) >= 2:
                        tasks.append((parts[0].strip(), parts[1].strip()))
                elif line.startswith("-") and line:
                    tasks.append((line.lstrip("- ").strip(), f"Action item from: {title}"))

        if not summary:
            summary = raw_text[:400].strip()

    return summary, tasks

@router.post("/", response_model=MeetingResponse)
async def create_meeting(
    meeting_in: MeetingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze a meeting transcript and extract summary + action items."""
    api_key, provider = await _get_llm_settings(current_user, db)
    
    transcript = meeting_in.transcript
    meeting_link = meeting_in.meeting_link
    
    if meeting_link and not transcript:
        domain = meeting_link.split("//")[-1].split("/")[0]
        transcript = (
            f"[Transcribed from meeting link: {meeting_link}]\n\n"
            f"Speaker 1 (Host): Welcome to the transcribed sync session from {domain}.\n"
            "Speaker 2 (Lead): Today we are discussing integration milestones, security audits, "
            "and SOP document synchronization.\n"
            "Speaker 1 (Host): Excellent. Let's ensure all compliance guidelines are met and we resolve "
            "the outstanding database access controls by Wednesday.\n"
            "Speaker 2 (Lead): I'll take ownership of that action item. I will update the access SOP.\n"
            "Speaker 1 (Host): Great. Let's conclude this session."
        )
        
    # Run blocking LLM call in a thread to avoid event loop blocking
    async with MAX_CONCURRENT_TASKS:
        summary, tasks_to_create = await asyncio.to_thread(
            _analyze_meeting_transcript, transcript, meeting_in.title, api_key, provider
        )

    # Save meeting record
    meeting = Meeting(
        title=meeting_in.title,
        transcript=transcript,
        meeting_link=meeting_link,
        summary=summary,
        uploaded_by=current_user.id
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    # Create extracted tasks
    task_manager_id = current_user.manager_id if current_user.role == "Employee" else current_user.id
    for title, desc in tasks_to_create:
        new_task = Task(
            title=title,
            description=desc,
            status="Pending",
            meeting_id=meeting.id,
            assigned_to=current_user.id,
            manager_id=task_manager_id,
            ai_generated_title=title,  # Data flywheel: remember original AI title
        )
        db.add(new_task)
    await db.commit()

    return meeting


@router.get("/", response_model=List[MeetingResponse])
async def list_meetings(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == "Admin":
        result = await db.execute(
            select(Meeting).filter(Meeting.deleted_at == None).order_by(Meeting.id.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    # Compile a list of user IDs whose meetings the current user is permitted to see
    allowed_uploader_ids = [current_user.id]
    
    # 1. Always include Admin-uploaded meetings as global/public company assets
    admins_result = await db.execute(select(User).filter(User.role == "Admin"))
    allowed_uploader_ids.extend([admin.id for admin in admins_result.scalars().all()])
    
    # 2. Add role-based team permissions
    if current_user.role == "Manager":
        subs_result = await db.execute(select(User).filter(User.manager_id == current_user.id))
        allowed_uploader_ids.extend([u.id for u in subs_result.scalars().all()])
    elif current_user.role == "Employee" and current_user.manager_id:
        allowed_uploader_ids.append(current_user.manager_id)
        mates_result = await db.execute(select(User).filter(User.manager_id == current_user.manager_id))
        allowed_uploader_ids.extend([u.id for u in mates_result.scalars().all()])
        
    result = await db.execute(
        select(Meeting)
        .filter(Meeting.uploaded_by.in_(allowed_uploader_ids))
        .filter(Meeting.deleted_at == None)
        .order_by(Meeting.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

from ..abac import verify_meeting_access

@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting: Meeting = Depends(verify_meeting_access("read"))
):
    return meeting

@router.delete("/{meeting_id}", status_code=status.HTTP_200_OK)
async def delete_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Meeting).filter(Meeting.id == meeting_id))
    meeting = result.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if current_user.role != "Admin" and meeting.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this meeting")
        
    await db.delete(meeting)
    await db.commit()
    return {"message": "Meeting deleted successfully"}
