
from ..llm_client import LLMClient

llm_client = LLMClient()

class SOPAgent:
    async def execute(self, query: str, context_chunks: list[str], api_key: str | None, llm_provider: str = "simulation", system_prompt: str | None = None) -> str:
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

    async def execute_stream(self, query: str, context_chunks: list[str], api_key: str | None, llm_provider: str = "simulation", system_prompt: str | None = None, db=None, user_id=None):
        prompt = (
            "You are an expert Operations SOP (Standard Operating Procedure) writer.\n"
            "Based on the following document context, draft a standard operating procedure "
            "answering the user's query.\n"
            f"Query: {query}\n\n"
            f"Context:\n" + "\n---\n".join(context_chunks) + "\n\n"
            "Create a clean, formatted Markdown document with sections: 'Overview', 'Prerequisites', 'Step-by-Step Procedure', 'Safety/Verification'."
        )
        sys_p = system_prompt or "You are an expert Operations SOP writer."
        async for chunk in llm_client.stream(
            provider=llm_provider,
            api_key=api_key or "",
            system_prompt=sys_p,
            user_message=prompt,
            db=db,
            user_id=user_id
        ):
            yield chunk

