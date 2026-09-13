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