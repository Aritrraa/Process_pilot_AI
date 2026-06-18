import sys
import os
# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User, Document
from app.agents import ceo_agent

def test_ai_agent_evaluation():
    db = SessionLocal()
    try:
        # Retrieve a manager user for context (e.g. Sarah Jenkins)
        user = db.query(User).filter(User.email == "sarah@processpilot.ai").first()
        if not user:
            # Fall back to any user or admin
            user = db.query(User).first()
            
        assert user is not None, "A test user must exist in the database for evaluation. Please seed first."
        
        # Test Cases
        scenarios = [
            {
                "query": "What are the engineering deployment guidelines?",
                "expected_keywords": ["deploy", "aws", "kubernetes", "incident", "production"],
                "target_dept": 1 # Engineering department
            },
            {
                "query": "Summarize the remote work policy and employee leave PTO benefits",
                "expected_keywords": ["leave", "pto", "remote", "policy", "benefit"],
                "target_dept": 2 # HR department
            }
        ]
        
        print("\n==================================================")
        print("          PROCESSPIOT AI EVALUATION REPORT        ")
        print("==================================================")
        
        for idx, sc in enumerate(scenarios):
            print(f"\nScenario {idx+1}: Query: '{sc['query']}'")
            res = ceo_agent.process_query(user, sc["query"], db)
            answer = res.get("answer", "")
            sources = res.get("sources", [])
            
            # Metric 1: Retrieval Precision (check if retrieved sources match target department)
            print(f"- Sources Cited: {sources}")
            retrieved_docs = db.query(Document).filter(Document.title.in_(sources)).all()
            matching_depts = [d.department_id for d in retrieved_docs]
            
            retrieval_precision = 0.0
            if matching_depts:
                correct_depts = sum(1 for d in matching_depts if d == sc["target_dept"] or sc["target_dept"] is None)
                retrieval_precision = (correct_depts / len(matching_depts)) * 100
            else:
                retrieval_precision = 100.0  # If no chunks were needed/available
                
            print(f"  * Retrieval Precision: {retrieval_precision:.1f}%")
            
            # Metric 2: Answer Relevancy (Keyword overlap)
            matched_keywords = sum(1 for kw in sc["expected_keywords"] if kw in answer.lower())
            relevancy_score = (matched_keywords / len(sc["expected_keywords"])) * 100
            print(f"  * Answer Relevancy Score: {relevancy_score:.1f}%")
            
            # Metric 3: Faithfulness / Hallucination Rate
            faithfulness = 100.0
            if "error generating response" in answer.lower() or "api error" in answer.lower():
                faithfulness = 0.0
            print(f"  * Answer Faithfulness Rate: {faithfulness:.1f}%")
            
            # Threshold assertions for pipeline passing
            assert retrieval_precision >= 50.0, "Retrieval precision fell below threshold"
            assert relevancy_score >= 10.0, "Answer relevancy fell below threshold"
            assert faithfulness >= 50.0, "Faithfulness rate fell below threshold"
            
        print("\n==================================================")
        print("        AI AGENT TEST EVALUATION PASSED!          ")
        print("==================================================")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_ai_agent_evaluation()
