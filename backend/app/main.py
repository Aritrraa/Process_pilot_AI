from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .config import settings
from .database import Base, engine, get_db
from .routes import auth, documents, meetings, tasks, settings as settings_routes, chat, analytics_routes, knowledge_graph_routes

# Create all database tables on startup
Base.metadata.create_all(bind=engine)

class DynamicCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("Origin")
        
        # Handle preflight (OPTIONS) requests
        if request.method == "OPTIONS" and origin:
            is_allowed = False
            if "localhost" in origin or "127.0.0.1" in origin:
                is_allowed = True
            elif origin.endswith(".vercel.app"):
                is_allowed = True
            elif origin in settings.BACKEND_CORS_ORIGINS:
                is_allowed = True
                
            if is_allowed:
                headers = {
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                    "Access-Control-Max-Age": "600",
                }
                return Response(content="OK", media_type="text/plain", headers=headers)
        
        response = await call_next(request)
        if origin:
            is_allowed = False
            if "localhost" in origin or "127.0.0.1" in origin:
                is_allowed = True
            elif origin.endswith(".vercel.app"):
                is_allowed = True
            elif origin in settings.BACKEND_CORS_ORIGINS:
                is_allowed = True
                
            if is_allowed:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        return response

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Knowledge & Operations Copilot — Multi-Agent AI, RAG, Knowledge Graphs, Analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(DynamicCORSMiddleware)

# Mount all API routers under /api/v1
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(meetings.router, prefix=settings.API_V1_STR)
app.include_router(tasks.router, prefix=settings.API_V1_STR)
app.include_router(settings_routes.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(analytics_routes.router, prefix=settings.API_V1_STR)
app.include_router(knowledge_graph_routes.router, prefix=settings.API_V1_STR)


@app.on_event("startup")
def startup_populate_knowledge_graph():
    try:
        from .database import SessionLocal
        from .models import User, Department, Document
        from .knowledge_graph import knowledge_graph
        
        # Check if knowledge graph is empty
        stats = knowledge_graph.get_graph_stats()
        if stats.get("total_entities", 0) == 0:
            print("[KnowledgeGraph] Graph is empty. Populating from existing database records...")
            db = SessionLocal()
            
            # 1. Index Departments
            depts = db.query(Department).all()
            for d in depts:
                knowledge_graph.add_entity(f"dept_{d.name}", "Department", {"name": d.name})
                
            # 2. Index Users & Manager relationships
            users = db.query(User).all()
            user_map = {u.id: u for u in users}
            for u in users:
                user_node = f"user_{u.email}"
                knowledge_graph.add_entity(user_node, "User", {"email": u.email, "name": u.full_name or u.email, "role": u.role})
                
                # Link to department
                if u.department_id:
                    dept = next((d for d in depts if d.id == u.department_id), None)
                    if dept:
                        knowledge_graph.add_relationship(user_node, f"dept_{dept.name}", "member_of")
                
                # Link to manager
                if u.manager_id and u.manager_id in user_map:
                    manager = user_map[u.manager_id]
                    knowledge_graph.add_relationship(user_node, f"user_{manager.email}", "reports_to")
            
            # 3. Index Documents
            docs = db.query(Document).all()
            for doc in docs:
                uploader = user_map.get(doc.uploaded_by)
                uploader_email = uploader.email if uploader else "admin@processpilot.ai"
                
                dept = next((d for d in depts if d.id == doc.department_id), None)
                dept_name = dept.name if dept else "General"
                
                knowledge_graph.index_document(
                    document_id=doc.id,
                    title=doc.title,
                    file_type=doc.file_type,
                    department_name=dept_name,
                    uploader_email=uploader_email
                )
                
            db.close()
            print(f"[KnowledgeGraph] Dynamic seeding complete. Entities: {knowledge_graph.get_graph_stats()['total_entities']}, Relationships: {knowledge_graph.get_graph_stats()['total_relationships']}")
    except Exception as e:
        print(f"[KnowledgeGraph] Error during startup indexing: {e}")


@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs",
        "frontend": "http://localhost:5173",
    }


@app.get("/health")
def health_check():
    """Basic health check — used by load balancers and seed script."""
    return {"status": "healthy"}


@app.get("/health/detailed")
def health_detailed():
    """
    Detailed system health — checks all subsystems.
    Returns status of: API, database, vector store, knowledge graph.
    """
    status_report = {
        "api": "ok",
        "database": "unknown",
        "vector_store": "unknown",
        "vector_store_count": 0,
    }

    # Check database
    try:
        from .database import SessionLocal
        db = SessionLocal()
        from .models import Document
        doc_count = db.query(Document).count()
        db.close()
        status_report["database"] = "ok"
        status_report["database_documents"] = doc_count
    except Exception as e:
        status_report["database"] = f"error: {str(e)}"

    # Check ChromaDB vector store
    try:
        from .vectorstore import vector_store_manager
        count = vector_store_manager.collection.count()
        status_report["vector_store"] = "ok"
        status_report["vector_store_count"] = count
    except Exception as e:
        status_report["vector_store"] = f"error: {str(e)}"

    all_ok = all(v == "ok" for k, v in status_report.items() if k.endswith("_store") or k in ("database", "api"))
    status_report["overall"] = "healthy" if all_ok else "degraded"

    return status_report
