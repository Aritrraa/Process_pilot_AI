"""
Document routes — Upload, List, Delete.

Key design decisions:
  - Upload returns 202 Accepted IMMEDIATELY after saving to Supabase Storage.
    Actual PDF parsing + embedding runs in a FastAPI BackgroundTask (via asyncio.to_thread)
    so the async event loop is never blocked on large file processing.
  - Files are persisted to Supabase Storage (not Render's ephemeral disk).
    Falls back to local disk gracefully when SUPABASE_URL env var is absent.
  - GET /documents supports skip/limit pagination to prevent OOM on large datasets.
  - _ingest_document_background intentionally uses a SYNCHRONOUS SQLAlchemy session
    because it runs inside asyncio.to_thread() (a thread pool), not the async event loop.
"""
import logging
import os
import uuid
import aiofiles
import asyncio
import datetime
from typing import Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends,
    HTTPException, UploadFile, File, Form, status
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete as sql_delete

from ..database import get_db
from ..models import User, Document, DocumentChunk, UserSetting
from ..schemas import DocumentResponse
from ..auth import get_current_user
from ..ingestion import process_file_upload
from ..vectorstore import vector_store_manager
from ..storage import storage_client
from ..config import settings
from ..abac import verify_document_access

logger = logging.getLogger("processpilot.documents")

router = APIRouter(prefix="/documents", tags=["Documents"])


# ---------------------------------------------------------------------------
# Background task: parse, chunk, embed — runs in a thread (asyncio.to_thread)
# Uses a SYNC session intentionally — this runs in a thread, not the event loop.
# ---------------------------------------------------------------------------

# Global semaphore to limit heavy background processing on free tiers
MAX_CONCURRENT_TASKS = asyncio.Semaphore(2)

async def _async_ingest_wrapper(*args, **kwargs):
    """Async wrapper to enforce concurrency limits before offloading to a thread."""
    async with MAX_CONCURRENT_TASKS:
        await asyncio.to_thread(_ingest_document_background, *args, **kwargs)

def _ingest_document_background(
    document_id: int,
    file_path: str,
    file_ext: str,
    api_key: Optional[str],
    llm_provider: str,
    department_id: Optional[int],
):
    """
    Heavy processing moved off the async event loop via asyncio.to_thread:
      1. Extract text from raw bytes.
      2. Semantic-aware recursive chunking with 150-char overlap.
      3. PII redaction before embedding.
      4. Generate embeddings + upsert into pgvector / ChromaDB.
      5. Save DocumentChunk records to SQL for audit/viewing.
      6. Update ingestion_status to 'done' or 'failed'.
    """
    # Sync session for thread context — do NOT use AsyncSession here
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    db_url = settings.DATABASE_URL
    engine = create_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {})
    SyncSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SyncSession()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"[Ingest] Document {document_id} not found in DB — aborting.")
            return

        document.ingestion_status = "processing"
        db.commit()

        logger.info(f"[Ingest] Starting ingestion for document {document_id} ({file_ext})")

        # 1-2. Extract text and chunk (from disk to save RAM)
        processed_chunks = process_file_upload(file_path, file_ext, document_id)
        logger.info(f"[Ingest] Document {document_id} → {len(processed_chunks)} chunks")

        # 3. Save chunks to SQL (for audit trail)
        for chunk in processed_chunks:
            db_chunk = DocumentChunk(
                document_id=document_id,
                content=chunk["text"],
                chunk_index=chunk["index"],
                metadata_json=chunk["metadata"],
            )
            db.add(db_chunk)
        db.commit()

        # 4. Tag department on each chunk metadata before vectorizing
        for chunk in processed_chunks:
            chunk["metadata"]["department_id"] = department_id

        # 5. Embed + upsert into pgvector / ChromaDB
        vector_store_manager.add_chunks(
            document_id, processed_chunks,
            api_key=api_key, llm_provider=llm_provider
        )

        document.ingestion_status = "done"
        db.commit()
        logger.info(f"[Ingest] Document {document_id} ingestion complete.")

    except Exception as e:
        logger.error(f"[Ingest] Document {document_id} ingestion FAILED: {e}", exc_info=True)
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.ingestion_status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
        engine.dispose()
        # Clean up the temporary file from disk
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"[Ingest] Failed to delete temp file {file_path}: {e}")


# ---------------------------------------------------------------------------
# POST /documents/upload  — returns 202 immediately
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    department_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document and kick off background ingestion.
    """
    if (
        current_user.role != "Admin"
        and department_id
        and current_user.department_id != department_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload documents to your own department.",
        )

    # Fetch user settings async
    from ..crypto import decrypt_key
    result = await db.execute(select(UserSetting).filter(UserSetting.user_id == current_user.id))
    settings_record = result.scalars().first()
    llm_provider = settings_record.llm_provider if settings_record else "simulation"
    api_key: Optional[str] = None
    if llm_provider == "gemini" and settings_record:
        api_key = decrypt_key(settings_record.gemini_api_key) or os.getenv("GEMINI_API_KEY")
    elif llm_provider == "groq" and settings_record:
        api_key = decrypt_key(settings_record.groq_api_key) or os.getenv("GROQ_API_KEY")
    elif llm_provider == "openai" and settings_record:
        api_key = decrypt_key(settings_record.openai_api_key) or os.getenv("OPENAI_API_KEY")
    if not api_key:
        llm_provider = "simulation"

    # ── Upload validation ──────────────────────────────────────────────────
    file_ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "bin"
    if file_ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail=f"File type {file_ext} not allowed.")

    # ── Stream file to disk to prevent OOM crashes ─────────────────────────
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    temp_file_name = f"temp_{uuid.uuid4()}.{file_ext}"
    temp_file_path = os.path.join(settings.UPLOAD_DIR, temp_file_name)
    
    file_size = 0
    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    try:
        async with aiofiles.open(temp_file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                file_size += len(content)
                if file_size > max_size_bytes:
                    break
                await out_file.write(content)
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")

    if file_size > max_size_bytes:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit."
        )

    # ── Upload to Supabase Storage (or local fallback) ────────────────────
    try:
        # Avoid loading file into memory — pass path directly
        storage_path, storage_url = storage_client.upload(temp_file_path, file.filename)
    except Exception as e:
        logger.error(f"[Upload] Storage upload failed for '{file.filename}': {e}")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store file: {str(e)}",
        )

    # ── Create Document record (status=pending) ───────────────────────────
    effective_dept = department_id or current_user.department_id
    document = Document(
        title=file.filename,
        file_path=storage_path,
        storage_path=storage_path,
        storage_url=storage_url,
        ingestion_status="pending",
        file_type=file_ext,
        department_id=effective_dept,
        uploaded_by=current_user.id,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info(
        f"[Upload] Document {document.id} saved. "
        f"Storage: {'Supabase' if storage_client.is_supabase_enabled() else 'Local'}. "
        f"Queuing background ingestion…"
    )

    # ── Queue background ingestion — HTTP response returns IMMEDIATELY ─────
    # We use add_task to call the async wrapper which enforces the semaphore
    background_tasks.add_task(
        _async_ingest_wrapper,
        document.id,
        temp_file_path,
        file_ext,
        api_key,
        llm_provider,
        effective_dept,
    )

    return document


# ---------------------------------------------------------------------------
# GET /documents/  — paginated list
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return documents visible to the current user (ABAC-scoped, paginated)."""
    if current_user.role == "Admin":
        result = await db.execute(select(Document).filter(Document.deleted_at == None).offset(skip).limit(limit))
        return result.scalars().all()

    dept_id = current_user.department_id
    if not dept_id and current_user.manager_id:
        mgr_result = await db.execute(select(User).filter(User.id == current_user.manager_id))
        manager = mgr_result.scalars().first()
        if manager:
            dept_id = manager.department_id

    result = await db.execute(
        select(Document)
        .filter(
            ((Document.department_id == dept_id) | (Document.uploaded_by == current_user.id))
            & (Document.deleted_at == None)
        )
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# GET /documents/{document_id}/status  — polling endpoint
# ---------------------------------------------------------------------------

@router.get("/{document_id}/status")
async def get_document_status(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lightweight poll endpoint so the frontend can show ingestion progress.
    Returns: { id, title, ingestion_status }
    """
    result = await db.execute(select(Document).filter(Document.id == document_id, Document.deleted_at == None))
    document = result.scalars().first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {
        "id": document.id,
        "title": document.title,
        "ingestion_status": document.ingestion_status,
    }

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    doc: Document = Depends(verify_document_access("read"))
):
    """Get a specific document by ID."""
    return doc


# ---------------------------------------------------------------------------
# DELETE /documents/{document_id}
# ---------------------------------------------------------------------------

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document: Document = Depends(verify_document_access("delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document, its chunks, and its stored file."""
    # Remove from Supabase Storage (or local disk)
    if document.storage_path:
        storage_client.delete(document.storage_path)
    elif document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except Exception as e:
            logger.warning(f"[Delete] Could not remove local file {document.file_path}: {e}")

    try:
        # Remove embeddings from pgvector / ChromaDB
        vector_store_manager.delete_document_chunks(document.id)
        # Hard-delete SQL chunks to prevent DB bloat
        from ..models import DocumentChunk
        await db.execute(
            sql_delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        # Soft delete the document record itself
        document.deleted_at = datetime.datetime.utcnow()
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document records: {str(e)}",
        )
