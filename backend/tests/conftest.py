import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth import get_password_hash
from app.database import Base, get_db
from app.main import app
from app.models import Department, User, UserSetting
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = "sqlite:///./test_processpilot.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=NullPool)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

ASYNC_TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_processpilot.db"
async_test_engine = create_async_engine(ASYNC_TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=NullPool)
AsyncTestSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=async_test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def client(db):
    """FastAPI test client with overridden DB dependency."""
    async def override_get_db():
        async with AsyncTestSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            
    # Clear rate limiter before each test to avoid 429 errors
    from app.rate_limiter import _limiter
    _limiter.requests.clear()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def seed_data(db):
    """Seed test database with departments, users, and settings."""
    eng = Department(id=1, name="Engineering", description="Engineering team")
    hr = Department(id=2, name="HR", description="HR team")
    db.add_all([eng, hr])
    db.commit()
    
    admin = User(
        id=1, email="admin@test.com", hashed_password=get_password_hash("admin123"),
        full_name="Admin User", role="Admin", department_id=1
    )
    manager = User(
        id=2, email="manager@test.com", hashed_password=get_password_hash("manager123"),
        full_name="Manager User", role="Manager", department_id=1
    )
    employee = User(
        id=3, email="employee@test.com", hashed_password=get_password_hash("employee123"),
        full_name="Employee User", role="Employee", department_id=1, manager_id=2
    )
    other_emp = User(
        id=4, email="other@test.com", hashed_password=get_password_hash("other123"),
        full_name="Other Employee", role="Employee", department_id=2
    )
    db.add_all([admin, manager, employee, other_emp])
    db.commit()
    
    for u in [admin, manager, employee, other_emp]:
        setting = UserSetting(user_id=u.id, gemini_api_key="", system_prompt="")
        db.add(setting)
    db.commit()
    
    return {
        "admin": admin, "manager": manager, 
        "employee": employee, "other": other_emp,
        "eng": eng, "hr": hr
    }

def get_auth_token(client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]

def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
