import networkx as nx
import json
import os
import time
import threading
from typing import List, Dict, Any, Optional

GRAPH_FILE = "./knowledge_graph.json"
LOCK_FILE = "./knowledge_graph.json.lock"

class FileLock:
    _thread_lock = threading.Lock()

    def __init__(self, lock_path=LOCK_FILE, timeout=5.0):
        self.lock_path = lock_path
        self.timeout = timeout

    def __enter__(self):
        self._thread_lock.acquire()
        start_time = time.time()
        while True:
            try:
                # Attempt to create the lock file atomically
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except FileExistsError:
                if time.time() - start_time > self.timeout:
                    # Timeout reached, break the lock for recovery safety
                    try:
                        os.remove(self.lock_path)
                    except:
                        pass
                time.sleep(0.05)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        finally:
            self._thread_lock.release()

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._load()

    def _load(self):
        with FileLock():
            self._load_internal()

    def _save(self):
        with FileLock():
            self._save_internal()

    def _load_internal(self):
        if os.path.exists(GRAPH_FILE):
            try:
                with open(GRAPH_FILE, "r") as f:
                    data = json.load(f)
                self.graph = nx.node_link_graph(data)
            except Exception:
                self.graph = nx.DiGraph()
        else:
            self.graph = nx.DiGraph()

    def _save_internal(self):
        try:
            data = nx.node_link_data(self.graph)
            with open(GRAPH_FILE, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"[KnowledgeGraph] Failed to persist graph: {e}")

    def add_entity(self, entity_id: str, entity_type: str, properties: Dict[str, Any] = None):
        """Add a node to the knowledge graph."""
        with FileLock():
            self._load_internal()
            props = properties or {}
            props["type"] = entity_type
            self.graph.add_node(entity_id, **props)
            self._save_internal()

    def add_relationship(self, source_id: str, target_id: str, relationship: str, properties: Dict[str, Any] = None):
        """Add a directed edge (relationship) between two entities."""
        with FileLock():
            self._load_internal()
            props = properties or {}
            props["relationship"] = relationship
            self.graph.add_edge(source_id, target_id, **props)
            self._save_internal()

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        with FileLock():
            self._load_internal()
            if entity_id in self.graph.nodes:
                return dict(self.graph.nodes[entity_id])
            return None

    def get_neighbors(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all entities connected to a given entity."""
        with FileLock():
            self._load_internal()
            if entity_id not in self.graph.nodes:
                return []
            
            neighbors = []
            # Outgoing edges
            for _, target, data in self.graph.out_edges(entity_id, data=True):
                target_data = dict(self.graph.nodes[target])
                neighbors.append({
                    "id": target,
                    "direction": "outgoing",
                    "relationship": data.get("relationship", "related_to"),
                    **target_data
                })
            # Incoming edges
            for source, _, data in self.graph.in_edges(entity_id, data=True):
                source_data = dict(self.graph.nodes[source])
                neighbors.append({
                    "id": source,
                    "direction": "incoming",
                    "relationship": data.get("relationship", "related_to"),
                    **source_data
                })
            return neighbors

    def search_entities(self, entity_type: Optional[str] = None, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search entities by type and/or keyword in their ID or properties."""
        with FileLock():
            self._load_internal()
            results = []
            for node_id, data in self.graph.nodes(data=True):
                if entity_type and data.get("type") != entity_type:
                    continue
                if keyword and keyword.lower() not in str(node_id).lower() and keyword.lower() not in str(data).lower():
                    continue
                results.append({"id": node_id, **data})
            return results

    def get_graph_stats(self) -> Dict[str, Any]:
        """Return basic statistics about the knowledge graph."""
        with FileLock():
            self._load_internal()
            type_counts = {}
            for _, data in self.graph.nodes(data=True):
                t = data.get("type", "Unknown")
                type_counts[t] = type_counts.get(t, 0) + 1

            return {
                "total_entities": self.graph.number_of_nodes(),
                "total_relationships": self.graph.number_of_edges(),
                "entity_types": type_counts
            }

    def get_full_graph(self) -> Dict[str, Any]:
        """Return the full graph as nodes and edges for visualization."""
        with FileLock():
            self._load_internal()
            nodes = []
            for node_id, data in self.graph.nodes(data=True):
                nodes.append({"id": node_id, **data})
            
            edges = []
            for source, target, data in self.graph.edges(data=True):
                edges.append({
                    "source": source,
                    "target": target,
                    "relationship": data.get("relationship", "related_to")
                })
            
            return {"nodes": nodes, "edges": edges}

    def index_document(self, document_id: int, title: str, file_type: str, department_name: str, uploader_email: str):
        """
        Auto-index a document into the knowledge graph when uploaded.
        Creates entity nodes and relationships.
        """
        doc_node = f"doc_{document_id}"
        dept_node = f"dept_{department_name}"
        user_node = f"user_{uploader_email}"

        # Add entities
        self.add_entity(doc_node, "Document", {"title": title, "file_type": file_type})
        self.add_entity(dept_node, "Department", {"name": department_name})
        self.add_entity(user_node, "User", {"email": uploader_email})

        # Add relationships
        self.add_relationship(user_node, doc_node, "uploaded")
        self.add_relationship(doc_node, dept_node, "belongs_to")

        # Extract technology keywords from title
        tech_keywords = ["docker", "kubernetes", "fastapi", "python", "react", "ci/cd", 
                        "security", "deployment", "api", "database", "postgresql"]
        title_lower = title.lower()
        for tech in tech_keywords:
            if tech in title_lower:
                tech_node = f"tech_{tech}"
                self.add_entity(tech_node, "Technology", {"name": tech})
                self.add_relationship(doc_node, tech_node, "covers")


# Singleton instance
knowledge_graph = KnowledgeGraph()
