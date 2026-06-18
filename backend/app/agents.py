import os
import datetime
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from sqlalchemy.orm import Session

from .models import User, Document, Task, Memory, AgentLog, UserSetting
from .vectorstore import vector_store_manager

class SearchAgent:
    def execute(self, query: str, department_id: Optional[int], api_key: Optional[str], llm_provider: str = "simulation") -> List[Dict[str, Any]]:
        # Retrieve chunks from ChromaDB
        chunks = vector_store_manager.search(query, limit=4, department_id=department_id, api_key=api_key, llm_provider=llm_provider)
        return chunks

class IncidentAgent:
    def execute(self, query: str, db: Session) -> List[Dict[str, Any]]:
        # Retrieve tasks/tickets related to logs/incidents
        # Query task titles or descriptions containing parts of the query
        import re
        cleaned_query = re.sub(r'[^\w\s]', ' ', query)
        keywords = [word.lower() for word in cleaned_query.split() if len(word) > 3]
        if not keywords:
            return []
        
        # Simple text matching in DB for demo purposes
        matching_tasks = []
        for keyword in keywords[:3]:
            tasks = db.query(Task).filter(
                (Task.title.like(f"%{keyword}%")) | 
                (Task.description.like(f"%{keyword}%"))
            ).limit(3).all()
            for t in tasks:
                if t.id not in [x["id"] for x in matching_tasks]:
                    matching_tasks.append({
                        "id": t.id,
                        "title": t.title,
                        "description": t.description,
                        "status": t.status,
                        "created_at": t.created_at.strftime("%Y-%m-%d")
                    })
        return matching_tasks

class GraphAgent:
    def execute(self, query: str) -> List[Dict[str, Any]]:
        # Query local NetworkX knowledge graph for entities and neighbors
        from .knowledge_graph import knowledge_graph
        
        # Simple extraction of keywords (cleaning punctuation)
        import re
        cleaned_query = re.sub(r'[^\w\s]', ' ', query)
        keywords = [word.lower() for word in cleaned_query.split() if len(word) > 3]
        if not keywords:
            return []
            
        results = []
        # Search node IDs or properties
        for node_id, data in knowledge_graph.graph.nodes(data=True):
            node_type = data.get("type", "Unknown")
            # If any keyword is in the node ID or properties
            match = False
            if any(kw in str(node_id).lower() for kw in keywords):
                match = True
            else:
                for k, v in data.items():
                    if any(kw in str(v).lower() for kw in keywords):
                        match = True
                        break
                        
            if match:
                # Find connected neighbors/relationships
                neighbors = knowledge_graph.get_neighbors(node_id)
                results.append({
                    "entity_id": node_id,
                    "type": node_type,
                    "properties": {k: v for k, v in data.items() if k != "type"},
                    "connections": [
                        {
                            "target": n["id"],
                            "relationship": n["relationship"],
                            "type": n.get("type", "Unknown"),
                            "direction": n["direction"]
                        } for n in neighbors[:4] # limit to 4 connected neighbors to avoid context explosion
                    ]
                })
        return results[:3] # Return top 3 matched entities

class SOPAgent:
    def execute(self, query: str, context_chunks: List[str], api_key: Optional[str], llm_provider: str = "simulation", system_prompt: Optional[str] = None) -> str:
        """
        Creates/formats SOPs or instructions.
        """
        prompt = (
            "You are an expert Operations SOP (Standard Operating Procedure) writer.\n"
            "Based on the following document context, draft a standard operating procedure "
            "answering the user's query.\n"
            f"Query: {query}\n\n"
            f"Context:\n" + "\n---\n".join(context_chunks) + "\n\n"
            "Create a clean, formatted Markdown document with sections: 'Overview', 'Prerequisites', 'Step-by-Step Procedure', 'Safety/Verification'."
        )
        if system_prompt:
            prompt = f"System Instruction: {system_prompt}\n\n{prompt}"
        
        if not api_key or llm_provider == "simulation":
            # Fallback mock template generator
            return (
                f"# Standard Operating Procedure: {query.capitalize()} (Simulation Mode)\n\n"
                "## Overview\n"
                "This SOP outlines the protocol for handling the requested process as extracted from local files.\n\n"
                "## Prerequisites\n"
                "- Verify environment variables\n"
                "- Ensure access permissions are granted\n\n"
                "## Step-by-Step Procedure\n"
                "1. **Analyze logs & requirements**: Search for related configurations in settings.\n"
                "2. **Execute Deployment / Operations**: Follow standard deployment instructions.\n"
                "3. **Post-execution review**: Audit status logs to confirm success.\n\n"
                "## Verification\n"
                "- Run standard health check endpoint to verify uptime."
            )
            
        if llm_provider == "openai":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"Error generating SOP via OpenAI API: {str(e)}"
                
        elif llm_provider == "groq":
            try:
                from groq import Groq
                client = Groq(api_key=api_key)
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"Error generating SOP via Groq API: {str(e)}"
                
        elif llm_provider == "gemini":
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Error generating SOP via Gemini API: {str(e)}"
        
        return "Unsupported LLM provider."

class MemoryAgent:
    def get_memories(self, user_id: int, query: str, db: Session) -> str:
        # Get past conversation memories
        memories = db.query(Memory).filter(Memory.user_id == user_id).all()
        if not memories:
            return "No previous long-term memories stored."
        
        memory_str = "\n".join([f"- {m.key}: {m.value}" for m in memories])
        return memory_str

    def save_memory(self, user_id: int, key: str, value: str, db: Session):
        # Update or create memory
        existing = db.query(Memory).filter(Memory.user_id == user_id, Memory.key == key).first()
        if existing:
            existing.value = value
        else:
            new_memory = Memory(user_id=user_id, key=key, value=value)
            db.add(new_memory)
        db.commit()

ACTIVE_AGENT_SESSIONS = {}

class CEOAgent:
    def __init__(self):
        self.search_agent = SearchAgent()
        self.incident_agent = IncidentAgent()
        self.sop_agent = SOPAgent()
        self.memory_agent = MemoryAgent()
        self.graph_agent = GraphAgent()

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

    def process_query(self, user: User, query: str, db: Session) -> Dict[str, Any]:
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
                        from .models import Task
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
        
        # Step 3: Run Search Agent (ChromaDB Vector search)
        # Apply role check/department isolation
        dept_id = None if user.role == "Admin" else user.department_id
        search_results = self.search_agent.execute(query, dept_id, api_key, llm_provider)
        
        # Step 4: Run Incident Agent (DB metadata lookup)
        incident_results = self.incident_agent.execute(query, db)
        
        # Step 4.5: Run Graph Agent (Knowledge Graph Graph-RAG lookup)
        graph_results = self.graph_agent.execute(query)
        
        # Step 5: Construct full context
        context_chunks = [res["document"] for res in search_results]
        sources = [res["metadata"].get("file_name", "Unknown File") for res in search_results]
        # Remove duplicate sources
        sources = list(set(sources))
        
        # Assemble steps for agent logging
        steps = [
            {"agent": "MemoryAgent", "action": "Retrieved past context", "result": f"Found {len(user_memories.splitlines())} items"},
            {"agent": "SearchAgent", "action": f"Searched vector store (Dept: {user.department_id if dept_id else 'All'})", "result": f"Found {len(search_results)} relevant document segments"},
            {"agent": "IncidentAgent", "action": "Searched database ticket logs", "result": f"Found {len(incident_results)} tasks/tickets"},
            {"agent": "GraphAgent", "action": "Queried local knowledge graph (Graph-RAG)", "result": f"Retrieved {len(graph_results)} connected entities"}
        ]
        
        # Step 6: Query LLM (or fallback) for final response
        sop_needed = "sop" in query.lower() or "procedure" in query.lower() or "how to" in query.lower()
        
        if sop_needed:
            steps.append({"agent": "SOPAgent", "action": f"Generating structured markdown procedure using {llm_provider}", "result": "Success"})
            answer = self.sop_agent.execute(query, context_chunks, api_key, llm_provider, system_prompt)
        else:
            from .analytics import get_system_analytics
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
            prompt = (
                "You are ProcessPilot AI, an Enterprise Operations Copilot.\n"
                "Synthesize an answer for the user query using the retrieved knowledge, incident tickets, past memories, organizational directory, and system/team analytics.\n"
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
                f"System/Team Analytics Context:\n{analytics_info}\n\n"
                f"User: {user.email} (Role: {user.role})\n"
                f"Query: {query}\n\n"
                f"User Memories:\n{user_memories}\n\n"
                f"Retrieved Document Context:\n" + "\n---\n".join(context_chunks) + "\n\n"
                f"Related Tickets/Incidents:\n" + str(incident_results) + "\n\n"
                "Answer the user clearly. Highlight steps, source citations, and any related incidents/tickets if applicable."
            )
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
            elif llm_provider == "openai":
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key)
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    answer = response.choices[0].message.content
                    steps.append({"agent": "CEOAgent", "action": "Synthesized response via OpenAI", "result": "Success"})
                except Exception as e:
                    answer = f"Error generating response via OpenAI API: {str(e)}"
                    steps.append({"agent": "CEOAgent", "action": "OpenAI generation failed", "result": "Error"})
            elif llm_provider == "groq":
                try:
                    from groq import Groq
                    client = Groq(api_key=api_key)
                    response = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    answer = response.choices[0].message.content
                    steps.append({"agent": "CEOAgent", "action": "Synthesized response via Groq", "result": "Success"})
                except Exception as e:
                    answer = f"Error generating response via Groq API: {str(e)}"
                    steps.append({"agent": "CEOAgent", "action": "Groq generation failed", "result": "Error"})
            elif llm_provider == "gemini":
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(prompt)
                    answer = response.text
                    steps.append({"agent": "CEOAgent", "action": "Synthesized response via Gemini", "result": "Success"})
                except Exception as e:
                    answer = f"Error generating response via Gemini API: {str(e)}"
                    steps.append({"agent": "CEOAgent", "action": "Gemini generation failed", "result": "Error"})
                    
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

ceo_agent = CEOAgent()
