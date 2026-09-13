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