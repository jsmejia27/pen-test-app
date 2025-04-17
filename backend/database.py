import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL found in environment variables")

# Use connect_args for SQLite specific options if needed
engine = create_async_engine(DATABASE_URL, echo=True) # echo=True for logging SQL statements (optional)
# For SQLite, connect_args might be needed, e.g., {"check_same_thread": False} is NOT needed for aiosqlite
# engine = create_async_engine(DATABASE_URL, echo=True, connect_args={})

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    """Dependency to get a database session."""
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """Initialize the database tables."""
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Uncomment to drop tables on startup
        await conn.run_sync(Base.metadata.create_all)