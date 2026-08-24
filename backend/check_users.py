import asyncio
from sqlalchemy.future import select
from app.database import SessionLocal
from app.models import User, Department

async def check():
    async with SessionLocal() as db:
        r = await db.execute(select(User))
        users = r.scalars().all()
        r2 = await db.execute(select(Department))
        depts = {d.id: d.name for d in r2.scalars().all()}
        print(f"Total users: {len(users)}")
        print()
        for u in users:
            dept = depts.get(u.department_id, 'None')
            print(f"  ID={u.id} | {u.full_name or u.email} | role={u.role} | dept={dept} | manager_id={u.manager_id}")

asyncio.run(check())
