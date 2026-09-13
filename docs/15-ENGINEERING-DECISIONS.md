# Engineering Decisions (ADRs)

1. **Database:** Chosen PostgreSQL (Supabase) to combine relational RBAC data with pgvector embeddings.
2. **Knowledge Graph:** Migrated from in-memory NetworkX JSON to SQL tables (kg_nodes, kg_edges) to support stateless horizontal scaling.
3. **Embeddings:** Implemented a deterministic hash-based local simulator to save API costs during development.
4. **Hybrid Search:** Added BM25Okapi locally to complement dense vector similarity.