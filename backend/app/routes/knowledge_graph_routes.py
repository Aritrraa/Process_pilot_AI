from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import User
from ..auth import get_current_user
from ..knowledge_graph import knowledge_graph

router = APIRouter(prefix="/knowledge-graph", tags=["Knowledge Graph"])

@router.get("/stats")
def get_graph_stats(current_user: User = Depends(get_current_user)):
    """Get knowledge graph statistics."""
    return knowledge_graph.get_graph_stats()

@router.get("/full")
def get_full_graph(current_user: User = Depends(get_current_user)):
    """Get full knowledge graph data for visualization."""
    return knowledge_graph.get_full_graph()

@router.get("/search")
def search_graph(
    entity_type: Optional[str] = Query(None, description="Filter by entity type: Document, User, Department, Technology"),
    keyword: Optional[str] = Query(None, description="Search keyword"),
    current_user: User = Depends(get_current_user)
):
    """Search the knowledge graph."""
    return knowledge_graph.search_entities(entity_type=entity_type, keyword=keyword)

@router.get("/entity/{entity_id}")
def get_entity_details(
    entity_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get entity and its relationships."""
    entity = knowledge_graph.get_entity(entity_id)
    if not entity:
        return {"error": "Entity not found"}
    neighbors = knowledge_graph.get_neighbors(entity_id)
    return {
        "entity": {"id": entity_id, **entity},
        "relationships": neighbors
    }
