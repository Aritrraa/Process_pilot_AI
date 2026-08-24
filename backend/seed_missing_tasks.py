import asyncio
from sqlalchemy.future import select
from app.database import SessionLocal
from app.models import User, Task
from sqlalchemy import text

NEW_TASKS = [
    # Mark Somerhalder (Operations Manager)
    {"email": "mark@processpilot.ai", "title": "Quarterly Operations Review", "desc": "Prepare Q3 Ops review presentation.", "status": "In_Progress"},
    {"email": "mark@processpilot.ai", "title": "Vendor Contract Renewals", "desc": "Review SOC2 compliance for 3 new vendors.", "status": "Pending"},
    {"email": "mark@processpilot.ai", "title": "Budget Forecasting", "desc": "Align with Finance on 2026 OPEX.", "status": "Completed"},

    # John Doe (Engineering Employee)
    {"email": "john@processpilot.ai", "title": "Fix GraphQL N+1 Issues", "desc": "Optimize the resolver for Analytics view.", "status": "In_Progress"},
    {"email": "john@processpilot.ai", "title": "Write unit tests for Auth", "desc": "Get coverage above 90% in auth.py.", "status": "Pending"},

    # Emma Watson (HR Employee)
    {"email": "emma@processpilot.ai", "title": "Onboarding for 5 new hires", "desc": "Coordinate with IT for laptop provisioning.", "status": "Pending"},
    {"email": "emma@processpilot.ai", "title": "Update Employee Handbook", "desc": "Add new remote work policy.", "status": "Completed"},
    {"email": "emma@processpilot.ai", "title": "Conduct Exit Interviews", "desc": "Follow up with leaving contractors.", "status": "In_Progress"},
    
    # Alice Vance (Operations Employee)
    {"email": "alice@processpilot.ai", "title": "Set Up Datadog Alerts", "desc": "Configure alerting for P1/P2 threshold breaches on production APIs", "status": "Pending"},
    {"email": "alice@processpilot.ai", "title": "Inventory home office monitors", "desc": "Audit shipping receipts to check monitors dispatched in Q1", "status": "In_Progress"},

    # Elena Rostova (Operations Employee)
    {"email": "elena@processpilot.ai", "title": "Configure Jamf profiles", "desc": "Setup MDM for new batch of macOS devices", "status": "Completed"},
]

async def seed():
    async with SessionLocal() as db:
        r = await db.execute(select(User))
        user_map = {u.email: u for u in r.scalars().all()}
        
        count = 0
        for t in NEW_TASKS:
            user = user_map.get(t["email"])
            if user:
                # Check if task already exists
                r2 = await db.execute(select(Task).filter(Task.title == t["title"]))
                existing = r2.scalars().first()
                if existing:
                    continue
                
                mgr_id = user.manager_id if user.role != "Manager" else user.id
                task = Task(
                    title=t["title"],
                    description=t["desc"],
                    status=t["status"],
                    assigned_to=user.id,
                    manager_id=mgr_id
                )
                db.add(task)
                count += 1
                
        if count > 0:
            await db.commit()
            print(f"Seeded {count} new tasks.")
        else:
            print("Tasks already seeded.")

asyncio.run(seed())
