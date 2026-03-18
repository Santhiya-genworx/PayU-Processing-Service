import uuid
from fastapi import Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.services.email_service import send_email
from src.api.rest.dependencies import get_db
from src.data.models.invoice_model import Decision, Invoice, InvoiceItem
from src.data.models.purchase_order_model import PurchaseOrder
from src.data.models.upload_history_model import InvoiceUploadHistory
from src.data.models.vendor_model import Vendor
from src.data.repositories.base_repository import commit_transaction, delete_data_by_any, get_data_by_any, insert_data, update_data_by_any
from src.schemas.invoice_schema import InvoiceAction, InvoiceRequest
from src.data.clients.redis import match_queue

async def uploadInvoice(invoice: InvoiceRequest, file_url: str, db: AsyncSession = Depends(get_db)):
    try:
        vendors = await get_data_by_any(Vendor, db, email=invoice.vendor.email)
        vendor = vendors[0] if vendors else None
        if not vendor:
            vendor_data = {
                "name": invoice.vendor.name,
                "email": invoice.vendor.email,
                "address": invoice.vendor.address,
                "country_code": invoice.vendor.country_code,
                "mobile_number": invoice.vendor.mobile_number,
                "gst_number": invoice.vendor.gst_number,
                "bank_name": invoice.vendor.bank_name,
                "account_holder_name": invoice.vendor.account_holder_name,
                "account_number": invoice.vendor.account_number,
                "ifsc_code": invoice.vendor.ifsc_code
            }
            await insert_data(Vendor, db, **vendor_data)
            await commit_transaction(db)
            vendors = await get_data_by_any(Vendor, db, email=invoice.vendor.email)
            vendor =  vendors[0] if vendors else None

        po = None
        if invoice.po_id:
            pos = await get_data_by_any(PurchaseOrder, db, po_id=invoice.po_id)
            po = pos[0] if pos else None

            if po:
                if po.vendor_id != vendor.id:
                    raise HTTPException(status_code=400, detail="PO does not belong to given vendor")

        try:
            invoices = await get_data_by_any(Invoice, db, invoice_id=invoice.invoice_id)
            existing_invoice = invoices[0] if invoices else None

            if existing_invoice:
                raise HTTPException(status_code=409, detail=f"Invoice {invoice.invoice_id} already exists")
        except HTTPException as e:
            if e.status_code!=404:
                raise e

        data = {
            "invoice_id": invoice.invoice_id,
            "vendor_id": vendor.id,
            "po_id": invoice.po_id,
            "is_po_matched": po is not None,
            "invoice_date": invoice.invoice_date,
            "due_date": invoice.due_date,
            "currency_code": invoice.currency_code,
            "subtotal": invoice.subtotal,
            "tax_amount": invoice.tax_amount,
            "discount_amount": invoice.discount_amount,
            "total_amount": invoice.total_amount,
            "status": "pending",
            "file_url": file_url
        }
        await insert_data(Invoice, db, **data)
        await commit_transaction(db)

        inserted_invoices = await get_data_by_any(Invoice, db, invoice_id=invoice.invoice_id)
        inserted_invoice = inserted_invoices[0] if inserted_invoices else None
        for item in invoice.invoice_items:
            data = {
                "invoice_id": inserted_invoice.invoice_id,
                "item_description": item.item_description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price
            }
            await insert_data(InvoiceItem, db, **data)

        await commit_transaction(db)
        if not po or (po and inserted_invoice.is_po_matched):
            from src.tasks.payu_tasks import execute_task
            match_queue.enqueue(
                execute_task,
                {
                    "invoice_id": invoice.invoice_id,
                    "task_type": "validate_invoice",
                    "type": "new",
                    "job_id": str(uuid.uuid4())
                }
            )
        return {"message": f"Invoice {inserted_invoice.invoice_id} uploaded successfully"}
    
    except SQLAlchemyError as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(err)}")
    
    except Exception as err:
        await db.rollback()
        raise 
    
async def overrideInvoice(invoice: InvoiceRequest, file_url: str, db: AsyncSession = Depends(get_db)):
    try:
        vendors = await get_data_by_any(Vendor, db, email=invoice.vendor.email)
        vendor = vendors[0] if vendors else None
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")

        po = None
        if invoice.po_id:
            pos = await get_data_by_any(PurchaseOrder, db, po_id=invoice.po_id)
            po = pos[0] if pos else None

            if po and po.vendor_id != vendor.id:
                raise HTTPException(status_code=400, detail="PO does not belong to given vendor")

        invoices = await get_data_by_any(Invoice, db, invoice_id=invoice.invoice_id)
        existing_invoice = invoices[0] if invoices else None
        if not existing_invoice:
            raise HTTPException(status_code=404, detail="Invoice does not exist to override")

        old_file_url = existing_invoice.file_url

        updated_data = {
            "vendor_id": vendor.id,
            "po_id": invoice.po_id if invoice.po_id else None,
            "invoice_date": invoice.invoice_date,
            "due_date": invoice.due_date,
            "currency_code": invoice.currency_code,
            "subtotal": invoice.subtotal,
            "tax_amount": invoice.tax_amount,
            "discount_amount": invoice.discount_amount or 0,
            "total_amount": invoice.total_amount,
            "status": "pending",
            "file_url": file_url
        }
        await update_data_by_any(Invoice, db, {"invoice_id": invoice.invoice_id}, **updated_data)
        await delete_data_by_any(InvoiceItem, db, invoice_id=existing_invoice.invoice_id)

        for item in invoice.invoice_items:
            item_data = {
                "invoice_id": existing_invoice.invoice_id,
                "item_description": item.item_description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price
            }
            await insert_data(InvoiceItem, db, **item_data)

        history_data = {
            "invoice_id": existing_invoice.invoice_id,
            "old_file_url": old_file_url,
            "new_file_url": file_url
        }
        await insert_data(InvoiceUploadHistory, db, **history_data)
        await commit_transaction(db)
        if not po or (po and existing_invoice.is_po_matched):
            from src.tasks.payu_tasks import execute_task
            match_queue.enqueue(
                execute_task,
                {
                    "invoice_id": invoice.invoice_id,
                    "task_type": "validate_invoice",
                    "type": "override",
                    "job_id": str(uuid.uuid4())
                }
            )

        return { "message": f"Invoice {invoice.invoice_id} overridden successfully" }

    except SQLAlchemyError as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(err)}")

    except Exception as err:
        await db.rollback()
        raise

async def approveInvoice(data: InvoiceAction, db: AsyncSession):
    try:
        invoice_id = data.invoice_id
        await update_data_by_any(Invoice, db, {"invoice_id": invoice_id}, status="approved")
        await commit_transaction(db)
        return {"status": "approved", "invoice_id": invoice_id}
    
    except Exception as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Invoice {invoice_id} approval failed: {str(err)}")

async def reviewInvoice(data: InvoiceAction, db: AsyncSession):
    try:
        invoice_id = data.invoice_id
        await update_data_by_any(Invoice, db, {"invoice_id": invoice_id}, status="reviewed")
        updated_mail = {}
        if data.mail_to:
            updated_mail["mail_to"] = data.mail_to
        if data.mail_subject:
            updated_mail["mail_subject"] = data.mail_subject
        if data.mail_body:
            updated_mail["mail_body"] = data.mail_body
        if updated_mail:
            await update_data_by_any(Decision, db, {"invoice_id": invoice_id}, **updated_mail)
        await commit_transaction(db)
        decisions = await get_data_by_any(Decision, db, invoice_id=invoice_id)
        decision = decisions[0] if decisions else None

        if decision and decision.mail_to:
            await send_email(decision.mail_to, decision.mail_subject, decision.mail_body)

        return {"status": "reviewed", "invoice_id": invoice_id}
    
    except Exception as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Invoice {invoice_id} review failed: {str(err)}")

async def rejectInvoice(data: InvoiceAction, db: AsyncSession):
    try:
        invoice_id = data.invoice_id
        await update_data_by_any(Invoice, db, {"invoice_id": invoice_id}, status="rejected")
        updated_mail = {}
        if data.mail_to:
            updated_mail["mail_to"] = data.mail_to
        if data.mail_subject:
            updated_mail["mail_subject"] = data.mail_subject
        if data.mail_body:
            updated_mail["mail_body"] = data.mail_body
        if updated_mail:
            await update_data_by_any(Decision, db, {"invoice_id": invoice_id}, **updated_mail)
        await commit_transaction(db)

        decisions = await get_data_by_any(Decision, db, invoice_id=invoice_id)
        decision = decisions[0] if decisions else None

        if decision and decision.mail_to:
            await send_email(decision.mail_to, decision.mail_subject, decision.mail_body)

        return {"status": "rejected", "invoice_id": invoice_id}
    
    except Exception as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Invoice {invoice_id} rejection failed: {str(err)}")