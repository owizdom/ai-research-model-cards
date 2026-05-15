from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from .config import settings

engine = create_async_engine(
    settings.DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=10, max_overflow=20,
    # Postgres auto-aborts any transaction that sits idle this long, which
    # releases held advisory locks if a worker thread crashes mid-extraction.
    # Set in milliseconds; 30 min covers the longest legitimate Claude CLI call.
    connect_args={"server_settings": {"idle_in_transaction_session_timeout": "1800000"}},
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        from .models import lab, document, taxonomy, model_family, eval, eval_source  # noqa
        await conn.run_sync(Base.metadata.create_all)
