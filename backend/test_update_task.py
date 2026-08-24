import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy.future import select
from app.models import User, Task
from app.auth import create_access_token
import httpx

async def test_update_task():
    async with AsyncSessionLocal() as db:
        # Get an admin user
        r_u = await db.execute(select(User).filter(User.role == "Admin"))
        admin = r_u.scalars().first()
        if not admin:
            print("No admin user found")
            return
            
        token = create_access_token({"sub": admin.id})
        
        # Get a task
        r_t = await db.execute(select(Task))
        task = r_t.scalars().first()
        if not task:
            print("No task found")
            return
            
        print(f"Task {task.id} initial status: {task.status}")
        
        # Call API
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"http://localhost:8000/api/v1/tasks/{task.id}",
                headers=headers,
                json={"status": "In_Progress"}
            )
            print(f"Status Code: {resp.status_code}")
            print(f"Response: {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_update_task())
