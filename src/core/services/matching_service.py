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


async def validateInvoicePo(invoice_id: str, operation_type: str) -> GraphResult:
    """
    Validates a group of invoices against their shared PO(s).

    Handles two relationship shapes:
      - 1 PO : N Invoices  → all invoices sharing the same PO are validated together
      - N POs : 1 Invoice  → the single invoice is validated against all its linked POs

    In both cases invoke_graph receives the full set of invoices + POs so the AI
    can reason about the combined picture. One decision is returned and written
    to every InvoiceMatching row in the group.
    """
    try:
        async with AsyncSessionLocal() as db:

            # ── Step 1: load the triggering invoice ──────────────────────────
            invoice_records = await get_data_by_any(
                Invoice,
                db,
                options=[
                    selectinload(Invoice.vendor),
                    selectinload(Invoice.invoice_items),
                ],
                invoice_id=invoice_id,
            )
            trigger_invoice = invoice_records[0] if invoice_records else None
            if not trigger_invoice:
                raise NotFoundException(detail=f"Invoice {invoice_id} not found")

            # ── Step 2: find all POs linked to the triggering invoice ─────────
            trigger_matching_rows = await get_data_by_any(
                InvoiceMatching, db, invoice_id=invoice_id
            )
            all_po_ids: set[str] = {
                row.po_id for row in trigger_matching_rows if row.po_id is not None
            }

            # ── Step 3: expand — find ALL invoices that share any of those POs ─
            #
            # Example: PO-X is linked to Invoice-1 and Invoice-2.
            # When Invoice-2 arrives and triggers validation, we reverse-lookup
            # PO-X to discover Invoice-1 and include it in the validation group.
            # This ensures invoke_graph always sees the full picture.
            all_invoice_ids: set[str] = {invoice_id}

            for po_id in all_po_ids:
                sibling_rows = await get_data_by_any(
                    InvoiceMatching, db, po_id=po_id
                )
                for row in sibling_rows:
                    if row.invoice_id:
                        all_invoice_ids.add(row.invoice_id)

            # ── Step 4: load all invoice ORM objects ──────────────────────────
            invoices_data: list[Invoice] = []

            for inv_id in all_invoice_ids:
                if inv_id == invoice_id:
                    trigger_invoice.po_id = list(all_po_ids)
                    invoices_data.append(trigger_invoice)
                    continue

                sibling_records = await get_data_by_any(
                    Invoice,
                    db,
                    options=[
                        selectinload(Invoice.vendor),
                        selectinload(Invoice.invoice_items),
                    ],
                    invoice_id=inv_id,
                )
                if sibling_records:
                    sibling_invoice = sibling_records[0]
                    sibling_matching_rows = await get_data_by_any(
                        InvoiceMatching, db, invoice_id=inv_id
                    )
                    sibling_invoice.po_id = [
                        row.po_id
                        for row in sibling_matching_rows
                        if row.po_id is not None
                    ]
                    invoices_data.append(sibling_invoice)

            # ── Step 5: load all PO ORM objects ───────────────────────────────
            pos_data: list[PurchaseOrder] = []

            for po_id in all_po_ids:
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

            # ── Step 6: invoke the validation graph ───────────────────────────
            #
            # invoke_graph now receives the full group:
            #   1 PO  : 2 invoices → invoices_data=[inv1, inv2], pos_data=[po]
            #   2 POs : 1 invoice  → invoices_data=[inv],        pos_data=[po1, po2]
            #
            # The graph evaluates the group as a whole and returns ONE decision.
            raw_result: Any = await invoke_graph(invoices_data, pos_data)
            result: GraphResult = cast(GraphResult, raw_result)

            # ── Step 7: write the same decision to every row in the group ─────
            #
            # Since the decision is about the PO-Invoice group as a whole
            # (do all these invoices together satisfy this PO?), the same
            # outcome — approve / review / reject — is applied to every
            # InvoiceMatching row that belongs to this group.
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

                for inv_id in all_invoice_ids:
                    await update_data_by_any(
                        InvoiceMatching,
                        db,
                        {"invoice_id": inv_id},
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
