# ProcessPilot AI — Complete Technical Documentation

> **Generated from**: Deep source-code inspection of every file in the repository.  
> **Methodology**: 4 parallel research agents read every backend, frontend, AI pipeline, and API route file in full.  
> **Policy**: Only functionality verified in the actual codebase is documented. Unverified claims are labeled.

---

## Table of Contents

1. [Project Overview (Simple Terms)](#1-project-overview)
2. [Complete Technology Stack](#2-complete-technology-stack)
3. [Complete Project Structure](#3-complete-project-structure)
4. [Frontend — Complete Explanation](#4-frontend)
5. [Backend — Complete Explanation](#5-backend)
6. [Complete API Documentation](#6-complete-api-documentation)
7. [Database Architecture](#7-database-architecture)
8. [Vector Database — Deep Analysis](#8-vector-database)
9. [Knowledge Graph — Deep Analysis](#9-knowledge-graph)
10. [Complete RAG Pipeline](#10-complete-rag-pipeline)
11. [LLM Implementation](#11-llm-implementation)
12. [Embedding System](#12-embedding-system)
13. [Agents Architecture](#13-agents-architecture)
14. [External APIs](#14-external-apis)
15. [Authentication & Authorization](#15-authentication--authorization)
16. [File Upload & Document Processing](#16-file-upload--document-processing)
17. [Configuration & Environment Variables](#17-configuration--environment-variables)
18. [Complete Data Flows](#18-complete-data-flows)
19. [Error Handling](#19-error-handling)
20. [Logging & Monitoring](#20-logging--monitoring)
21. [Security](#21-security)
22. [Deployment](#22-deployment)
23. [Dependencies](#23-dependencies)
24. [Code-Level Component Map](#24-code-level-component-map)
25. [Feature-by-Feature Documentation](#25-feature-by-feature-documentation)
26. [Major Functions](#26-major-functions)
27. [Major Classes](#27-major-classes)
28. [AI Architecture Summary](#28-ai-architecture-summary)
29. [Project Complexity Assessment](#29-project-complexity-assessment)
30. [Final Project Explanations](#30-final-project-explanations)
31. [Interview-Ready Explanations](#31-interview-ready-explanations)
32. [Final Summary Table](#32-final-summary-table)

---

## 1. Project Overview

### Project Name
**ProcessPilot AI** — An AI-Powered Enterprise Knowledge Management & Process Automation Platform.

### What problem does it solve?
In large organizations, critical knowledge is scattered across PDFs, DOCX files, spreadsheets, meeting transcripts, and task tickets. Employees waste hours searching for the right document, managers lack visibility into team workload, and meeting action items get lost. ProcessPilot AI solves this by:
- Ingesting all organizational documents into a searchable AI brain
- Providing an AI copilot that answers questions using the organization's own data
- Automatically summarizing meetings and extracting action items as tasks
- Visualizing organizational knowledge as an interactive graph
- Enforcing role-based data isolation so employees only see what they should

### Who is the target user?
Enterprise teams with hierarchical structures: **Admins** (system-wide control), **Directors/Managers** (team oversight), and **Employees** (day-to-day knowledge workers and contractors).

### What can the user actually do with it?
1. **Upload documents** (PDF, DOCX, TXT, CSV, XLSX) → AI automatically extracts, chunks, embeds, and indexes them
2. **Ask the AI copilot questions** → Get answers grounded in the organization's actual documents with source citations
3. **Upload meeting transcripts** → AI generates structured summaries and auto-creates task tickets
4. **Manage tasks** on a Kanban board → Assign, track status, and get AI-suggested action items
5. **Explore a Knowledge Graph** → Visualize how departments, people, documents, and tasks connect
6. **Scope AI queries** → Select specific graph nodes to restrict AI context to just those entities
7. **Review AI quality** → Thumbs up/down feedback creates a human-in-the-loop dataset for fine-tuning
8. **Export synthetic datasets** → Admins can export high-quality Q&A pairs as JSONL for LLM fine-tuning
9. **Manage teams** → Transfer employees, swap manager/employee positions, change roles

### What happens when a user opens the application?
```
User opens URL
 ↓
Landing Page (marketing/storybook page with feature demos)
 ↓
User clicks "Sign In"
 ↓
Login Page (enter email + password, or click demo role shortcuts)
 ↓
JWT token stored in localStorage
 ↓
Dashboard loads (stats, doc health, recent AI queries, department overview)
 ↓
Sidebar navigation to Documents, Chat, Tasks, Meetings, Analytics, Graph, Settings
```

### What happens when the user performs the main action (asking the AI)?
```
User types question in Chat page
 ↓
Frontend sends POST /api/v1/chat/ with SSE streaming
 ↓
CEOAgent (orchestrator) receives the query
 ↓
Checks for fast-path queries (org directory, task creation approval)
 ↓
Classifies intent (comparison, SOP generation, or general)
 ↓
Concurrently dispatches sub-agents:
 ├── SearchAgent → Vector DB (Hybrid: Cosine + BM25 via RRF)
 ├── GraphAgent → Knowledge Graph (entity + neighbor traversal)
 ├── IncidentAgent → SQL Task table text search
 └── MemoryAgent → User-specific key-value memory retrieval
 ↓
All context merged + user's analytics/tasks/history injected
 ↓
LLM called (Gemini / OpenAI / Groq / Simulation) with streaming
 ↓
SSE chunks streamed back: metadata → text chunks → done signal
 ↓
Frontend renders markdown with source citations + agent pipeline steps
 ↓
Interaction logged to AgentLog table with full trace
```

### What makes this an AI-powered application?
- **RAG (Retrieval-Augmented Generation)**: Documents are chunked, embedded, and stored in a vector database. User queries are embedded and matched against document chunks to provide grounded answers.
- **Hybrid Search**: Combines semantic vector similarity (cosine) with lexical BM25 matching via Reciprocal Rank Fusion.
- **Multi-Agent Architecture**: A CEO Agent orchestrates specialized sub-agents (Search, Memory, Graph, Incident, Comparison, SOP) that each contribute different types of context.
- **Knowledge Graph RAG**: Entities and relationships are extracted from documents and traversed at query time for topological context.
- **Meeting Summarization**: Raw transcripts are processed by LLMs to generate structured summaries with action items.
- **PII Redaction**: Documents are sanitized via regex + optional Microsoft Presidio NER before embedding.
- **Human-in-the-Loop**: Users can give thumbs-down feedback, which feeds into a synthetic fine-tuning dataset export.
- **Data Flywheel**: When managers edit AI-generated task titles, the system auto-logs this as implicit correction feedback.

---

## 2. Complete Technology Stack

| Category | Technology | Version | Where Used | What It Does | Why It Is Used |
|---|---|---|---|---|---|
| **Frontend Framework** | React | 19.2.6 | `frontend/src/` | Component-based UI rendering | Modern declarative UI with hooks |
| **Frontend Build** | Vite | 5.4.19 | `frontend/vite.config.js` | Dev server, HMR, production bundling | Fastest React build tool |
| **Frontend Routing** | react-router-dom | 7.17.0 | `frontend/src/App.jsx` | Client-side page routing | SPA navigation without full reloads |
| **Frontend Data Fetching** | @tanstack/react-query | 5.101.2 | `frontend/src/main.jsx` | Server-state caching, auto-refetch | Eliminates manual fetch/state boilerplate |
| **Frontend Icons** | lucide-react | 1.18.0 | All page components | SVG icon library | Consistent, tree-shakeable icons |
| **Frontend Sanitization** | DOMPurify | 3.4.11 | `Chat.jsx` | Strips XSS from AI-generated markdown | Prevents stored XSS from AI output |
| **Backend Framework** | FastAPI | 0.110.0 | `backend/app/main.py` | Async REST API server with OpenAPI | High-performance Python API with auto-docs |
| **Backend Server** | Uvicorn | 0.28.0 | `backend/run.py` | ASGI server running FastAPI | Production-grade async HTTP server |
| **ORM** | SQLAlchemy | 2.0.28 | `backend/app/models.py` | Object-Relational Mapping for all DB models | Type-safe database operations |
| **Async DB Driver (Postgres)** | asyncpg | 0.29.0 | `backend/app/database.py` | Async PostgreSQL wire protocol | Non-blocking DB queries in FastAPI |
| **Async DB Driver (SQLite)** | aiosqlite | 0.20.0 | `backend/app/database.py` | Async SQLite adapter for local dev | Local development without Postgres |
| **DB Migrations** | Alembic | 1.18.4 | `backend/alembic/` | Schema version control and migrations | Tracks DB schema changes |
| **Postgres Extensions** | pgvector | 0.5.0 | `backend/app/vectorstore.py` | Native vector similarity search in Postgres | Eliminates need for separate vector DB |
| **Vector DB (Local)** | ChromaDB | 0.4.24 | `backend/app/vectorstore.py` | Local embedded vector database | Zero-config local development |
| **Vector DB (Cloud)** | Pinecone | 3.2.2 | `backend/app/vectorstore.py` | Managed cloud vector database | Production-scale vector search |
| **Hybrid Search** | rank-bm25 | 0.2.2+ | `backend/app/vectorstore.py` | BM25 lexical text matching | Supplements semantic search with keyword matching |
| **LLM: Google** | google-generativeai | 0.4.1 | `backend/app/llm_client.py` | Gemini API for text generation & embeddings | Primary LLM provider |
| **LLM: OpenAI** | openai | 1.30.1 | `backend/app/llm_client.py` | GPT-4/3.5 for text generation & embeddings | Alternative LLM provider |
| **LLM: Groq** | groq | 0.8.0 | `backend/app/llm_client.py` | Llama models via Groq inference | Fast/cheap LLM via semantic routing |
| **PDF Parsing** | PyMuPDF | 1.23.26 | `backend/app/ingestion.py` | Extract text from PDF files | Handles complex PDF layouts |
| **DOCX Parsing** | python-docx | 1.1.0 | `backend/app/ingestion.py` | Extract text from Word documents | Native .docx support |
| **Auth: JWT** | PyJWT | 2.8.0 | `backend/app/auth.py` | JSON Web Token generation/verification | Stateless authentication |
| **Auth: Hashing** | Passlib + bcrypt | 1.7.4 / 4.0.1 | `backend/app/auth.py` | Password hashing with bcrypt | Industry-standard password security |
| **Validation** | Pydantic | 2.6.4 | `backend/app/schemas.py` | Request/response validation | Type-safe API contracts |
| **Configuration** | pydantic-settings | 2.2.1 | `backend/app/config.py` | Environment variable loading | 12-factor app configuration |
| **File Storage (Cloud)** | Supabase | 2.16.0 | `backend/app/storage.py` | S3-compatible object storage | Persistent file storage on ephemeral hosts |
| **HTTP Client** | httpx | 0.27.2 | `backend/app/llm_client.py` | Async HTTP requests to LLM APIs | Non-blocking external API calls |
| **Retry Logic** | tenacity | 8.2.3 | `backend/app/llm_client.py` | Exponential backoff retries | Resilience against transient API failures |
| **Graph Library** | NetworkX | 3.2.1 | `requirements.txt` | Graph data structures (legacy dependency) | Originally used for KG, now replaced by SQL |
| **Async File I/O** | aiofiles | 23.2.1 | `backend/app/routes/documents.py` | Non-blocking file writes | Prevents I/O blocking in async handlers |
| **Email Validation** | email-validator | 2.1.1 | `backend/app/schemas.py` | Validates email format in registration | Prevents malformed email registration |
| **Deployment: Frontend** | Vercel | — | Cloud | Static React app hosting | Free, auto-deploys from GitHub |
| **Deployment: Backend** | Render | — | Cloud | Python web service hosting | Free tier with auto-deploy |
| **Deployment: Database** | Supabase PostgreSQL | — | Cloud | Managed PostgreSQL | Free tier, session pooler for IPv4 |
| **CI/CD** | GitHub Actions | — | `.github/workflows/ci.yml` | Lint (Ruff) + Test (Pytest) + Coverage | Automated quality gates on push/PR |
| **Fonts** | Google Fonts | — | `frontend/index.html` | Inter, Sora, Cormorant Garamond, IBM Plex Mono | Typography system |

---

## 3. Complete Project Structure

```
ProcessPilot_AI/
│
├── .github/
│   └── workflows/
│       └── ci.yml                    # GitHub Actions: lint + test + coverage
│
├── backend/
│   ├── .env                          # Environment variables (gitignored)
│   ├── .gitignore                    # Excludes .env from git
│   ├── run.py                        # Entry point: uvicorn launcher
│   ├── requirements.txt              # Python dependencies (30 packages)
│   ├── alembic.ini                   # Alembic migration config
│   ├── alembic/
│   │   └── env.py                    # Migration environment setup
│   ├── seed_demo.py                  # Populates DB with realistic demo data
│   ├── knowledge_graph.json          # Serialized KG state (legacy)
│   ├── processpilot.db               # SQLite database (local dev)
│   ├── chroma_db/                    # ChromaDB persistence directory
│   ├── uploads/                      # Local file upload directory
│   │
│   └── app/
│       ├── __init__.py               # Package marker
│       ├── main.py                   # FastAPI app, middleware, lifespan, routes
│       ├── config.py                 # Pydantic Settings (env vars, defaults)
│       ├── database.py               # SQLAlchemy async engine + session factory
│       ├── models.py                 # 16 SQLAlchemy ORM models
│       ├── schemas.py                # Pydantic request/response schemas
│       ├── auth.py                   # JWT auth utilities (hash, verify, token)
│       ├── abac.py                   # Attribute-Based Access Control policies
│       ├── audit.py                  # Audit trail logging
│       ├── rate_limiter.py           # In-memory rate limiting decorator
│       ├── pii_redactor.py           # PII redaction (regex + optional Presidio)
│       ├── storage.py                # Supabase/local file storage client
│       ├── analytics.py              # Role-scoped analytics computation
│       ├── ingestion.py              # Document parsing, chunking pipeline
│       ├── vectorstore.py            # Vector DB abstraction (4 providers)
│       ├── knowledge_graph.py        # SQL-backed Knowledge Graph
│       ├── llm_client.py             # Multi-provider LLM client with streaming
│       │
│       ├── agents/
│       │   ├── __init__.py           # Agent exports + session state
│       │   ├── base_agent.py         # Empty base class
│       │   ├── ceo_agent.py          # Main orchestrator (43KB, largest file)
│       │   ├── search_agent.py       # Vector search wrapper
│       │   ├── memory_agent.py       # User memory retrieval/storage
│       │   ├── graph_agent.py        # Knowledge Graph RAG agent
│       │   ├── incident_agent.py     # Task/ticket text search
│       │   ├── comparison_agent.py   # Document comparison via LLM
│       │   └── sop_agent.py          # SOP generation via LLM
│       │
│       └── routes/
│           ├── __init__.py           # Package marker
│           ├── auth.py               # Auth, user mgmt, team mgmt (24KB)
│           ├── documents.py          # Document upload, ingestion, CRUD
│           ├── tasks.py              # Task CRUD with Kanban workflow
│           ├── meetings.py           # Meeting upload + AI summarization
│           ├── chat.py               # AI Copilot SSE streaming endpoint
│           ├── settings.py           # User LLM config management
│           ├── analytics_routes.py   # Dashboard metrics + HITL export
│           ├── knowledge_graph_routes.py  # Graph API endpoints
│           └── ws.py                 # WebSocket connection manager
│
├── frontend/
│   ├── .env                          # VITE_API_URL
│   ├── package.json                  # React 19 + Vite + dependencies
│   ├── vite.config.js                # Vite build configuration
│   ├── index.html                    # HTML shell + Google Fonts
│   │
│   └── src/
│       ├── main.jsx                  # React root + QueryClient + ErrorBoundary
│       ├── App.jsx                   # Router + lazy-loaded pages
│       ├── api.js                    # Fetch-based API client layer
│       ├── index.css                 # Main dark theme stylesheet (38KB)
│       ├── index_crimson.css         # Alternative crimson theme
│       ├── index_light.css           # Alternative light theme
│       │
│       ├── context/
│       │   ├── AuthContext.jsx        # Auth state + login/logout
│       │   └── WebSocketContext.jsx   # Real-time task update notifications
│       │
│       ├── components/
│       │   ├── Layout.jsx            # App shell + manager assignment guard
│       │   ├── Sidebar.jsx           # Navigation menu + user profile
│       │   └── ErrorBoundary.jsx     # React error boundary wrapper
│       │
│       └── pages/
│           ├── Landing.jsx           # Marketing landing page
│           ├── Login.jsx             # Login form + demo shortcuts
│           ├── Register.jsx          # Registration form
│           ├── Dashboard.jsx         # Stats overview
│           ├── Documents.jsx         # File management + drag-drop upload
│           ├── Chat.jsx              # AI Copilot with SSE streaming
│           ├── Tasks.jsx             # Kanban task board
│           ├── Meetings.jsx          # Transcript upload + AI summary
│           ├── Analytics.jsx         # Deep analytics + team management
│           ├── Settings.jsx          # LLM provider + API key config
│           └── Graph.jsx             # Knowledge Graph visualization
│
├── README.md                         # Project overview
├── deployment_guide.md               # Cloud deployment instructions
├── walkthrough.md                    # Change log / walkthrough
├── sample_employees.xlsx             # Sample data file
├── sample_projects.xlsx              # Sample data file
└── sample_datasets/                  # Additional sample data
```

---

## 4. Frontend

### Framework & Language
- **React 19** with **JSX** (not TypeScript)
- **Vite 5** for build tooling with HMR
- **Vanilla CSS** (no Tailwind) — 3 theme files (~38KB each)

### Routing Structure (`App.jsx`)
Uses `react-router-dom` with `lazy()` + `Suspense` for code-splitting:

| Path | Component | Access | Description |
|---|---|---|---|
| `/` | `Landing` | Public | Marketing page |
| `/login` | `Login` | Public | Auth form |
| `/register` | `Register` | Public | Registration form |
| `/dashboard` | `Dashboard` | Protected | Stats overview |
| `/documents` | `Documents` | Protected | File management |
| `/chat` | `Chat` | Protected | AI Copilot |
| `/tasks` | `Tasks` | Protected | Kanban board |
| `/meetings` | `Meetings` | Protected | Meeting summaries |
| `/analytics` | `Analytics` | Protected | Deep analytics |
| `/settings` | `Settings` | Protected | LLM config |
| `/graph` | `Graph` | Protected | Knowledge Graph |

### State Management
- **AuthContext**: Manages `user` state in React Context. On mount, checks `localStorage` for JWT token and calls `GET /auth/me`. Exposes `login()` and `logout()` functions.
- **WebSocketContext**: Connects to `ws://[API]/ws/{user.id}`. Listens for `task_update` events and shows transient toast notifications.
- **@tanstack/react-query**: Used in `Documents.jsx` for automatic data fetching, caching (60s stale time), and refetch-on-mutation.
- **localStorage**: Chat history is persisted client-side in `localStorage`.

### API Client (`api.js`)
- Wrapper around native `fetch()` targeting `VITE_API_URL` (defaults to `http://localhost:8000/api/v1`)
- Automatically attaches `Authorization: Bearer <token>` header
- Parses JSON responses and throws on non-OK status
- Exposes methods for all backend interactions: auth, documents, chat, meetings, tasks, settings, analytics, knowledge graph

### Key Page Components

#### `Landing.jsx` — Marketing Page
- Botanical journal-themed storybook landing page
- Animated visual timeline of platform features
- Fake terminal simulating "Integrity Verification"
- Multi-Agent Sandbox demo simulating RAG queries and agent interactions
- No backend API calls — purely presentational

#### `Login.jsx` — Authentication
- Email + password form with validation
- **Demo shortcut buttons** that auto-fill credentials for Admin, Director, Manager, Employee, Contractor roles
- "Cold boot" warning if login takes > 4 seconds (Render free tier wake-up)
- Calls `POST /auth/login`, stores JWT in `localStorage`

#### `Dashboard.jsx` — Command Center
- Fetches `GET /analytics/` on mount
- Circular SVG chart for "Documentation Health" percentage
- Recent AI queries list (from `AgentLog` data)
- Department size breakdown table
- Quick action tiles linking to other pages

#### `Documents.jsx` — File Management
- Uses `@tanstack/react-query` for fetching documents
- **Drag-and-drop upload zone** with simulated progress bar
- Client-side validation: max 10MB, allowed extensions only
- Calls `POST /documents/upload` with `FormData`
- Polls `GET /documents/{id}/status` for ingestion progress
- Table view with file type badges, department tags, delete buttons

#### `Chat.jsx` — AI Copilot (Most Complex Frontend Component)
- **SSE Streaming**: Bypasses `api.js` to use native `fetch()` with `res.body.getReader()`
- Parses Server-Sent Events: `metadata` (sources + agent steps), `chunk` (incremental text), `done`
- **Scoped Context**: Accepts `scopedNodeIds` from Graph.jsx via router state, sends them to backend to restrict AI context
- Custom `renderMarkdown()` function: strips XSS via DOMPurify, renders lists/headers/bold/code
- Source citation pills below AI messages
- Expandable accordion showing "Agent Pipeline Steps"
- **Thumbs Up / Thumbs Down** buttons that POST HITL feedback to `/chat/feedback`
- Chat history persisted in `localStorage`

#### `Tasks.jsx` — Kanban Board
- Three columns: Pending, In Progress, Completed
- Click-to-advance workflow (Pending → In Progress → Completed)
- Admin/Manager: inline dropdown to reassign tasks to team members
- Client-side search filtering across all columns
- Calls `PATCH /tasks/{id}` on status changes

#### `Meetings.jsx` — Transcript Processing
- Upload raw transcript text or paste a meeting link (Zoom/Google Meet)
- Calls `POST /meetings/` which triggers LLM summarization
- Expandable cards showing AI-generated markdown summary + raw transcript
- Auto-creates Task records from extracted action items

#### `Analytics.jsx` — Deep Dashboard (50KB, Largest Frontend File)
- **Overview Tab**: Custom SVG bar charts for document types, task status, LLM token usage/costs. Stacked progress bars for team workload per member.
- **Team Management Tab**: Admins/Managers can reassign employees, change roles, swap manager↔employee positions, delete users with successor assignment
- **AI Failures Tab**: Reviews thumbs-down feedback. Admin can export as synthetic JSONL fine-tuning dataset via `GET /analytics/synthetic-export`

#### `Graph.jsx` — Knowledge Graph Visualization
- Bloomberg-terminal style layout with 4 columns: Departments, Users, Content (Documents + Meetings), Tasks
- Dynamic SVG edge rendering between related nodes
- **Shift-click** for multi-node selection
- Side drawer shows metadata for selected nodes
- **"Scope AI Chat Session"** button navigates to `/chat` with `scopedNodeIds` in router state

#### `Settings.jsx` — LLM Configuration
- Dropdown: Simulation, Gemini, Groq, OpenAI
- Masked API key inputs (displays `••••••••` for set keys)
- Custom system prompt textarea
- Read-only system tech stack information display

---

## 5. Backend

### Architecture
```
HTTP Request
 ↓
DynamicCORSMiddleware (CORS headers)
 ↓
Global Exception Handlers (500, 422)
 ↓
FastAPI Router (path matching)
 ↓
Rate Limiter (optional, per-endpoint)
 ↓
JWT Authentication (get_current_user dependency)
 ↓
RBAC Check (check_role dependency)
 ↓
ABAC Policy (verify_document_access / verify_task_access)
 ↓
Route Handler (business logic)
 ↓
Service Layer (analytics.py, ingestion.py, vectorstore.py, etc.)
 ↓
Database (SQLAlchemy async) / LLM API / Vector DB
 ↓
Response (JSON or SSE stream)
```

### Entry Point (`run.py`)
```python
uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
```

### Application Setup (`main.py`)
- Creates FastAPI app with `lifespan` context manager
- **Startup**: Creates DB tables (with `CREATE EXTENSION IF NOT EXISTS vector` for Postgres), populates empty Knowledge Graph from existing relational data
- **Middleware**: Custom `DynamicCORSMiddleware` that dynamically evaluates Origins (allows localhost, `*.vercel.app`, and configured origins)
- **Exception Handlers**: Global catch-all for 500s and 422 validation errors
- **Routes mounted**: auth, documents, meetings, tasks, settings, chat, analytics, knowledge_graph, ws — all prefixed under `/api/v1`
- **Root endpoints**: `GET /` (welcome JSON), `GET /health` (basic), `GET /health/detailed` (DB + vector + graph status)

### Configuration (`config.py`)
- `pydantic-settings.BaseSettings` loading from `.env` file
- Auto-detects `production` environment if `DATABASE_URL` contains `postgres`
- **Production safety**: Fails fast if default `SECRET_KEY` is used in production
- Configurable: CORS origins, JWT settings, database URL, vector DB type, upload limits, Supabase credentials, Pinecone/Qdrant credentials

### Database Layer (`database.py`)
- Auto-rewrites connection strings: `postgresql://` → `postgresql+asyncpg://`, `sqlite://` → `sqlite+aiosqlite://`
- Creates `AsyncSession` factory via `async_sessionmaker`
- `get_db()` dependency yields sessions with automatic cleanup

---

## 6. Complete API Documentation

### Authentication & User Management (`/api/v1/auth/`)

| Method | Endpoint | Auth | Rate Limit | Purpose |
|---|---|---|---|---|
| POST | `/auth/register` | Public | 10/hr | Register new user |
| POST | `/auth/login` | Public | 20/hr | Login, returns JWT |
| GET | `/auth/me` | JWT | — | Get current user profile |
| GET | `/auth/departments` | JWT | — | List all departments |
| POST | `/auth/departments` | Admin | — | Create department |
| GET | `/auth/users` | Admin | — | List all users |
| GET | `/auth/managers` | JWT | — | List all managers |
| GET | `/auth/team` | JWT | — | Role-scoped team list |
| PATCH | `/auth/employees/{id}/transfer` | Manager/Admin | — | Transfer employee to new manager |
| PATCH | `/auth/select-manager` | Employee | — | Self-assign manager |
| PATCH | `/auth/users/{id}/role` | Admin | — | Change user role |
| DELETE | `/auth/users/{id}` | Admin | — | Delete user with cascade |
| POST | `/auth/users/swap-positions` | Admin | — | Swap manager ↔ employee |

### Document Management (`/api/v1/documents/`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/documents/upload` | JWT | Upload file (returns 202, background ingestion) |
| GET | `/documents/` | JWT | List documents (ABAC-filtered) |
| GET | `/documents/{id}` | JWT | Get single document |
| GET | `/documents/{id}/status` | JWT | Poll ingestion status |
| DELETE | `/documents/{id}` | Owner/Admin | Delete document + vector cleanup |

### Task Management (`/api/v1/tasks/`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/tasks/` | JWT | Create task |
| GET | `/tasks/` | JWT | List tasks (RBAC-scoped) |
| GET | `/tasks/{id}` | JWT | Get single task |
| PATCH | `/tasks/{id}` | JWT | Update task (status, title, assignee) |
| DELETE | `/tasks/{id}` | Manager/Admin | Delete task |

### Meeting Management (`/api/v1/meetings/`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/meetings/` | JWT | Upload transcript → AI summary + task extraction |
| GET | `/meetings/` | JWT | List meetings |
| GET | `/meetings/{id}` | JWT | Get single meeting |
| DELETE | `/meetings/{id}` | Owner/Admin | Delete meeting |

### AI Copilot (`/api/v1/chat/`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/chat/` | JWT | SSE streaming AI query via CEOAgent |
| POST | `/chat/feedback` | JWT | Submit thumbs-down HITL feedback |

### Settings (`/api/v1/settings/`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/settings/` | JWT | Get user LLM settings (keys masked) |
| PUT | `/settings/` | JWT | Update LLM provider, keys, system prompt |

### Analytics (`/api/v1/analytics/`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/analytics/` | JWT | Role-scoped dashboard metrics |
| GET | `/analytics/ai-failures` | JWT | HITL thumbs-down feedback list |
| GET | `/analytics/synthetic-export` | Admin | JSONL fine-tuning dataset export |

### Knowledge Graph (`/api/v1/knowledge-graph/`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/knowledge-graph/full` | JWT | All nodes + edges |
| GET | `/knowledge-graph/stats` | JWT | Node/edge counts by type |
| GET | `/knowledge-graph/neighbors/{id}` | JWT | Get neighbors of a node |

### WebSocket (`/api/v1/ws/`)

| Protocol | Endpoint | Purpose |
|---|---|---|
| WS | `/ws/{user_id}` | Real-time task update notifications |

### Utility Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health` | Basic health check |
| GET | `/health/detailed` | DB + Vector + KG status |

---

## 7. Database Architecture

### Technology
**SQLAlchemy 2.0** (async) with **PostgreSQL** (production via Supabase) or **SQLite** (local development).

### Models (16 total)

#### Core Models

```
Department (id, name, description)
 │
 ├── 1:N → User (id, email, hashed_password, full_name, role, department_id, manager_id, created_at)
 │           │
 │           ├── 1:1 → UserSetting (gemini_api_key, groq_api_key, openai_api_key, llm_provider, system_prompt)
 │           ├── 1:N → Memory (key, value, updated_at)
 │           ├── 1:N → AgentLog (query, response, agent_steps JSON, timestamp)
 │           └── 1:N → AuditLog (action, resource_type, resource_id, details, ip_address, timestamp)
 │
 ├── 1:N → Document (title, file_path, storage_path, storage_url, ingestion_status, file_type, uploaded_by, created_at)
 │           │
 │           ├── 1:N → DocumentChunk (content, chunk_index, metadata_json)
 │           ├── 1:N → DocumentEmbedding (chunk_index, content, embedding Vector(768), metadata_json)
 │           └── 1:N → Task
 │
 └── 1:N → Meeting (title, transcript, meeting_link, summary, uploaded_by, created_at)
              │
              └── 1:N → Task (title, description, status, assigned_to, manager_id, document_id, meeting_id, ai_generated_title)
```

#### AI/ML Models
```
LLMUsage (user_id, provider, model, input_tokens, output_tokens, estimated_cost, timestamp)
Conversation (user_id, title, created_at) → ConversationMessage (role, content, metadata_json)
PromptVersion (name, content, version, is_active) — System prompt A/B testing
AIFailure (user_id, query, ai_response, feedback_type, correction, created_at) — HITL feedback
```

#### Knowledge Graph Models
```
KGNode (entity_id, entity_type, label, properties JSON)
KGEdge (source_entity_id, target_entity_id, relationship, properties JSON)
```

### Cascade Rules
- `Document.department_id` → `ondelete="SET NULL"`
- `Document.uploaded_by` → `ondelete="SET NULL"`
- `Task.assigned_to` → `ondelete="SET NULL"`
- `DocumentChunk.document_id` → `ondelete="CASCADE"`
- `AgentLog.user_id` → `ondelete="CASCADE"`
- `Memory.user_id` → `ondelete="CASCADE"`

### Key Relationships
- **Self-referential**: `User.manager_id` → `User.id` (hierarchical org structure)
- **Cross-entity**: `Task` connects to both `Document` and `Meeting` (action items can come from either)

---

## 8. Vector Database — Deep Analysis

### Supported Providers
| Provider | Class | Use Case |
|---|---|---|
| ChromaDB | `ChromaVectorStore` | Local development |
| Pinecone | `PineconeVectorStore` | Cloud production |
| Qdrant | `QdrantVectorStore` | Alternative cloud |
| PGVector | `PGVectorStore` | Native Postgres (via pgvector extension) |

### Embedding Model
| Provider | Model | Dimensions |
|---|---|---|
| Gemini | `models/text-embedding-004` | 768 |
| OpenAI | `text-embedding-3-small` | 1536 |
| Simulation | Deterministic hash-based | 768 |

### Hybrid Search (ChromaDB Implementation)
```
User Query
 ↓
Generate query embedding (768 or 1536 dims)
 ↓
┌─────────────────────┐    ┌──────────────────┐
│  Vector Similarity   │    │   BM25 Lexical    │
│  (Cosine Distance)   │    │   (Text Match)    │
│  Top-K from ChromaDB │    │  In-memory index  │
└─────────┬───────────┘    └────────┬─────────┘
          │                         │
          └──────────┬──────────────┘
                     ↓
         Reciprocal Rank Fusion (RRF)
                     ↓
              Merged Results
                     ↓
         Department ID Filtering
                     ↓
           Top-5 Context Chunks
```

### Document Ingestion Pipeline
```
Document (PDF/DOCX/TXT/CSV/XLSX)
 ↓
Parser (PyMuPDF / python-docx / pandas)
 ↓
Raw Text Extraction
 ↓
PII Redaction (regex + optional Presidio NER)
 ↓
Semantic Chunking (800 chars, 150 overlap)
 ├── Split by: ## headers → \n\n paragraphs → \n lines → . sentences → words
 ↓
Metadata Attachment (file_name, department_id, chunk_index)
 ↓
Embedding Generation (Gemini/OpenAI/Simulation)
 ↓
Batch Insert to Vector DB (50 chunks per batch to prevent OOM)
 ↓
Store readable chunks in SQL DocumentChunk table
 ↓
Update Document.ingestion_status → "done" or "failed"
```

### Query-Time Retrieval
```
User Query String
 ↓
Generate Query Embedding
 ↓
Vector Search (filtered by department_id)
 ↓
Top-5 Similar Chunks (with metadata)
 ↓
Return as context to CEOAgent
```

---

## 9. Knowledge Graph — Deep Analysis

### Implementation
**SQL-backed** using `KGNode` and `KGEdge` SQLAlchemy models. NOT a dedicated graph database like Neo4j.

### Node Types
| Type | Examples |
|---|---|
| `department` | Engineering, HR, Finance |
| `user` | Individual employees |
| `document` | Uploaded files |
| `meeting` | Uploaded transcripts |
| `task` | Action items |
| `technology` | Extracted from document titles |

### Relationship Types
| Relationship | Source → Target |
|---|---|
| `member_of` | User → Department |
| `reports_to` | User → Manager |
| `uploaded` | User → Document |
| `belongs_to` | Document → Department |
| `covers` | Document → Technology |

### Graph Construction
```
Document Upload Event
 ↓
knowledge_graph.index_document(document, user, department)
 ↓
Creates/Updates Nodes:
 ├── Document node (title, type, status)
 ├── Department node (if not exists)
 ├── User node (if not exists)
 └── Technology nodes (extracted from title keywords)
 ↓
Creates Edges:
 ├── Document --belongs_to--> Department
 ├── User --uploaded--> Document
 └── Document --covers--> Technology
```

### Graph RAG (Query-Time)
```
User Query
 ↓
GraphAgent extracts keywords
 ↓
Searches KGNode labels for matches
 ↓
For each matched node: retrieves up to 4 neighbors
 ↓
Formats as "Entity [type]: label → relationship → neighbor [type]"
 ↓
Injected as additional context into LLM prompt
```

### Vector Search + Knowledge Graph Interaction
```
User Query
 ↓
CEOAgent dispatches concurrently:
 ├── SearchAgent → Vector DB → semantic document chunks
 ├── GraphAgent → KG Nodes/Edges → topological relationships
 └── IncidentAgent → SQL Tasks → ticket context
 ↓
All results merged into unified context string
 ↓
LLM generates answer grounded in both semantic + structural context
```

---

## 10. Complete RAG Pipeline

### Ingestion Pipeline (Verified ✅)
```
File Upload (POST /documents/upload)
 ↓ (202 Accepted immediately)
 ↓
Background Task (asyncio.to_thread with semaphore)
 ↓
extract_content_from_bytes() [ingestion.py]
 ├── PDF → fitz.open() → page.get_text()
 ├── DOCX → python-docx → paragraph.text
 ├── XLSX/CSV → pandas → DataFrame.to_string()
 └── TXT/MD → direct read
 ↓
redact_document() [pii_redactor.py]
 ├── Layer 1: Presidio NER (if installed)
 └── Layer 2: Regex patterns (emails, SSN, phone, CC, IP, passport, DOB)
 ↓
chunk_text(text, 800, 150) [ingestion.py]
 ↓ Recursive splitting: headers → paragraphs → lines → sentences → words
 ↓
EmbeddingProvider.get_embeddings(chunks) [vectorstore.py]
 ↓
VectorStore.add_chunks() [vectorstore.py]
 ↓ Batched in groups of 50
 ↓
SQL: INSERT DocumentChunk records
 ↓
SQL: UPDATE Document SET ingestion_status = 'done'
```

### Query Pipeline (Verified ✅)
```
User types question in Chat UI
 ↓
POST /api/v1/chat/ (SSE stream)
 ↓
CEOAgent.process_query_stream()
 ↓
1. Safety: Check turn limit (max 10 per session)
 ↓
2. Fast-path checks:
   ├── Org directory query? → RBAC-filtered SQL response (no LLM)
   └── Pending task approval? → Intercept and create task
 ↓
3. Intent classification (keyword-based):
   ├── "compare" → ComparisonAgent path
   ├── "sop"/"procedure" → SOPAgent path
   └── default → General retrieval path
 ↓
4. Context gathering (concurrent):
   ├── SearchAgent → VectorDB hybrid search → top-5 chunks
   ├── GraphAgent → KG entity + neighbor traversal
   ├── IncidentAgent → SQL text search on Tasks table
   └── MemoryAgent → User-specific key-value memory
 ↓
5. Context compilation:
   ├── Document chunks with source citations
   ├── Graph relationships
   ├── Task tickets
   ├── System analytics summary
   ├── User's current tasks
   ├── Org directory (RBAC-scoped)
   ├── User memories
   └── Conversation history
 ↓
6. LLM call (streaming):
   ├── System prompt (custom or default)
   ├── Compiled context as user message
   └── Provider: Gemini / OpenAI / Groq / Simulation
 ↓
7. SSE response:
   ├── Event: metadata {sources: [...], steps: [...]}
   ├── Event: chunk {text: "..."} (repeated)
   └── Event: done {}
 ↓
8. Post-processing:
   ├── MemoryAgent stores any "remember" directives
   └── AgentLog record created with full trace
```

> **NOT IMPLEMENTED / NOT VERIFIED**: LangChain, LangGraph, re-ranking, query rewriting, multi-hop retrieval.

---

## 11. LLM Implementation

### Providers (`llm_client.py`)

| Provider | Models Used | When |
|---|---|---|
| **Gemini** | `gemini-2.0-flash` | Default when user sets `llm_provider=gemini` |
| **OpenAI** | `gpt-4o-mini` | When user sets `llm_provider=openai` |
| **Groq** | `llama-3.1-8b-instant` (simple queries), `llama-3.3-70b-versatile` (complex) | When user sets `llm_provider=groq` |
| **Simulation** | None (hardcoded responses) | Default mode, no API key needed |

### Semantic Routing (Groq Only)
Short/simple queries (< 100 chars, no complex words) → cheap `llama-3.1-8b-instant`.  
Complex queries → powerful `llama-3.3-70b-versatile`.

### Fault Tolerance
- **Exponential backoff**: 3 retries with 1s, 2s, 4s delays
- **Circuit breaker**: After 5 consecutive failures, all subsequent calls fall back to simulation mode
- **Exact-match caching**: Hash of `(system_prompt + user_message)` → cached response

### Cost Tracking
- Estimates token counts (input chars / 4, output chars / 4)
- Applies per-provider pricing rates
- Stores in `LLMUsage` SQL table for analytics

### Streaming
- All providers support async streaming
- Gemini: `model.generate_content_async(stream=True)`
- OpenAI: `client.chat.completions.create(stream=True)`
- Groq: `client.chat.completions.create(stream=True)`
- Simulation: yields hardcoded chunks with `asyncio.sleep(0.02)` delays

---

## 12. Embedding System

### Provider Selection
Determined by user's `llm_provider` setting in `UserSetting`:
- `gemini` → Google `models/text-embedding-004` (768 dims)
- `openai` → OpenAI `text-embedding-3-small` (1536 dims)
- `simulation` → Deterministic hash-based random vectors (768 dims)

### Where Embeddings Are Generated
1. **Document ingestion** (`vectorstore.py` → `EmbeddingProvider.get_embeddings()`): Chunks are embedded in batches during background ingestion
2. **Query time** (`vectorstore.py` → `EmbeddingProvider.get_embedding()`): Single query string embedded for similarity search

### Why Embeddings Are Required
Embeddings convert text into numerical vectors that capture semantic meaning. This enables:
- **Semantic search**: Finding relevant document chunks even when the user's query uses different words than the document
- **Department isolation**: Metadata filtering ensures users only retrieve chunks from their own department's documents

---

## 13. Agents Architecture

### Hierarchy
```
CEOAgent (Orchestrator)
 ├── SearchAgent      — Vector DB retrieval
 ├── MemoryAgent      — User memory read/write
 ├── GraphAgent       — Knowledge Graph RAG
 ├── IncidentAgent    — Task/ticket SQL search
 ├── ComparisonAgent  — Document diff via LLM
 └── SOPAgent         — SOP generation via LLM
```

### Agent Details

#### CEOAgent (`ceo_agent.py`, 43KB)
- **Role**: Primary orchestrator. Routes queries, enforces RBAC, manages sub-agents, compiles context, calls LLM
- **Key Methods**:
  - `process_query_stream()`: Main SSE streaming entry point
  - `_get_org_directory()`: RBAC-enforced directory queries (Admin sees all, Manager sees reports, Employee sees peers)
  - `_handle_org_directory_query()`: Fast-path that returns directory data without LLM
- **Loop Prevention**: Max 10 turns per active session
- **Human-in-the-Loop**: Intercepts task creation requests for user approval

#### SearchAgent (`search_agent.py`)
- Thin wrapper around `vector_store_manager.search(query, department_id, api_key, provider)`
- Returns top-5 relevant document chunks

#### MemoryAgent (`memory_agent.py`)
- **Retrieve**: Queries `Memory` SQL table for user's stored key-value pairs
- **Store**: Detects "remember" directives in queries and persists new memories

#### GraphAgent (`graph_agent.py`)
- Extracts keywords from query
- Searches `KGNode` labels
- Traverses up to 4 neighbors per matched node
- Returns formatted graph context strings

#### IncidentAgent (`incident_agent.py`)
- SQL `LIKE` query against `Task.title` and `Task.description`
- Returns matching task tickets as context

#### ComparisonAgent (`comparison_agent.py`)
- Fetches 10 chunks (larger context) from vector DB
- Prompts LLM to identify differences between documents

#### SOPAgent (`sop_agent.py`)
- Uses retrieved context to generate structured Markdown SOP
- Format: Overview → Prerequisites → Step-by-Step → Safety Notes

> **NOT IMPLEMENTED / NOT VERIFIED**: LangChain, LangGraph, tool calling, function calling, agent loops, conditional edges.

---

## 14. External APIs

| API | Provider | Purpose | Called From | Authentication |
|---|---|---|---|---|
| Gemini API | Google | Text generation + embeddings | `llm_client.py`, `vectorstore.py` | API key via user settings |
| OpenAI API | OpenAI | Text generation + embeddings | `llm_client.py`, `vectorstore.py` | API key via user settings |
| Groq API | Groq | Fast LLM inference | `llm_client.py` | API key via user settings |
| Pinecone API | Pinecone | Cloud vector storage/search | `vectorstore.py` | `PINECONE_API_KEY` env var |
| Supabase Storage | Supabase | File upload/download | `storage.py` | `SUPABASE_URL` + `SUPABASE_KEY` env vars |
| Supabase PostgreSQL | Supabase | Relational database | `database.py` | `DATABASE_URL` env var |

> API keys for LLM providers are stored **per-user** in the `UserSetting` table, not as global environment variables. This allows each user to bring their own key.

---

## 15. Authentication & Authorization

### Authentication Flow
```
User submits email + password
 ↓
POST /api/v1/auth/login
 ↓
Verify email exists in DB
 ↓
bcrypt.verify(password, hashed_password)
 ↓
Generate JWT (HS256, 24hr expiry) containing {sub: user_id}
 ↓
Return {access_token, token_type: "bearer"}
 ↓
Frontend stores in localStorage
 ↓
All subsequent requests include Authorization: Bearer <token>
 ↓
Backend: get_current_user() decodes JWT, loads User from DB
```

### RBAC (Role-Based Access Control)
Enforced via `check_role()` dependency:
- **Admin**: Full system access, can manage all users, departments, documents
- **Director**: Same as Manager with broader visibility
- **Manager**: Can manage direct reports, view team documents/tasks
- **Employee**: Can view own department data, manage own tasks
- **Contractor**: Limited employee access

### ABAC (Attribute-Based Access Control)
Enforced via `abac.py` policies:
- **Documents**: Read access scoped by department. Delete limited to uploader or Admin.
- **Tasks**: Update limited to assignee. Delete limited to Manager of assignee or Admin.
- **Meetings**: View scoped to team members.
- **Admin bypass**: All ABAC checks return `True` for Admin role.

### Security Features
- Passwords hashed with bcrypt (Passlib)
- JWT tokens with HS256 algorithm, 24-hour expiry
- Admin registration blocked (cannot self-register as Admin)
- Production safety check: crash on startup if default SECRET_KEY detected

---

## 16. File Upload & Document Processing

```
User drags file onto Documents page
 ↓
Client validates: size < 10MB, extension ∈ {pdf, docx, txt, csv, xlsx, md}
 ↓
POST /documents/upload (multipart/form-data)
 ↓
Server streams file to disk in 1MB chunks (prevents OOM)
 ↓
StorageClient uploads to Supabase Storage bucket (if configured)
 ↓
SQL: INSERT Document (status: "pending")
 ↓
Return 202 Accepted immediately
 ↓
BackgroundTask spawned (with asyncio.to_thread + semaphore)
 ↓
extract_content_from_bytes():
 ├── PDF → PyMuPDF page extraction
 ├── DOCX → python-docx paragraph extraction
 ├── XLSX/CSV → pandas DataFrame → string
 └── TXT/MD → direct UTF-8 read
 ↓
PII Redaction (regex patterns + optional Presidio NER)
 ↓
Semantic Chunking (800 char chunks, 150 char overlap)
 ↓
Embedding Generation (batched, 50 chunks at a time)
 ↓
Vector DB Insertion (ChromaDB / Pinecone / PGVector)
 ↓
SQL: INSERT DocumentChunk records
 ↓
SQL: UPDATE Document SET ingestion_status = "done"
 ↓
Frontend polls GET /documents/{id}/status until "done"
```

### Supported File Types
| Extension | Parser | Library |
|---|---|---|
| `.pdf` | Page-by-page text extraction | PyMuPDF (fitz) |
| `.docx` | Paragraph iteration | python-docx |
| `.xlsx`, `.xls` | Sheet-by-sheet DataFrame | pandas |
| `.csv` | DataFrame | pandas |
| `.txt`, `.md` | Direct read | Built-in |

---

## 17. Configuration & Environment Variables

| Variable | Purpose | Required | Default |
|---|---|---|---|
| `DATABASE_URL` | PostgreSQL/SQLite connection string | Yes | `sqlite:///./processpilot.db` |
| `SECRET_KEY` | JWT signing key | Yes (production) | Dev default (crashes in prod) |
| `BACKEND_CORS_ORIGINS` | Allowed frontend origins (comma-separated) | No | localhost:5173, localhost:3000 |
| `ENVIRONMENT` | `development` or `production` | No | Auto-detected from DB URL |
| `VECTOR_DB_TYPE` | `pgvector`, `pinecone`, `qdrant`, `chroma` | No | `pgvector` |
| `PINECONE_API_KEY` | Pinecone authentication | If using Pinecone | None |
| `PINECONE_INDEX` | Pinecone index name | If using Pinecone | `processpilot` |
| `QDRANT_URL` | Qdrant server URL | If using Qdrant | None |
| `QDRANT_API_KEY` | Qdrant authentication | If using Qdrant | None |
| `CHROMA_PERSIST_DIR` | ChromaDB local storage path | If using ChromaDB | `./chroma_db` |
| `SUPABASE_URL` | Supabase project URL | For cloud storage | None |
| `SUPABASE_KEY` | Supabase anon/public key | For cloud storage | None |
| `SUPABASE_STORAGE_BUCKET` | Supabase storage bucket name | For cloud storage | `documents` |
| `UPLOAD_DIR` | Local upload directory | No | `./uploads` |
| `MAX_UPLOAD_SIZE_MB` | Max file size | No | `10` |
| `REDIS_URL` | Redis connection | No | `redis://localhost:6379/0` |
| `VITE_API_URL` | Backend API URL (frontend) | Yes (production) | `http://localhost:8000/api/v1` |

> **Note**: `REDIS_URL` is configured but Redis is **NOT IMPLEMENTED / NOT VERIFIED** as actually used anywhere in the codebase. The rate limiter uses in-memory storage instead.

---

## 18. Complete Data Flows

### User Registration
```
Register page form submission
 ↓
POST /api/v1/auth/register {email, password, full_name, role, department_id, manager_id}
 ↓
Validate email uniqueness
 ↓
Block Admin self-registration (403)
 ↓
Hash password with bcrypt
 ↓
INSERT User → INSERT UserSetting (blank)
 ↓
Return UserResponse (201)
 ↓
Redirect to Login page
```

### User Login
```
Login page form submission
 ↓
POST /api/v1/auth/login {email, password}
 ↓
SELECT User WHERE email = ?
 ↓
bcrypt.verify(password, user.hashed_password)
 ↓
Generate JWT {sub: user.id, exp: now + 24h}
 ↓
Return {access_token, token_type: "bearer"}
 ↓
Frontend stores token in localStorage
 ↓
GET /api/v1/auth/me (with Bearer token)
 ↓
AuthContext updates user state
 ↓
Redirect to /dashboard
```

### AI Query (Main Workflow)
```
Chat.jsx: user types question, clicks send
 ↓
fetch POST /api/v1/chat/ {query, scoped_node_ids?, history}
 ↓
SSE stream opened
 ↓
CEOAgent.process_query_stream(query, user, db, settings)
 ↓
Safety check: session turn < 10
 ↓
Fast-path: is this an org directory query? → return SQL data directly
 ↓
Intent: comparison? → ComparisonAgent
         SOP? → SOPAgent
         general? → continue
 ↓
Concurrent sub-agent dispatch:
 ├── SearchAgent.execute(query, dept_id) → vector chunks
 ├── GraphAgent.execute(query, db) → graph neighbors
 ├── IncidentAgent.execute(query, db) → task tickets
 └── MemoryAgent.retrieve(user_id, db) → user memories
 ↓
Compile all context + analytics + tasks + history
 ↓
LLMClient.stream(system_prompt, compiled_context)
 ↓
yield SSE events: metadata → chunk → chunk → ... → done
 ↓
Chat.jsx: ReadableStream reader processes chunks
 ↓
Messages rendered with markdown + source pills + agent steps
 ↓
Post-LLM: MemoryAgent stores any "remember" directives
 ↓
INSERT AgentLog {query, response, steps, timestamp}
```

### Document Upload
```
Documents.jsx: file dropped onto upload zone
 ↓
Client validation (size, extension)
 ↓
POST /api/v1/documents/upload (FormData)
 ↓
Server streams to disk (1MB chunks)
 ↓
StorageClient.upload() → Supabase or local
 ↓
INSERT Document (status: pending)
 ↓
Return 202
 ↓
Background: extract → redact PII → chunk → embed → store vectors → store chunks
 ↓
UPDATE Document status → done/failed
 ↓
KnowledgeGraph.index_document() → create nodes + edges
 ↓
Frontend polls /status until done
```

### Meeting Summarization
```
Meetings.jsx: paste transcript text or URL
 ↓
POST /api/v1/meetings/ {title, transcript, meeting_link}
 ↓
If URL provided: extract mock text (or use transcript directly)
 ↓
asyncio.to_thread → LLM call with summarization prompt
 ↓
Parse LLM JSON response: {summary, action_items[]}
 ↓
INSERT Meeting {title, transcript, summary}
 ↓
For each action_item: INSERT Task {title, status: "Pending", assigned_to: user}
 ↓
Return meeting with summary + created tasks
```

---

## 19. Error Handling

### Backend
- **Global exception handler** (`main.py`): Catches all unhandled exceptions → returns 500 JSON
- **Validation exception handler**: Catches Pydantic `RequestValidationError` → returns 422 with field details
- **Per-route try/except**: Most route handlers wrap logic in try/except for specific HTTP errors (400, 401, 403, 404)
- **Background task errors**: Ingestion failures caught and logged; `ingestion_status` set to `"failed"`
- **LLM errors**: Circuit breaker falls back to simulation mode after 5 failures; exponential backoff retries

### Frontend
- **ErrorBoundary** (`ErrorBoundary.jsx`): React error boundary wrapping the entire app
- **API errors**: `api.js` throws on non-OK responses; pages catch in try/catch and display error banners
- **Chat streaming errors**: Reader errors caught; error message appended to chat history

---

## 20. Logging & Monitoring

### Logging Framework
- Python `logging` module with custom logger name `"processpilot"`
- Log levels used: INFO, WARNING, ERROR, DEBUG
- Key log points:
  - `[Startup]` — Database and KG initialization
  - `[Storage]` — Supabase connection status
  - `[Ingest]` — Document processing progress
  - `[PII]` — Redaction counts
  - `[KnowledgeGraph]` — Entity/relationship counts
  - `[LLM]` — Provider selection, token counts, costs, failures

### AI Observability
- `AgentLog` table: Full query + response + agent steps (JSON) per interaction
- `LLMUsage` table: Token counts + estimated costs per provider per call
- `AIFailure` table: Human feedback (thumbs down) with original query + AI response
- `AuditLog` table: Action-level compliance trail (who did what, when, from which IP)

### Monitoring Endpoints
- `GET /health` — Basic alive check
- `GET /health/detailed` — Database connectivity + vector store status + KG node count

---

## 21. Security

### Implemented Security Measures
| Area | Implementation | File |
|---|---|---|
| Password hashing | bcrypt via Passlib | `auth.py` |
| JWT authentication | HS256, 24hr expiry | `auth.py` |
| Admin registration block | Cannot self-register as Admin | `routes/auth.py` |
| Production SECRET_KEY check | Crashes on startup if default key in production | `config.py` |
| CORS | Dynamic origin validation | `main.py` |
| Rate limiting | In-memory per-IP limiting (10/hr register, 20/hr login) | `rate_limiter.py` |
| RBAC | Role-based route protection | `auth.py`, route files |
| ABAC | Attribute-based resource access | `abac.py` |
| PII redaction | Regex + Presidio before embedding | `pii_redactor.py` |
| XSS prevention | DOMPurify on AI output | `Chat.jsx` |
| API key masking | Settings endpoint returns booleans, not keys | `routes/settings.py` |
| File validation | Size + extension checks on upload | `routes/documents.py` |
| Audit trail | Action logging with IP address | `audit.py` |
| SQL injection | SQLAlchemy parameterized queries | All route files |

### Known Limitations
- Rate limiter is **in-memory** (resets on server restart, not shared across workers)
- `REDIS_URL` configured but Redis not actually used
- WebSocket connections are not authenticated (only user_id path parameter)
- No CSRF protection (mitigated by JWT Bearer tokens)

---

## 22. Deployment

### Architecture
```
┌──────────────────┐          ┌──────────────────┐
│   Vercel (Free)  │   HTTP   │   Render (Free)  │
│   React Frontend │ ──────── │  FastAPI Backend  │
│   Static SPA     │          │  Python 3.11     │
└──────────────────┘          └────────┬─────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
              ┌─────▼─────┐    ┌──────▼──────┐    ┌─────▼─────┐
              │ Supabase   │    │ Supabase    │    │ Pinecone  │
              │ PostgreSQL │    │ Storage     │    │ Vector DB │
              │ (Session   │    │ (documents  │    │ (embeddings│
              │  Pooler)   │    │  bucket)    │    │  index)   │
              └────────────┘    └─────────────┘    └───────────┘
```

### CI/CD Pipeline (`.github/workflows/ci.yml`)
Triggers on push/PR to `main`:
1. **Setup**: Python 3.11 with pip caching
2. **Install**: Backend requirements + pytest + ruff
3. **Lint**: `ruff check backend/` with GitHub output format
4. **Test**: `pytest backend/tests/` with coverage report
5. **Coverage**: Upload to Codecov

### Render Configuration
- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python run.py`
- **Instance Type**: Free (sleeps after 15 min inactivity)

### Vercel Configuration
- **Root Directory**: `frontend`
- **Framework Preset**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Environment**: `VITE_API_URL` pointing to Render URL

---

## 23. Dependencies

### Backend (Python)

| Package | Version | Purpose | Why Needed |
|---|---|---|---|
| `fastapi` | 0.110.0 | Web framework | Async API server with OpenAPI |
| `uvicorn` | 0.28.0 | ASGI server | Runs FastAPI in production |
| `sqlalchemy` | 2.0.28 | ORM | Database abstraction |
| `asyncpg` | 0.29.0 | Postgres driver | Async PostgreSQL queries |
| `aiosqlite` | 0.20.0 | SQLite driver | Local dev async queries |
| `alembic` | 1.18.4 | Migrations | DB schema versioning |
| `pgvector` | 0.5.0 | Vector extension | Native Postgres vector search |
| `pydantic` | 2.6.4 | Validation | Request/response schemas |
| `pydantic-settings` | 2.2.1 | Config | Environment variable loading |
| `pyjwt` | 2.8.0 | JWT | Authentication tokens |
| `passlib` | 1.7.4 | Hashing | Password hashing |
| `bcrypt` | 4.0.1 | Bcrypt | Hash algorithm |
| `python-multipart` | 0.0.9 | Multipart | File upload parsing |
| `google-generativeai` | 0.4.1 | Gemini | LLM + embeddings |
| `openai` | 1.30.1 | OpenAI | LLM + embeddings |
| `groq` | 0.8.0 | Groq | Fast LLM inference |
| `chromadb` | 0.4.24 | Vector DB | Local vector storage |
| `pinecone-client` | 3.2.2 | Pinecone | Cloud vector storage |
| `rank-bm25` | 0.2.2+ | BM25 | Lexical search for hybrid |
| `pymupdf` | 1.23.26 | PDF parser | Text extraction from PDFs |
| `python-docx` | 1.1.0 | DOCX parser | Text extraction from Word |
| `networkx` | 3.2.1 | Graph lib | Legacy (KG now SQL-backed) |
| `numpy` | 1.26.4 | Numeric | Array operations for embeddings |
| `httpx` | 0.27.2 | HTTP client | Async external API calls |
| `tenacity` | 8.2.3 | Retry | Exponential backoff for LLM |
| `aiofiles` | 23.2.1 | Async I/O | Non-blocking file writes |
| `email-validator` | 2.1.1 | Validation | Email format checking |
| `psycopg2-binary` | 2.9.9 | Postgres | Sync Postgres (Alembic) |
| `supabase` | 2.16.0 | Storage | Cloud file storage |

> **Potentially Unused**: `networkx` (Knowledge Graph is now SQL-backed via KGNode/KGEdge models, not NetworkX)

### Frontend (JavaScript)

| Package | Version | Purpose |
|---|---|---|
| `react` | 19.2.6 | UI framework |
| `react-dom` | 19.2.6 | DOM rendering |
| `react-router-dom` | 7.17.0 | Client-side routing |
| `@tanstack/react-query` | 5.101.2 | Server-state management |
| `lucide-react` | 1.18.0 | Icon library |
| `dompurify` | 3.4.11 | XSS sanitization |

---

## 24. Code-Level Component Map

### AI Chat Query Flow
```
frontend/src/pages/Chat.jsx
 ↓ fetch POST /api/v1/chat/
frontend/src/api.js (bypassed for streaming)
 ↓
backend/app/routes/chat.py → process_query_stream()
 ↓
backend/app/agents/ceo_agent.py → CEOAgent.process_query_stream()
 ├── backend/app/agents/search_agent.py → VectorStoreManager.search()
 │    ↓
 │    backend/app/vectorstore.py → ChromaVectorStore / PineconeVectorStore
 │    ↓
 │    Vector Database (ChromaDB / Pinecone / PGVector)
 ├── backend/app/agents/graph_agent.py → KnowledgeGraph.search_entities()
 │    ↓
 │    backend/app/knowledge_graph.py → KGNode / KGEdge SQL queries
 ├── backend/app/agents/incident_agent.py → Task SQL LIKE query
 ├── backend/app/agents/memory_agent.py → Memory SQL query
 ↓
backend/app/llm_client.py → LLMClient.stream()
 ↓
External LLM API (Gemini / OpenAI / Groq)
 ↓
SSE chunks back to Chat.jsx
```

### Document Upload Flow
```
frontend/src/pages/Documents.jsx
 ↓ FormData POST /api/v1/documents/upload
frontend/src/api.js
 ↓
backend/app/routes/documents.py → upload_document()
 ↓
backend/app/storage.py → StorageClient.upload()
 ↓ Supabase Storage or local disk
 ↓
BackgroundTask: _ingest_document_background()
 ↓
backend/app/ingestion.py → extract_content_from_bytes() + chunk_text()
 ↓
backend/app/pii_redactor.py → redact_document()
 ↓
backend/app/vectorstore.py → EmbeddingProvider + VectorStore.add_chunks()
 ↓
backend/app/knowledge_graph.py → KnowledgeGraph.index_document()
```

### Meeting Summarization Flow
```
frontend/src/pages/Meetings.jsx
 ↓ POST /api/v1/meetings/
frontend/src/api.js
 ↓
backend/app/routes/meetings.py → create_meeting()
 ↓
backend/app/llm_client.py → LLMClient.call() (blocking via asyncio.to_thread)
 ↓
External LLM API → structured JSON {summary, action_items}
 ↓
SQL: INSERT Meeting + INSERT Task[] (action items)
```

---

## 25. Feature-by-Feature Documentation

### Feature: AI Copilot Chat
- **What**: Natural language Q&A over organizational documents with source citations
- **Frontend**: `Chat.jsx` — SSE streaming, markdown rendering, DOMPurify XSS prevention
- **Backend**: `routes/chat.py` → `ceo_agent.py` → sub-agents → `llm_client.py`
- **AI**: RAG with hybrid search (vector + BM25), Knowledge Graph context, multi-agent orchestration
- **Data**: `AgentLog` (traces), `Memory` (user context), `LLMUsage` (cost tracking)

### Feature: Document Ingestion
- **What**: Upload PDF/DOCX/TXT/CSV/XLSX → auto-extract, redact PII, chunk, embed, index
- **Frontend**: `Documents.jsx` — drag-drop upload, ingestion status polling
- **Backend**: `routes/documents.py` → `ingestion.py` → `pii_redactor.py` → `vectorstore.py`
- **AI**: PII redaction (regex + NER), semantic chunking, embedding generation
- **Data**: `Document`, `DocumentChunk`, `DocumentEmbedding` (pgvector)

### Feature: Meeting Summarization
- **What**: Paste transcript → AI generates structured summary + auto-creates task tickets
- **Frontend**: `Meetings.jsx` — transcript input, expandable summary cards
- **Backend**: `routes/meetings.py` → `llm_client.py`
- **AI**: LLM prompted to extract summary + action items in JSON format
- **Data**: `Meeting`, `Task` (auto-created from action items)

### Feature: Knowledge Graph
- **What**: Visual graph showing how departments, people, documents, and tasks relate
- **Frontend**: `Graph.jsx` — 4-column layout, SVG edges, shift-click multi-select, scoped chat
- **Backend**: `routes/knowledge_graph_routes.py` → `knowledge_graph.py`
- **AI**: Graph RAG via `GraphAgent` — entity search + neighbor traversal
- **Data**: `KGNode`, `KGEdge`

### Feature: Team Management
- **What**: Admin/Manager can transfer employees, change roles, swap positions, delete users
- **Frontend**: `Analytics.jsx` (Team Management tab)
- **Backend**: `routes/auth.py` — transfer, role change, swap-positions, cascading delete
- **Data**: `User`, `Task`, `Document` (reassignment cascades)

### Feature: Human-in-the-Loop Feedback
- **What**: Users rate AI responses (thumbs up/down). Data feeds synthetic fine-tuning dataset
- **Frontend**: `Chat.jsx` — feedback buttons; `Analytics.jsx` — failure review + JSONL export
- **Backend**: `routes/chat.py` (feedback), `routes/analytics_routes.py` (export)
- **AI**: Data flywheel — filtered JSONL export excludes thumbs-down entries
- **Data**: `AIFailure`, `AgentLog`

### Feature: Data Flywheel (Implicit Feedback)
- **What**: When managers edit AI-generated task titles, the edit is auto-logged as implicit correction
- **Backend**: `routes/tasks.py` — compares `ai_generated_title` with new title on PATCH
- **Data**: `AIFailure` (type: `implicit_title_edit`)

### Feature: PII Redaction
- **What**: Automatically strips personally identifiable information before embedding
- **Backend**: `pii_redactor.py` — dual-layer (regex + optional Presidio NER)
- **Patterns**: Email, SSN, phone, credit card, IP, passport, DOB

### Feature: Real-Time Notifications
- **What**: WebSocket-based push notifications for task updates
- **Frontend**: `WebSocketContext.jsx` — connects on login, shows toast notifications
- **Backend**: `routes/ws.py` — `ConnectionManager` broadcasts to targeted user sockets

---

## 26. Major Functions

| Function | File | Purpose | Called By |
|---|---|---|---|
| `process_query_stream()` | `ceo_agent.py` | Main AI orchestrator — routes, retrieves, calls LLM, streams | `routes/chat.py` |
| `extract_content_from_bytes()` | `ingestion.py` | Parses file bytes into text | `routes/documents.py` |
| `chunk_text()` | `ingestion.py` | Recursive semantic text splitting | `ingestion.py` |
| `redact_pii()` | `pii_redactor.py` | Dual-layer PII removal | `ingestion.py` |
| `get_embeddings()` | `vectorstore.py` | Generates vectors from text chunks | `vectorstore.py` |
| `search()` | `vectorstore.py` | Hybrid vector + BM25 retrieval | `search_agent.py` |
| `call()` / `stream()` | `llm_client.py` | Unified LLM invocation with retry + cache | `ceo_agent.py`, `meetings.py` |
| `get_system_analytics()` | `analytics.py` | Role-scoped metrics computation | `routes/analytics_routes.py` |
| `evaluate_policy()` | `abac.py` | ABAC access decision | Route handlers |
| `index_document()` | `knowledge_graph.py` | Auto-creates KG nodes/edges on upload | `routes/documents.py` |
| `create_access_token()` | `auth.py` | JWT generation | `routes/auth.py` |
| `get_current_user()` | `auth.py` | JWT verification + user loading | All protected routes |

---

## 27. Major Classes

| Class | File | Responsibility |
|---|---|---|
| `CEOAgent` | `ceo_agent.py` | Primary AI orchestrator managing all sub-agents |
| `LLMClient` | `llm_client.py` | Multi-provider LLM with retry, cache, cost tracking |
| `EmbeddingProvider` | `vectorstore.py` | Multi-provider embedding generation |
| `VectorStoreManager` | `vectorstore.py` | Factory initializing correct vector DB backend |
| `ChromaVectorStore` | `vectorstore.py` | Local vector DB with hybrid BM25+vector search |
| `PineconeVectorStore` | `vectorstore.py` | Cloud vector DB adapter |
| `PGVectorStore` | `vectorstore.py` | Native Postgres vector search via pgvector |
| `KnowledgeGraph` | `knowledge_graph.py` | SQL-backed entity/relationship graph |
| `StorageClient` | `storage.py` | Supabase/local file storage abstraction |
| `Settings` | `config.py` | Pydantic-based configuration management |
| `InMemoryRateLimiter` | `rate_limiter.py` | Per-IP request throttling |
| `DynamicCORSMiddleware` | `main.py` | Runtime CORS origin validation |

---

## 28. AI Architecture Summary

This qualifies as an AI project because it implements a complete, production-grade **Retrieval-Augmented Generation (RAG)** system with multiple AI subsystems:

```
Enterprise Documents (PDF, DOCX, XLSX, TXT)
 ↓
[1] Text Extraction (PyMuPDF, python-docx, pandas)
 ↓
[2] PII Redaction (Regex + Microsoft Presidio NER)
 ↓
[3] Semantic Chunking (Recursive splitter: headers → paragraphs → sentences)
 ↓
[4] Embedding Generation (Gemini text-embedding-004 / OpenAI text-embedding-3-small)
 ↓
[5] Vector Storage (ChromaDB / Pinecone / PGVector)
 ↓
[6] Knowledge Graph Construction (SQL-backed nodes + directed edges)
 ↓
                    ── QUERY TIME ──
 ↓
[7] Multi-Agent Orchestration (CEOAgent → Search, Graph, Incident, Memory agents)
 ↓
[8] Hybrid Retrieval (Cosine similarity + BM25 lexical → Reciprocal Rank Fusion)
 ↓
[9] Graph RAG (Entity search + neighbor traversal for structural context)
 ↓
[10] Context Compilation (chunks + graph + tasks + analytics + memory + history)
 ↓
[11] LLM Generation (Gemini / OpenAI / Groq with streaming + circuit breaker)
 ↓
[12] Human-in-the-Loop (Thumbs feedback → synthetic fine-tuning dataset export)
 ↓
[13] Data Flywheel (Implicit corrections logged for continuous improvement)
```

---

## 29. Project Complexity Assessment

### Genuine Complexity (Meaningful Engineering)
- **Multi-agent orchestration** with concurrent sub-agent dispatch, context merging, and RBAC-aware data scoping
- **Hybrid search** combining vector similarity with BM25 via Reciprocal Rank Fusion
- **Knowledge Graph RAG** providing structural/relational context alongside semantic retrieval
- **PII redaction pipeline** with dual-layer (regex + NER) before any data leaves the system
- **ABAC policy engine** with hierarchical org-aware access control
- **User deletion cascade** with document reassignment, subordinate transfer, and position swapping
- **Data flywheel** capturing both explicit (thumbs down) and implicit (title edits) feedback
- **Streaming SSE** from multi-agent pipeline through to frontend with real-time rendering
- **LLM circuit breaker** with automatic fallback to simulation mode

### Framework-Provided Complexity
- JWT authentication (standard PyJWT pattern)
- SQLAlchemy ORM models and async sessions
- FastAPI dependency injection for auth/ABAC
- React Router lazy loading
- @tanstack/react-query data fetching

### Observations
- `networkx` is listed as a dependency but the Knowledge Graph is now SQL-backed — this is a **legacy dependency** that could be removed
- Redis URL is configured but no Redis-backed functionality exists — **NOT IMPLEMENTED**
- The `base_agent.py` is an empty class — agents don't inherit from a shared interface

---

## 30. Final Project Explanations

### For a Non-Technical Person
ProcessPilot AI is like having a super-smart assistant for your company. You upload all your company documents — reports, meeting notes, procedures — and the AI reads and understands them all. Then anyone in the company can ask questions like "What's our procedure for handling customer complaints?" and the AI gives an accurate answer based on your actual documents, not made-up information. It also automatically summarizes meetings and creates to-do items. Managers can see what their team is working on, and the system makes sure people only see documents they're supposed to see.

### For a Software Engineer
ProcessPilot AI is a full-stack RAG application with a React 19 SPA frontend (Vite, react-router, tanstack-query) and a FastAPI async backend. The backend implements a multi-agent architecture where a CEOAgent orchestrates specialized agents (Search, Graph, Memory, Incident, Comparison, SOP) that concurrently gather context from a hybrid vector store (ChromaDB/Pinecone/PGVector with BM25+cosine RRF), a SQL-backed Knowledge Graph, and relational task data. Documents go through a PII redaction pipeline before semantic chunking and embedding. The system supports three LLM providers (Gemini, OpenAI, Groq) with per-user API keys, circuit breakers, and cost tracking. Auth is JWT-based with RBAC + ABAC policies. Deployment is Vercel (frontend) + Render (backend) + Supabase (Postgres + Storage) + Pinecone (vectors).

### For an AI/ML Engineer
The RAG pipeline uses recursive semantic chunking (800 chars, 150 overlap, splitting by document structure) with PII redaction before embedding. Embeddings are generated via Google's `text-embedding-004` (768d) or OpenAI's `text-embedding-3-small` (1536d). Retrieval uses hybrid search: cosine similarity from the vector store is fused with BM25 lexical matching via Reciprocal Rank Fusion (RRF). A Graph RAG layer extracts keyword-matched entities from a SQL-backed Knowledge Graph and traverses neighbors for structural context. The multi-agent orchestrator concurrently gathers semantic, structural, and relational context before calling the LLM. The system implements a data flywheel with explicit HITL feedback (thumbs down → AIFailure table) and implicit feedback (manager edits to AI-generated task titles), with JSONL export for synthetic fine-tuning datasets. LLM calls use semantic routing (Groq: cheap model for simple queries, powerful model for complex ones), exponential backoff retries, and a circuit breaker that falls back to simulation mode after 5 consecutive failures.

### For a Technical Interviewer
The key engineering decisions were: (1) Using hybrid search (vector + BM25 via RRF) rather than pure vector search, because lexical matching catches exact terms that embeddings sometimes miss. (2) SQL-backed Knowledge Graph instead of Neo4j, trading query expressiveness for operational simplicity on free-tier hosting. (3) Per-user LLM API keys stored in the database rather than global env vars, enabling multi-tenant usage. (4) Background document ingestion with semaphore-controlled concurrency and batched vector writes (50/batch) to prevent OOM on Render's 512MB free tier. (5) ABAC policy engine that evaluates access based on user role + department + manager chain, not just roles. (6) The data flywheel that captures both explicit and implicit feedback for future model improvement. The main tradeoff was complexity vs. operational cost — everything runs on free tiers.

---

## 31. Interview-Ready Explanations

### 2-Minute Explanation
"ProcessPilot AI is an enterprise knowledge management platform I built using React and FastAPI. Companies upload their documents — PDFs, spreadsheets, meeting transcripts — and the system automatically processes them through a PII redaction pipeline, chunks them semantically, generates embeddings, and stores them in a vector database. Users then interact with an AI copilot that answers questions grounded in the company's actual data. The AI uses a multi-agent architecture: a CEO agent orchestrates specialized sub-agents that concurrently search the vector database using hybrid retrieval — combining cosine similarity with BM25 lexical matching through Reciprocal Rank Fusion — traverse a Knowledge Graph for structural context, and retrieve relevant task tickets. All context is compiled and streamed to an LLM. The system enforces role-based and attribute-based access control, so employees only see documents from their department. It's deployed on Vercel, Render, Supabase, and Pinecone — entirely on free tiers."

### 5-Minute Deep Explanation
*[Include the 2-minute version above, then continue:]*

"Let me walk through the technical details. The document ingestion pipeline extracts text using PyMuPDF for PDFs, python-docx for Word files, and pandas for spreadsheets. Before any text is stored or sent to an LLM, it passes through a dual-layer PII redactor — fast regex patterns catch emails, SSNs, phone numbers, and credit cards, and optionally Microsoft Presidio's NER engine provides deep entity detection. The cleaned text is then recursively chunked at 800 characters with 150-character overlap, splitting intelligently by markdown headers, paragraphs, sentences, and finally words.

For retrieval, I implemented hybrid search in the ChromaDB provider. It maintains an in-memory BM25 index per department alongside the vector index. At query time, both are searched and results are merged using Reciprocal Rank Fusion, which gives us the best of semantic understanding and exact keyword matching. The Knowledge Graph is SQL-backed using SQLAlchemy models rather than Neo4j — this was a deliberate tradeoff for operational simplicity since we're running on free-tier hosting.

The agent architecture has a CEO orchestrator that classifies query intent and concurrently dispatches to specialized agents — Search, Graph, Memory, and Incident. The LLM client supports three providers with semantic routing for Groq: short simple queries go to the cheap 8B model, complex ones to the 70B model. There's a circuit breaker that falls back to simulation mode after 5 consecutive API failures, and an exact-match response cache.

On the human-in-the-loop side, users can give thumbs-down feedback which gets stored and can be exported as JSONL for fine-tuning. There's also an implicit feedback mechanism: when a manager edits an AI-generated task title, the original and edited versions are automatically logged as correction pairs."

### 10-Minute Architecture Walkthrough
*[Include the 5-minute version above, then continue with sections on:]*

**Authentication & Authorization**: "Auth uses JWT with bcrypt password hashing. Beyond simple RBAC, I implemented an Attribute-Based Access Control engine that evaluates policies based on the user's role, department, and position in the management hierarchy. For example, a Manager can delete documents uploaded by their direct reports but not by other teams' members."

**Team Management**: "The admin interface supports complex organizational operations like swapping a Manager and Employee position atomically — it uses a temporary sentinel ID to prevent foreign key collisions during the swap, transfers all direct reports, and realigns department assignments."

**Deployment Architecture**: "The system runs entirely on free tiers. Frontend on Vercel, backend on Render with a key constraint: Render's free tier has an ephemeral filesystem, so we use Supabase for both PostgreSQL (via session pooler for IPv4 compatibility) and S3-compatible object storage. Vector embeddings go to Pinecone's free index. The CI/CD pipeline runs Ruff linting and Pytest with coverage on every push."

**Data Flywheel**: "This is what makes the system improve over time. Every AI interaction is logged with the full agent pipeline trace. Negative feedback is captured both explicitly through user ratings and implicitly through behavioral signals. The admin can export high-quality interactions as JSONL fine-tuning datasets, automatically filtering out any queries that received negative feedback."

---

## 32. Final Summary Table

| Area | Technology | Purpose | Main Files | Key APIs | Key Components |
|---|---|---|---|---|---|
| **Frontend** | React 19 + Vite | SPA web interface | `App.jsx`, `api.js`, 11 page components | fetch + SSE | AuthContext, Chat, Graph, Analytics |
| **Backend** | FastAPI + Uvicorn | Async REST API | `main.py`, 9 route files | 30+ endpoints | DynamicCORSMiddleware, lifespan |
| **Database** | SQLAlchemy + PostgreSQL | Relational data (16 models) | `models.py`, `database.py` | asyncpg | User, Document, Task, Meeting |
| **Vector DB** | ChromaDB / Pinecone / PGVector | Semantic document search | `vectorstore.py` | Embedding + search | Hybrid search with RRF |
| **Knowledge Graph** | SQL-backed (KGNode/KGEdge) | Entity-relationship graph | `knowledge_graph.py` | CRUD + traversal | Auto-indexing on upload |
| **RAG Pipeline** | Custom (no LangChain) | End-to-end retrieval + generation | `ingestion.py`, `vectorstore.py`, `ceo_agent.py` | Ingest + search + generate | PII redaction, semantic chunking |
| **LLM** | Gemini / OpenAI / Groq | Text generation + embeddings | `llm_client.py` | call() / stream() | Circuit breaker, semantic routing |
| **Agents** | Custom multi-agent | Orchestrated context gathering | `ceo_agent.py`, 6 sub-agents | Internal dispatch | CEO orchestrator pattern |
| **Auth** | JWT + bcrypt | Authentication + authorization | `auth.py`, `abac.py` | login, register | RBAC + ABAC |
| **Deployment** | Vercel + Render + Supabase | Free-tier cloud hosting | `ci.yml`, `run.py` | GitHub Actions | Auto-deploy on push |
