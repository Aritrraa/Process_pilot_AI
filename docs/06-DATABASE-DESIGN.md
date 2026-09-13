# Database Design

## Technology
PostgreSQL (via Supabase) with SQLAlchemy 2.0 (asyncpg).

## Key Tables
- users, departments, user_settings
- documents, document_chunks, document_embeddings
- meetings, 	asks
- gent_logs, memories, udit_logs, llm_usage, i_failures, prompt_versions
- kg_nodes, kg_edges (Replaced legacy NetworkX JSON implementation)