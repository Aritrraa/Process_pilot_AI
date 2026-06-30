from typing import List, Dict, Any, Optional
from ..vectorstore import vector_store_manager

class SearchAgent:
    def execute(self, query: str, department_id: Optional[int], api_key: Optional[str], llm_provider: str = "simulation") -> List[Dict[str, Any]]:
        # Retrieve chunks from ChromaDB
        chunks = vector_store_manager.search(query, limit=4, department_id=department_id, api_key=api_key, llm_provider=llm_provider)
        return chunks
