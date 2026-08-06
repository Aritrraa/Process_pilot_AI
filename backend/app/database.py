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

# For SQLite async we would need aiosqlite, but assuming production is Postgres
if is_sqlite:
    # Use aiosqlite for local dev if they still use sqlite
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")

engine = create_async_engine(
    db_url, connect_args=connect_args
)

SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Dependency to get db session
async def get_db():
    async with SessionLocal() as db:
        yield db
