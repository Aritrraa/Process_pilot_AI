import os
import datetime
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from ..models import User, Document, DocumentChunk, Meeting, Task, Memory, AgentLog, UserSetting

from .search_agent import SearchAgent
from .incident_agent import IncidentAgent
from .sop_agent import SOPAgent
from .memory_agent import MemoryAgent
from .graph_agent import GraphAgent
from .comparison_agent import ComparisonAgent
from ..llm_client import LLMClient

llm_client = LLMClient()

ACTIVE_AGENT_SESSIONS = {}

class CEOAgent:
    def __init__(self):
        self.search_agent = SearchAgent()
        self.incident_agent = IncidentAgent()
        self.sop_agent = SOPAgent()
        self.memory_agent = MemoryAgent()
        self.graph_agent = GraphAgent()
        self.comparison_agent = ComparisonAgent()

    def _get_org_directory(self, db: Session, user: User) -> str:
        all_users = db.query(User).all()
        user_map = {u.id: u for u in all_users}
        
        if user.role == "Admin":
            filtered_users = all_users[:20]
        else:
            # Filter users: same department, or direct manager, or direct reports
            dept_users = [u for u in all_users if u.department_id == user.department_id]
            manager = user_map.get(user.manager_id) if user.manager_id else None
            reports = [u for u in all_users if u.manager_id == user.id]
            
            seen = set()
            filtered_users = []
            for u in dept_users + ([manager] if manager else []) + reports:
                if u.id not in seen:
                    seen.add(u.id)
                    filtered_users.append(u)
            
            # Sort by ID for stability
            filtered_users.sort(key=lambda u: u.id)
            filtered_users = filtered_users[:20]

        lines = []
        lines.append("Organizational Directory:")
        for u in filtered_users:
            manager_email = user_map[u.manager_id].email if u.manager_id in user_map else "None"
            manager_name = user_map[u.manager_id].full_name if u.manager_id in user_map else "None"
            lines.append(
                f"- ID: {u.id} | Name: {u.full_name or 'Unknown'} | Email: {u.email} | "
                f"Role: {u.role} | Manager: {manager_name} ({manager_email})"
            )
        return "\n".join(lines)

    def _handle_org_directory_query(self, query: str, user: User, db: Session) -> Optional[str]:
        q = query.lower()
        is_directory_query = any(x in q for x in ["manager", "report", "who is", "email", "contact", "phone", "details", "team", "reports to", "work under", "id details"])
        if not is_directory_query:
            return None
            
        users = db.query(User).all()
        user_map = {u.id: u for u in users}
        
        # 1. Employee asks "who is the current hr manager"
        if "hr manager" in q or "human resources manager" in q:
            hr_mgr = next((u for u in users if u.role == "Manager" and u.department_id == 2), None) # HR department id is 2
            if hr_mgr:
                return f"The current HR Manager is **{hr_mgr.full_name}** ({hr_mgr.email})."
            return "No HR Manager could be found in the system."
            
        # 2. General manager query: "who is my manager" or "who do i report to"
        if "my manager" in q or "who do i report to" in q or "who is my boss" in q:
            if user.manager_id and user.manager_id in user_map:
                mgr = user_map[user.manager_id]
                return f"You report directly to **{mgr.full_name}** ({mgr.email}), who is a {mgr.role}."
            elif user.role == "Admin":
                return "As an Administrator, you are independent and do not report to a manager."
            elif user.role == "Manager":
                return "You are a Manager. You report directly to the executive leadership team."
            return "No manager is assigned to your profile in the directory."
            
        if "who reports to me" in q or "my team" in q or "my employees" in q:
            subordinates = [u for u in users if u.manager_id == user.id]
            if not subordinates:
                return "According to the directory, no employees report directly to you."
            team_list = "\n".join([f"- **{s.full_name}** ({s.email}) — ID: {s.id}" for s in subordinates])
            return f"The following employees report directly to you:\n{team_list}"
            
        # Helper to find a user by email username or full name in query
        target_user = None
        for u in users:
            name_parts = (u.full_name or "").lower().split()
            username = u.email.split('@')[0].lower()
            if username in q or (u.full_name and u.full_name.lower() in q) or (name_parts and any(part in q for part in name_parts if len(part) > 2)):
                target_user = u
                break
                
        # 3. Specific contact request: e.g. "provide the email of Rohan" or "what is john's email"
        if target_user:
            # Check permissions
            # Admin can ask about anyone
            if user.role == "Admin":
                return f"User details for **{target_user.full_name}**:\n- **Email**: {target_user.email}\n- **User ID**: {target_user.id}\n- **Role**: {target_user.role}"
                
            # Manager can ask about their direct reports
            if user.role == "Manager":
                if target_user.manager_id == user.id:
                    return f"Contact details for your team member **{target_user.full_name}**:\n- **Email**: {target_user.email}\n- **User ID**: {target_user.id}"
                elif target_user.id == user.id:
                    return f"Your details:\n- **Email**: {target_user.email}\n- **User ID**: {target_user.id}"
                else:
                    return "Sorry, due to privacy policy, you can only access contact details of members in your direct team."
                    
            # Employee can ask about manager, peer, or HR manager
            if user.role == "Employee":
                # Check if target is their manager
                if target_user.id == user.manager_id:
                    return f"Contact details for your manager **{target_user.full_name}**:\n- **Email**: {target_user.email}\n- **User ID**: {target_user.id}"
                # Check if target is peer (reports to same manager)
                elif target_user.manager_id == user.manager_id and user.manager_id is not None:
                    return f"Contact details for your team peer **{target_user.full_name}**:\n- **Email**: {target_user.email}\n- **User ID**: {target_user.id}"
                # Check if target is HR manager
                elif target_user.role == "Manager" and target_user.department_id == 2: # HR
                    return f"Contact details for HR Manager **{target_user.full_name}**:\n- **Email**: {target_user.email}\n- **User ID**: {target_user.id}"
                elif target_user.id == user.id:
                    return f"Your details:\n- **Email**: {target_user.email}\n- **User ID**: {target_user.id}"
                else:
                    return "Sorry, you only have permission to view contact details of your manager, team peers, or the HR manager."
                    
        # 4. If someone asks general queries about reporting hierarchy
        if "reports to" in q or "works under" in q:
            for u in users:
                if u.role == "Manager" and ((u.full_name and u.full_name.lower() in q) or u.email.split('@')[0] in q):
                    if user.role == "Admin" or user.id == u.id or user.manager_id == u.id:
                        reports = [r for r in users if r.manager_id == u.id]
                        if not reports:
                            return f"No direct reports found for **{u.full_name}**."
                        return f"The following employees report to **{u.full_name}**:\n" + "\n".join([f"- **{r.full_name}** ({r.email})" for r in reports])
                    else:
                        return "Sorry, you do not have permission to view this reporting structure."
                        
        return None

    def _build_conversation_history(self, db: Session, user: User, max_tokens: int = 2500) -> str:
        logs = db.query(AgentLog).filter(AgentLog.user_id == user.id).order_by(AgentLog.id.desc()).limit(15).all()
        if not logs:
            return "No previous conversation history."
            
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            enc = None
            
        history_chunks = []
        current_tokens = 0
        truncated = False
        
        for log in logs:
            turn = f"User: {log.query}\nProcessPilot AI: {log.response}\n"
            if enc:
                tokens = len(enc.encode(turn))
                if current_tokens + tokens > max_tokens:
                    truncated = True
                    break
                current_tokens += tokens
            history_chunks.append(turn)
            
        if truncated:
            history_chunks.append("[System Note: Earlier conversation history was summarized/truncated to preserve LLM context window limits.]\n")
            
        history_chunks.reverse()
        return "\n".join(history_chunks)

    def process_query(self, user: User, query: str, db: Session, scope: Optional[List[str]] = None) -> Dict[str, Any]:
        # Initialize or retrieve user session for agent loop tracking
        if user.id not in ACTIVE_AGENT_SESSIONS:
            ACTIVE_AGENT_SESSIONS[user.id] = {
                "turns": 0,
                "pending_action": None,
                "history": []
            }
        
        session = ACTIVE_AGENT_SESSIONS[user.id]
        session["turns"] += 1
        
        # Safe turn limit checkpoint to prevent infinite agent/tool call execution loops
        if session["turns"] > 10:
            session["turns"] = 0
            steps = [{"agent": "CEOAgent", "action": "Safe Turn Checkpoint", "result": "Halted due to loop detection"}]
            return {
                "answer": "⚠️ **Execution Halted**: Safe turn limit (10) exceeded to prevent infinite agent reasoning loops.",
                "sources": [],
                "incidents": [],
                "steps": steps
            }

        # Intercept directory/contact query to handle programmatically (RBAC enforced, 100% accurate, fast)
        org_answer = self._handle_org_directory_query(query, user, db)
        if org_answer:
            session["turns"] = 0
            steps = [
                {"agent": "MemoryAgent", "action": "Skipped memory lookup for directory query", "result": "Success"},
                {"agent": "CEOAgent", "action": "Queried live database org directory (RBAC enforced)", "result": "Success"}
            ]
            
            # Log this agent session
            agent_log = AgentLog(
                user_id=user.id,
                query=query,
                response=org_answer,
                agent_steps=steps
            )
            db.add(agent_log)
            db.commit()
            
            return {
                "answer": org_answer,
                "sources": [],
                "incidents": [],
                "steps": steps
            }

        # Handle human-in-the-loop pending approval response
        if session["pending_action"]:
            action = session["pending_action"]
            session["pending_action"] = None
            session["turns"] = 0
            
            steps = [{"agent": "CEOAgent", "action": "Process Human approval checkpoint", "result": "Success"}]
            
            if query.lower() in ("yes", "approve", "proceed", "confirm", "y"):
                if action["type"] == "create_task":
                    try:
                        new_task = Task(
                            title=action["data"]["title"],
                            description=action["data"]["description"],
                            assigned_to=action["data"]["assigned_to"],
                            status="Pending"
                        )
                        db.add(new_task)
                        db.commit()
                        db.refresh(new_task)
                        ans = (
                            f"✅ **Action Approved & Task Created Successfully!**\n"
                            f"- **Title**: {new_task.title}\n"
                            f"- **Description**: {new_task.description}\n"
                            f"- **Assignee ID**: {new_task.assigned_to}\n"
                            f"- **Status**: {new_task.status}"
                        )
                        steps.append({"agent": "CEOAgent", "action": "Task Creation Completed", "result": "Success"})
                    except Exception as e:
                        ans = f"Error executing task creation action: {e}"
                        steps.append({"agent": "CEOAgent", "action": "Task Creation Failed", "result": "Error"})
                else:
                    ans = "Proposed action completed successfully."
            else:
                ans = "❌ **Action Cancelled.** Operation aborted by user."
                steps.append({"agent": "CEOAgent", "action": "Action Rejected", "result": "Aborted"})
                
            agent_log = AgentLog(
                user_id=user.id,
                query=query,
                response=ans,
                agent_steps=steps
            )
            db.add(agent_log)
            db.commit()
            return {"answer": ans, "sources": [], "incidents": [], "steps": steps}

        # Check for sensitive action that requires human-in-the-loop approval
        is_create_task_query = any(x in query.lower() for x in ["create task", "assign task", "new task", "add task"])
        if is_create_task_query:
            # Parse proposed task data (simple heuristics or extract from query)
            title = "Extracted Action Item"
            desc = f"Action item created from query: {query}"
            assigned_to = user.id
            
            # Simple keyword matching to find assignee name in directory
            try:
                users = db.query(User).all()
                for u in users:
                    if u.full_name and u.full_name.lower() in query.lower():
                        assigned_to = u.id
                        break
            except:
                pass
                
            session["pending_action"] = {
                "type": "create_task",
                "data": {
                    "title": title,
                    "description": desc,
                    "assigned_to": assigned_to
                }
            }
            steps = [{"agent": "CEOAgent", "action": "Create Task Requested", "result": "Suspended for Approval"}]
            ans = (
                f"🛡️ **Human-in-the-Loop Verification Required**\n\n"
                f"You requested to create/assign a task. Here is the proposed action:\n"
                f"- **Action**: Create Task\n"
                f"- **Title**: {title}\n"
                f"- **Assignee ID**: {assigned_to}\n\n"
                f"Please reply with **'yes'** or **'approve'** to execute this, or anything else to cancel."
            )
            # Log this agent session
            agent_log = AgentLog(
                user_id=user.id,
                query=query,
                response=ans,
                agent_steps=steps
            )
            db.add(agent_log)
            db.commit()
            return {"answer": ans, "sources": [], "incidents": [], "steps": steps}

        # Step 1: Check settings for API keys and provider
        settings_record = db.query(UserSetting).filter(UserSetting.user_id == user.id).first()
        system_prompt = settings_record.system_prompt if settings_record else None
        
        llm_provider = settings_record.llm_provider if settings_record else "simulation"
        if llm_provider == "gemini":
            api_key = settings_record.gemini_api_key if settings_record else os.getenv("GEMINI_API_KEY")
        elif llm_provider == "groq":
            api_key = settings_record.groq_api_key if settings_record else os.getenv("GROQ_API_KEY")
        elif llm_provider == "openai":
            api_key = settings_record.openai_api_key if settings_record else os.getenv("OPENAI_API_KEY")
        else:
            api_key = None
            
        if not api_key:
            llm_provider = "simulation"
        
        # Step 2: Retrieve long term memory for context
        user_memories = self.memory_agent.get_memories(user.id, query, db)
        
        # Step 3: Run Search Agent, Incident Agent, Graph Agent, or Scoped Filtering
        if scope:
            context_chunks = []
            sources = []
            incident_results = []
            graph_results = []
            
            doc_ids = []
            meet_ids = []
            task_ids = []
            
            for s in scope:
                if s.startswith("doc_"):
                    try: doc_ids.append(int(s.split("_")[1]))
                    except: pass
                elif s.startswith("meet_"):
                    try: meet_ids.append(int(s.split("_")[1]))
                    except: pass
                elif s.startswith("task_"):
                    try: task_ids.append(int(s.split("_")[1]))
                    except: pass
                elif s.startswith("tech_") or s.startswith("dept_") or s.startswith("user_"):
                    from ..knowledge_graph import knowledge_graph
                    neighbors = knowledge_graph.get_neighbors(s)
                    for n in neighbors:
                        n_id = n["id"]
                        if n_id.startswith("doc_"):
                            try: doc_ids.append(int(n_id.split("_")[1]))
                            except: pass
                        elif n_id.startswith("meet_"):
                            try: meet_ids.append(int(n_id.split("_")[1]))
                            except: pass
                        elif n_id.startswith("task_"):
                            try: task_ids.append(int(n_id.split("_")[1]))
                            except: pass
            
            # Deduplicate IDs to avoid duplicate processing of linked files/tasks
            doc_ids = list(set(doc_ids))
            meet_ids = list(set(meet_ids))
            task_ids = list(set(task_ids))
            
            # Fetch scoped documents
            if doc_ids:
                docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
                for d in docs:
                    sources.append(d.title)
                    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).all()
                    for chunk in chunks:
                        context_chunks.append(f"[Document: {d.title}] {chunk.content}")
            
            # Fetch scoped meetings
            if meet_ids:
                meets = db.query(Meeting).filter(Meeting.id.in_(meet_ids)).all()
                for m in meets:
                    sources.append(f"Meeting: {m.title}")
                    context_chunks.append(
                        f"[Meeting Transcript: {m.title}]\n"
                        f"Summary: {m.summary or 'No summary'}\n"
                        f"Transcript:\n{m.transcript}"
                    )
            
            # Fetch scoped tasks
            if task_ids:
                tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
                for t in tasks:
                    sources.append(f"Task: {t.title}")
                    incident_results.append({
                        "id": t.id,
                        "title": t.title,
                        "description": t.description,
                        "status": t.status,
                        "created_at": t.created_at.strftime("%Y-%m-%d")
                    })
                    context_chunks.append(
                        f"[Task Ticket: {t.title}]\n"
                        f"Description: {t.description or 'No description'}\n"
                        f"Status: {t.status}\n"
                        f"Created At: {t.created_at.strftime('%Y-%m-%d')}"
                    )
            
            # Deduplicate sources
            sources = list(set(sources))
            
            steps = [
                {"agent": "MemoryAgent", "action": "Retrieved past context", "result": f"Found {len(user_memories.splitlines())} items"},
                {"agent": "SearchAgent", "action": "Applied Knowledge Graph scope filters", "result": f"Loaded {len(doc_ids)} documents, {len(meet_ids)} meetings, {len(task_ids)} tasks"}
            ]
        else:
            # Apply role check/department isolation
            dept_id = None if user.role == "Admin" else user.department_id
            search_results = self.search_agent.execute(query, dept_id, api_key, llm_provider)
            
            # Run Incident Agent (DB metadata lookup)
            incident_results = self.incident_agent.execute(query, db)
            
            # Run Graph Agent (Knowledge Graph Graph-RAG lookup)
            graph_results = self.graph_agent.execute(query)
            
            # Run Comparison Agent if necessary
            comparison_needed = any(word in query.lower() for word in ["compare", "difference", "differences", "versus", " vs "])
            comparison_results = ""
            if comparison_needed:
                comparison_results = self.comparison_agent.execute(query, user, db, api_key=api_key, llm_provider=llm_provider)
            
            # Construct full context
            context_chunks = [res["document"] for res in search_results]
            sources = [res["metadata"].get("file_name", "Unknown File") for res in search_results]
            # Remove duplicate sources
            sources = list(set(sources))
            
            if comparison_needed and comparison_results:
                context_chunks.append(f"[Document Comparison Report]\n{comparison_results}")

            # Assemble steps for agent logging
            steps = [
                {"agent": "MemoryAgent", "action": "Retrieved past context", "result": f"Found {len(user_memories.splitlines())} items"},
                {"agent": "SearchAgent", "action": f"Searched vector store (Dept: {user.department_id if dept_id else 'All'})", "result": f"Found {len(search_results)} relevant document segments"},
                {"agent": "IncidentAgent", "action": "Searched database ticket logs", "result": f"Found {len(incident_results)} tasks/tickets"},
                {"agent": "GraphAgent", "action": "Queried local knowledge graph (Graph-RAG)", "result": f"Retrieved {len(graph_results)} connected entities"}
            ]
            if comparison_needed:
                steps.append({"agent": "ComparisonAgent", "action": "Compared documents", "result": "Generated comparison report"})
        
        # Step 6: Query LLM (or fallback) for final response
        sop_needed = "sop" in query.lower() or "procedure" in query.lower() or "how to" in query.lower()
        
        if sop_needed:
            steps.append({"agent": "SOPAgent", "action": f"Generating structured markdown procedure using {llm_provider}", "result": "Success"})
            answer = self.sop_agent.execute(query, context_chunks, api_key, llm_provider, system_prompt)
        else:
            from ..analytics import get_system_analytics
            analytics_data = get_system_analytics(db, user)
            
            # Format analytics details nicely
            analytics_summary = []
            analytics_summary.append("System & Team Analytics Overview:")
            analytics_summary.append(f"- Documentation Health Score: {analytics_data.get('documentation_health')}%")
            analytics_summary.append(f"- Task Status Distribution: {analytics_data.get('task_status')}")
            
            team_workload = analytics_data.get("team_workload", [])
            if team_workload:
                analytics_summary.append("- Team Members Workload & Progress:")
                for member in team_workload:
                    analytics_summary.append(
                        f"  * Name: {member['name']} ({member['email']}) | "
                        f"Tasks Completed: {member['completed']} | Tasks In Progress: {member['in_progress']} | Tasks Left/Pending: {member['pending']}"
                    )
            analytics_info = "\n".join(analytics_summary)

            directory_info = self._get_org_directory(db, user)
            
            # Query the database for the active user's assigned tasks list
            user_tasks = db.query(Task).filter(Task.assigned_to == user.id).all()
            user_tasks_summary = []
            if user_tasks:
                user_tasks_summary.append("Your Current Assigned Tasks:")
                for t in user_tasks:
                    user_tasks_summary.append(
                        f"- [Task ID: task_{t.id}] Title: {t.title} | Status: {t.status} | Description: {t.description or 'No description'}"
                    )
            else:
                user_tasks_summary.append("You currently have no tasks assigned to you.")
            user_tasks_info = "\n".join(user_tasks_summary)
            
            conversation_history = self._build_conversation_history(db, user)

            prompt = (
                "You are ProcessPilot AI, an Enterprise Operations Copilot.\n"
                "Synthesize an answer for the user query using the retrieved knowledge, incident tickets, past memories, organizational directory, system/team analytics, and the user's specific assigned task list.\n"
                "Adhere to strict facts. Cite documents if they are available.\n\n"
                "SECURITY RULES for Contact Info & Details disclosure:\n"
                "1. Admin (Independent): Can query contact info (email, id) of ANY employee or manager.\n"
                "2. Managers: Can query details of employees who report directly to them. If they ask about other employees or other managers, refuse politely: 'Sorry, due to privacy policy, you can only access contact details of members in your direct team.'\n"
                "3. Employees:\n"
                "   - Can query details of their own manager.\n"
                "   - Can query details of their peer team members (who report to the same manager).\n"
                "   - Can query who is the current HR manager or query the HR manager's details.\n"
                "   - CANNOT query details of other managers or employees from other teams. Refuse politely: 'Sorry, you only have permission to view contact details of your manager, team peers, or the HR manager.'\n\n"
                f"Current User details:\n"
                f"- Email: {user.email}\n"
                f"- Name: {user.full_name or 'Unknown'}\n"
                f"- Role: {user.role}\n"
                f"- Department ID: {user.department_id}\n"
                f"- Manager ID: {user.manager_id}\n\n"
                f"{directory_info}\n\n"
                f"Your Current Assigned Tasks:\n{user_tasks_info}\n\n"
                f"System/Team Analytics Context:\n{analytics_info}\n\n"
                f"User: {user.email} (Role: {user.role})\n"
                f"Query: {query}\n\n"
                f"Recent Conversation History:\n{conversation_history}\n\n"
                f"User Memories:\n{user_memories}\n\n"
                f"Retrieved Document Context:\n" + "\n---\n".join(context_chunks) + "\n\n"
                f"Related Tickets/Incidents:\n" + str(incident_results) + "\n\n"
                "Answer the user clearly. Highlight steps, source citations, and any related incidents/tickets if applicable."
            )
            
            # Context window tracking feature to be implemented here
            # Add token count calculation or truncate history...
            
            if system_prompt:
                prompt = f"System Instruction: {system_prompt}\n\n{prompt}"
                
            if llm_provider == "simulation":
                # Simulating a professional response if API Key is not set
                if any(x in query.lower() for x in ["progress", "workload", "team working", "how is my team", "analytics", "status of tasks", "team reports"]):
                    # Build a simulated answer using the live database analytics we fetched!
                    summary_parts = []
                    summary_parts.append("**ProcessPilot AI Response (Simulation Mode)**\n\n")
                    summary_parts.append("Here is the current status and progress of your team based on live database metrics:\n\n")
                    
                    if team_workload:
                        for member in team_workload:
                            total = member["pending"] + member["in_progress"] + member["completed"]
                            summary_parts.append(
                                f"- **{member['name']}** ({member['email']}):\n"
                                f"  * Done: {member['completed']}\n"
                                f"  * In Progress: {member['in_progress']}\n"
                                f"  * Pending (Left): {member['pending']}\n"
                                f"  * Total assigned: {total}\n"
                            )
                    else:
                        summary_parts.append("No subordinates or team member workload details were found for your profile.")
                        
                    summary_parts.append(f"\n*Overall Task Distribution: Completed: {analytics_data['task_status']['Completed']}, In Progress: {analytics_data['task_status']['In_Progress']}, Pending: {analytics_data['task_status']['Pending']}*")
                    answer = "\n".join(summary_parts)
                else:
                    source_citation = f" [Source: {sources[0]}]" if sources else ""
                    ticket_citation = f" [Ticket Reference: {incident_results[0]['title']}]" if incident_results else ""
                    
                    graph_citation = ""
                    if graph_results:
                        first_ent = graph_results[0]
                        conns = ", ".join([f"{c['relationship']} {c['target']}" for c in first_ent['connections']])
                        graph_citation = f"\n- **Knowledge Graph Match**: Found entity '{first_ent['entity_id']}' ({first_ent['type']}) linked to [{conns}]"
                        
                    answer = (
                        f"**ProcessPilot AI Response (Simulation Mode)**\n\n"
                        f"Based on your query *\"{query}\"*, I retrieved relevant corporate information from "
                        f"your files{source_citation} and matched recent incidents{ticket_citation}.\n\n"
                        f"### Key Details:\n"
                        f"- **Retrieved Document Context**: {context_chunks[0] if context_chunks else 'No documents match your query directly.'}\n"
                        f"- **Incidents Found**: {incident_results[0]['description'] if incident_results else 'No past incidents match this query.'}\n"
                        f"{graph_citation}\n\n"
                        f"*(Please configure your Gemini, Groq, or OpenAI API Key in Settings to unlock real-time LLM answers)*"
                    )
                steps.append({"agent": "CEOAgent", "action": "Synthesized response (Simulation)", "result": "Success"})
            else:
                answer = llm_client.call(
                    provider=llm_provider,
                    api_key=api_key,
                    system_prompt=system_prompt,
                    user_message=prompt,
                    db=db,
                    user_id=user.id
                )
                steps.append({"agent": "CEOAgent", "action": f"Synthesized response via {llm_provider}", "result": "Success"})
                    
        # Step 7: Update Long-Term Memory if the query contains important personal settings or context
        if "remember" in query.lower() or "my name is" in query.lower() or "deploy" in query.lower():
            # Extract key/value via a simple rule or save query directly
            self.memory_agent.save_memory(user.id, f"Query_Context_{datetime.datetime.now().strftime('%M%S')}", query, db)
            steps.append({"agent": "MemoryAgent", "action": "Stored key-value context to long-term memory", "result": "Success"})
            
        # Log this agent session
        agent_log = AgentLog(
            user_id=user.id,
            query=query,
            response=answer,
            agent_steps=steps
        )
        db.add(agent_log)
        db.commit()
        
        # Reset turns on successful completion of active query
        if user.id in ACTIVE_AGENT_SESSIONS:
            ACTIVE_AGENT_SESSIONS[user.id]["turns"] = 0
            
        return {
            "answer": answer,
            "sources": sources,
            "incidents": incident_results,
            "steps": steps
        }

    def process_query_stream(self, user: User, query: str, db: Session, scope: Optional[List[str]] = None):
        """
        Stream the LLM response as Server-Sent Events (SSE).
        Re-uses the context gathering from the normal pipeline, but streams the LLM completion.
        """
        import json
        from ..llm_client import llm_client

        # Get context (same as process_query but optimized for stream setup)
        user_settings = db.query(UserSetting).filter(UserSetting.user_id == user.id).first()
        api_key = None
        llm_provider = "simulation"
        system_prompt = None
        if user_settings:
            llm_provider = user_settings.llm_provider or "simulation"
            system_prompt = user_settings.system_prompt
            if llm_provider == "gemini": api_key = user_settings.gemini_api_key
            elif llm_provider == "openai": api_key = user_settings.openai_api_key
            elif llm_provider == "groq": api_key = user_settings.groq_api_key

        # Memory
        user_memories = "\n".join([f"- {m.key}: {m.value}" for m in db.query(Memory).filter(Memory.user_id == user.id).all()])
        
        steps = []
        
        # Scope + Dept isolation
        dept_id = None if user.role == "Admin" else user.department_id
        search_results = self.search_agent.execute(query, dept_id, api_key, llm_provider)
        steps.append({"agent": "SearchAgent", "action": "Queried Vector DB for context", "result": "Success"})
        
        incident_results = self.incident_agent.execute(query, db)
        if incident_results:
            steps.append({"agent": "IncidentAgent", "action": "Matched semantic incident tickets", "result": "Success"})
            
        graph_results = self.graph_agent.execute(query)
        if graph_results:
            steps.append({"agent": "GraphAgent", "action": "Queried organizational knowledge graph", "result": "Success"})
        
        comparison_needed = any(word in query.lower() for word in ["compare", "difference", "differences", "versus", " vs "])
        comparison_results = ""
        if comparison_needed:
            comparison_results = self.comparison_agent.execute(query, user, db, api_key=api_key, llm_provider=llm_provider)
            steps.append({"agent": "ComparisonAgent", "action": "Executed document comparison", "result": "Success"})
            
        context_chunks = [res["document"] for res in search_results]
        if comparison_needed and comparison_results:
            context_chunks.append(f"[Document Comparison Report]\n{comparison_results}")

        sources = list(set([res["metadata"].get("file_name", "Unknown File") for res in search_results]))
        
        from ..analytics import get_system_analytics
        analytics_data = get_system_analytics(db, user)
        analytics_summary = []
        analytics_summary.append("System & Team Analytics Overview:")
        analytics_summary.append(f"- Documentation Health Score: {analytics_data.get('documentation_health')}%")
        analytics_summary.append(f"- Task Status Distribution: {analytics_data.get('task_status')}")
        analytics_info = "\n".join(analytics_summary)
        directory_info = self._get_org_directory(db, user)
        
        user_tasks = db.query(Task).filter(Task.assigned_to == user.id).all()
        user_tasks_summary = [f"- {t.title} [{t.status}]" for t in user_tasks] if user_tasks else ["No tasks"]
        user_tasks_info = "\n".join(user_tasks_summary)
        
        conversation_history = self._build_conversation_history(db, user)

        sop_needed = "sop" in query.lower() or "procedure" in query.lower() or "how to" in query.lower()
        if sop_needed:
            prompt = (
                "You are an expert Operations SOP writer.\n"
                f"Query: {query}\n\n"
                f"Context:\n" + "\n---\n".join(context_chunks) + "\n\n"
                "Create a clean, formatted Markdown document with sections: 'Overview', 'Prerequisites', 'Step-by-Step Procedure', 'Safety/Verification'."
            )
        else:
            prompt = (
                "You are ProcessPilot AI, an Enterprise Operations Copilot.\n"
                "Synthesize an answer for the user query using the retrieved knowledge, incident tickets, past memories, organizational directory, system/team analytics, and the user's specific assigned task list.\n"
                f"User Details: {user.email} (Role: {user.role})\n"
                f"{directory_info}\n"
                f"Assigned Tasks:\n{user_tasks_info}\n"
                f"Analytics:\n{analytics_info}\n"
                f"Memories:\n{user_memories}\n"
                f"Recent Conversation History:\n{conversation_history}\n"
                f"Context:\n" + "\n---\n".join(context_chunks) + "\n"
                f"Incidents: {incident_results}\n"
                f"Query: {query}\n"
            )
            
        if system_prompt:
            prompt = f"System Instruction: {system_prompt}\n\n{prompt}"

        # Yield initial metadata (sources, incidents) so UI can show them immediately
        init_data = json.dumps({
            "type": "metadata",
            "sources": sources,
            "incidents": incident_results,
            "steps": steps
        })
        yield f"data: {init_data}\n\n"

        # Stream LLM tokens
        full_answer = ""
        for chunk in llm_client.stream(
            provider=llm_provider, 
            api_key=api_key, 
            system_prompt=system_prompt or "You are an Enterprise AI.", 
            user_message=prompt, 
            db=db, 
            user_id=user.id
        ):
            full_answer += chunk
            chunk_data = json.dumps({"type": "chunk", "content": chunk})
            yield f"data: {chunk_data}\n\n"

        # End of stream
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

        # Save log asynchronously (in the background, but since we are yielding, we can just save it here at the end)
        try:
            steps.append({"agent": "CEOAgent", "action": f"Synthesized response via {llm_provider}", "result": "Success"})
            agent_log = AgentLog(user_id=user.id, query=query, response=full_answer, agent_steps=steps)
            db.add(agent_log)
            db.commit()
        except Exception:
            pass

ceo_agent = CEOAgent()
process_query = ceo_agent.process_query
process_query_stream = ceo_agent.process_query_stream
