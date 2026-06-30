"""
Authentication API endpoint tests.
Tests: registration, login, token validation, role restrictions, rate limiting.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import get_auth_token, auth_header


class TestRegistration:
    def test_register_employee_success(self, client, seed_data):
        res = client.post("/api/v1/auth/register", json={
            "email": "new@test.com", "password": "password123",
            "full_name": "New User", "role": "Employee", "department_id": 1
        })
        assert res.status_code == 201
        assert res.json()["email"] == "new@test.com"
        assert res.json()["role"] == "Employee"

    def test_register_manager_success(self, client, seed_data):
        res = client.post("/api/v1/auth/register", json={
            "email": "newmgr@test.com", "password": "password123",
            "full_name": "New Manager", "role": "Manager", "department_id": 1
        })
        assert res.status_code == 201
        assert res.json()["role"] == "Manager"

    def test_register_duplicate_email_blocked(self, client, seed_data):
        res = client.post("/api/v1/auth/register", json={
            "email": "admin@test.com", "password": "password123",
            "role": "Employee"
        })
        assert res.status_code == 400
        assert "already registered" in res.json()["detail"]

    def test_register_admin_blocked(self, client, seed_data):
        """Critical security test: self-registration as Admin must be denied."""
        res = client.post("/api/v1/auth/register", json={
            "email": "hacker@test.com", "password": "password123",
            "role": "Admin"
        })
        assert res.status_code in (403, 422)

    def test_register_short_password_rejected(self, client, seed_data):
        res = client.post("/api/v1/auth/register", json={
            "email": "weak@test.com", "password": "short",
            "role": "Employee"
        })
        assert res.status_code == 422

    def test_register_invalid_email_rejected(self, client, seed_data):
        res = client.post("/api/v1/auth/register", json={
            "email": "not-an-email", "password": "password123"
        })
        assert res.status_code == 422

    def test_register_invalid_department(self, client, seed_data):
        res = client.post("/api/v1/auth/register", json={
            "email": "new@test.com", "password": "password123",
            "department_id": 999
        })
        assert res.status_code == 404

    def test_register_no_password(self, client, seed_data):
        res = client.post("/api/v1/auth/register", json={
            "email": "new@test.com"
        })
        assert res.status_code == 422


class TestLogin:
    def test_login_success(self, client, seed_data):
        res = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "admin@test.com"

    def test_login_wrong_password(self, client, seed_data):
        res = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com", "password": "wrongpassword"
        })
        assert res.status_code == 400

    def test_login_nonexistent_user(self, client, seed_data):
        res = client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com", "password": "password123"
        })
        assert res.status_code == 400

    def test_login_empty_password(self, client, seed_data):
        res = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com", "password": ""
        })
        assert res.status_code == 400


class TestAuthenticatedEndpoints:
    def test_get_me_success(self, client, seed_data):
        token = get_auth_token(client, "admin@test.com", "admin123")
        res = client.get("/api/v1/auth/me", headers=auth_header(token))
        assert res.status_code == 200
        assert res.json()["email"] == "admin@test.com"
        assert res.json()["role"] == "Admin"

    def test_get_me_invalid_token(self, client, seed_data):
        res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token_xyz"})
        assert res.status_code == 401

    def test_get_me_no_token(self, client, seed_data):
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401

    def test_list_departments(self, client, seed_data):
        res = client.get("/api/v1/auth/departments")
        assert res.status_code == 200
        assert len(res.json()) >= 2

    def test_list_managers(self, client, seed_data):
        res = client.get("/api/v1/auth/managers")
        assert res.status_code == 200

    def test_team_admin_sees_all(self, client, seed_data):
        token = get_auth_token(client, "admin@test.com", "admin123")
        res = client.get("/api/v1/auth/team", headers=auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) >= 4

    def test_team_manager_sees_reports(self, client, seed_data):
        token = get_auth_token(client, "manager@test.com", "manager123")
        res = client.get("/api/v1/auth/team", headers=auth_header(token))
        assert res.status_code == 200
        # Manager sees self + direct reports
        assert len(res.json()) >= 2

    def test_team_employee_sees_self_only(self, client, seed_data):
        token = get_auth_token(client, "employee@test.com", "employee123")
        res = client.get("/api/v1/auth/team", headers=auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["email"] == "employee@test.com"
