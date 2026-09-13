# Knowledge Graph

## Implementation
- **Current State:** SQL-Backed (kg_nodes, kg_edges tables).
- **Legacy:** Previously used NetworkX and JSON files. The codebase explicitly notes this was replaced for stateless horizontal scaling.
- **Frontend:** Rendered natively via HTML/CSS positioning or simple generic graph libraries (NO react-force-graph-2d dependency found in package.json).