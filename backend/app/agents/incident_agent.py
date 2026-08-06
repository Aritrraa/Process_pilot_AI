from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models import Task

class IncidentAgent:
    async def execute(self, query: str, db: AsyncSession) -> List[Dict[str, Any]]:
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
            r_tasks = await db.execute(select(Task).filter(
                (Task.title.like(f"%{keyword}%")) | 
                (Task.description.like(f"%{keyword}%"))
            ).limit(3))
            tasks = r_tasks.scalars().all()
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
