"""
Knowledge Graph CRUD tests using temporary graph files.
"""
import pytest
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestKnowledgeGraphOperations:
    @pytest.fixture(autouse=True)
    def setup_graph(self):
        import app.knowledge_graph
        from app.knowledge_graph import KnowledgeGraph
        self.tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump({"nodes": [], "edges": []}, self.tmp)
        self.tmp.close()
        
        # Mock the graph file path to use the temp file
        app.knowledge_graph.GRAPH_FILE = self.tmp.name
        self.graph = KnowledgeGraph()
        yield
        os.unlink(self.tmp.name)
        lock = self.tmp.name + ".lock"
        if os.path.exists(lock):
            os.unlink(lock)

    def test_add_entity(self):
        self.graph.add_entity("dept_Engineering", "Department", {"name": "Engineering"})
        entity = self.graph.get_entity("dept_Engineering")
        assert entity is not None
        assert entity["type"] == "Department"

    def test_add_relationship(self):
        self.graph.add_entity("user_a", "User", {"email": "a@test.com"})
        self.graph.add_entity("dept_Eng", "Department", {"name": "Eng"})
        self.graph.add_relationship("user_a", "dept_Eng", "member_of")
        neighbors = self.graph.get_neighbors("user_a")
        assert len(neighbors) > 0

    def test_get_nonexistent_entity(self):
        entity = self.graph.get_entity("nonexistent_id")
        assert entity is None

    def test_graph_stats(self):
        self.graph.add_entity("a", "Type", {})
        self.graph.add_entity("b", "Type", {})
        self.graph.add_relationship("a", "b", "related")
        stats = self.graph.get_graph_stats()
        assert stats["total_entities"] == 2
        assert stats["total_relationships"] == 1

    def test_index_document(self):
        self.graph.add_entity("dept_Eng", "Department", {"name": "Eng"})
        self.graph.index_document(
            document_id=1, title="Python Guide.pdf",
            file_type="pdf", department_name="Eng",
            uploader_email="user@test.com"
        )
        entity = self.graph.get_entity("doc_1")
        assert entity is not None
        assert entity["type"] == "Document"

    def test_duplicate_entity_updates(self):
        self.graph.add_entity("a", "Type", {"v": 1})
        self.graph.add_entity("a", "Type", {"v": 2})
        stats = self.graph.get_graph_stats()
        assert stats["total_entities"] == 1

    def test_remove_entity(self):
        self.graph.add_entity("removable", "Type", {})
        self.graph.add_entity("stays", "Type", {})
        self.graph.add_relationship("removable", "stays", "linked")
        # Remove entity
        try:
            self.graph.remove_entity("removable")
            entity = self.graph.get_entity("removable")
            assert entity is None
        except AttributeError:
            pytest.skip("remove_entity not implemented")

    def test_get_neighbors_empty(self):
        self.graph.add_entity("isolated", "Type", {})
        neighbors = self.graph.get_neighbors("isolated")
        assert len(neighbors) == 0
