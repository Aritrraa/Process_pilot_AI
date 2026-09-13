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