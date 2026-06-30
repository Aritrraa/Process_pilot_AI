from typing import List, Dict, Any

class GraphAgent:
    def execute(self, query: str) -> List[Dict[str, Any]]:
        # Query local NetworkX knowledge graph for entities and neighbors
        from ..knowledge_graph import knowledge_graph
        
        # Simple extraction of keywords (cleaning punctuation)
        import re
        cleaned_query = re.sub(r'[^\w\s]', ' ', query)
        keywords = [word.lower() for word in cleaned_query.split() if len(word) > 3]
        if not keywords:
            return []
            
        results = []
        # Search node IDs or properties
        for node_id, data in knowledge_graph.graph.nodes(data=True):
            node_type = data.get("type", "Unknown")
            # If any keyword is in the node ID or properties
            match = False
            if any(kw in str(node_id).lower() for kw in keywords):
                match = True
            else:
                for k, v in data.items():
                    if any(kw in str(v).lower() for kw in keywords):
                        match = True
                        break
                        
            if match:
                # Find connected neighbors/relationships
                neighbors = knowledge_graph.get_neighbors(node_id)
                results.append({
                    "entity_id": node_id,
                    "type": node_type,
                    "properties": {k: v for k, v in data.items() if k != "type"},
                    "connections": [
                        {
                            "target": n["id"],
                            "relationship": n["relationship"],
                            "type": n.get("type", "Unknown"),
                            "direction": n["direction"]
                        } for n in neighbors[:4] # limit to 4 connected neighbors to avoid context explosion
                    ]
                })
        return results[:3] # Return top 3 matched entities
