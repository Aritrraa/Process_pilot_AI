# ProcessPilot AI - Complete Master Documentation

This document is a concatenation of all individual technical and product documents for ProcessPilot AI.

---

# ProcessPilot AI - Product Requirements Document (PRD)

## Product Summary
ProcessPilot AI is an Enterprise Knowledge Operating System that ingests documents, transcripts, and meetings to form a centralized, conversational, and relational organizational brain.

## Problem Statement
Enterprises suffer from fragmented knowledge, lost meeting action items, and unstructured data silos.

## Goals
- Centralize documentation and meetings.
- Provide a conversational interface (AI Copilot) for querying knowledge.
- Automatically extract tasks from meetings.
- Map organizational relationships via a Knowledge Graph.

## Current Implementation Status
- **Implemented:** RBAC, JWT Auth, Semantic Ingestion (pgvector & ChromaDB fallback), Multi-Agent Orchestration (Routing), BM25 Hybrid Retrieval, SQL-backed Knowledge Graph.
- **Not Implemented:** True Autonomous AI loops (agents only execute defined sub-routines).

---

# Technical Requirements Document (TRD)

## System Requirements
- **Frontend:** React 19, Vite, React Router 7.
- **Backend:** Python 3.x, FastAPI, Uvicorn, SQLAlchemy 2.0.
- **Database:** PostgreSQL (via Supabase) with pgvector extension.
- **AI/LLM:** Multiple providers (Groq, OpenAI, Gemini) and local simulated embedding fallback.

## Security Requirements
- **Implemented:** AES-GCM encryption for API keys, Regex-based PII redaction.
- **NOT Implemented:** Formal SOC2/GDPR certification.

---

# System Architecture

## High-Level Architecture
ProcessPilot AI is built on a decoupled client-server architecture.

`mermaid
graph TD
    A[React 19 Frontend] -->|REST/WebSockets| B(FastAPI Backend)
    B -->|SQLAlchemy / asyncpg| C[(PostgreSQL + pgvector)]
    B -->|HTTPS| D[Groq/OpenAI APIs]
`

---

# AI & RAG Architecture

## Document Ingestion Lifecycle
`mermaid
flowchart TD
    A[File Upload] --> B[PyMuPDF / docx Extraction]
    B --> C[PII Redaction Regex]
    C --> D[Semantic Chunking]
    D --> E[Embedding Generation]
    E --> F[(PGVector / ChromaDB)]
`

## Chunking & Embeddings
- **Providers:** Gemini (google.generativeai), OpenAI, or a deterministic hash-based local simulation to bypass API costs in development.
- **Storage:** PGVectorStore using native <=> cosine similarity. A ChromaDB fallback exists.
- **Retrieval:** Hybrid (Cosine Similarity + BM25 keyword matching via rank_bm25).
- **NOT Implemented:** RRF (Reciprocal Rank Fusion).

---

# Multi-Agent Architecture

ProcessPilot AI utilizes a **Hierarchical Routing Architecture**. 
*Note: This is a routing/delegation system. It does NOT currently support unconstrained autonomous tool-calling loops.*

## The Orchestrator
- **CEOAgent (ceo_agent.py):** The primary router. Synthesizes user queries and delegates tasks to specialized sub-agents.

## Sub-Agents
- **SearchAgent:** Handles PGVector RAG queries.
- **GraphAgent:** Queries the SQL-backed knowledge graph.
- **MemoryAgent:** Fetches user context.
- **SOPAgent:** Dedicated policy retrieval.
- **IncidentAgent:** Searches technical logs.
- **ComparisonAgent:** Analyzes multiple documents.

---

# Database Design

## Technology
PostgreSQL (via Supabase) with SQLAlchemy 2.0 (asyncpg).

## Key Tables
- users, departments, user_settings
- documents, document_chunks, document_embeddings
- meetings, 	asks
- gent_logs, memories, udit_logs, llm_usage, i_failures, prompt_versions
- kg_nodes, kg_edges (Replaced legacy NetworkX JSON implementation)

---

# Security Architecture

## Implemented Controls
- **Authentication:** JWT with PyJWT. Passwords hashed via passlib (bcrypt).
- **Authorization:** RBAC (Admin, Manager, Employee) and strict ABAC isolating department data.
- **PII Redaction:** Regex-based scrubbing (pii_redactor.py) for SSNs, credit cards, emails. Presidio is configured as optional but relies on regex primarily.
- **API Key Security:** AES-GCM encryption (crypto.py) for user-provided LLM keys.
- **Database:** Supabase Row Level Security (RLS) enabled on all 18 tables to block direct PostgREST access.

---

# API Documentation

Endpoints exist for:
- Auth (/auth/register, /auth/login)
- Documents (/documents/upload, /documents)
- Meetings (/meetings/upload)
- Tasks (/tasks/)
- WebSockets (/ws/{user_id})
- Knowledge Graph (/graph/data)

---

# Document Ingestion Pipeline

1. **Upload:** Client uploads PDF/DOCX.
2. **Extraction:** PyMuPDF (fitz) or python-docx extracts raw text.
3. **Redaction:** pii_redactor.py scrubs sensitive data.
4. **Chunking:** Semantic chunking with overlap.
5. **Embedding:** vectorstore.py generates 768-d vectors (Gemini or simulated).
6. **Storage:** Saved to PGVectorStore (document_embeddings).
7. **Graph Indexing:** knowledge_graph.py extracts entities to kg_nodes and kg_edges.

---

# Knowledge Graph

## Implementation
- **Current State:** SQL-Backed (kg_nodes, kg_edges tables).
- **Legacy:** Previously used NetworkX and JSON files. The codebase explicitly notes this was replaced for stateless horizontal scaling.
- **Frontend:** Rendered natively via HTML/CSS positioning or simple generic graph libraries (NO react-force-graph-2d dependency found in package.json).

---

# Meeting Intelligence

1. **Input:** Raw meeting transcript.
2. **LLM Parsing:** Sends transcript to Groq/OpenAI with strict JSON schema instructions.
3. **Regex Extraction:** Uses regex to extract JSON, bypassing conversational hallucinations.
4. **Automation:** Automatically parses Action Items into Task database rows.
5. **Notifications:** Fires WebSocket events to assigned users.

---

# LLM Architecture

## Unified Client (llm_client.py)
Provides a single abstraction layer for LLM interactions.

## Providers
- **Groq:** Primary provider.
- **OpenAI / Gemini:** Fallback providers.
- **Dynamic Fallback:** Handles Groq model deprecations by querying active models dynamically.

---

# Deployment

## Infrastructure
- **Frontend:** Deployed via static hosting.
- **Backend:** FastAPI Uvicorn web service (Render).
- **Database:** Supabase Managed PostgreSQL.

---

# Observability

## Implemented Tracking
- **agent_logs:** Tracks multi-agent decision steps.
- **llm_usage:** Tracks token counts and estimated costs.
- **ai_failures:** Logs API timeouts or model errors.
- **Timezone Handling:** Strictly normalizes Postgres timezone-aware datetimes to UTC.

---

# Engineering Decisions (ADRs)

1. **Database:** Chosen PostgreSQL (Supabase) to combine relational RBAC data with pgvector embeddings.
2. **Knowledge Graph:** Migrated from in-memory NetworkX JSON to SQL tables (kg_nodes, kg_edges) to support stateless horizontal scaling.
3. **Embeddings:** Implemented a deterministic hash-based local simulator to save API costs during development.
4. **Hybrid Search:** Added BM25Okapi locally to complement dense vector similarity.

---

# Testing & Evaluation

## Test Suite
- Framework: pytest
- Location: backend/tests/

## Implemented Tests
- test_abac_policies.py
- test_auth_api.py
- test_ingestion.py
- test_knowledge_graph.py
- test_llm_client.py
- test_rate_limiter.py

---

# Technical Limitations

## IMPLEMENTED
- Hybrid Retrieval (PGVector + BM25).
- Multi-Agent Delegation (Routing).
- SQL-backed Knowledge Graph.

## NOT IMPLEMENTED / NOT VERIFIED
- **SOC2 / GDPR:** No formal external certification verified.
- **Autonomous Loops:** Agents do not currently have unconstrained tool-calling loops (they are strict routers).

## LEGACY / UNUSED
- chromadb: Imported but overshadowed by pgvector.
- NetworkX: Retained in code but replaced by SQL for stateless deployment.

---

# Roadmap

## CURRENT
- Stabilize PGVector RAG ingestion.
- Secure RBAC and WebSocket notifications.

## NEXT
- Implement Reciprocal Rank Fusion (RRF) for better hybrid retrieval scoring.

## FUTURE
- True autonomous agentic loops with dynamic tool calling.

---

# Documentation Audit Report

## 1. Verified Architecture
- FastAPI Backend, React 19 Frontend.
- Supabase PostgreSQL with pgvector.
- WebSockets for real-time tasks.
- Hierarchical Agent Routing (CEOAgent).

## 2. Verified Technologies
- PyMuPDF, BM25 (rank_bm25), SQLAlchemy asyncpg.
- Groq, OpenAI, Gemini.

## 3. Legacy / Configured but Unused
- ChromaDB: Configured but superseded by native pgvector.
- NetworkX: Graph logic migrated to SQL tables.
- react-force-graph-2d / recharts: Not present in package.json. Visuals are handled natively.

## 4. Contradictions Found in Previous Documentation
- Previous documentation claimed local HuggingFace MiniLM-L6 was used. Code review reveals embeddings use Gemini or a deterministic local simulator.
- Previous documentation claimed react-force-graph-2d was used. Code review reveals it is absent from the dependency list.
- Previous documentation claimed NetworkX was the primary graph store. Code review reveals it was replaced by SQL (kg_nodes, kg_edges).

---

