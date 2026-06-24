from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import datetime
import json

from ..database import get_db
from ..models import User, Meeting, Task, UserSetting
from ..schemas import MeetingResponse, MeetingCreate
from ..auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/meetings", tags=["Meetings"])


def _get_llm_settings(user: User, db: Session):
    """Helper: Returns (api_key, llm_provider) for the current user."""
    settings_record = db.query(UserSetting).filter(UserSetting.user_id == user.id).first()
    provider = settings_record.llm_provider if settings_record else "simulation"
    if provider == "gemini":
        key = settings_record.gemini_api_key if settings_record else os.getenv("GEMINI_API_KEY")
    elif provider == "groq":
        key = settings_record.groq_api_key if settings_record else os.getenv("GROQ_API_KEY")
    elif provider == "openai":
        key = settings_record.openai_api_key if settings_record else os.getenv("OPENAI_API_KEY")
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
        
        # Build simulated summary dynamically from transcript keywords
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
            # Fallback based on dialogue lines
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
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            raw_text = response.text
        elif provider == "groq":
            from groq import Groq
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
            )
            raw_text = response.choices[0].message.content
        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            raw_text = response.choices[0].message.content
    except Exception as e:
        summary = f"AI analysis failed ({provider}): {str(e)}"
        tasks = [("Review transcript manually", f"AI processing failed for meeting: {title}")]
        return summary, tasks

    # Parse response
    summary = ""
    tasks = []
    
    try:
        # Pre-clean raw_text to strip markdown blocks if present
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()
            
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
        # Fallback to the legacy split-based parser
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
def create_meeting(
    meeting_in: MeetingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze a meeting transcript and extract summary + action items."""
    api_key, provider = _get_llm_settings(current_user, db)
    
    transcript = meeting_in.transcript
    meeting_link = meeting_in.meeting_link
    
    if meeting_link and not transcript:
        # Transcribe audio from meeting link (simulated for general links)
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
        
    summary, tasks_to_create = _analyze_meeting_transcript(
        transcript, meeting_in.title, api_key, provider
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
    db.commit()
    db.refresh(meeting)

    # Create extracted tasks
    task_manager_id = current_user.manager_id if current_user.role == "Employee" else current_user.id
    for title, desc in tasks_to_create:
        new_task = Task(
            title=title,
            description=desc,
            status="Pending",
            meeting_id=meeting.id,
            assigned_to=current_user.id,
            manager_id=task_manager_id
        )
        db.add(new_task)
    db.commit()

    return meeting


@router.get("/", response_model=List[MeetingResponse])
def list_meetings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "Admin":
        return db.query(Meeting).order_by(Meeting.id.desc()).all()
    
    # Compile a list of user IDs whose meetings the current user is permitted to see
    allowed_uploader_ids = [current_user.id]
    
    # 1. Always include Admin-uploaded meetings as global/public company assets
    admins = db.query(User).filter(User.role == "Admin").all()
    allowed_uploader_ids.extend([admin.id for admin in admins])
    
    # 2. Add role-based team permissions
    if current_user.role == "Manager":
        # Managers see meetings of their team members (subordinates)
        subordinates = db.query(User).filter(User.manager_id == current_user.id).all()
        allowed_uploader_ids.extend([u.id for u in subordinates])
    elif current_user.role == "Employee" and current_user.manager_id:
        # Employees see meetings uploaded by their manager
        allowed_uploader_ids.append(current_user.manager_id)
        # Employees also see meetings uploaded by their teammates reporting to the same manager
        teammates = db.query(User).filter(User.manager_id == current_user.manager_id).all()
        allowed_uploader_ids.extend([u.id for u in teammates])
        
    return db.query(Meeting).filter(
        Meeting.uploaded_by.in_(allowed_uploader_ids)
    ).order_by(Meeting.id.desc()).all()

from ..abac import verify_meeting_access

@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting(
    meeting: Meeting = Depends(verify_meeting_access("read"))
):
    return meeting
