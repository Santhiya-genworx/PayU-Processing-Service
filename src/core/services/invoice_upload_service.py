from fastapi import Depends, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.rest.dependencies import get_db
from src.data.models.invoice_model import Invoice, InvoiceItem
from src.data.models.purchase_order_model import PurchaseOrder
from src.data.models.upload_history_model import InvoiceUploadHistory
from src.data.models.vendor_model import Vendor
from src.data.repositories.base_repository import commit_transaction, delete_data_by_any, get_data_by_any, insert_data, update_data_by_any
from src.schemas.invoice_schema import InvoiceRequest
from src.utils.file_upload import upload

async def uploadInvoice(invoice: InvoiceRequest, file_url: str, db: AsyncSession = Depends(get_db)):
    try:
        # Check Vendor Exists
        vendor = await get_data_by_any(Vendor, db, email=invoice.vendor.email)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        else:
            vendor = vendor[0]

        # Check PO Exists & Belongs to Vendor
        po = await get_data_by_any(PurchaseOrder, db, po_id=invoice.po_id)
        if not po:
            raise HTTPException(status_code=404, detail="Purchase Order not found")
        else:
            po = po[0]

        if po.vendor_id != vendor.id:
            raise HTTPException(status_code=400, detail="PO does not belong to given vendor")

        # Check Duplicate Invoice Number
        try:
            existing_invoice = await get_data_by_any(Invoice, db, invoice_id=invoice.invoice_id)

            if existing_invoice:
                raise HTTPException(status_code=409, detail=f"Invoice {invoice.invoice_id} already exists")
        except HTTPException as e:
            if e.status_code!=404:
                raise e

        # Insert Invoice
        data = {
            "invoice_id": invoice.invoice_id,
            "vendor_id": vendor.id,
            "po_id": invoice.po_id,
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

        inserted_invoice = await get_data_by_any(Invoice, db, invoice_id=invoice.invoice_id)
        inserted_invoice = inserted_invoice[0]
        # Insert Invoice Items
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
        return {"message": f"Invoice {inserted_invoice.invoice_id} uploaded successfully"}
    
    except SQLAlchemyError as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(err)}")
    
    except Exception as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}")
    
async def overrideInvoice(invoice: InvoiceRequest, file_url: str, db: AsyncSession = Depends(get_db)):
    try:
        # Check Vendor Exists
        vendor = await get_data_by_any(Vendor, db, email=invoice.vendor.email)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")

        # Check PO Exists & Belongs to Vendor
        po = await get_data_by_any(PurchaseOrder, db, po_id=invoice.po_id)
        if not po:
            raise HTTPException(status_code=404, detail="Purchase Order not found")

        if po.vendor_id != vendor.id:
            raise HTTPException(status_code=400, detail="PO does not belong to given vendor")

        # Check Duplicate Invoice Number
        existing_invoice = await get_data_by_any(Invoice, db, invoice_id=invoice.invoice_id)

        if not existing_invoice:
            raise HTTPException(status_code=404, detail="Invoice does not exist to override")

        old_file_url = existing_invoice.file_url

        # Update Invoice Fields
        updated_data = {
            "vendor_id": vendor.id,
            "po_id": invoice.po_id,
            "invoice_date": invoice.invoice_date,
            "due_date": invoice.due_date,
            "subtotal": invoice.subtotal,
            "tax_amount": invoice.tax_amount,
            "discount_amount": invoice.discount_amount,
            "total_amount": invoice.total_amount,
            "status": invoice.status.value,
            "file_url": file_url
        }
        await update_data_by_any(Invoice, db, {"invoice_id": invoice.invoice_id}, **updated_data)

        # Delete Old Invoice Items
        await delete_data_by_any(InvoiceItem, db, invoice_id = existing_invoice.id)

        # Insert New Invoice Items
        for item in invoice.invoice_items:
            data = {
                "invoice_id": existing_invoice.id,
                "item_description": item.item_description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price
            }
            await insert_data(InvoiceItem, db, **data)

        # Insert Upload History
        data = {
            "invoice_id": existing_invoice.id,
            "old_file_url": old_file_url,
            "new_file_url": invoice.file_url
        }
        await insert_data(InvoiceUploadHistory, db, **data)
        await commit_transaction(db)

        return {"message": f"Invoice {invoice.invoice_number} overridden successfully"}

    except SQLAlchemyError as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(err)}")

    except Exception as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}")