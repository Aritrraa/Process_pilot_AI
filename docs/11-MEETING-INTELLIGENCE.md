# Meeting Intelligence

1. **Input:** Raw meeting transcript.
2. **LLM Parsing:** Sends transcript to Groq/OpenAI with strict JSON schema instructions.
3. **Regex Extraction:** Uses regex to extract JSON, bypassing conversational hallucinations.
4. **Automation:** Automatically parses Action Items into Task database rows.
5. **Notifications:** Fires WebSocket events to assigned users.