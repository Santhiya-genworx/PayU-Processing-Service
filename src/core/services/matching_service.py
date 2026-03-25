from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.schemas.matching_schema import InvoiceMatchingBase
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
    update_data_by_any,
)
from src.schemas.graph_output_schema import GraphResult
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest


async def validateInvoicePo(invoice_id: str, operation_type: str) -> GraphResult:
    try:
        async with AsyncSessionLocal() as db:
            invoices = await get_data_by_any(
                Invoice,
                db,
                options=[
                    selectinload(Invoice.vendor),
                    selectinload(Invoice.invoice_items),
                ],
                invoice_id=invoice_id,
            )
            invoice = invoices[0] if invoices else None
            if not invoice:
                raise NotFoundException(detail=f"Invoice {invoice_id} not found")

            matching_rows = await get_data_by_any(InvoiceMatching, db, invoice_id=invoice_id)

            po_ids: list[str] = list({row.po_id for row in matching_rows if row.po_id is not None})

            pos_data: list[PurchaseOrderRequest] = []
            for po_id in po_ids:
                po_records = await get_data_by_any(
                    PurchaseOrder,
                    db,
                    options=[
                        selectinload(PurchaseOrder.vendor),
                        selectinload(PurchaseOrder.ordered_items),
                    ],
                    po_id=po_id,
                )
                if not po_records:
                    raise NotFoundException(detail=f"Purchase Order {po_id} not found")

                pos_data.append(po_records[0])

            invoice_data = invoice
            invoice_data.po_id = po_ids

            # 🔥 FIX: cast result to GraphResult
            raw_result: Any = await invoke_graph([invoice_data], pos_data)
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

                await update_data_by_any(
                    InvoiceMatching,
                    db,
                    {"invoice_id": invoice_id},
                    **decision_fields,
                )

                await commit_transaction(db)

            return result

    except Exception:
        raise


async def getInvoiceDecision(invoice_id: str, db: AsyncSession) -> list[InvoiceMatchingBase]:
    try:
        matchings = await get_data_by_any(InvoiceMatching, db, invoice_id=invoice_id)
        return matchings
    except Exception:
        raise
