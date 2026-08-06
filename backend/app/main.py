import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy import text
from sqlalchemy.future import select

from .config import settings
from .database import Base, engine
from .routes import auth, documents, meetings, tasks, settings as settings_routes, chat, analytics_routes, knowledge_graph_routes, ws

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("processpilot")


# ──── Application Lifespan: Async startup/shutdown ────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async lifespan context — replaces deprecated @app.on_event."""
    # ── Startup ────────────────────────────────────────────────────────────
    logger.info("[Startup] Initializing database schema...")
    async with engine.begin() as conn:
        is_postgres = "postgresql" in settings.DATABASE_URL or "postgres" in settings.DATABASE_URL
        if is_postgres:
            # Ensure pgvector extension is enabled before creating tables
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        # Create all tables (idempotent)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[Startup] Database schema ready.")

    # ── Populate knowledge graph from existing records ─────────────────────
    await _populate_knowledge_graph()

    yield  # App is now running

    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("[Shutdown] Disposing DB engine connections...")
    await engine.dispose()
    logger.info("[Shutdown] Cleanup complete.")


async def _populate_knowledge_graph():
    """Async knowledge graph seeding on first startup."""
    try:
        from .database import SessionLocal
        from .models import User, Department, Document
        from .knowledge_graph import knowledge_graph

        async with SessionLocal() as db:
            stats = await knowledge_graph.get_graph_stats(db)
            if stats.get("total_entities", 0) == 0:
                logger.info("[KnowledgeGraph] Graph is empty. Populating from existing database records...")

                r_depts = await db.execute(select(Department))
                depts = r_depts.scalars().all()
                for d in depts:
                    await knowledge_graph.add_entity(db, f"dept_{d.name}", "Department", {"name": d.name})

                r_users = await db.execute(select(User))
                users = r_users.scalars().all()
                user_map = {u.id: u for u in users}
                for u in users:
                    user_node = f"user_{u.email}"
                    await knowledge_graph.add_entity(db, user_node, "User", {"email": u.email, "name": u.full_name or u.email, "role": u.role})
                    if u.department_id:
                        dept = next((d for d in depts if d.id == u.department_id), None)
                        if dept:
                            await knowledge_graph.add_relationship(db, user_node, f"dept_{dept.name}", "member_of")
                    if u.manager_id and u.manager_id in user_map:
                        manager = user_map[u.manager_id]
                        await knowledge_graph.add_relationship(db, user_node, f"user_{manager.email}", "reports_to")

                r_docs = await db.execute(select(Document))
                docs = r_docs.scalars().all()
                for doc in docs:
                    uploader = user_map.get(doc.uploaded_by)
                    uploader_email = uploader.email if uploader else "admin@processpilot.ai"
                    dept = next((d for d in depts if d.id == doc.department_id), None)
                    dept_name = dept.name if dept else "General"
                    await knowledge_graph.index_document(
                        db=db, document_id=doc.id, title=doc.title,
                        file_type=doc.file_type, department_name=dept_name,
                        uploader_email=uploader_email
                    )

                stats_after = await knowledge_graph.get_graph_stats(db)
                logger.info(
                    f"[KnowledgeGraph] Dynamic seeding complete. "
                    f"Entities: {stats_after['total_entities']}, "
                    f"Relationships: {stats_after['total_relationships']}"
                )
    except Exception as e:
        logger.error(f"[KnowledgeGraph] Error during startup indexing: {e}")


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
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ──── Global Exception Handlers ────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions — log details but return sanitized error to client."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": [
                {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
                for err in exc.errors()
            ]
        }
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
app.include_router(ws.router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "operational",
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Basic health check — used by load balancers and seed script."""
    return {"status": "healthy"}


@app.get("/health/detailed")
async def health_detailed():
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
        from .models import Document
        from sqlalchemy import func
        async with SessionLocal() as db:
            r = await db.execute(select(func.count(Document.id)))
            doc_count = r.scalar()
        status_report["database"] = "ok"
        status_report["database_documents"] = doc_count
    except Exception as e:
        status_report["database"] = "error"
        logger.error(f"Health check DB error: {e}")

    # Check vector store
    try:
        from .vectorstore import vector_store_manager
        count = vector_store_manager.collection.count()
        status_report["vector_store"] = "ok"
        status_report["vector_store_count"] = count
    except Exception as e:
        status_report["vector_store"] = "error"
        logger.error(f"Health check vector store error: {e}")

    all_ok = all(v == "ok" for k, v in status_report.items() if k.endswith("_store") or k in ("database", "api"))
    status_report["overall"] = "healthy" if all_ok else "degraded"

    return status_report
