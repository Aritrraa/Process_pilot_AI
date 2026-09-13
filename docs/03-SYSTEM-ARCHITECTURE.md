# System Architecture

## High-Level Architecture
ProcessPilot AI is built on a decoupled client-server architecture.

`mermaid
graph TD
    A[React 19 Frontend] -->|REST/WebSockets| B(FastAPI Backend)
    B -->|SQLAlchemy / asyncpg| C[(PostgreSQL + pgvector)]
    B -->|HTTPS| D[Groq/OpenAI APIs]
`