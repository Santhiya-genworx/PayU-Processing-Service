"""Module: database.py"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config.settings import settings
from src.data.migrations.runner import apply_migrations

engine = create_async_engine(settings.db_url)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


engine = create_async_engine(
    settings.db_url,
    pool_pre_ping=True,
)


async def init_db() -> None:
    """Initialize the database by applying any pending migrations. This function is called during the startup event of the API application to ensure that the database schema is up to date before handling any requests. It uses an asynchronous context manager to create a connection to the database and applies migrations using the apply_migrations function from the migrations runner module. If any errors occur during the database initialization process, they will be raised and can be handled by the calling function."""
    async with engine.begin() as conn:
        await apply_migrations(conn)
