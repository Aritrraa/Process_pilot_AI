from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

class GraphAgent:
    async def execute(self, query: str, db: AsyncSession) -> List[Dict[str, Any]]:
        # Query PostgreSQL knowledge graph for entities and neighbors
        from ..knowledge_graph import knowledge_graph
        
        # Simple extraction of keywords (cleaning punctuation)
        import re
        cleaned_query = re.sub(r'[^\w\s]', ' ', query)
        keywords = [word.lower() for word in cleaned_query.split() if len(word) > 3]
        if not keywords:
            return []
            
        results = []
        # Since we can't easily iterate all nodes in a large DB, we search by keyword
        # or we just return nothing if search_entities doesn't yield anything
        for kw in keywords:
            # We search for the keyword in the ID
            nodes = await knowledge_graph.search_entities(db, keyword=kw)
            for n in nodes:
                node_id = n["id"]
                node_type = n.get("type", "Unknown")
                
                # Find connected neighbors/relationships
                neighbors = await knowledge_graph.get_neighbors(db, node_id)
                results.append({
                    "entity_id": node_id,
                    "type": node_type,
                    "properties": {k: v for k, v in n.items() if k not in ("id", "type")},
                    "connections": [
                        {
                            "target": neighbor["id"],
                            "relationship": neighbor["relationship"],
                            "type": neighbor.get("type", "Unknown"),
                            "direction": neighbor["direction"]
                        } for neighbor in neighbors[:4] # limit to 4 connected neighbors to avoid context explosion
                    ]
                })
                
        # Deduplicate results by entity_id
        unique_results = {r["entity_id"]: r for r in results}
        return list(unique_results.values())[:3] # Return top 3 matched entities
