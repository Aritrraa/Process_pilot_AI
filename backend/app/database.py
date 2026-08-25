from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .config import settings

# Rewrite URL for asyncpg if it's PostgreSQL
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

is_sqlite = db_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Fix for Supabase Transaction Pooler (port 6543) crashing asyncpg
if not is_sqlite:
    connect_args["prepared_statement_cache_size"] = 0

# For SQLite async we would need aiosqlite, but assuming production is Postgres
if is_sqlite:
    # Use aiosqlite for local dev if they still use sqlite
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")

engine = create_async_engine(
    db_url, connect_args=connect_args
)

SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession, expire_on_commit=False)

# Create a synchronous engine and sessionmaker for background threads (e.g. pgvector ingestion/search)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sync_db_url = settings.DATABASE_URL
sync_connect_args = {"check_same_thread": False} if is_sqlite else {}
sync_engine = create_engine(sync_db_url, connect_args=sync_connect_args)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

# Dependency to get db session
async def get_db():
    async with SessionLocal() as db:
        yield db
