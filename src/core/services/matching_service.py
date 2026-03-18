import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.data.repositories.base_repository import commit_transaction, insert_data
from src.data.clients.database import AsyncSessionLocal
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest
from src.control.validation_agent.graph import invoke_graph
from src.data.models.purchase_order_model import PurchaseOrder
from src.data.models.invoice_model import Decision, Invoice
from src.data.repositories.base_repository import get_data_by_any, update_data_by_any
from sqlalchemy.orm import selectinload
from src.data.clients.redis import match_queue

async def validateInvoicePo(invoice_id: str, type: str):
    try:
        async with AsyncSessionLocal() as db:
            invoices = await get_data_by_any(Invoice, db, options=[selectinload(Invoice.vendor), selectinload(Invoice.invoice_items)], invoice_id=invoice_id)
            invoice = invoices[0] if invoices else None
            if not invoice:
                raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
            
            po = None        
            if invoice.po_id:
                pos = await get_data_by_any(PurchaseOrder, db, options=[selectinload(PurchaseOrder.vendor), selectinload(PurchaseOrder.ordered_items)], po_id=invoice.po_id)
                po = pos[0] if pos else None
                if not po:
                    raise HTTPException(status_code=404, detail=f"Purchase Order {invoice.po_id} not found")
                
            invoice_data = InvoiceRequest.model_validate(invoice)
            po_data = PurchaseOrderRequest.model_validate(po) if po else None
                
            result = await invoke_graph(invoice_data, po_data)

            if type=="new":
                await insert_data(Decision, db, **result)
            elif type=="override":
                await update_data_by_any(Decision, db, {"invoice_id": invoice_data.invoice_id}, **result)
            await commit_transaction(db)
            return result

    except Exception as err:
        raise

async def getInvoiceDecision(invoice_id: str, db: AsyncSession):
    try:
        decisions = await get_data_by_any(Decision, db, invoice_id=invoice_id)
        decision = decisions[0] if decisions else None
        return decision
    except Exception as err:
        raise

async def matchPo(po_id: str, db: AsyncSession):
    try:
        invoices = await get_data_by_any(Invoice, db, po_id=po_id, is_po_matched = False)
        invoice = invoices[0] if invoices else None
        if invoice:
            await update_data_by_any(Invoice, db, {"invoice_id": invoice.invoice_id}, is_po_matched=True)
            await commit_transaction(db)
            from src.tasks.payu_tasks import execute_task
            match_queue.enqueue(
                execute_task,
                {
                    "invoice_id": invoice.invoice_id,
                    "task_type": "validate_invoice",
                    "type": "new",
                    "job_id": str(uuid.uuid4())
                },
                job_timeout=600
            )
    except Exception as err:
        await db.rollback()
        raise