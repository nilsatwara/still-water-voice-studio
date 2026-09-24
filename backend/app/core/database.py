"""Central PostgreSQL engine and async session lifecycle.

The engine is created once per API process and owns its connection pool. No
connection is attempted until a session executes a query, which keeps the
existing database-free catalog API usable during the migration.
"""
from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .config import Settings, settings


class Database:
    def __init__(self, config: Settings):
        self._engine: AsyncEngine | None = None
        self._sessions: async_sessionmaker[AsyncSession] | None = None
        if config.database_url:
            self._engine = create_async_engine(
                config.database_url,
                pool_size=config.db_pool_size,
                max_overflow=config.db_max_overflow,
                pool_timeout=config.db_pool_timeout,
                pool_recycle=config.db_pool_recycle,
                pool_pre_ping=True,
            )
            self._sessions = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )

    @property
    def configured(self) -> bool:
        return self._engine is not None

    @property
    def engine(self) -> AsyncEngine | None:
        return self._engine

    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessions is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Database service is not configured.',
            )
        async with self._sessions() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()


database = Database(settings)


async def get_database_session() -> AsyncIterator[AsyncSession]:
    async for session in database.session():
        yield session
