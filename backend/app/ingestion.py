"""
Document ingestion pipeline — text extraction and semantic-aware chunking.
Supports PDF, DOCX, TXT, CSV, and Markdown files.
"""
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
    Semantic-aware recursive text splitter.
    Splits by hierarchy: sections → paragraphs → sentences → words.
    Preserves structural formatting better than naive character splitting.
    """
    if not text or not text.strip():
        return []
    
    # Normalize excessive whitespace while preserving paragraph breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()
    
    if len(text) <= chunk_size:
        return [text]
    
    # Separators in order of priority (most meaningful boundaries first)
    separators = ["\n## ", "\n### ", "\n\n", "\n", ". ", "; ", ", ", " "]
    
    def _split_recursive(text: str, seps: List[str]) -> List[str]:
        if len(text) <= chunk_size:
            return [text.strip()] if text.strip() else []
        
        # Try each separator starting from most meaningful
        for sep in seps:
            if sep in text:
                parts = text.split(sep)
                chunks = []
                current = ""
                
                for part in parts:
                    candidate = current + sep + part if current else part
                    
                    if len(candidate) <= chunk_size:
                        current = candidate
                    else:
                        if current.strip():
                            chunks.append(current.strip())
                        
                        # If single part exceeds chunk_size, recurse with finer separators
                        if len(part) > chunk_size:
                            remaining_seps = seps[seps.index(sep) + 1:]
                            if remaining_seps:
                                chunks.extend(_split_recursive(part, remaining_seps))
                            else:
                                # Last resort: hard split with overlap
                                for i in range(0, len(part), chunk_size - chunk_overlap):
                                    chunk = part[i:i + chunk_size]
                                    if chunk.strip():
                                        chunks.append(chunk.strip())
                        else:
                            current = part
                
                if current.strip():
                    chunks.append(current.strip())
                
                if chunks:
                    return chunks
        
        # No separator found — hard split with overlap
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += chunk_size - chunk_overlap
        return chunks
    
    return _split_recursive(text, separators)


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
