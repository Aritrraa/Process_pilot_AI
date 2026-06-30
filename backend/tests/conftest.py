"""
Shared test fixtures and configuration for ProcessPilot AI test suite.
Uses in-memory SQLite for fast, isolated tests.
"""
import pytest
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.auth import get_password_hash
from app.models import User, Department, UserSetting

# In-memory SQLite for tests — fast, isolated, disposable
TEST_DATABASE_URL = "sqlite:///./test_processpilot.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


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
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    # Clear rate limiter before each test to avoid 429 errors
    from app.rate_limiter import limiter
    limiter._requests.clear()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_data(db):
    """Seed test database with departments, users, and settings."""
    # Create departments
    eng = Department(id=1, name="Engineering", description="Engineering team")
    hr = Department(id=2, name="HR", description="HR team")
    db.add_all([eng, hr])
    db.commit()
    
    # Create users
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
    
    # Create user settings
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
    """Helper to get auth token."""
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]


def auth_header(token: str) -> dict:
    """Helper to create auth header dict."""
    return {"Authorization": f"Bearer {token}"}
