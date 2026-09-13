from typing import Any

from ..vectorstore import vector_store_manager


class SearchAgent:
    def execute(self, query: str, department_id: int | None, api_key: str | None, llm_provider: str = "simulation") -> list[dict[str, Any]]:
        # Retrieve chunks from ChromaDB
        chunks = vector_store_manager.search(query, limit=4, department_id=department_id, api_key=api_key, llm_provider=llm_provider)
        return chunks
