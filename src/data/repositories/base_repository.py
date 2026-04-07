"""Module: base_repository.py"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, delete, insert, select, update
from sqlalchemy import text as sa_text
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.exceptions import (
    AppException,
    ConflictException,
    NotFoundException,
)


async def commit_transaction(db: AsyncSession) -> None:
    """Commit the current transaction in the database session. This function attempts to commit the transaction and handles any exceptions that may occur during the commit process. If the commit is successful, it simply returns. If an exception occurs, it rolls back the transaction to maintain database integrity and raises an AppException with details about the error. This function is intended to be used after performing a series of database operations to ensure that all changes are saved atomically, and to provide error handling in case something goes wrong during the commit."""
    try:
        await db.commit()
    except Exception as err:
        await db.rollback()
        raise AppException(detail=f"Commit failed {str(err)}") from err


async def insert_data(model: type[Any], db: AsyncSession, **kwargs: Any) -> None:
    """Insert a new record into the database for the specified model. This function takes a SQLAlchemy model class, a database session, and keyword arguments representing the fields and values to be inserted. It constructs an insert statement using the provided model and values, and executes it against the database. If the insertion is successful, it simply returns. If an IntegrityError occurs (e.g., due to a unique constraint violation), it raises a ConflictException with details about the error. For any other SQLAlchemy-related errors, it raises a generic AppException with the error details. This function abstracts away the common pattern of inserting data into the database while providing consistent error handling for different types of exceptions that may arise during the insertion process."""
    try:
        stmt = insert(model).values(**kwargs)
        await db.execute(stmt)
    except IntegrityError as err:
        raise ConflictException(detail=str(err)) from err
    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def update_data_by_id(model: type[Any], id: int, db: AsyncSession, **kwargs: Any) -> None:
    """Update an existing record in the database for the specified model based on its ID. This function takes a SQLAlchemy model class, the ID of the record to be updated, a database session, and keyword arguments representing the fields and values to be updated. It constructs an update statement that targets the record with the specified ID and applies the provided updates. If the update is successful and at least one record is affected, it simply returns. If no records are affected (i.e., no record with the given ID exists), it raises a NotFoundException with a message indicating that the data was not found. For any other SQLAlchemy-related errors, it raises a generic AppException with the error details. This function abstracts away the common pattern of updating data in the database by ID while providing consistent error handling for cases where the target record does not exist or when other database errors occur during the update process."""
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
    """Update existing records in the database for the specified model based on arbitrary conditions. This function takes a SQLAlchemy model class, a database session, a dictionary of conditions to identify the records to be updated, and keyword arguments representing the fields and values to be updated. It constructs an update statement that targets records matching the provided conditions and applies the updates. If the update is successful and at least one record is affected, it simply returns. If no records are affected (i.e., no records match the given conditions), it raises a NotFoundException with a message indicating that the data was not found. For any other SQLAlchemy-related errors, it raises a generic AppException with the error details. This function abstracts away the common pattern of updating data in the database based on arbitrary conditions while providing consistent error handling for cases where no matching records exist or when other database errors occur during the update process."""
    try:
        conditions = [getattr(model, key) == value for key, value in data.items()]

        stmt = update(model).where(and_(*conditions)).values(**kwargs)
        result = await db.execute(stmt)
        if getattr(result, "rowcount", 0) == 0:
            raise NotFoundException(detail="Data not found")

    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def get_data_by_id(model: type[Any], id: int, db: AsyncSession) -> Any | None:
    """Retrieve a single record from the database for the specified model based on its ID. This function takes a SQLAlchemy model class, the ID of the record to be retrieved, and a database session. It constructs a select statement that targets the record with the specified ID and executes it against the database. If a record with the given ID exists, it returns that record; otherwise, it returns None. If any SQLAlchemy-related errors occur during the retrieval process, it raises an AppException with the error details. This function abstracts away the common pattern of retrieving data from the database by ID while providing consistent error handling for any issues that may arise during the query execution."""
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
    """Retrieve records from the database for the specified model based on arbitrary conditions. This function takes a SQLAlchemy model class, a database session, optional parameters for pagination (limit and offset), ordering (order_by), and query options (options), as well as keyword arguments representing the conditions to filter the records. It constructs a select statement that targets records matching the provided conditions, applies any specified ordering and pagination, and executes it against the database. It returns a list of records that match the given conditions. If any SQLAlchemy-related errors occur during the retrieval process, it raises an AppException with the error details. This function abstracts away the common pattern of retrieving data from the database based on arbitrary conditions while providing consistent error handling for any issues that may arise during query execution."""
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
    """Delete a record from the database for the specified model based on its ID. This function takes a SQLAlchemy model class, the ID of the record to be deleted, and a database session. It constructs a delete statement that targets the record with the specified ID and executes it against the database. If a record with the given ID exists and is successfully deleted, it simply returns. If no record with the given ID exists (i.e., no records are affected), it raises a NotFoundException with a message indicating that the data was not found. For any other SQLAlchemy-related errors that occur during the deletion process, it raises a generic AppException with the error details. This function abstracts away the common pattern of deleting data from the database by ID while providing consistent error handling for cases where the target record does not exist or when other database errors occur during the deletion process."""
    try:
        stmt = delete(model).where(model.id == id)
        result = await db.execute(stmt)
        if getattr(result, "rowcount", 0) == 0:
            raise NotFoundException(detail="Data not found")

    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def delete_data_by_any(model: type[Any], db: AsyncSession, **kwargs: Any) -> None:
    """Delete records from the database for the specified model based on arbitrary conditions. This function takes a SQLAlchemy model class, a database session, and keyword arguments representing the conditions to identify the records to be deleted. It constructs a delete statement that targets records matching the provided conditions and executes it against the database. If at least one record matching the conditions exists and is successfully deleted, it simply returns. If no records match the given conditions (i.e., no records are affected), it raises a NotFoundException with a message indicating that the data was not found. For any other SQLAlchemy-related errors that occur during the deletion process, it raises a generic AppException with the error details. This function abstracts away the common pattern of deleting data from the database based on arbitrary conditions while providing consistent error handling for cases where no matching records exist or when other database errors occur during the deletion process."""
    try:
        conditions = [getattr(model, key) == value for key, value in kwargs.items()]

        stmt = delete(model).where(and_(*conditions))
        result = await db.execute(stmt)
        if getattr(result, "rowcount", 0) == 0:
            raise NotFoundException(detail="Data not found")

    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def get_matching_group_containing_invoice(db: AsyncSession, invoice_id: str) -> "Any | None":
    """Return the first InvoiceMatching group whose `invoices` array contains invoice_id."""
    from src.data.models.matching_model import InvoiceMatching

    try:
        stmt = select(InvoiceMatching).where(InvoiceMatching.invoices.contains([invoice_id]))
        result = await db.execute(stmt)
        return result.scalars().first()
    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def get_matching_group_containing_po(db: AsyncSession, po_id: str) -> "Any | None":
    """Return the first InvoiceMatching group whose `pos` array contains po_id."""
    from src.data.models.matching_model import InvoiceMatching

    try:
        stmt = select(InvoiceMatching).where(InvoiceMatching.pos.contains([po_id]))
        result = await db.execute(stmt)
        return result.scalars().first()
    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def get_all_matching_groups_containing_po(db: AsyncSession, po_id: str) -> "list[Any]":
    """Return all InvoiceMatching groups whose `pos` array contains po_id."""
    from src.data.models.matching_model import InvoiceMatching

    try:
        stmt = select(InvoiceMatching).where(InvoiceMatching.pos.contains([po_id]))
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def append_invoice_to_group(db: AsyncSession, group_id: int, invoice_id: str) -> None:
    """Append invoice_id to the group's invoices array (idempotent guard in caller)."""
    from src.data.models.matching_model import InvoiceMatching

    try:
        stmt = (
            update(InvoiceMatching)
            .where(InvoiceMatching.id == group_id)
            .values(invoices=sa_text(f"array_append(invoices, '{invoice_id}')"))
        )
        await db.execute(stmt)
    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err


async def append_po_to_group(db: AsyncSession, group_id: int, po_id: str) -> None:
    """Append po_id to the group's pos array (idempotent guard in caller)."""
    from src.data.models.matching_model import InvoiceMatching

    try:
        stmt = (
            update(InvoiceMatching)
            .where(InvoiceMatching.id == group_id)
            .values(pos=sa_text(f"array_append(pos, '{po_id}')"))
        )
        await db.execute(stmt)
    except SQLAlchemyError as err:
        raise AppException(detail=str(err)) from err
