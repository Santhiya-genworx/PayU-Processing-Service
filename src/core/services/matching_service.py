"""Module: matching_service.py"""

from typing import Any, cast

from PayU_Processing_Service.src.schemas.purchase_order_schema import PurchaseOrderRequest
from sqlalchemy.orm import selectinload

from src.control.validation_agent.validation_graph import invoke_graph
from src.core.exceptions.exceptions import NotFoundException
from src.data.clients.database import AsyncSessionLocal
from src.data.models.invoice_model import Invoice
from src.data.models.matching_model import (
    DecisionStatus,
    InvoiceMatching,
)
from src.data.models.purchase_order_model import PurchaseOrder
from src.data.repositories.base_repository import (
    commit_transaction,
    get_data_by_any,
    get_data_by_id,
    update_data_by_id,
)
from src.schemas.graph_output_schema import GraphResult
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.matching_schema import InvoiceMatchingBase


async def validateInvoicePo(group_id: int, operation_type: str) -> GraphResult:
    """Function to validate the matching of an invoice and purchase order group using a graph-based approach. This function retrieves the matching group based on the provided group ID, loads all associated invoices and purchase orders, and then invokes a validation graph to determine the matching status. The result from the graph includes a decision status, confidence score, and email details for notifications. The function updates the matching group in the database with the decision results and returns the graph result. If any errors occur during this process, appropriate exceptions are raised with details about the failure."""
    try:
        async with AsyncSessionLocal() as db:
            group: InvoiceMatching | None = await get_data_by_id(InvoiceMatching, group_id, db)
            if not group:
                raise NotFoundException(detail=f"Matching group {group_id} not found")

            invoice_ids: list[str] = group.invoices or []
            po_ids: list[str] = group.pos or []

            invoices_data: list[InvoiceRequest] = []
            for invoice_id in invoice_ids:
                records = await get_data_by_any(
                    Invoice,
                    db,
                    options=[
                        selectinload(Invoice.vendor),
                        selectinload(Invoice.invoice_items),
                    ],
                    invoice_id=invoice_id,
                )
                if not records:
                    raise NotFoundException(detail=f"Invoice {invoice_id} not found")
                inv = records[0]

                invoice_schema = InvoiceRequest.model_validate(
                    {
                        "invoice_id": inv.invoice_id,
                        "vendor": inv.vendor,
                        "po_id": po_ids,
                        "invoice_date": inv.invoice_date,
                        "due_date": inv.due_date,
                        "invoice_items": inv.invoice_items,
                        "currency_code": inv.currency_code,
                        "subtotal": float(inv.subtotal),
                        "tax_amount": float(inv.tax_amount),
                        "discount_amount": float(inv.discount_amount or 0),
                        "total_amount": float(inv.total_amount),
                    }
                )

                invoices_data.append(invoice_schema)

            pos_data: list[PurchaseOrderRequest] = []
            for po_id in po_ids:
                records = await get_data_by_any(
                    PurchaseOrder,
                    db,
                    options=[
                        selectinload(PurchaseOrder.vendor),
                        selectinload(PurchaseOrder.ordered_items),
                    ],
                    po_id=po_id,
                )
                if not records:
                    raise NotFoundException(detail=f"Purchase Order {po_id} not found")
                po = records[0]

                po_schema = PurchaseOrderRequest.model_validate(
                    {
                        "po_id": po.po_id,
                        "vendor": po.vendor,
                        "gl_code": po.gl_code,
                        "currency_code": po.currency_code,
                        "total_amount": float(po.total_amount),
                        "ordered_date": po.ordered_date,
                        "ordered_items": po.ordered_items,
                    }
                )

                pos_data.append(po_schema)

            raw_result: Any = await invoke_graph(invoices_data, pos_data)
            result: GraphResult = cast(GraphResult, raw_result)

            output: dict[str, Any] | None = dict(result).get("output")

            if output:
                decision_fields: dict[str, Any] = {
                    "decision": DecisionStatus[output["status"]],
                    "confidence_score": output["confidence_score"],
                    "command": output["command"],
                    "mail_to": output["mail_to"],
                    "mail_subject": output["mail_subject"],
                    "mail_body": output["mail_body"],
                }
                await update_data_by_id(InvoiceMatching, group_id, db, **decision_fields)
                await commit_transaction(db)

            return result

    except Exception:
        raise


async def getInvoiceDecision(invoice_id: str, db: Any) -> list[InvoiceMatchingBase]:
    """Function to retrieve the matching decision for a specific invoice. This function queries the database to find the matching group that contains the given invoice ID and returns a list of InvoiceMatchingBase objects representing the matching decision for that invoice. If no matching group is found, it returns an empty list. If any errors occur during the database operations, appropriate exceptions are raised with details about the failure."""
    from src.data.repositories.base_repository import get_matching_group_containing_invoice

    group = await get_matching_group_containing_invoice(db, invoice_id)
    return [group] if group else []
