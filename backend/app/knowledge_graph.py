import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from .models import KGNode, KGEdge

logger = logging.getLogger("processpilot.knowledge_graph")

class KnowledgeGraph:
    """
    PostgreSQL-backed Knowledge Graph using SQLAlchemy AsyncSession.
    Replaces the legacy JSON+NetworkX implementation for stateless horizontally scaled deployments.
    """

    async def add_entity(self, db: AsyncSession, entity_id: str, entity_type: str, properties: Dict[str, Any] = None):
        """Add or update a node in the knowledge graph."""
        props = properties or {}
        result = await db.execute(select(KGNode).filter(KGNode.id == entity_id))
        node = result.scalars().first()
        if not node:
            node = KGNode(id=entity_id, entity_type=entity_type, properties=props)
            db.add(node)
        else:
            node.entity_type = entity_type
            merged_props = dict(node.properties) if node.properties else {}
            merged_props.update(props)
            node.properties = merged_props

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"[KnowledgeGraph] Failed to add entity {entity_id}: {e}")

    async def add_relationship(self, db: AsyncSession, source_id: str, target_id: str, relationship: str, properties: Dict[str, Any] = None):
        """Add a directed edge (relationship) between two entities."""
        r_src = await db.execute(select(KGNode).filter(KGNode.id == source_id))
        source_node = r_src.scalars().first()
        r_tgt = await db.execute(select(KGNode).filter(KGNode.id == target_id))
        target_node = r_tgt.scalars().first()

        if not source_node:
            await self.add_entity(db, source_id, "Unknown")
        if not target_node:
            await self.add_entity(db, target_id, "Unknown")

        r_edge = await db.execute(
            select(KGEdge).filter(
                KGEdge.source_id == source_id,
                KGEdge.target_id == target_id,
                KGEdge.relationship_type == relationship
            )
        )
        existing_edge = r_edge.scalars().first()

        props = properties or {}
        if not existing_edge:
            edge = KGEdge(
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship,
                properties=props
            )
            db.add(edge)
            try:
                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error(f"[KnowledgeGraph] Failed to add edge {source_id}->{target_id}: {e}")
        else:
            merged_props = dict(existing_edge.properties) if existing_edge.properties else {}
            merged_props.update(props)
            existing_edge.properties = merged_props
            await db.commit()

    async def get_entity(self, db: AsyncSession, entity_id: str) -> Optional[Dict[str, Any]]:
        result = await db.execute(select(KGNode).filter(KGNode.id == entity_id))
        node = result.scalars().first()
        if not node:
            return None
        return {"id": node.id, "type": node.entity_type, **(node.properties or {})}

    async def get_neighbors(self, db: AsyncSession, entity_id: str) -> List[Dict[str, Any]]:
        """Get all entities connected to a given entity."""
        neighbors = []

        r_out = await db.execute(select(KGEdge).filter(KGEdge.source_id == entity_id))
        for edge in r_out.scalars().all():
            r_tgt = await db.execute(select(KGNode).filter(KGNode.id == edge.target_id))
            target = r_tgt.scalars().first()
            if target:
                neighbors.append({
                    "id": target.id,
                    "direction": "outgoing",
                    "relationship": edge.relationship_type,
                    "type": target.entity_type,
                    **(target.properties or {})
                })

        r_in = await db.execute(select(KGEdge).filter(KGEdge.target_id == entity_id))
        for edge in r_in.scalars().all():
            r_src = await db.execute(select(KGNode).filter(KGNode.id == edge.source_id))
            source = r_src.scalars().first()
            if source:
                neighbors.append({
                    "id": source.id,
                    "direction": "incoming",
                    "relationship": edge.relationship_type,
                    "type": source.entity_type,
                    **(source.properties or {})
                })

        return neighbors

    async def search_entities(self, db: AsyncSession, entity_type: Optional[str] = None, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search entities by type and/or keyword in their ID."""
        query = select(KGNode)
        if entity_type:
            query = query.filter(KGNode.entity_type == entity_type)
        if keyword:
            kw = f"%{keyword.lower()}%"
            query = query.filter(KGNode.id.ilike(kw))

        result = await db.execute(query.limit(50))
        nodes = result.scalars().all()
        return [{"id": n.id, "type": n.entity_type, **(n.properties or {})} for n in nodes]

    async def get_graph_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Return basic statistics about the knowledge graph."""
        from sqlalchemy import func
        r_n = await db.execute(select(func.count(KGNode.id)))
        total_nodes = r_n.scalar()
        r_e = await db.execute(select(func.count(KGEdge.id)))
        total_edges = r_e.scalar()

        r_types = await db.execute(select(KGNode.entity_type).distinct())
        type_counts = {}
        for (t,) in r_types.all():
            r_cnt = await db.execute(select(func.count(KGNode.id)).filter(KGNode.entity_type == t))
            type_counts[t] = r_cnt.scalar()

        return {
            "total_entities": total_nodes,
            "total_relationships": total_edges,
            "entity_types": type_counts
        }

    async def get_full_graph(self, db: AsyncSession) -> Dict[str, Any]:
        """Return the full graph as nodes and edges for visualization (limited for safety)."""
        r_n = await db.execute(select(KGNode).limit(500))
        nodes = r_n.scalars().all()
        r_e = await db.execute(select(KGEdge).limit(2000))
        edges = r_e.scalars().all()

        node_list = [{"id": n.id, "type": n.entity_type, **(n.properties or {})} for n in nodes]
        edge_list = [{
            "source": e.source_id,
            "target": e.target_id,
            "relationship": e.relationship_type
        } for e in edges]

        return {"nodes": node_list, "edges": edge_list}

    async def index_document(self, db: AsyncSession, document_id: int, title: str, file_type: str, department_name: str, uploader_email: str):
        """
        Auto-index a document into the knowledge graph when uploaded.
        Creates entity nodes and relationships.
        """
        doc_node = f"doc_{document_id}"
        dept_node = f"dept_{department_name}"
        user_node = f"user_{uploader_email}"

        await self.add_entity(db, doc_node, "Document", {"title": title, "file_type": file_type})
        await self.add_entity(db, dept_node, "Department", {"name": department_name})
        await self.add_entity(db, user_node, "User", {"email": uploader_email})

        await self.add_relationship(db, user_node, doc_node, "uploaded")
        await self.add_relationship(db, doc_node, dept_node, "belongs_to")

        tech_keywords = ["docker", "kubernetes", "fastapi", "python", "react", "ci/cd",
                        "security", "deployment", "api", "database", "postgresql", "supabase"]
        title_lower = title.lower()
        for tech in tech_keywords:
            if tech in title_lower:
                tech_node = f"tech_{tech}"
                await self.add_entity(db, tech_node, "Technology", {"name": tech})
                await self.add_relationship(db, doc_node, tech_node, "covers")


# Singleton instance
knowledge_graph = KnowledgeGraph()
