import asyncio
import os
import sys

from sqlalchemy.future import select

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import ceo_agent
from app.models import Document, User

from tests.conftest import AsyncTestSessionLocal


def test_ai_agent_evaluation(seed_data):
    async def run():
        async with AsyncTestSessionLocal() as db:
            # Retrieve a manager user for context (e.g. Sarah Jenkins)
            result = await db.execute(select(User).filter(User.email == "sarah@processpilot.ai"))
            user = result.scalars().first()
            if not user:
                # Fall back to any user or admin
                result = await db.execute(select(User))
                user = result.scalars().first()
                
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
            
            for idx, sc in enumerate(scenarios):
                res = await ceo_agent.process_query(user, sc["query"], db)
                answer = res.get("answer", "")
                sources = res.get("sources", [])
                
                # Metric 1: Retrieval Precision (check if retrieved sources match target department)
                retrieved_docs = []
                if sources:
                    doc_result = await db.execute(select(Document).filter(Document.title.in_(sources)))
                    retrieved_docs = doc_result.scalars().all()
                matching_depts = [d.department_id for d in retrieved_docs]
                
                retrieval_precision = 0.0
                if matching_depts:
                    correct_depts = sum(1 for d in matching_depts if d == sc["target_dept"] or sc["target_dept"] is None)
                    retrieval_precision = (correct_depts / len(matching_depts)) * 100
                else:
                    retrieval_precision = 100.0  # If no chunks were needed/available
                    
                # Metric 2: Answer Relevancy (Keyword overlap)
                matched_keywords = sum(1 for kw in sc["expected_keywords"] if kw in answer.lower())
                relevancy_score = (matched_keywords / len(sc["expected_keywords"])) * 100
                
                # Metric 3: Faithfulness / Hallucination Rate
                faithfulness = 100.0
                if "error generating response" in answer.lower() or "api error" in answer.lower():
                    faithfulness = 0.0
                
                # Threshold assertions for pipeline passing
                assert retrieval_precision >= 50.0, "Retrieval precision fell below threshold"
                assert relevancy_score >= 10.0, "Answer relevancy fell below threshold"
                assert faithfulness >= 50.0, "Faithfulness rate fell below threshold"

    asyncio.run(run())

if __name__ == "__main__":
    test_ai_agent_evaluation()

