
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..knowledge_graph import knowledge_graph
from ..models import User

router = APIRouter(prefix="/knowledge-graph", tags=["Knowledge Graph"])

@router.get("/stats")
async def get_graph_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get knowledge graph statistics."""
    return await knowledge_graph.get_graph_stats(db)

@router.get("/full")
async def get_full_graph(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get full knowledge graph data for visualization."""
    return await knowledge_graph.get_full_graph(db)

@router.get("/search")
async def search_graph(
    entity_type: str | None = Query(None, description="Filter by entity type: Document, User, Department, Technology"),
    keyword: str | None = Query(None, description="Search keyword"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search the knowledge graph."""
    return await knowledge_graph.search_entities(db, entity_type=entity_type, keyword=keyword)

@router.get("/entity/{entity_id}")
async def get_entity_details(
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get entity and its relationships."""
    entity = await knowledge_graph.get_entity(db, entity_id)
    if not entity:
        return {"error": "Entity not found"}
    neighbors = await knowledge_graph.get_neighbors(db, entity_id)
    return {
        "entity": {"id": entity_id, **entity},
        "relationships": neighbors
    }
