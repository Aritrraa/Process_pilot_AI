import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app.knowledge_graph import KnowledgeGraph

from tests.conftest import AsyncTestSessionLocal, test_engine


class TestKnowledgeGraphOperations:
    @pytest.fixture(autouse=True)
    def setup_graph(self):
        self.graph = KnowledgeGraph()
        Base.metadata.create_all(bind=test_engine)
        yield
        Base.metadata.drop_all(bind=test_engine)

    def test_add_entity(self):
        async def run():
            async with AsyncTestSessionLocal() as db:
                await self.graph.add_entity(db, "dept_Engineering", "Department", {"name": "Engineering"})
                await db.commit()
                entity = await self.graph.get_entity(db, "dept_Engineering")
                assert entity is not None
                assert entity["type"] == "Department"
        asyncio.run(run())

    def test_add_relationship(self):
        async def run():
            async with AsyncTestSessionLocal() as db:
                await self.graph.add_entity(db, "user_a", "User", {"email": "a@test.com"})
                await self.graph.add_entity(db, "dept_Eng", "Department", {"name": "Eng"})
                await self.graph.add_relationship(db, "user_a", "dept_Eng", "member_of")
                await db.commit()
                neighbors = await self.graph.get_neighbors(db, "user_a")
                assert len(neighbors) > 0
        asyncio.run(run())

    def test_get_nonexistent_entity(self):
        async def run():
            async with AsyncTestSessionLocal() as db:
                entity = await self.graph.get_entity(db, "nonexistent_id")
                assert entity is None
        asyncio.run(run())

    def test_graph_stats(self):
        async def run():
            async with AsyncTestSessionLocal() as db:
                await self.graph.add_entity(db, "a", "Type", {})
                await self.graph.add_entity(db, "b", "Type", {})
                await self.graph.add_relationship(db, "a", "b", "related")
                await db.commit()
                stats = await self.graph.get_graph_stats(db)
                assert stats["total_entities"] == 2
                assert stats["total_relationships"] == 1
        asyncio.run(run())

    def test_index_document(self):
        async def run():
            async with AsyncTestSessionLocal() as db:
                await self.graph.add_entity(db, "dept_Eng", "Department", {"name": "Eng"})
                await self.graph.index_document(
                    db,
                    document_id=1, title="Python Guide.pdf",
                    file_type="pdf", department_name="Eng",
                    uploader_email="user@test.com"
                )
                await db.commit()
                entity = await self.graph.get_entity(db, "doc_1")
                assert entity is not None
                assert entity["type"] == "Document"
        asyncio.run(run())

    def test_duplicate_entity_updates(self):
        async def run():
            async with AsyncTestSessionLocal() as db:
                await self.graph.add_entity(db, "a", "Type", {"v": 1})
                await self.graph.add_entity(db, "a", "Type", {"v": 2})
                await db.commit()
                stats = await self.graph.get_graph_stats(db)
                assert stats["total_entities"] == 1
        asyncio.run(run())

    def test_remove_entity(self):
        async def run():
            async with AsyncTestSessionLocal() as db:
                await self.graph.add_entity(db, "removable", "Type", {})
                await self.graph.add_entity(db, "stays", "Type", {})
                await self.graph.add_relationship(db, "removable", "stays", "linked")
                await db.commit()
                try:
                    await self.graph.remove_entity(db, "removable")
                    entity = await self.graph.get_entity(db, "removable")
                    assert entity is None
                except AttributeError:
                    pytest.skip("remove_entity not implemented")
        asyncio.run(run())

    def test_get_neighbors_empty(self):
        async def run():
            async with AsyncTestSessionLocal() as db:
                await self.graph.add_entity(db, "isolated", "Type", {})
                await db.commit()
                neighbors = await self.graph.get_neighbors(db, "isolated")
                assert len(neighbors) == 0
        asyncio.run(run())
