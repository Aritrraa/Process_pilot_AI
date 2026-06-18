import sys
import os

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User, Document, Task
from app.abac import evaluate_policy

def test_abac_authorization():
    db = SessionLocal()
    try:
        # Mock users representing Subject
        admin = User(id=1, email="admin@test.com", role="Admin", department_id=1, manager_id=None)
        manager = User(id=2, email="manager@test.com", role="Manager", department_id=1, manager_id=None)
        employee = User(id=3, email="employee@test.com", role="Employee", department_id=1, manager_id=2)
        other_employee = User(id=4, email="other@test.com", role="Employee", department_id=2, manager_id=None)
        
        # Mock document representing Object
        doc = Document(id=10, title="file.pdf", department_id=1, uploaded_by=2) # Uploaded by Manager, Dept 1
        
        # Mock task representing Object
        task = Task(id=20, title="Do work", assigned_to=3, status="Pending") # Assigned to Employee 3
        
        print("\n==================================================")
        print("     RUNNING SECURITY ABAC POLICY UNIT TESTS      ")
        print("==================================================")
        
        # Scenario 1: Employee reading a document from their own department (Should succeed)
        print("Scenario 1: Employee reads same-dept document -> Expected: Allowed")
        allowed = evaluate_policy(employee, "document", doc, "read", db)
        print(f"  * Result: {allowed}")
        assert allowed is True, "Employee should be allowed to read document in their department"

        # Scenario 2: Employee from another department reading the document (Should fail)
        print("Scenario 2: Employee reads other-dept document -> Expected: Denied")
        allowed = evaluate_policy(other_employee, "document", doc, "read", db)
        print(f"  * Result: {allowed}")
        assert allowed is False, "Employee from another department should be blocked from reading document"

        # Scenario 3: Employee trying to delete Manager's document (Should fail)
        print("Scenario 3: Employee deletes Manager document -> Expected: Denied")
        allowed = evaluate_policy(employee, "document", doc, "delete", db)
        print(f"  * Result: {allowed}")
        assert allowed is False, "Employee should be blocked from deleting manager's document"

        # Scenario 4: Admin trying to delete Manager's document (Should succeed)
        print("Scenario 4: Admin deletes Manager document -> Expected: Allowed")
        allowed = evaluate_policy(admin, "document", doc, "delete", db)
        print(f"  * Result: {allowed}")
        assert allowed is True, "Admin should be allowed to delete any document"

        # Scenario 5: Employee updating status of their own assigned task (Should succeed)
        print("Scenario 5: Employee updates assigned task -> Expected: Allowed")
        allowed = evaluate_policy(employee, "task", task, "update", db)
        print(f"  * Result: {allowed}")
        assert allowed is True, "Employee should be allowed to update task assigned to them"

        # Scenario 6: Employee trying to update someone else's task (Should fail)
        print("Scenario 6: Employee updates other employee's task -> Expected: Denied")
        allowed = evaluate_policy(other_employee, "task", task, "update", db)
        print(f"  * Result: {allowed}")
        assert allowed is False, "Employee should be blocked from updating a task not assigned to them"

        print("==================================================")
        print("      ALL SECURITY ABAC POLICY TESTS PASSED!      ")
        print("==================================================")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_abac_authorization()
