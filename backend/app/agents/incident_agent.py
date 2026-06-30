from typing import List, Dict, Any
from sqlalchemy.orm import Session
from ..models import Task

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
