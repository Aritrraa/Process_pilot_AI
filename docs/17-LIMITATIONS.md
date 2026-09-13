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