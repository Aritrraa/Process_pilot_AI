"""
Fix missing users: create Mark (manager) and John, Emma, assign all employees properly.
Run: python fix_users.py
"""
import asyncio
from sqlalchemy.future import select
from sqlalchemy import text
from app.database import SessionLocal
from app.models import User, Department
from passlib.context import CryptContext
import sys

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MISSING_USERS = [
    {
        "email": "mark@processpilot.ai",
        "password": "mark123",
        "full_name": "Mark Somerhalder",
        "role": "Manager",
        "department_name": "Operations",
        "manager_id": None,
    },
    {
        "email": "john@processpilot.ai",
        "password": "john123",
        "full_name": "John Doe",
        "role": "Employee",
        "department_name": "Engineering",
        "manager_email": "sarah@processpilot.ai",
    },
    {
        "email": "emma@processpilot.ai",
        "password": "emma123",
        "full_name": "Emma Watson",
        "role": "Employee",
        "department_name": "HR",
        "manager_email": "mark@processpilot.ai",
    },
]

REASSIGN = [
    # employee_email -> manager_email
    ("alice@processpilot.ai", "mark@processpilot.ai"),
    ("elena@processpilot.ai", "mark@processpilot.ai"),
]


async def fix():
    async with SessionLocal() as db:
        # Get departments
        r = await db.execute(select(Department))
        dept_map = {d.name: d.id for d in r.scalars().all()}
        print("Departments:", dept_map)

        # Get existing users
        r = await db.execute(select(User))
        users = r.scalars().all()
        user_map = {u.email: u for u in users}
        print("Existing users:", list(user_map.keys()))

        # Create missing users
        for u_data in MISSING_USERS:
            if u_data["email"] in user_map:
                print(f"  SKIP (exists): {u_data['email']}")
                continue

            dept_id = dept_map.get(u_data["department_name"])
            manager_id = None
            if u_data.get("manager_email"):
                mgr = user_map.get(u_data["manager_email"])
                if mgr:
                    manager_id = mgr.id
                else:
                    # Mark might have just been created above - re-fetch
                    r2 = await db.execute(select(User).filter(User.email == u_data["manager_email"]))
                    mgr = r2.scalars().first()
                    if mgr:
                        manager_id = mgr.id

            new_user = User(
                email=u_data["email"],
                hashed_password=pwd_context.hash(u_data["password"]),
                full_name=u_data["full_name"],
                role=u_data["role"],
                department_id=dept_id,
                manager_id=manager_id,
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            user_map[new_user.email] = new_user
            print(f"  CREATED: {new_user.email} (id={new_user.id}, mgr={manager_id})")

        # Refresh user_map after creating Mark
        r = await db.execute(select(User))
        user_map = {u.email: u for u in r.scalars().all()}

        # Re-assign orphaned employees
        for emp_email, mgr_email in REASSIGN:
            emp = user_map.get(emp_email)
            mgr = user_map.get(mgr_email)
            if emp and mgr:
                emp.manager_id = mgr.id
                await db.commit()
                print(f"  REASSIGNED: {emp_email} -> manager {mgr_email} (id={mgr.id})")
            else:
                print(f"  SKIP reassign: emp={emp_email} exists={emp is not None}, mgr={mgr_email} exists={mgr is not None}")

        # Final summary
        r = await db.execute(select(User))
        all_users = r.scalars().all()
        r2 = await db.execute(select(Department))
        dept_by_id = {d.id: d.name for d in r2.scalars().all()}
        print("\n=== FINAL USER LIST ===")
        for u in sorted(all_users, key=lambda x: (x.role, x.id)):
            dept = dept_by_id.get(u.department_id, '?')
            print(f"  {u.id:2d} | {(u.full_name or u.email):<22} | {u.role:<10} | {dept:<15} | mgr_id={u.manager_id}")


asyncio.run(fix())
