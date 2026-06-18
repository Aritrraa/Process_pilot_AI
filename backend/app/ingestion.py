import os
import re
from typing import List, Dict, Any

# Optional imports with safe fallbacks
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import docx
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False

def extract_text_from_pdf(file_path: str) -> str:
    if not HAS_PYMUPDF:
        return "[PyMuPDF not installed] Fallback: Please install pymupdf to parse PDF text."
    try:
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text() + "\n"
        return text
    except Exception as e:
        return f"[PDF parsing error]: {str(e)}"

def extract_text_from_docx(file_path: str) -> str:
    if not HAS_PYTHON_DOCX:
        return "[python-docx not installed] Fallback: Please install python-docx to parse Word documents."
    try:
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"[Word parsing error]: {str(e)}"

def extract_text_from_txt(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"[Text file reading error]: {str(e)}"

def extract_content(file_path: str, file_type: str) -> str:
    ext = file_type.lower()
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    elif ext in ["docx", "doc"]:
        return extract_text_from_docx(file_path)
    else:
        return extract_text_from_txt(file_path)

def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> List[str]:
    """
    Split text into chunks of chunk_size characters with chunk_overlap characters overlap.
    """
    # Clean excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    if not text:
        return []
        
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
        
    return chunks

def process_file_upload(file_path: str, file_type: str, document_id: int) -> List[Dict[str, Any]]:
    """
    Extracts text, chunks it, and returns the chunks ready for vector database insertion.
    """
    raw_text = extract_content(file_path, file_type)
    text_chunks = chunk_text(raw_text)
    
    processed_chunks = []
    for idx, chunk in enumerate(text_chunks):
        processed_chunks.append({
            "id": f"doc_{document_id}_chunk_{idx}",
            "text": chunk,
            "index": idx,
            "metadata": {
                "file_name": os.path.basename(file_path),
                "file_type": file_type
            }
        })
    return processed_chunks
