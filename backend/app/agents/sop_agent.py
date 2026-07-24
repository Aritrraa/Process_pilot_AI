from typing import List, Optional
from ..llm_client import LLMClient

llm_client = LLMClient()

class SOPAgent:
    async def execute(self, query: str, context_chunks: List[str], api_key: Optional[str], llm_provider: str = "simulation", system_prompt: Optional[str] = None) -> str:
        """
        Creates/formats SOPs or instructions.
        """
        prompt = (
            "You are an expert Operations SOP (Standard Operating Procedure) writer.\n"
            "Based on the following document context, draft a standard operating procedure "
            "answering the user's query.\n"
            f"Query: {query}\n\n"
            f"Context:\n" + "\n---\n".join(context_chunks) + "\n\n"
            "Create a clean, formatted Markdown document with sections: 'Overview', 'Prerequisites', 'Step-by-Step Procedure', 'Safety/Verification'."
        )
        sys_p = system_prompt or "You are an expert Operations SOP writer."
        return await llm_client.call(
            provider=llm_provider,
            api_key=api_key or "",
            system_prompt=sys_p,
            user_message=prompt
        )
