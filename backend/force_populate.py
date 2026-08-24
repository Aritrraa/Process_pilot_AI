import asyncio
import logging
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models import KGNode, KGEdge, User, Department, Document
from app.knowledge_graph import knowledge_graph
from sqlalchemy.future import select

logging.basicConfig(level=logging.INFO)

async def force_populate():
    async with SessionLocal() as db:
        # Wipe existing graph
        await db.execute(text("DELETE FROM kg_edges"))
        await db.execute(text("DELETE FROM kg_nodes"))
        await db.commit()
        
        # Populate
        print("Populating...")
        r_depts = await db.execute(select(Department))
        depts = r_depts.scalars().all()
        for d in depts:
            await knowledge_graph.add_entity(db, f"dept_{d.name}", "Department", {"name": d.name})

        r_users = await db.execute(select(User))
        users = r_users.scalars().all()
        user_map = {u.id: u for u in users}
        for u in users:
            user_node = f"user_{u.email}"
            await knowledge_graph.add_entity(db, user_node, "User", {"email": u.email, "name": u.full_name or u.email, "role": u.role})
            if u.department_id:
                dept = next((d for d in depts if d.id == u.department_id), None)
                if dept:
                    await knowledge_graph.add_relationship(db, user_node, f"dept_{dept.name}", "member_of")
            if u.manager_id and u.manager_id in user_map:
                manager = user_map[u.manager_id]
                await knowledge_graph.add_relationship(db, user_node, f"user_{manager.email}", "reports_to")

        r_docs = await db.execute(select(Document))
        docs = r_docs.scalars().all()
        for doc in docs:
            uploader = user_map.get(doc.uploaded_by)
            uploader_email = uploader.email if uploader else "admin@processpilot.ai"
            dept = next((d for d in depts if d.id == doc.department_id), None)
            dept_name = dept.name if dept else "General"
            await knowledge_graph.index_document(
                db=db, document_id=doc.id, title=doc.title,
                file_type=doc.file_type, department_name=dept_name,
                uploader_email=uploader_email
            )
            
        print("Done!")

if __name__ == "__main__":
    asyncio.run(force_populate())
