# ProcessPilot AI — Complete Project Guide & Interview Preparation

---

# PART 1: UNDERSTANDING THE PROJECT (Beginner-Friendly)

---

## What is ProcessPilot AI?

Imagine you join a big company with 500 employees. There are thousands of documents — HR policies, engineering specs, meeting notes, project reports. You need to find "What is the leave policy for contractors?" — but you don't know which PDF has the answer.

**ProcessPilot AI** solves this. It:
1. **Reads** all your company documents (PDFs, Word files, Excel sheets)
2. **Understands** them using AI (not just keyword search — it understands *meaning*)
3. **Answers** your questions in plain English, telling you exactly which document the answer came from
4. **Summarizes** meeting recordings into action items
5. **Manages** tasks across teams with role-based permissions

Think of it as **"ChatGPT, but trained on YOUR company's data, with access control."**

---

## How Does It Work? (The Big Picture)

```
┌─────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                        │
│  React Frontend (Vercel)                                     │
│  ┌─────────┐ ┌──────┐ ┌──────┐ ┌─────────┐ ┌─────────────┐│
│  │Dashboard│ │ Chat │ │Docs  │ │Meetings │ │Knowledge    ││
│  │         │ │(AI)  │ │Upload│ │Summary  │ │Graph        ││
│  └────┬────┘ └──┬───┘ └──┬───┘ └────┬────┘ └──────┬──────┘│
└───────┼─────────┼────────┼──────────┼──────────────┼────────┘
        │         │        │          │              │
        ▼         ▼        ▼          ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (Render)                   │
│                                                               │
│  ┌──────────┐  ┌──────────────────────────────────────────┐  │
│  │   Auth   │  │         CEO AGENT (Orchestrator)         │  │
│  │  (JWT)   │  │  ┌────────┐ ┌───────┐ ┌───────────────┐ │  │
│  │  + RBAC  │  │  │Search  │ │Graph  │ │Memory Agent   │ │  │
│  │  + ABAC  │  │  │Agent   │ │Agent  │ │(remembers you)│ │  │
│  └──────────┘  │  └───┬────┘ └───┬───┘ └───────────────┘ │  │
│                │      │          │                         │  │
│                └──────┼──────────┼─────────────────────────┘  │
│                       │          │                             │
│              ┌────────▼────┐  ┌──▼──────────────┐             │
│              │ Vector DB   │  │ Knowledge Graph  │             │
│              │(ChromaDB/   │  │ (SQL nodes +     │             │
│              │ Pinecone)   │  │  edges)           │             │
│              └─────────────┘  └──────────────────┘             │
│                                                               │
│              ┌─────────────────────────────┐                  │
│              │  PostgreSQL (Supabase)      │                  │
│              │  Users, Tasks, Meetings,    │                  │
│              │  Documents, Audit Logs      │                  │
│              └─────────────────────────────┘                  │
└───────────────────────────────────────────────────────────────┘
```

---

## The Two Most Important Flows

### Flow 1: Document Upload (How the AI "Learns")

When you upload a PDF, here's what happens behind the scenes:

```
You drop a PDF file onto the upload zone
        │
        ▼
┌──── STEP 1: Text Extraction ────┐
│  PyMuPDF opens the PDF and      │
│  reads text from every page     │
└────────────┬────────────────────┘
             ▼
┌──── STEP 2: PII Redaction ──────┐
│  Before storing anything, we    │
│  strip out sensitive data:      │
│  • Email addresses              │
│  • Phone numbers                │
│  • Social Security Numbers      │
│  • Credit card numbers          │
│  Why? So they never leak to AI  │
└────────────┬────────────────────┘
             ▼
┌──── STEP 3: Chunking ──────────┐
│  A 50-page PDF = too big for   │
│  AI to process at once.        │
│  We split it into ~800 char    │
│  chunks with 150 char overlap  │
│  so no information is lost at  │
│  chunk boundaries.             │
└────────────┬────────────────────┘
             ▼
┌──── STEP 4: Embedding ─────────┐
│  Each chunk is converted into  │
│  a 768-dimensional vector      │
│  (a list of 768 numbers) that  │
│  captures its MEANING.         │
│  "Leave policy" and "vacation  │
│  rules" will have SIMILAR      │
│  vectors even though the       │
│  words are different!          │
└────────────┬────────────────────┘
             ▼
┌──── STEP 5: Storage ───────────┐
│  Vectors → ChromaDB/Pinecone   │
│  Chunks → SQL DocumentChunk    │
│  File → Supabase Storage       │
│  Status → "done" ✅            │
└─────────────────────────────────┘
```

**The actual code that does the chunking** (`backend/app/ingestion.py`):

```python
def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150):
    """
    Semantic-aware recursive text splitter.
    Splits by: ## headers → paragraphs → lines → sentences → words
    This preserves context better than naive character splitting.
    """
    separators = ["\n## ", "\n\n", "\n", ". ", " "]
    
    for separator in separators:
        if separator in text:
            parts = text.split(separator)
            chunks = []
            current = ""
            for part in parts:
                if len(current) + len(part) > chunk_size:
                    chunks.append(current.strip())
                    # Overlap: keep the last 150 chars for context continuity
                    current = current[-chunk_overlap:] + separator + part
                else:
                    current += separator + part
            if current.strip():
                chunks.append(current.strip())
            return chunks
    
    # Fallback: character-level splitting
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - chunk_overlap)]
```

**Why 800 characters? Why 150 overlap?**
- 800 chars ≈ 200 tokens, which fits comfortably in any embedding model's context
- 150 char overlap ensures sentences at chunk boundaries aren't cut in half
- If a sentence says "The leave policy (continued from previous section) allows 15 days", the overlap captures that continuity

---

### Flow 2: AI Query (How the AI "Answers")

When you ask "What is the leave policy for contractors?":

```
Your question: "What is the leave policy for contractors?"
        │
        ▼
┌──── STEP 1: Your question → Vector ────┐
│  Same embedding model converts your    │
│  question into a 768-dim vector        │
└────────────┬───────────────────────────┘
             ▼
┌──── STEP 2: Hybrid Search ─────────────┐
│                                         │
│  TWO searches happen simultaneously:    │
│                                         │
│  Vector Search (Semantic):              │
│  "leave policy" is SIMILAR to           │
│  "vacation rules", "time-off policy"    │
│  → finds conceptually related chunks    │
│                                         │
│  BM25 Search (Keyword):                 │
│  Exact word matching — catches          │
│  "contractor" even if embedding         │
│  doesn't perfectly capture it           │
│                                         │
│  Results merged using Reciprocal        │
│  Rank Fusion (RRF):                     │
│  score = 1/(rank_vector + 60)           │
│        + 1/(rank_bm25 + 60)             │
│  → Best of both worlds!                 │
└────────────┬───────────────────────────┘
             ▼
┌──── STEP 3: Knowledge Graph ───────────┐
│  GraphAgent searches for entities:      │
│  "contractor" → finds User nodes       │
│  with role=Contractor                   │
│  → traverses edges to find related      │
│  departments, documents, tasks          │
└────────────┬───────────────────────────┘
             ▼
┌──── STEP 4: Context Compilation ───────┐
│  All results merged into one prompt:    │
│  • Top 5 document chunks               │
│  • Graph relationships                 │
│  • Related task tickets                │
│  • Your personal memory context        │
│  • Your conversation history           │
└────────────┬───────────────────────────┘
             ▼
┌──── STEP 5: LLM Generation ───────────┐
│  System prompt + compiled context      │
│  sent to Gemini/OpenAI/Groq           │
│  Response streamed back in real-time   │
│  with source citations                 │
└────────────┬───────────────────────────┘
             ▼
┌──── STEP 6: You see the answer ───────┐
│  "According to [HR_Policy_2024.pdf],  │
│   contractors are entitled to 10 days │
│   of paid leave per quarter..."       │
│                                        │
│  📎 Sources: HR_Policy_2024.pdf       │
│  🔄 Agent Steps: Search → Graph → LLM│
└────────────────────────────────────────┘
```

**The actual hybrid search code** (`backend/app/vectorstore.py`):

```python
def search(self, query, department_id, api_key, llm_provider, top_k=5):
    # 1. Vector similarity search
    query_embedding = self.embedding_provider.get_embedding(query, api_key, llm_provider)
    vector_results = self.collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k * 2,
        where={"department_id": str(department_id)}  # Department isolation!
    )
    
    # 2. BM25 keyword search
    bm25_index = self._get_bm25_index(department_id)
    tokenized_query = query.lower().split()
    bm25_scores = bm25_index.get_scores(tokenized_query)
    
    # 3. Reciprocal Rank Fusion (merge both)
    rrf_scores = {}
    for rank, doc_id in enumerate(vector_results):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (rank + 60)
    for rank, doc_id in enumerate(bm25_ranked):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (rank + 60)
    
    # 4. Return top-K by combined score
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
```

---

## The Multi-Agent System (The Brain)

The AI isn't one monolithic function. It's a team of specialized agents:

```
                    ┌─────────────────────┐
                    │     CEO AGENT       │
                    │   (Orchestrator)    │
                    │                     │
                    │  "I decide WHO to   │
                    │   ask and WHAT to   │
                    │   compile"          │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
     ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
     │SearchAgent  │   │ GraphAgent  │   │MemoryAgent  │
     │             │   │             │   │             │
     │"I search    │   │"I find      │   │"I remember  │
     │ documents   │   │ entity      │   │ what you    │
     │ in the      │   │ connections │   │ told me     │
     │ vector DB"  │   │ in the      │   │ before"     │
     │             │   │ knowledge   │   │             │
     │             │   │ graph"      │   │             │
     └─────────────┘   └─────────────┘   └─────────────┘
```

**The actual orchestration code** (`backend/app/agents/ceo_agent.py`):

```python
async def process_query_stream(self, query, user, db, settings):
    # Step 1: Safety — prevent infinite loops
    session = ACTIVE_AGENT_SESSIONS.get(user.id, {"turns": 0})
    if session["turns"] >= 10:
        yield {"type": "error", "text": "Session limit reached"}
        return
    
    # Step 2: Fast-path — org directory queries don't need AI
    if self._is_org_directory_query(query):
        directory = await self._get_org_directory(user, db)
        yield {"type": "chunk", "text": directory}
        return
    
    # Step 3: Concurrent sub-agent dispatch
    # All agents run AT THE SAME TIME for speed
    search_results = self.search_agent.execute(query, dept_id, api_key, provider)
    graph_context = await self.graph_agent.execute(query, db)
    incident_context = await self.incident_agent.execute(query, db)
    user_memories = await self.memory_agent.retrieve(user.id, db)
    
    # Step 4: Compile everything into one context
    context = f"""
    DOCUMENT CONTEXT:
    {search_results}
    
    KNOWLEDGE GRAPH:
    {graph_context}
    
    RELATED TASKS:
    {incident_context}
    
    USER MEMORY:
    {user_memories}
    """
    
    # Step 5: Stream LLM response
    async for chunk in self.llm_client.stream(system_prompt, context + query):
        yield {"type": "chunk", "text": chunk}
```

---

## The Authentication & Access Control System

This isn't just "login/logout". It's a 3-layer security system:

### Layer 1: JWT Authentication
```python
# backend/app/auth.py

def create_access_token(data: dict):
    """Creates a JWT token that expires in 24 hours"""
    expire = datetime.utcnow() + timedelta(minutes=1440)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    """Every protected API call goes through this"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload.get("sub")
    user = await db.execute(select(User).filter(User.id == user_id))
    return user.scalars().first()
```

### Layer 2: RBAC (Role-Based Access Control)
```python
# "Only Admins can delete users"
def check_role(allowed_roles: list):
    async def role_checker(current_user = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user
    return role_checker

# Usage in routes:
@router.delete("/users/{user_id}", dependencies=[Depends(check_role(["Admin"]))])
```

### Layer 3: ABAC (Attribute-Based Access Control)
```python
# backend/app/abac.py
# "A Manager can only delete documents uploaded by their direct reports"

def verify_document_access(action: str):
    async def checker(document_id, current_user, db):
        document = await get_document(document_id, db)
        
        if current_user.role == "Admin":
            return True  # Admins bypass everything
        
        if action == "delete":
            if document.uploaded_by == current_user.id:
                return True  # You can delete YOUR OWN docs
            if current_user.role == "Manager":
                uploader = await get_user(document.uploaded_by, db)
                if uploader.manager_id == current_user.id:
                    return True  # Managers can delete their team's docs
            return False
        
        if action == "read":
            return document.department_id == current_user.department_id
    return checker
```

---

## The PII Redaction Pipeline

Before ANY document text is stored or sent to an AI:

```python
# backend/app/pii_redactor.py

# These patterns catch sensitive data BEFORE it enters the system
_PII_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[REDACTED_EMAIL]"),
    (r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b', "[REDACTED_SSN]"),
    (r'(\+?\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4})', "[REDACTED_PHONE]"),
    (r'\b(?:\d[ -]?){13,16}\b', "[REDACTED_CARD]"),
]

# BEFORE: "Contact john@company.com or call 555-123-4567"
# AFTER:  "Contact [REDACTED_EMAIL] or call [REDACTED_PHONE]"
```

**Why this matters**: If you send "John's SSN is 123-45-6789" to OpenAI's API, that data could be stored on their servers. PII redaction prevents this.

---

## The LLM Client (How We Talk to AI Models)

```python
# backend/app/llm_client.py

class LLMClient:
    def __init__(self):
        self._cache = {}           # Don't call API for same question twice
        self._failure_count = 0    # Track consecutive failures
        self._circuit_open = False # Circuit breaker flag
    
    async def stream(self, system_prompt, user_message, api_key, provider):
        # Circuit Breaker: After 5 failures, stop trying
        if self._circuit_open:
            yield "I'm currently in simulation mode..."
            return
        
        # Check cache first
        cache_key = hash(system_prompt + user_message)
        if cache_key in self._cache:
            yield self._cache[cache_key]
            return
        
        # Semantic Routing (Groq only):
        # Short simple questions → cheap small model
        # Complex questions → expensive powerful model
        if provider == "groq":
            if len(user_message) < 100 and not any(w in user_message for w in ["compare", "analyze"]):
                model = "llama-3.1-8b-instant"      # Fast & cheap
            else:
                model = "llama-3.3-70b-versatile"    # Powerful
        
        # Retry with exponential backoff
        for attempt in range(3):
            try:
                async for chunk in self._call_provider(provider, model, ...):
                    yield chunk
                self._failure_count = 0  # Reset on success
                return
            except Exception:
                await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
                self._failure_count += 1
        
        # If all retries failed
        if self._failure_count >= 5:
            self._circuit_open = True  # Stop trying, go to simulation
```

---

# PART 2: WHY THESE TECHNOLOGIES? (vs. Alternatives)

---

## Frontend: React vs. Alternatives

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| **UI Framework** | React 19 | Next.js, Angular, Vue | React is the most widely used, has the largest ecosystem, and this is an SPA that doesn't need SSR. Next.js would add unnecessary complexity for a dashboard app. |
| **Build Tool** | Vite | Create React App, Webpack | Vite is 10-100x faster than CRA for dev server startup. CRA is deprecated. |
| **Styling** | Vanilla CSS | Tailwind, CSS-in-JS | Full control over design. No utility class bloat. Three theme files (dark, crimson, light) would be harder with Tailwind. |
| **Data Fetching** | @tanstack/react-query | SWR, Redux, manual fetch | Auto-caching, background refetch, stale-time management. Redux is overkill for server-state. |
| **Icons** | lucide-react | Font Awesome, Material Icons | Tree-shakeable (only imports used icons), consistent SVG quality, 0 font downloads. |
| **Sanitization** | DOMPurify | sanitize-html | Industry standard for XSS prevention. Critical because we render AI-generated markdown. |

## Backend: FastAPI vs. Alternatives

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| **Framework** | FastAPI | Django, Flask, Express.js | FastAPI is async-native (critical for streaming + concurrent AI calls). Auto-generates OpenAPI docs. Django is too opinionated. Flask lacks async. Express.js would split the backend language from Python's AI ecosystem. |
| **ORM** | SQLAlchemy 2.0 (async) | Django ORM, Prisma, raw SQL | SQLAlchemy supports both sync and async, works with both SQLite and PostgreSQL, and has the most mature Python ecosystem. |
| **Auth** | JWT (PyJWT) | Session cookies, OAuth2 | JWT is stateless — no server-side session storage needed. Works perfectly with SPA frontends and mobile apps. |
| **Password Hashing** | bcrypt (Passlib) | argon2, scrypt | bcrypt is the industry standard, battle-tested for decades. Passlib provides a clean abstraction. |

## Database: PostgreSQL vs. Alternatives

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| **Relational DB** | PostgreSQL (Supabase) | MySQL, MongoDB, Firebase | PostgreSQL supports the `pgvector` extension for native vector search. Supabase gives us free managed Postgres + S3 storage in one service. MongoDB would lose relational integrity for user→task→document relationships. |
| **Vector DB** | ChromaDB + Pinecone | Weaviate, Milvus, FAISS | ChromaDB for local dev (zero config, embedded). Pinecone for production (managed, free tier, no ops). FAISS doesn't persist to disk. Weaviate requires Docker. |
| **Knowledge Graph** | SQL-backed (KGNode/KGEdge) | Neo4j, Amazon Neptune | Neo4j requires a separate server and paid hosting. Our graph is simple enough (departments→users→documents) that SQL tables with foreign keys work perfectly. This saved hosting costs. |

## AI: Architecture Decisions

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| **RAG approach** | Custom multi-agent | LangChain, LlamaIndex | Custom gives us full control over the retrieval pipeline. LangChain adds heavy abstraction and dependency bloat. Our hybrid search (vector + BM25 + graph) is more sophisticated than LangChain's default retriever. |
| **Search strategy** | Hybrid (Vector + BM25 + RRF) | Pure vector search | Pure vector search misses exact keywords. If someone searches for "Policy #A-2847", vector similarity might not catch the exact ID. BM25 catches it. RRF combines both intelligently. |
| **Embedding model** | Per-user configurable | Fixed single model | Different users may have different API keys. Per-user config allows teams to use their own Gemini, OpenAI, or Groq accounts. |
| **LLM streaming** | Server-Sent Events (SSE) | WebSocket, polling | SSE is simpler than WebSocket for unidirectional streaming. The browser natively supports it. No need for bidirectional communication for chat responses. |
| **PII handling** | Redact before embedding | Redact at query time | If PII enters the vector database, it's already leaked. Redacting BEFORE embedding ensures it never reaches third-party APIs or storage. |

---

# PART 3: INTERVIEW PREPARATION

---

## Category 1: Project Overview Questions

### Q1: "Tell me about your project."
**Answer**: "I built ProcessPilot AI, an enterprise knowledge management platform that uses RAG — Retrieval-Augmented Generation — to let employees ask questions about their company's documents and get accurate, cited answers. It has a React frontend, FastAPI backend, and uses a multi-agent AI architecture where a CEO agent orchestrates specialized sub-agents for document search, knowledge graph traversal, and user memory. The system supports hybrid search combining vector similarity with BM25 keyword matching via Reciprocal Rank Fusion, and enforces role-based plus attribute-based access control so employees only see their department's data."

### Q2: "What problem does it solve?"
**Answer**: "In large organizations, knowledge is scattered across hundreds of documents. Employees waste 20-30% of their time searching for information. ProcessPilot AI centralizes this knowledge and makes it searchable through natural language. Unlike simple keyword search, our RAG pipeline understands meaning — so asking 'vacation policy' finds documents about 'leave rules' even if those exact words aren't used."

### Q3: "How is this different from just using ChatGPT?"
**Answer**: "Three critical differences:
1. **Grounded in your data**: ChatGPT hallucinates because it doesn't know your company's specific policies. Our RAG pipeline retrieves actual document chunks before generating answers, with source citations.
2. **Access control**: ChatGPT can't enforce 'Engineers shouldn't see HR salary data'. Our ABAC system isolates data by department.
3. **Data stays private**: Documents are embedded and stored in YOUR database, not sent to OpenAI for training. PII is redacted before any text reaches external APIs."

### Q4: "Why did you build this? What was the motivation?"
**Answer**: "I wanted to solve a real enterprise problem — knowledge fragmentation — while implementing cutting-edge AI concepts: RAG with hybrid retrieval, multi-agent orchestration, knowledge graphs, and human-in-the-loop feedback loops. It also gave me hands-on experience with production challenges like free-tier deployment constraints, circuit breakers for API reliability, and data flywheel design for continuous model improvement."

---

## Category 2: Architecture & Design Questions

### Q5: "Explain the architecture of your project."
**Answer**: "It's a three-tier architecture:
- **Frontend**: React 19 SPA hosted on Vercel, communicating via REST APIs and SSE streaming
- **Backend**: FastAPI async server on Render, with a multi-agent AI pipeline
- **Data Layer**: Supabase PostgreSQL for relational data, ChromaDB/Pinecone for vector embeddings, and a SQL-backed Knowledge Graph

The key architectural decision was making everything async — FastAPI with asyncpg for non-blocking database queries, which is critical because AI API calls can take 2-5 seconds and we can't block the server."

### Q6: "Why FastAPI instead of Django or Express?"
**Answer**: "Three reasons:
1. **Async-native**: AI queries call external LLM APIs that take seconds. FastAPI's async/await means one slow AI call doesn't block other users' requests. Django's sync nature would require Celery for this.
2. **Streaming**: Our chat uses Server-Sent Events. FastAPI's `StreamingResponse` makes this trivial. Django would need Django Channels.
3. **Python ecosystem**: All major AI libraries (OpenAI, Gemini, ChromaDB, PyMuPDF) are Python-native. Using Express.js would mean a language boundary between the API and AI layers."

### Q7: "Why React instead of Next.js?"
**Answer**: "ProcessPilot is a dashboard application, not a content website. It doesn't need:
- Server-side rendering (no SEO requirements for a login-protected app)
- File-system based routing (we have 11 simple routes)
- API routes (our API is a separate FastAPI server)

React with Vite gives us the fastest dev experience with the smallest bundle. Next.js would add server-side complexity we don't need."

### Q8: "Why did you use SQL for the Knowledge Graph instead of Neo4j?"
**Answer**: "This was a pragmatic engineering decision. Our graph is relatively simple — departments, users, documents, and their relationships. For this use case, two SQL tables (KGNode and KGEdge) with indexed queries are fast enough. Neo4j would require:
- A separate managed database service ($$$)
- A separate driver and connection pool
- More operational complexity

On our free-tier hosting constraint, this saved significant cost. If the graph grew to millions of nodes with complex traversal queries (shortest path, page rank), I would migrate to Neo4j."

### Q9: "Why is the ceo_agent.py file so large (43KB)?"
**Answer**: "It's the orchestrator for the entire AI pipeline. It handles:
- Intent classification (comparison vs SOP vs general)
- RBAC-aware data scoping
- Concurrent sub-agent dispatch
- Context compilation from 6+ sources
- LLM prompt construction
- Streaming response generation
- Memory management
- Logging

In hindsight, I could refactor it into smaller modules — separating intent classification, context compilation, and prompt formatting into their own files. But the current design keeps the entire orchestration flow readable in one place."

---

## Category 3: RAG & AI Questions

### Q10: "Explain RAG in simple terms."
**Answer**: "RAG stands for Retrieval-Augmented Generation. Instead of asking an AI to answer from its training data (which may be outdated or wrong), we first RETRIEVE relevant documents from our database, then give those documents to the AI as context, and ask it to GENERATE an answer based on that context. This grounds the AI's response in factual data and dramatically reduces hallucination."

### Q11: "What is the difference between vector search and keyword search?"
**Answer**: "Keyword search (like BM25) matches exact words — searching 'vacation policy' won't find a document titled 'Leave Rules'. Vector search converts text into mathematical representations (embeddings) where semantically similar texts have similar vectors. So 'vacation policy' and 'leave rules' would have similar embeddings and would match.

However, vector search can miss exact identifiers — searching for 'Policy #A-2847' might not work well with vectors. That's why we use HYBRID search: vector for meaning, BM25 for exact terms, merged via Reciprocal Rank Fusion."

### Q12: "What is Reciprocal Rank Fusion?"
**Answer**: "RRF is a simple but effective way to merge results from multiple ranking systems. For each document, we calculate: `score = Σ 1/(rank_i + k)` where `rank_i` is its position in each system and `k` is a constant (we use 60). A document ranked #1 in both systems gets `1/61 + 1/61 = 0.033`. A document ranked #1 in vector but #10 in BM25 gets `1/61 + 1/70 = 0.031`. This naturally promotes documents that rank well in BOTH systems."

### Q13: "Why 768 dimensions for embeddings?"
**Answer**: "We use Google's `text-embedding-004` model which outputs 768-dimensional vectors. This is the model's native dimension — it's what Google trained the model to produce. If we used OpenAI's `text-embedding-3-small`, we'd get 1536 dimensions. Higher dimensions can capture more nuance but use more storage and compute. 768 is a good balance for our use case."

### Q14: "How do you handle the context window limit of LLMs?"
**Answer**: "Multiple strategies:
1. **Chunking**: Documents are split into 800-char chunks, so we only retrieve the most relevant chunks, not entire documents
2. **Top-K retrieval**: We only send the top 5 most relevant chunks to the LLM
3. **Compression**: Context is formatted concisely with clear section headers
4. **Semantic chunking**: We split at natural boundaries (headers, paragraphs) so each chunk is self-contained"

### Q15: "What is the Knowledge Graph? How does it help RAG?"
**Answer**: "The Knowledge Graph stores entities (departments, users, documents) and their relationships (belongs_to, uploaded, reports_to) as a graph. When a user asks about 'Engineering department documents', the GraphAgent:
1. Finds the 'Engineering' node
2. Traverses edges to find all connected document nodes
3. Provides this structural context to the LLM

This helps because vector search might miss organizational relationships. A document about 'Server Migration' might not semantically match 'Engineering department' — but the Knowledge Graph knows it was uploaded BY an engineering employee."

### Q16: "What is the circuit breaker in your LLM client?"
**Answer**: "It's a fault tolerance pattern. If the OpenAI/Gemini API fails 5 times consecutively, instead of keeping trying (and making users wait), the circuit breaker 'opens' and all subsequent requests immediately fall back to simulation mode with pre-written responses. This ensures the app remains usable even when external APIs are down. The circuit breaker resets when the server restarts."

### Q17: "What is the 'Data Flywheel' you implemented?"
**Answer**: "A data flywheel is a self-improving loop:
1. Users ask questions → AI responds
2. Users give thumbs-down on bad responses → logged to AIFailure table
3. When managers edit AI-generated task titles → the edit is logged as implicit feedback
4. Admins export high-quality Q&A pairs (excluding thumbs-down entries) as JSONL
5. This JSONL can be used to fine-tune a custom model
6. The fine-tuned model gives better answers → fewer thumbs-downs → better training data

Each cycle improves the system without manual intervention."

---

## Category 4: Database & Data Questions

### Q18: "Why SQLAlchemy instead of raw SQL?"
**Answer**: "Three reasons:
1. **Database portability**: Same code runs on SQLite (development) and PostgreSQL (production) without changes
2. **Async support**: SQLAlchemy 2.0's async sessions work seamlessly with FastAPI's async routes
3. **Type safety**: ORM models catch schema mismatches at import time, not at runtime"

### Q19: "Explain the cascade delete logic when a user is deleted."
**Answer**: "This was one of the most complex parts. When an Admin deletes a user:
1. **Employee deletion**: Their assigned tasks go to their manager. Their documents get reassigned to an Admin with a note '(originally by [Name])'.
2. **Manager deletion**: Requires a `successor_id`. The successor inherits all direct reports, all overseen tasks, and the department. If the successor is an Employee, they get automatically promoted to Manager.
3. **Admin deletion**: Documents and tasks reassigned to the Admin performing the deletion.
4. **Safety**: An Admin cannot delete themselves while logged in."

### Q20: "How do you handle database migrations?"
**Answer**: "We use Alembic, which tracks schema changes as versioned migration scripts. However, for the initial deployment, we use SQLAlchemy's `Base.metadata.create_all()` during app startup, which auto-creates tables. For PostgreSQL specifically, we also run `CREATE EXTENSION IF NOT EXISTS vector` to enable the pgvector extension."

---

## Category 5: Security Questions

### Q21: "How do you prevent SQL injection?"
**Answer**: "SQLAlchemy uses parameterized queries by default. When I write `select(User).filter(User.email == email)`, SQLAlchemy generates `SELECT * FROM users WHERE email = $1` with the value passed as a parameter, not concatenated into the SQL string. This makes SQL injection impossible."

### Q22: "How do you prevent XSS attacks?"
**Answer**: "Two layers:
1. **Backend**: Pydantic schemas validate all input. No raw HTML is stored in the database.
2. **Frontend**: All AI-generated markdown is passed through DOMPurify before rendering. Even if the AI somehow outputs `<script>alert('hack')</script>`, DOMPurify strips it to plain text."

### Q23: "How do you protect API keys?"
**Answer**: "Multiple strategies:
1. **Environment variables**: Backend API keys are in `.env` files that are gitignored
2. **Production safety check**: The app crashes on startup if the default SECRET_KEY is used in production
3. **Per-user keys masked**: The settings API returns `gemini_api_key_set: true/false` instead of the actual key
4. **PII redaction**: Document text is sanitized before reaching any external API"

### Q24: "What is rate limiting and why did you implement it?"
**Answer**: "Rate limiting prevents abuse. Our login endpoint allows 20 attempts per hour per IP. Registration allows 10 per hour. Without this, an attacker could:
- Brute-force passwords with millions of attempts
- Create thousands of spam accounts
- Overload the server with requests

Our implementation uses an in-memory dictionary tracking IP → request timestamps. It's simple but effective for a single-server deployment."

### Q25: "What happens if someone tries to register as Admin?"
**Answer**: "The registration endpoint explicitly blocks it:
```python
if user_data.role and user_data.role.lower() == 'admin':
    raise HTTPException(status_code=403, detail='Admin registration is not allowed')
```
Admins can only be created by other Admins through the user management interface."

---

## Category 6: Deployment & DevOps Questions

### Q26: "How is the app deployed?"
**Answer**: "Entirely on free tiers:
- **Frontend**: Vercel auto-builds React on every GitHub push
- **Backend**: Render runs the FastAPI server (sleeps after 15 min inactivity)
- **Database**: Supabase PostgreSQL via session pooler (IPv4 compatible)
- **Storage**: Supabase S3 buckets for uploaded files
- **Vectors**: Pinecone free index for production embeddings
- **CI/CD**: GitHub Actions runs Ruff linting + Pytest on every push"

### Q27: "Why Render instead of AWS/GCP?"
**Answer**: "Cost. AWS requires configuring VPCs, security groups, load balancers, RDS instances — and charges even for idle resources. Render gives us a one-click deploy from GitHub with zero configuration. The tradeoff is the 15-minute sleep timeout on the free tier, which causes a ~50 second cold start. For a demo/portfolio project, this is acceptable."

### Q28: "How do you handle Render's ephemeral filesystem?"
**Answer**: "Render's free tier deletes all local files when the server sleeps. We solved this with:
1. **Database**: Supabase PostgreSQL (external, persistent)
2. **File storage**: Supabase Storage buckets (external, persistent)
3. **Vector DB**: Pinecone (external, persistent)
4. **In-memory state**: Accepted as ephemeral (rate limiter resets, BM25 caches rebuild)"

### Q29: "What does your CI/CD pipeline do?"
**Answer**: "On every push or PR to main:
1. **Lint**: Ruff checks for Python syntax errors and style violations
2. **Test**: Pytest runs the test suite with coverage reporting
3. **Coverage**: Results uploaded to Codecov for tracking

This prevents broken code from reaching production."

---

## Category 7: Edge Cases & Error Handling

### Q30: "What happens if the LLM API is down?"
**Answer**: "The circuit breaker kicks in. After 5 consecutive failures, all requests automatically fall back to 'simulation mode' which returns pre-written helpful responses. The user sees a notice that the AI is in simulation mode. The system remains fully functional for all non-AI features."

### Q31: "What happens if someone uploads a 500MB file?"
**Answer**: "Multiple guards:
1. **Frontend**: JavaScript checks file size before upload (max 10MB)
2. **Backend**: Server-side validation rejects files exceeding `MAX_UPLOAD_SIZE_MB`
3. **Streaming upload**: Files are written to disk in 1MB chunks, not loaded entirely into memory, preventing OOM"

### Q32: "What happens if document ingestion fails?"
**Answer**: "The ingestion runs as a background task. If it fails at any point (parsing error, embedding API failure, vector DB write failure), the exception is caught, logged, and the document's `ingestion_status` is set to `'failed'`. The user sees this status in the UI and can re-upload. The partially-processed chunks are cleaned up."

### Q33: "What happens if two people upload at the same time?"
**Answer**: "Background ingestion uses an asyncio semaphore to limit concurrent processing. This prevents multiple large uploads from consuming all memory simultaneously. Uploads are queued and processed in order within the semaphore's capacity."

### Q34: "What if a Manager is deleted but they have 50 direct reports?"
**Answer**: "The deletion endpoint REQUIRES a `successor_id`. All 50 direct reports are automatically transferred to the successor. If the successor is currently an Employee, they get promoted to Manager and inherit the department. This ensures zero orphaned employees."

### Q35: "What if the WebSocket connection drops?"
**Answer**: "The WebSocket context in the frontend handles disconnection gracefully. The `ConnectionManager` on the backend removes dead connections. Task updates that happen while disconnected are NOT retroactively sent — this is a known limitation. The user will see the updated data on their next page refresh."

---

## Category 8: Performance & Scalability Questions

### Q36: "How do you handle large PDFs (100+ pages)?"
**Answer**: "Three optimizations:
1. **Streaming extraction**: PyMuPDF processes pages one at a time
2. **Batched embedding**: Chunks are embedded in batches of 50 to prevent OOM on Render's 512MB
3. **Background processing**: Upload returns 202 immediately; ingestion happens asynchronously"

### Q37: "How does hybrid search scale?"
**Answer**: "The BM25 index is maintained per-department in memory. For ChromaDB, this means each department has its own cached index. For production with Pinecone, BM25 is not used — Pinecone handles the full semantic search server-side. The vector database itself scales horizontally."

### Q38: "What would you change for 10,000 users?"
**Answer**: "Several things:
1. **Rate limiter**: Move from in-memory to Redis-backed
2. **WebSocket**: Add Redis pub/sub for cross-worker broadcasting
3. **Background tasks**: Move from FastAPI BackgroundTasks to Celery with Redis broker
4. **Database**: Add connection pooling, read replicas
5. **Caching**: Add Redis caching for analytics queries
6. **LLM**: Implement request queuing to prevent API quota exhaustion"

---

## Category 9: Code Quality & Best Practices

### Q39: "How do you handle environment-specific configuration?"
**Answer**: "Using Pydantic Settings with automatic environment detection:
```python
class Settings(BaseSettings):
    DATABASE_URL: str = 'sqlite:///./processpilot.db'  # Dev default
    
    @field_validator('ENVIRONMENT', mode='before')
    def detect_environment(cls, v):
        db_url = os.getenv('DATABASE_URL', '')
        if 'postgresql' in db_url:
            return 'production'  # Auto-detect production
        return v or 'development'
```
Development uses SQLite with no configuration needed. Production uses PostgreSQL — detected automatically from the DATABASE_URL."

### Q40: "How do you handle async database operations?"
**Answer**: "SQLAlchemy 2.0 with `async_sessionmaker` and `AsyncSession`. The database URL is automatically rewritten:
```python
# postgresql:// → postgresql+asyncpg://  (async driver)
# sqlite://    → sqlite+aiosqlite://      (async driver)
```
Every route uses `async def` and `await` for database queries, ensuring no blocking I/O."

---

## Category 10: Tough/Tricky Questions

### Q41: "What are the weaknesses of your project?"
**Answer** (be honest — interviewers respect self-awareness):
"1. **Rate limiter is in-memory**: It resets when the server restarts and doesn't work across multiple workers
2. **No request queuing for LLM calls**: Under heavy load, all users hit the API simultaneously
3. **WebSocket not authenticated**: Only uses user_id path parameter, not JWT verification
4. **Knowledge Graph is simple**: SQL tables with basic traversal, not true graph queries like shortest path
5. **NetworkX dependency unused**: It's in requirements.txt but the KG was migrated to SQL
6. **No automated end-to-end tests**: We have API tests but no Cypress/Playwright UI tests"

### Q42: "If you had 6 more months, what would you add?"
**Answer**: "1. **Fine-tuning pipeline**: Use the synthetic dataset export to actually fine-tune a model
2. **Multi-modal RAG**: Support images and diagrams in documents
3. **Conversation memory**: Currently chat history is in localStorage; I'd move it to the Conversation SQL table
4. **Real-time collaboration**: Multiple users discussing AI responses in shared threads
5. **Advanced graph queries**: Migrate to Neo4j for shortest-path, community detection
6. **Evaluation framework**: RAGAS or similar to automatically measure RAG quality"

### Q43: "Why didn't you use LangChain?"
**Answer**: "I deliberately chose NOT to use LangChain for several reasons:
1. **Understanding**: Building the RAG pipeline from scratch gave me deep understanding of how embeddings, chunking, retrieval, and prompt construction actually work
2. **Control**: LangChain's abstractions sometimes hide important details. Our hybrid search with RRF would be harder to implement within LangChain's retriever interface
3. **Dependencies**: LangChain pulls in 50+ transitive dependencies. Our custom solution has minimal dependencies
4. **Performance**: Direct API calls to Gemini/OpenAI are faster than going through LangChain's abstraction layers"

### Q44: "How do you ensure AI responses are accurate?"
**Answer**: "Multiple strategies:
1. **Grounding**: Every response is based on retrieved document chunks, not the LLM's training data
2. **Source citations**: Users can verify answers by checking the cited documents
3. **Department isolation**: The AI can only access documents from the user's department, reducing confusion
4. **Human-in-the-loop**: Thumbs-down feedback identifies bad responses for review
5. **Data flywheel**: Implicit corrections (title edits) continuously improve quality
6. **System prompt**: Instructs the LLM to say 'I don't have information about that' rather than hallucinate"

### Q45: "Walk me through what happens when I click 'Send' in the chat."
**Answer**: "Let me trace the complete path:
1. `Chat.jsx`: `handleSend()` fires, appends user message to state
2. `fetch()` sends POST to `/api/v1/chat/` with `{query, history, scoped_node_ids}`
3. `routes/chat.py`: Validates JWT, loads user settings (API key, provider)
4. `ceo_agent.py`: `process_query_stream()` starts
5. Safety check: is this session under 10 turns?
6. Fast-path check: is this an org directory query?
7. Intent check: comparison, SOP, or general?
8. Concurrent dispatch: SearchAgent → vector DB, GraphAgent → KG, IncidentAgent → SQL
9. Context compilation: all results + analytics + tasks + memory + history
10. `llm_client.py`: `stream()` calls Gemini/OpenAI/Groq
11. SSE events yielded: `metadata` → `chunk` → `chunk` → ... → `done`
12. `Chat.jsx`: `ReadableStream` reader processes each chunk, updates state
13. React re-renders with each new token (streaming effect)
14. After completion: MemoryAgent checks for 'remember' directives
15. `AgentLog` record created with full trace

Total time: 2-5 seconds for the first token, streaming continues for 5-15 seconds."

---

## Quick Reference: All Technologies at a Glance

```
FRONTEND                          BACKEND                         DATA LAYER
────────                          ───────                         ──────────
React 19                          FastAPI 0.110                   PostgreSQL (Supabase)
Vite 5                            Uvicorn 0.28                    ChromaDB 0.4.24
react-router-dom 7                SQLAlchemy 2.0 (async)          Pinecone 3.2.2
@tanstack/react-query 5           Pydantic 2.6                    pgvector 0.5.0
lucide-react                      PyJWT 2.8 + bcrypt              Supabase Storage
DOMPurify 3.4                     PyMuPDF 1.23                    
                                  python-docx 1.1                 
AI/ML                             rank-bm25 0.2                   DEPLOYMENT
─────                             tenacity 8.2                    ──────────
Gemini (text-embedding-004)       httpx 0.27                      Vercel (Frontend)
OpenAI (text-embedding-3-small)   aiofiles 23.2                   Render (Backend)
Groq (Llama 3.1/3.3)                                              GitHub Actions (CI/CD)
Custom Multi-Agent System                                          
Hybrid Search (Vector + BM25)                                      
Reciprocal Rank Fusion                                             
PII Redaction (Regex + Presidio)                                   
```
