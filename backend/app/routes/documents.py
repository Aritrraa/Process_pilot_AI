from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
import shutil

from ..database import get_db
from ..models import User, Document, DocumentChunk, UserSetting
from ..schemas import DocumentResponse
from ..auth import get_current_user, check_role
from ..ingestion import process_file_upload
from ..vectorstore import vector_store_manager
from ..config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    department_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify user can upload to that department
    if current_user.role != "Admin" and department_id and current_user.department_id != department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload documents to your own department"
        )
        
    # Read settings API key if available
    settings_record = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    llm_provider = settings_record.llm_provider if settings_record else "simulation"
    if llm_provider == "gemini":
        api_key = settings_record.gemini_api_key if settings_record else os.getenv("GEMINI_API_KEY")
    elif llm_provider == "groq":
        api_key = settings_record.groq_api_key if settings_record else os.getenv("GROQ_API_KEY")
    elif llm_provider == "openai":
        api_key = settings_record.openai_api_key if settings_record else os.getenv("OPENAI_API_KEY")
    else:
        api_key = None
        
    if not api_key:
        llm_provider = "simulation"
    
    # Save file to uploads folder
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else "txt"
    
    # Unique filename using UUID to prevent naming collision
    clean_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, clean_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # 1. Create document record in database
        document = Document(
            title=file.filename,
            file_path=file_path,
            file_type=file_ext,
            department_id=department_id or current_user.department_id,
            uploaded_by=current_user.id
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # 2. Extract and chunk file text
        processed_chunks = process_file_upload(file_path, file_ext, document.id)
        
        # 3. Create document chunk records in SQL for audit/viewing
        for chunk in processed_chunks:
            db_chunk = DocumentChunk(
                document_id=document.id,
                content=chunk['text'],
                chunk_index=chunk['index'],
                metadata_json=chunk['metadata']
            )
            db.add(db_chunk)
        db.commit()
        
        # 4. Insert chunks into Chroma Vector Database
        # Pass the department_id as chunk metadata for filtering in ChromaDB
        for chunk in processed_chunks:
            chunk['metadata']['department_id'] = document.department_id
            
        vector_store_manager.add_chunks(document.id, processed_chunks, api_key=api_key, llm_provider=llm_provider)
        
        return document
        
    except Exception as e:
        # Cleanup uploaded file if DB/Chroma fails
        if os.path.exists(file_path):
            os.remove(file_path)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and index document: {str(e)}"
        )

@router.get("/", response_model=list[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Role-based restriction: Employees can only view their own department's documents
    if current_user.role == "Admin":
        return db.query(Document).all()
    else:
        dept_id = current_user.department_id
        if not dept_id and current_user.manager_id:
            manager = db.query(User).filter(User.id == current_user.manager_id).first()
            if manager:
                dept_id = manager.department_id
                
        # Return documents belonging to the user's department OR uploaded by the user themselves
        return db.query(Document).filter(
            (Document.department_id == dept_id) | 
            (Document.uploaded_by == current_user.id)
        ).all()

from ..abac import verify_document_access

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document: Document = Depends(verify_document_access("delete")),
    db: Session = Depends(get_db)
):
    file_path = document.file_path
    
    # Remove physical file first to ensure no orphaned files on deletion error
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove physical file from storage: {str(e)}"
        )
        
    try:
        # Delete from ChromaDB
        vector_store_manager.delete_document_chunks(document.id)
        
        # Delete from SQL
        db.delete(document)
        db.commit()
        return
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document database records: {str(e)}"
        )
