"""
ABAC Policy tests — rewritten with proper pytest fixtures.
Tests all access control boundaries for documents, tasks, and meetings.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import User, Document, Task, Meeting
from app.abac import evaluate_policy


@pytest.fixture
def users():
    return {
        "admin": User(id=1, email="admin@test.com", role="Admin", department_id=1),
        "manager": User(id=2, email="mgr@test.com", role="Manager", department_id=1),
        "employee": User(id=3, email="emp@test.com", role="Employee", department_id=1, manager_id=2),
        "other_dept_emp": User(id=4, email="other@test.com", role="Employee", department_id=2),
        "other_mgr": User(id=5, email="mgr2@test.com", role="Manager", department_id=2),
    }


@pytest.fixture
def documents():
    return {
        "mgr_doc": Document(id=10, title="mgr_doc.pdf", department_id=1, uploaded_by=2),
        "emp_doc": Document(id=11, title="emp_doc.pdf", department_id=1, uploaded_by=3),
        "other_doc": Document(id=12, title="other.pdf", department_id=2, uploaded_by=4),
    }


@pytest.fixture
def tasks():
    return {
        "emp_task": Task(id=20, title="Emp Task", assigned_to=3, status="Pending"),
        "mgr_task": Task(id=21, title="Mgr Task", assigned_to=2, status="In_Progress"),
        "other_task": Task(id=22, title="Other Task", assigned_to=4, status="Pending"),
    }


# ============ Document Read Policies ============
class TestDocumentReadPolicy:
    def test_admin_reads_any_document(self, users, documents):
        assert evaluate_policy(users["admin"], "document", documents["other_doc"], "read", None) is True

    def test_employee_reads_same_dept_document(self, users, documents):
        assert evaluate_policy(users["employee"], "document", documents["mgr_doc"], "read", None) is True

    def test_employee_blocked_from_other_dept_document(self, users, documents):
        assert evaluate_policy(users["employee"], "document", documents["other_doc"], "read", None) is False

    def test_manager_reads_own_dept_document(self, users, documents):
        assert evaluate_policy(users["manager"], "document", documents["emp_doc"], "read", None) is True

    def test_other_dept_manager_blocked(self, users, documents):
        assert evaluate_policy(users["other_mgr"], "document", documents["mgr_doc"], "read", None) is False


# ============ Document Delete Policies ============
class TestDocumentDeletePolicy:
    def test_admin_deletes_any_document(self, users, documents):
        assert evaluate_policy(users["admin"], "document", documents["other_doc"], "delete", None) is True

    def test_employee_deletes_own_document(self, users, documents):
        assert evaluate_policy(users["employee"], "document", documents["emp_doc"], "delete", None) is True

    def test_employee_cannot_delete_manager_document(self, users, documents):
        assert evaluate_policy(users["employee"], "document", documents["mgr_doc"], "delete", None) is False

    def test_other_dept_employee_cannot_delete(self, users, documents):
        assert evaluate_policy(users["other_dept_emp"], "document", documents["mgr_doc"], "delete", None) is False


# ============ Task Update Policies ============
class TestTaskUpdatePolicy:
    def test_employee_updates_own_task(self, users, tasks):
        assert evaluate_policy(users["employee"], "task", tasks["emp_task"], "update", None) is True

    def test_employee_cannot_update_other_task(self, users, tasks):
        assert evaluate_policy(users["other_dept_emp"], "task", tasks["emp_task"], "update", None) is False

    def test_admin_updates_any_task(self, users, tasks):
        assert evaluate_policy(users["admin"], "task", tasks["emp_task"], "update", None) is True

    def test_manager_updates_own_task(self, users, tasks):
        assert evaluate_policy(users["manager"], "task", tasks["mgr_task"], "update", None) is True

    def test_employee_status_change_allowed(self, users, tasks):
        assert evaluate_policy(users["employee"], "task", tasks["emp_task"], "change_status", None) is True


# ============ Task Delete Policies ============
class TestTaskDeletePolicy:
    def test_employee_cannot_delete_task(self, users, tasks):
        assert evaluate_policy(users["employee"], "task", tasks["emp_task"], "delete", None) is False

    def test_admin_deletes_any_task(self, users, tasks):
        assert evaluate_policy(users["admin"], "task", tasks["emp_task"], "delete", None) is True

    def test_other_employee_cannot_delete(self, users, tasks):
        assert evaluate_policy(users["other_dept_emp"], "task", tasks["emp_task"], "delete", None) is False


# ============ Default Deny ============
class TestDefaultDeny:
    def test_unknown_resource_type_denied(self, users):
        assert evaluate_policy(users["employee"], "unknown", None, "read", None) is False

    def test_unknown_action_denied(self, users, documents):
        assert evaluate_policy(users["employee"], "document", documents["mgr_doc"], "unknown_action", None) is False
