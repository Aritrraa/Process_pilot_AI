# Technical Requirements Document (TRD)

## System Requirements
- **Frontend:** React 19, Vite, React Router 7.
- **Backend:** Python 3.x, FastAPI, Uvicorn, SQLAlchemy 2.0.
- **Database:** PostgreSQL (via Supabase) with pgvector extension.
- **AI/LLM:** Multiple providers (Groq, OpenAI, Gemini) and local simulated embedding fallback.

## Security Requirements
- **Implemented:** AES-GCM encryption for API keys, Regex-based PII redaction.
- **NOT Implemented:** Formal SOC2/GDPR certification.