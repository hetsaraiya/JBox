# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
import logging

DATABASE_URL = "postgresql+asyncpg://postgres.hsgstrgqrxxlefxjzgds:BOMRAgaruFD3BOVU@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

# Create the async engine with `statement_cache_size` set to 0
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=1,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False,autocommit=False,autoflush=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logging.error(f"Database connection error: {e}")
            raise
        finally:
            await session.close()



# # app/database.py
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import sessionmaker, declarative_base

# DATABASE_URL = "sqlite+aiosqlite:///./data.db"
# engine = create_async_engine(DATABASE_URL, echo=True)
# AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
# Base = declarative_base()

# async def get_db():
#     async with AsyncSessionLocal() as session:
#         try:
#             yield session
#         finally:
#             await session.close()
