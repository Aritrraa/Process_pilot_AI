# Document Ingestion Pipeline

1. **Upload:** Client uploads PDF/DOCX.
2. **Extraction:** PyMuPDF (fitz) or python-docx extracts raw text.
3. **Redaction:** pii_redactor.py scrubs sensitive data.
4. **Chunking:** Semantic chunking with overlap.
5. **Embedding:** vectorstore.py generates 768-d vectors (Gemini or simulated).
6. **Storage:** Saved to PGVectorStore (document_embeddings).
7. **Graph Indexing:** knowledge_graph.py extracts entities to kg_nodes and kg_edges.