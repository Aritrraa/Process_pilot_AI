# AI & RAG Architecture

## Document Ingestion Lifecycle
`mermaid
flowchart TD
    A[File Upload] --> B[PyMuPDF / docx Extraction]
    B --> C[PII Redaction Regex]
    C --> D[Semantic Chunking]
    D --> E[Embedding Generation]
    E --> F[(PGVector / ChromaDB)]
`

## Chunking & Embeddings
- **Providers:** Gemini (google.generativeai), OpenAI, or a deterministic hash-based local simulation to bypass API costs in development.
- **Storage:** PGVectorStore using native <=> cosine similarity. A ChromaDB fallback exists.
- **Retrieval:** Hybrid (Cosine Similarity + BM25 keyword matching via rank_bm25).
- **NOT Implemented:** RRF (Reciprocal Rank Fusion).