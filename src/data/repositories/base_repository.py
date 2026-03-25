from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, delete, insert, select, update
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.exceptions import (
    AppException,
    ConflictException,
    NotFoundException,
)


async def commit_transaction(db: AsyncSession) -> None:
    try:
        await db.commit()
    except Exception as err:
        await db.rollback()
        raise AppException(detail=f"Commit failed {str(err)}") from err


async def insert_data(model: type[Any], db: AsyncSession, **kwargs: Any) -> None:
    try:
        stmt = insert(model).values(**kwargs)
        await db.execute(stmt)
    except IntegrityError as err:
        raise ConflictException(detail=str(err)) from err
    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def update_data_by_id(model: type[Any], id: int, db: AsyncSession, **kwargs: Any) -> None:
    try:
        stmt = update(model).where(model.id == id).values(**kwargs)
        result = await db.execute(stmt)
        if getattr(result, "rowcount", 0) == 0:
            raise NotFoundException(detail="Data not found")

    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def update_data_by_any(
    model: type[Any],
    db: AsyncSession,
    data: dict[str, Any],
    **kwargs: Any,
) -> None:
    try:
        conditions = [getattr(model, key) == value for key, value in data.items()]

        stmt = update(model).where(and_(*conditions)).values(**kwargs)
        result = await db.execute(stmt)
        if getattr(result, "rowcount", 0) == 0:
            raise NotFoundException(detail="Data not found")

    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def get_data_by_id(model: type[Any], id: int, db: AsyncSession) -> Any | None:
    try:
        stmt = select(model).where(model.id == id)
        result: Result[Any] = await db.execute(stmt)
        return result.scalar_one_or_none()
    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def get_data_by_any(
    model: type[Any],
    db: AsyncSession,
    limit: int | None = None,
    offset: int | None = None,
    order_by: Any | None = None,
    options: Sequence[Any] | None = None,
    **kwargs: Any,
) -> list[Any]:
    try:
        conditions = [getattr(model, key) == value for key, value in kwargs.items()]

        stmt = select(model)

        if options:
            for opt in options:
                stmt = stmt.options(opt)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        if order_by is not None:
            stmt = stmt.order_by(order_by)

        if limit is not None:
            stmt = stmt.limit(limit)

        if offset is not None:
            stmt = stmt.offset(offset)

        result: Result[Any] = await db.execute(stmt)
        return list(result.scalars().all())

    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def delete_data_by_id(model: type[Any], id: int, db: AsyncSession) -> None:
    try:
        stmt = delete(model).where(model.id == id)
        result = await db.execute(stmt)
        if getattr(result, "rowcount", 0) == 0:
            raise NotFoundException(detail="Data not found")

    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def delete_data_by_any(model: type[Any], db: AsyncSession, **kwargs: Any) -> None:
    try:
        conditions = [getattr(model, key) == value for key, value in kwargs.items()]

        stmt = delete(model).where(and_(*conditions))
        result = await db.execute(stmt)
        if getattr(result, "rowcount", 0) == 0:
            raise NotFoundException(detail="Data not found")

    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err
