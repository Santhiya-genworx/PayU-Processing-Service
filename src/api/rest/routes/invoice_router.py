"""This module defines the API routes for handling invoice-related actions such as approving, reviewing, and rejecting invoices. The routes are organized under the "/invoice" prefix and utilize FastAPI's APIRouter for modularity. Each route accepts an InvoiceAction object as input, which contains the necessary information to perform the respective action on an invoice. The routes interact with the database using SQLAlchemy's AsyncSession to execute the corresponding service functions that handle the business logic for each action. The responses from these routes are structured as dictionaries containing relevant information about the outcome of the action performed on the invoice."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db
from src.core.services.invoice_service import (
    approveInvoice,
    rejectInvoice,
    reviewInvoice,
)
from src.schemas.invoice_schema import DecisionResponse, InvoiceAction

invoice_router = APIRouter(prefix="/invoice")


@invoice_router.put("/approve")
async def approve_invoice(
    data: InvoiceAction, db: AsyncSession = Depends(get_db)
) -> DecisionResponse:
    """API route to approve an invoice based on the provided InvoiceAction data. This endpoint accepts an InvoiceAction object as input, which contains the necessary information to identify and approve a specific invoice. The route uses the database session dependency to interact with the database and execute the approval logic defined in the approveInvoice service function. The response is a dictionary containing relevant information about the outcome of the approval action performed on the invoice, such as success status, messages, or any additional details related to the approved invoice. Args:   data (InvoiceAction): The input data containing information required to approve the invoice. db (AsyncSession): The database session dependency for querying and updating the database. Returns:    A dictionary containing relevant information about the outcome of the approval action performed on the invoice."""
    return await approveInvoice(data, db)


@invoice_router.put("/review")
async def review_invoice(
    data: InvoiceAction, db: AsyncSession = Depends(get_db)
) -> DecisionResponse:
    """API route to review an invoice based on the provided InvoiceAction data. This endpoint accepts an InvoiceAction object as input, which contains the necessary information to identify and review a specific invoice. The route uses the database session dependency to interact with the database and execute the review logic defined in the reviewInvoice service function. The response is a dictionary containing relevant information about the outcome of the review action performed on the invoice, such as success status, messages, or any additional details related to the reviewed invoice. Args:   data (InvoiceAction): The input data containing information required to review the invoice. db (AsyncSession): The database session dependency for querying and updating the database. Returns:    A dictionary containing relevant information about the outcome of the review action performed on the invoice."""
    return await reviewInvoice(data, db)


@invoice_router.put("/reject")
async def reject_invoice(
    data: InvoiceAction, db: AsyncSession = Depends(get_db)
) -> DecisionResponse:
    """API route to reject an invoice based on the provided InvoiceAction data. This endpoint accepts an InvoiceAction object as input, which contains the necessary information to identify and reject a specific invoice. The route uses the database session dependency to interact with the database and execute the rejection logic defined in the rejectInvoice service function. The response is a dictionary containing relevant information about the outcome of the rejection action performed on the invoice, such as success status, messages, or any additional details related to the rejected invoice. Args:   data (InvoiceAction): The input data containing information required to reject the invoice. db (AsyncSession): The database session dependency for querying and updating the database. Returns:    A dictionary containing relevant information about the outcome of the rejection action performed on the invoice."""
    return await rejectInvoice(data, db)
