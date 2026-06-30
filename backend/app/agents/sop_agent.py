from typing import List, Optional
import google.generativeai as genai

class SOPAgent:
    def execute(self, query: str, context_chunks: List[str], api_key: Optional[str], llm_provider: str = "simulation", system_prompt: Optional[str] = None) -> str:
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
        if system_prompt:
            prompt = f"System Instruction: {system_prompt}\n\n{prompt}"
        
        if not api_key or llm_provider == "simulation":
            # Fallback mock template generator
            return (
                f"# Standard Operating Procedure: {query.capitalize()} (Simulation Mode)\n\n"
                "## Overview\n"
                "This SOP outlines the protocol for handling the requested process as extracted from local files.\n\n"
                "## Prerequisites\n"
                "- Verify environment variables\n"
                "- Ensure access permissions are granted\n\n"
                "## Step-by-Step Procedure\n"
                "1. **Analyze logs & requirements**: Search for related configurations in settings.\n"
                "2. **Execute Deployment / Operations**: Follow standard deployment instructions.\n"
                "3. **Post-execution review**: Audit status logs to confirm success.\n\n"
                "## Verification\n"
                "- Run standard health check endpoint to verify uptime."
            )
            
        if llm_provider == "openai":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"Error generating SOP via OpenAI API: {str(e)}"
                
        elif llm_provider == "groq":
            try:
                from groq import Groq
                client = Groq(api_key=api_key)
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"Error generating SOP via Groq API: {str(e)}"
                
        elif llm_provider == "gemini":
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Error generating SOP via Gemini API: {str(e)}"
        
        return "Unsupported LLM provider."
