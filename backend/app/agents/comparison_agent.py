from .base_agent import BaseAgent
from sqlalchemy.orm import Session
from ..models import User
from ..vectorstore import vector_store_manager
from ..llm_client import LLMClient

llm_client = LLMClient()

class ComparisonAgent(BaseAgent):
    """
    Agent responsible for comparing multiple documents or policies and highlighting differences.
    """
    
    def execute(self, query: str, user: User, db: Session, **kwargs) -> str:
        api_key = kwargs.get("api_key")
        llm_provider = kwargs.get("llm_provider", "simulation")
        
        # 1. Search for chunks related to the query
        # We fetch a larger limit to get more context for comparison
        results = vector_store_manager.search(
            query=query, 
            limit=10, 
            department_id=user.department_id if user.role != "Admin" else None,
            api_key=api_key,
            llm_provider=llm_provider
        )
        
        if not results:
            return "I couldn't find any relevant documents to compare for your query."
            
        # 2. Format the context from retrieved chunks
        context_parts = []
        for res in results:
            doc_id = res['metadata'].get('document_id', 'Unknown')
            file_name = res['metadata'].get('file_name', f'Doc {doc_id}')
            text = res['document']
            context_parts.append(f"--- Document: {file_name} (ID: {doc_id}) ---\n{text}")
            
        context_str = "\n\n".join(context_parts)
        
        # 3. Construct the LLM prompt
        prompt = (
            "You are an expert Enterprise Document Analyst.\n"
            "Your task is to compare the provided documents based on the user's query.\n"
            "Highlight the key differences, additions, and removals.\n"
            "Structure your response clearly using Markdown headings (e.g., ### Key Differences, ### Similarities).\n"
            "If the documents do not contain enough information to make a comparison, state that clearly.\n\n"
            f"User Query: {query}\n\n"
            "Retrieved Document Context:\n"
            f"{context_str}\n\n"
            "Please provide your comparison report:"
        )
        
        # 4. Generate the response
        system_prompt = "You are an expert Enterprise Document Analyst."
        return llm_client.call(
            provider=llm_provider,
            api_key=api_key,
            system_prompt=system_prompt,
            user_message=prompt,
            db=db,
            user_id=user.id
        )
