# ProcessPilot AI — From Problem to Production
### A Full-Stack AI Engineering & Problem-Solving Case Study

**Problem → Requirements → Architecture → Implementation → Debugging → Iteration → Testing → Deployment**

**Author:** Aritra Das  
**Version:** 1.0  
**Date:** September 2026

---

## 1. Project Overview

ProcessPilot AI is a multi-agent organizational intelligence system. It acts as a centralized brain for an enterprise by ingesting static documents, processing unstructured meeting transcripts, tracking derived tasks, and querying organizational relationships. 

It is designed for Admins, Managers, and Employees who need to cross-reference organizational policies with actual operational data.

**High-Level Stack:**
* **Frontend:** React 19, Vite
* **Backend:** FastAPI (Python), asyncpg, SQLAlchemy
* **Database / Vectors:** PostgreSQL (Supabase) + pgvector
* **AI Orchestration:** Hierarchical routing (CEOAgent → Sub-Agents)
* **Real-time:** WebSockets
* **Security:** ABAC (Attribute-Based Access Control), JWT, AES-GCM encryption, Regex PII Redaction

This is not a wrapper around a chatbot. It is a deterministic application environment built around probabilistic AI services, designed to manage strict access controls, observability, and infrastructure constraints.

---

## 2. The Problem

Organizational information is fundamentally fragmented. 
- **Documents** (policies, SOPs) live in static files.
- **Meetings** produce action items that disappear the moment the call ends.
- **Tasks** live in isolated ticketing systems.
- **Organizational relationships** (who reports to whom, what department owns what) live in HR systems.

**Why is this an engineering problem?**
You cannot just put an LLM behind a chat UI to solve this. 
- Documents require semantic search and vector retrieval.
- Relationships require structured graph queries, not vector similarity.
- Meetings produce unstructured conversational data that must be deterministically parsed into tasks.
- AI responses are probabilistic and prone to hallucination.
- Access must depend strictly on user identity and department context.

The challenge was building the surrounding system required to provide the right information, enforce access boundaries, handle failures, persist state, and operate under deployment constraints.

---

## 3. The Solution

ProcessPilot AI centralizes these silos through a unified architecture that provides:
1. **Document Knowledge:** A Hybrid RAG pipeline (Vector + BM25) for querying policies.
2. **Organizational Knowledge Graph:** A SQL-backed graph representing people, departments, and assets.
3. **Multi-Agent Routing:** A delegation system that sends semantic queries to a RAG agent and relational queries to a Graph agent.
4. **Meeting Intelligence:** Automated transcript extraction mapping action items to persistent database tasks.
5. **Real-Time Updates:** WebSocket pushes for instantaneous task assignment notification.
6. **Robust Security:** Pre-embedding PII redaction and strict database-level ABAC.
7. **AI Observability:** Dedicated tracking for LLM token usage, API timeouts, and agent routing decisions.

---

## 4. Product Requirements Document (PRD)

Starting development immediately would have led to uncontrolled feature growth. I wrote a PRD to establish users, workflows, and strict boundaries.

**Target Users & Roles:**
* Admin (Global access)
* Manager (Department-level access)
* Employee (Individual + Department access)

**Requirements Mapping:**

| Problem | Product Requirement | User Outcome |
|---------|---------------------|--------------|
| Fragmented documents | Centralized knowledge retrieval | Find relevant organizational information securely |
| Lost meeting actions | Action-item extraction | Convert discussions automatically into assigned tasks |
| Relationship questions | Organizational graph | Answer hierarchy and asset-ownership questions |
| Access restrictions | Role/department controls | Prevent unauthorized cross-department data leakage |
| AI failures | Resilient LLM layer | Reduce dependency on a single fragile external provider |
| Real-time work | Server-push updates | Immediate UI updates without manual polling |

---

## 5. Technical Requirements Document (TRD)

I did not choose technologies first. The product requirements created technical constraints, which dictated my engineering decisions.

| Requirement | Technical Constraint | Engineering Decision | Reason |
|-------------|----------------------|----------------------|--------|
| RBAC / ABAC | Persistent, relational connections | PostgreSQL | Users, departments, and permissions fit naturally into relational schemas. |
| Vector retrieval | Vector similarity search | pgvector extension | Allows relational (RBAC) and vector data to coexist, enabling SQL joins with semantic search. |
| Real-time tasks | Server push to client | WebSockets (`ws.py`) | Avoids expensive and slow HTTP polling when new tasks are generated from meetings. |
| AI responses | LLM integration flexibility | Unified dynamic LLM client | Needed fallback logic to handle provider API outages without bringing down the application. |

---

## 6. System Architecture

The architecture routes user intent through a security layer into specialized subsystems, executing on a fully asynchronous backend.

```text
[ React 19 Frontend ]
         ↓ (HTTP / WebSockets)
[ FastAPI Backend ]
         ↓
[ JWT Auth & ABAC Layer ]
         ↓
[ CEOAgent (Router) ]
    ↙      ↓      ↘
[RAG]   [Graph]  [Meetings]
  ↓        ↓          ↓
[   PostgreSQL Database   ]
(pgvector, kg_nodes, tasks)
```

**Major Components:**
* **Frontend:** React handles UI state and WebSocket task listeners.
* **Backend:** FastAPI handles async I/O, critical for LLM streaming and concurrent DB queries.
* **Database:** Supabase Postgres holds all state (users, vectors, graph nodes, logs).
* **AI Orchestration:** The backend acts as a stateless conduit delegating to specialized agents.

---

## 7. Architecture Evolution

### NetworkX to SQL-Backed Graph

**Initial Approach:** 
I built the Knowledge Graph prototype using NetworkX, storing nodes in memory and saving to a JSON file.

**Why it made sense initially:** 
It was extremely fast for prototyping and native graph traversal.

**Problem / Limitation:** 
When deployed to a stateless, horizontally scalable environment (like Render's free tier), the ephemeral filesystem wiped the JSON file on every restart. Furthermore, concurrency locks made updating the JSON file dangerous in an async web server.

**Decision & Implementation:** 
I migrated the entire graph to SQL, creating `kg_nodes` and `kg_edges` tables in PostgreSQL. The backend now queries standard relational joins to reconstruct relationships.

**Trade-off:** 
I lost the ability to run complex native graph algorithms (like PageRank) in memory. I gained persistence, ACID compliance, and compatibility with stateless backend deployment.

---

## 8. Database Design

I first asked: *What information does the system need to remember?*

1. **Identity & Organization:** `users`, `departments`. Defines ABAC.
2. **Documents & Knowledge:** `documents`, `chunks`, `embeddings`. Enables RAG.
3. **Meetings & Tasks:** `meetings`, `tasks`. Enables operational workflows.
4. **Conversations:** `memory`, `prompt_versions`.
5. **Knowledge Graph:** `kg_nodes`, `kg_edges`. Enables relational queries.
6. **Observability:** `ai_failures`, `llm_usage`, `agent_logs`. Tracks probabilistic AI behavior deterministically.

This resulted in an 18-table schema. Critically, access boundaries are enforced directly via Foreign Keys linking documents and users to specific `department_ids`.

---

## 9. Document Ingestion

**Problem:** How can arbitrary organizational documents become searchable AI knowledge safely?

**Pipeline Design:**
`File -> PyMuPDF Extraction -> Regex PII Redaction -> Semantic Chunking -> Embedding -> pgvector Storage`

**Why Each Stage Exists:**
* **Extraction:** Converts PDF binaries to raw text.
* **PII Redaction:** Scrubs sensitive data *before* it hits an LLM.
* **Chunking:** Splits text with overlap so the LLM receives context without exceeding token limits.
* **Embedding:** Translates text to dense vectors.
* **Storage:** Commits to Postgres.

**Problem Discovered:** 
Initially, I processed files asynchronously in a background thread. However, free-tier ephemeral filesystems deleted the uploaded PDF before the thread could finish chunking it.

**Solution:** 
I forced the extraction to happen in-memory synchronously upon upload. The trade-off is slower HTTP response times for massive PDFs, but it guarantees data persistence into Postgres before the ephemeral file vanishes.

---

## 10. PII and Security

**Problem:** 
HR documents contain SSNs, credit cards, and sensitive information. 

**Threat:** 
Sending raw text to an external LLM API (OpenAI/Groq/Gemini) creates a massive security exposure.

**Design Decision:** 
Redaction must occur *before* vectorization. If PII is embedded, it exists in the vector space forever.

**Implementation:** 
I built `pii_redactor.py` using Regex patterns to detect and replace sensitive strings with tokens like `[REDACTED_SSN]`.

**Trade-Off:** 
I heavily considered using an NLP-based detector like Microsoft Presidio. However, free-tier RAM constraints made running a secondary ML model impossible. Regex is extremely fast and memory-efficient but trades off by occasionally missing edge-case formatting.

---

## 11. RAG Pipeline

The problem was not "How do I use RAG?". It was "How do I make an LLM answer questions using internal documents reliably?"

**First Retrieval Approach:** 
Dense semantic retrieval using pgvector cosine similarity (`<=>`).

**Observation:** 
It answered conceptual questions ("How do I apply for leave?") perfectly.

**The Problem That Appeared:** 
It completely failed on keyword-heavy queries like "Summarize Document ID HR-992-B". Dense vectors compress tokens into semantic space, destroying exact character matching.

**Engineering Response:** 
I needed a sparse keyword signal. I added `BM25Okapi` to create a Hybrid Retrieval system. The system now retrieves dense vectors from Postgres and sparse keyword matches locally.

**Current Limitation:** 
Currently, the vector scores and BM25 scores are combined loosely. Reciprocal Rank Fusion (RRF) is mathematically superior for hybrid merging, and is explicitly **Planned but not implemented** in the current iteration.

---

## 12. Embeddings

**Initial Approach:** 
I initially planned to use a local HuggingFace MiniLM model for embeddings to avoid API costs and preserve privacy.

**Constraint Encountered:** 
Deployment memory constraints on Render made hosting a local ML model in the FastAPI container highly unstable. The application crashed due to OOM (Out of Memory) errors.

**Current Implementation:** 
I pivoted to using Gemini (`google.generativeai`) for production embeddings. To save API costs and allow rapid iteration during local development, I built a deterministic hash-based mock embedding generator that outputs valid 768-dimension vectors.

---

## 13. Multi-Agent Architecture

**Problem:** 
A single RAG prompt cannot answer every question. If a user asks "Who is the manager of Engineering?", standard vector search looks for semantic similarity, not SQL relationships, and fails.

**Design Question:** 
Should every query go through every subsystem (RAG + SQL + API)? This would cost massive amounts of LLM tokens and slow down response times.

**Architectural Decision:** 
I introduced controlled routing via a `CEOAgent`.

**Implementation:**
`User -> CEOAgent -> Intent Analysis -> Specialized Agent (SearchAgent / GraphAgent / SOPAgent) -> Context Aggregation -> LLM`

**Important Limitation:** 
This is specialized delegation/orchestration. It is NOT unrestricted autonomous tool-calling loops. Restricting the agents prevents infinite loops and catastrophic API token burn.

---

## 14. Knowledge Graph

**Problem:** 
Some questions depend entirely on operational relationships (e.g., "Show me all assets owned by the IT department"). Vector retrieval is blind to this.

**Architectural Evolution:**
As noted, I migrated from NetworkX (in-memory) to SQL (`kg_nodes`, `kg_edges`).

**Implementation:**
The `GraphAgent` translates natural language into controlled relational queries against the `kg_edges` table, allowing the LLM to traverse the organizational hierarchy deterministically. 

---

## 15. Meeting Intelligence

**Problem:** 
Meeting transcripts contain actionable tasks, but LLM output is probabilistic. Application code requires predictable structures to create database rows.

**First Design:** 
Prompt the LLM to output a JSON array of tasks.

**Problem:** 
LLMs frequently hallucinate conversational filler ("Here is the JSON you requested: [ ... ]"), which crashes standard `json.loads()`.

**Defensive Parsing Solution:** 
To bridge the gap between probabilistic AI and deterministic code, I built strict Regex extraction (`re.search(r'\{.*\}', text, re.DOTALL)`) to isolate the JSON payload from the surrounding text. 

**Real-Time Delivery:** 
Once safely parsed and committed to PostgreSQL, the backend fires a WebSocket event to the assigned user's frontend, updating their UI instantly.

---

## 16. LLM Client & Model Resilience

**Problem:** 
Relying on a single external LLM model string causes fatal application crashes if the provider deprecates it.

**Implementation:**
The `llm_client.py` does not just blindly forward requests. It features:
* **Dynamic Fallback:** If Groq returns a 404 (Model Deprecated), the client intercepts the error, queries the `/models` endpoint to discover active models, and automatically retries the prompt with a valid model.
* **Usage Tracking:** Every call logs token consumption to the `llm_usage` table.

---

## 17. Real-Time Architecture

**Implementation:**
I implemented WebSockets (`ws.py`) to handle server-to-client push events.
* **Event Flow:** LLM extracts task -> DB commits task -> WebSocket broadcasts to specific user ID -> React state updates.
* **Security Limitation:** The current implementation relies on query parameters for authentication during the handshake, which is weaker than standard HTTP Bearer headers.

---

## 18. Security Architecture

Security was implemented as a series of cascading boundaries.

`Request -> JWT Authentication -> RBAC (Role) -> ABAC (Department Isolation) -> PII Redaction -> Vector Storage`

* **ABAC:** Users can only query documents tied to their `department_id`.
* **API Keys:** AES-GCM encrypted in transit and at rest in the database.
* **PII:** Scrubber intercepts data before the LLM boundary.

---

## 19. Observability

A normal API can return HTTP 200 while still producing a poor AI hallucination. Standard application logs are insufficient.

**What I Built:**
* `agent_logs`: Captures routing decisions to debug why CEOAgent chose the wrong sub-agent.
* `llm_usage`: Tracks token consumption to prevent silent budget drains.
* `ai_failures`: Captures LLM API timeouts or parsing failures that ordinary HTTP middleware misses.

---

## 20. Testing

I did not just test to say I had tests. I targeted specific, catastrophic failure modes.

* **ABAC Tests:** 
  * *Potential Problem:* Cross-department data leakage.
  * *Test:* Forcing an employee to query a document outside their department.
  * *Expected Result:* Immediate 403 Forbidden.
* **Ingestion Tests:**
  * *Potential Problem:* Invalid PDF extraction crashing the event loop.
  * *Test:* Submitting malformed files to verify pipeline isolation.

---

## 21. Deployment

**Local Assumptions:** Infinite disk space, persistent memory, unbounded compute.
**Deployment Environment:** Render free tier.
**Constraint Encountered:** Ephemeral filesystems wiped uploaded PDFs, NetworkX JSON graphs, and ChromaDB vector files on every deploy/restart.
**Engineering Response:** Deployment changed my architecture. I migrated vectors to `pgvector` and the graph to `kg_nodes` inside the managed Supabase PostgreSQL instance. I designed around the constraint rather than assuming unlimited infrastructure.

---

## 22. Problems I Actually Encountered

### Problem 1: Groq Model Deprecations
**Symptom:** The AI suddenly stopped responding entirely, throwing HTTP 500s.
**Investigation:** I checked external API logs and found 404 Not Found errors. Groq had decommissioned the specific `llama3` model string I had hardcoded.
**Fix:** I rewrote `llm_client.py` to catch 404 errors, dynamically query Groq's active models, and automatically retry.
**Lesson:** Never hardcode external dependency identifiers in probabilistic systems.

### Problem 2: Timezone Mismatches
**Symptom:** The frontend Analytics page crashed entirely.
**Investigation:** `asyncpg` returns timezone-aware datetimes from Postgres. Python's `sorted()` function crashed when comparing these against naive datetimes generated locally in application code.
**Fix:** I implemented a strict UTC normalization utility in `analytics.py`. All dates are converted to UTC before any sorting occurs.
**Lesson:** Data boundaries (DB -> App) require strict type and format normalization.

---

## 23. Engineering Decision Log

| Problem / Constraint | Initial Approach | Observation / Problem | Decision | Trade-off | Current State |
|----------------------|------------------|-----------------------|----------|-----------|---------------|
| Graph Persistence | NetworkX (JSON) | JSON wiped on server restart | Migrate to SQL (`kg_nodes`) | Lost native graph algorithms | SQL-backed graph |
| Keyword Retrieval | Dense Vectors only | Failed on exact ID matches | Add BM25Okapi | Increased local memory usage | Hybrid RAG pipeline |
| PII Leaks | Raw extraction | Send sensitive data to LLM | Regex redaction | Misses obscure edge cases vs NLP | Fast in-memory redaction |
| LLM Deprecations | Hardcoded model | 404 crashes application | Dynamic fallback retry logic | Slower response on first failure | Resilient LLM client |
| Local Embeddings | HuggingFace MiniLM | OOM crashes on free tier | Gemini API | Relying on external provider | Gemini Embeddings |

---

## 24. Current Architecture vs Old Architecture

### Earlier
* **Graph:** NetworkX JSON files. (Chosen for prototyping speed).
* **Vectors:** ChromaDB locally. (Chosen for ease of use).
* **Embeddings:** Local HuggingFace models. (Chosen for privacy).
* **Search:** Pure Vector Search.

### What Changed
* Ephemeral serverless deployments destroyed local persistence. Free-tier memory constraints killed local ML models. Keyword queries failed on semantic search.

### Current
* **Graph:** PostgreSQL `kg_nodes`.
* **Vectors:** PostgreSQL `pgvector`.
* **Embeddings:** Gemini API.
* **Search:** Hybrid (Vector + BM25).

---

## 25. Current State

Today, ProcessPilot AI is a deployed, React/FastAPI/Postgres stack featuring Hybrid RAG, a SQL-backed Knowledge Graph, specialized multi-agent routing, real-time WebSocket task generation, and Pre-LLM PII protection.

---

## 26. Limitations

| Area | Status | Current Reality | Next Step |
|------|--------|-----------------|-----------|
| Reciprocal Rank Fusion (RRF) | **PLANNED** | Vector and BM25 scores are merged loosely. | Implement RRF for mathematically sound merging. |
| Autonomous Tool Loops | **NOT IMPLEMENTED** | System relies on controlled agent routing. | Deepen agent reasoning capabilities cautiously. |
| ChromaDB / NetworkX | **LEGACY** | Configured in early code, superseded by Postgres. | Remove legacy dependencies entirely. |
| Formal SOC2 / GDPR | **NOT VERIFIED** | No formal certification evidence. | Conduct third-party audit if going to enterprise prod. |

---

## 27. What I Would Do Next

If I built this again today, I would change:
1. **Durable Object Storage:** Implement AWS S3 immediately for document ingestion rather than trying to optimize ephemeral disk processing.
2. **Retrieval Evaluation:** Integrate RAGAS early in development to objectively measure retrieval quality, rather than relying on manual query testing.
3. **WebSocket Auth:** Move from query-parameter authentication to a more secure handshake protocol.

---

## 28. Final Engineering Mindset

I did not start with:
> *"Which AI technologies should I use?"*

I started with:
> *"What problem am I trying to solve?"*

Then:
> *"What information does the system need?"*  
> *"What architecture supports it?"*  
> *"What can fail?"*  
> *"How do I protect the data?"*  
> *"How do I observe failures?"*  
> *"How do I test it?"*  
> *"How does it behave under deployment constraints?"*  
> *"What should I change after learning from implementation?"*

ProcessPilot AI is the result of that iterative process: **Problem → Design → Implementation → Failure → Investigation → Adaptation → Deployment.**
