from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, distinct
from typing import Dict, Any, List
import datetime
from .models import User, Document, Task, AgentLog, Department, LLMUsage


async def get_system_analytics(db: AsyncSession, current_user: User = None) -> Dict[str, Any]:
    # 1. Resolve scoping based on role
    role = current_user.role if current_user else "Employee"
    scoped_usage = []

    if not current_user or role == "Admin":
        r_users = await db.execute(select(User))
        scoped_users = r_users.scalars().all()
        r_docs = await db.execute(select(Document))
        scoped_docs = r_docs.scalars().all()
        r_tasks = await db.execute(select(Task))
        scoped_tasks = r_tasks.scalars().all()
        r_logs = await db.execute(select(AgentLog))
        scoped_logs = r_logs.scalars().all()
        r_usage = await db.execute(select(LLMUsage))
        scoped_usage = r_usage.scalars().all()
    else:
        # Determine team user IDs
        if role in ("Manager", "Director"):
            r_subs = await db.execute(select(User).filter(User.manager_id == current_user.id))
            subordinates = r_subs.scalars().all()
            scoped_users = [current_user] + list(subordinates)
        else:  # Employee
            if current_user.manager_id:
                r_mates = await db.execute(select(User).filter(User.manager_id == current_user.manager_id))
                teammates = r_mates.scalars().all()
                r_mgr = await db.execute(select(User).filter(User.id == current_user.manager_id))
                manager = r_mgr.scalars().first()
                scoped_users = list(set([current_user] + list(teammates) + ([manager] if manager else [])))
            else:
                scoped_users = [current_user]

        user_ids = [u.id for u in scoped_users]
        dept_ids = list(set([u.department_id for u in scoped_users if u.department_id is not None]))

        # Scoped documents
        if dept_ids:
            r_docs = await db.execute(
                select(Document).filter(
                    (Document.department_id.in_(dept_ids)) | (Document.uploaded_by.in_(user_ids))
                )
            )
        else:
            r_docs = await db.execute(select(Document).filter(Document.uploaded_by.in_(user_ids)))
        scoped_docs = r_docs.scalars().all()

        r_tasks = await db.execute(select(Task).filter(Task.assigned_to.in_(user_ids)))
        scoped_tasks = r_tasks.scalars().all()

        r_logs = await db.execute(select(AgentLog).filter(AgentLog.user_id.in_(user_ids)))
        scoped_logs = r_logs.scalars().all()

        r_usage = await db.execute(select(LLMUsage).filter(LLMUsage.user_id.in_(user_ids)))
        scoped_usage = r_usage.scalars().all()

    # Calculate metrics
    total_users = len(scoped_users)
    total_docs = len(scoped_docs)
    total_tasks = len(scoped_tasks)
    total_logs = len(scoped_logs)

    docs_by_type = {}
    for doc in scoped_docs:
        ftype = doc.file_type or "Unknown"
        docs_by_type[ftype] = docs_by_type.get(ftype, 0) + 1

    completed_tasks = sum(1 for t in scoped_tasks if t.status == "Completed")
    pending_tasks = sum(1 for t in scoped_tasks if t.status == "Pending")
    in_progress_tasks = sum(1 for t in scoped_tasks if t.status == "In_Progress")

    # Department distribution
    dept_distribution = []
    if not current_user or role == "Admin":
        r_depts = await db.execute(select(Department))
        depts = r_depts.scalars().all()
        dept_ids_for_dist = []
    else:
        if dept_ids:
            r_depts = await db.execute(select(Department).filter(Department.id.in_(dept_ids)))
            depts = r_depts.scalars().all()
        else:
            depts = []
        dept_ids_for_dist = dept_ids

    for dept in depts:
        r_uc = await db.execute(select(func.count(User.id)).filter(User.department_id == dept.id))
        u_count = r_uc.scalar()
        r_dc = await db.execute(select(func.count(Document.id)).filter(Document.department_id == dept.id))
        d_count = r_dc.scalar()
        dept_distribution.append({
            "name": dept.name,
            "users": u_count,
            "documents": d_count
        })

    # Latest logs
    latest_logs = []
    
    def get_sort_key(log):
        if not log.timestamp:
            return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        if log.timestamp.tzinfo is None:
            return log.timestamp.replace(tzinfo=datetime.timezone.utc)
        return log.timestamp

    sorted_logs = sorted(scoped_logs, key=get_sort_key, reverse=True)[:10]
    
    r_all_users = await db.execute(select(User))
    user_map = {u.id: u for u in r_all_users.scalars().all()}

    for log in sorted_logs:
        user_email = user_map[log.user_id].email if log.user_id in user_map else "Unknown"
        latest_logs.append({
            "id": log.id,
            "user": user_email,
            "query": log.query,
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "N/A"
        })

    # Documentation health
    gap_count = sum(
        1 for log in sorted_logs
        if log.response and ("no documents match" in log.response.lower() or "simulation mode" in log.response.lower())
    )
    docs_health = 100
    if len(sorted_logs) > 0:
        docs_health = max(0, int(100 - (gap_count / len(sorted_logs)) * 100))

    # Team workload
    team_workload = []
    if current_user and role in ("Manager", "Director", "Admin"):
        for member in scoped_users:
            r_p = await db.execute(select(func.count(Task.id)).filter(Task.assigned_to == member.id, Task.status == "Pending"))
            pending = r_p.scalar()
            r_ip = await db.execute(select(func.count(Task.id)).filter(Task.assigned_to == member.id, Task.status == "In_Progress"))
            in_progress = r_ip.scalar()
            r_c = await db.execute(select(func.count(Task.id)).filter(Task.assigned_to == member.id, Task.status == "Completed"))
            completed = r_c.scalar()

            r_mt = await db.execute(select(Task).filter(Task.assigned_to == member.id))
            member_tasks = r_mt.scalars().all()
            member_tasks_list = [{
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "description": t.description or ""
            } for t in member_tasks]

            team_workload.append({
                "user_id": member.id,
                "name": member.full_name or member.email,
                "email": member.email,
                "role": member.role,
                "pending": pending,
                "in_progress": in_progress,
                "completed": completed,
                "tasks": member_tasks_list
            })

    # Team details
    team_details = {}
    if current_user:
        if role in ("Manager", "Director"):
            team_members = []
            for u in scoped_users:
                r_dept = await db.execute(select(Department).filter(Department.id == u.department_id))
                u_dept = r_dept.scalars().first()
                team_members.append({
                    "id": u.id,
                    "name": u.full_name or u.email,
                    "email": u.email,
                    "role": u.role,
                    "department": u_dept.name if u_dept else "General",
                    "is_manager": u.id == current_user.id
                })
            team_details = {
                "role": role,
                "team_size": len(team_members),
                "team_members": team_members
            }
        elif role == "Admin":
            admin_teams = []
            r_mgrs = await db.execute(select(User).filter(User.role.in_(["Manager", "Director"])))
            managers = r_mgrs.scalars().all()
            total_members_count = 0
            for mgr in managers:
                r_mgr_dept = await db.execute(select(Department).filter(Department.id == mgr.department_id))
                mgr_dept = r_mgr_dept.scalars().first()
                r_subs = await db.execute(select(User).filter(User.manager_id == mgr.id))
                subordinates = r_subs.scalars().all()
                mgr_team_users = [mgr] + list(subordinates)
                members_list = []
                for u in mgr_team_users:
                    r_udept = await db.execute(select(Department).filter(Department.id == u.department_id))
                    u_dept = r_udept.scalars().first()
                    members_list.append({
                        "id": u.id,
                        "name": u.full_name or u.email,
                        "email": u.email,
                        "role": u.role,
                        "department": u_dept.name if u_dept else "General",
                        "is_manager": u.id == mgr.id
                    })
                total_members_count += len(members_list)
                admin_teams.append({
                    "manager_id": mgr.id,
                    "manager_name": mgr.full_name or mgr.email,
                    "manager_email": mgr.email,
                    "department": mgr_dept.name if mgr_dept else "General",
                    "members": members_list,
                    "team_size": len(members_list)
                })
            team_details = {
                "role": "Admin",
                "total_teams": len(admin_teams),
                "total_team_members": total_members_count,
                "teams": admin_teams
            }
        elif role == "Employee":
            team_details = {
                "role": "Employee",
                "team_size": len(scoped_users)
            }

    # LLM Usage
    total_llm_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    usage_by_provider = {}

    if not current_user or role == "Admin":
        r_llm = await db.execute(select(LLMUsage))
        llm_records = r_llm.scalars().all()
    else:
        llm_records = scoped_usage

    for u in llm_records:
        try:
            total_llm_cost += float(u.estimated_cost)
        except Exception:
            pass
        total_input_tokens += u.input_tokens
        total_output_tokens += u.output_tokens

        if u.provider not in usage_by_provider:
            usage_by_provider[u.provider] = {"cost": 0.0, "calls": 0}
        try:
            usage_by_provider[u.provider]["cost"] += float(u.estimated_cost)
        except Exception:
            pass
        usage_by_provider[u.provider]["calls"] += 1

    llm_usage = {
        "total_cost": round(total_llm_cost, 4),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "by_provider": usage_by_provider
    }

    return {
        "stats": {
            "total_users": total_users,
            "total_documents": total_docs,
            "total_tasks": total_tasks,
            "total_searches": total_logs
        },
        "docs_by_type": docs_by_type,
        "task_status": {
            "Completed": completed_tasks,
            "Pending": pending_tasks,
            "In_Progress": in_progress_tasks
        },
        "department_activity": dept_distribution,
        "latest_searches": latest_logs,
        "documentation_health": docs_health,
        "team_workload": team_workload,
        "team_details": team_details,
        "llm_usage": llm_usage
    }
