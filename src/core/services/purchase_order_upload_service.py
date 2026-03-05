from fastapi import Depends, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.rest.dependencies import get_db
from src.data.models.purchase_order_model import OrderedItems, PurchaseOrder
from src.data.models.upload_history_model import PurchaseOrderUploadHistory
from src.data.models.vendor_model import Vendor
from src.data.repositories.base_repository import commit_transaction, delete_data_by_any, get_data_by_any, insert_data, update_data_by_any
from src.schemas.purchase_order_schema import PurchaseOrderRequest
from src.utils.file_upload import upload

async def uploadPurchaseOrder(po: PurchaseOrderRequest, file_url: str, db: AsyncSession = Depends(get_db)):
    try:
        # Check Vendor Exists
        vendors = await get_data_by_any(Vendor, db, email=po.vendor.email)
        vendor = None
        if vendors:
            vendor = vendors[0]
        if not vendor:
            vendor_data = {
                "name": po.vendor.name,
                "email": po.vendor.email,
                "address": po.vendor.address,
                "country_code": po.vendor.country_code,
                "mobile_number": po.vendor.mobile_number,
                "gst_number": po.vendor.gst_number,
                "bank_name": po.vendor.bank_name,
                "account_holder_name": po.vendor.account_holder_name,
                "account_number": po.vendor.account_number,
                "ifsc_code": po.vendor.ifsc_code
            }
            await insert_data(Vendor, db, **vendor_data)
            await commit_transaction(db)
            vendors = await get_data_by_any(Vendor, db, email=po.vendor.email)
            if vendors:
                vendor = vendors[0]

        # Check PO Exists
        try:
            existing_po = await get_data_by_any(PurchaseOrder, db, po_id=po.po_id)
            if existing_po:
                raise HTTPException(status_code=409, detail=f"Purchase Order {po.po_id} already exists")
        except HTTPException as e:
            if e.status_code != 404:
                raise e

        # Insert Purchase Order
        po_data = {
            "po_id": po.po_id,
            "vendor_id": vendor.id,
            "gl_code": po.gl_code,
            "currency_code": po.currency_code,
            "total_amount": po.total_amount,
            "ordered_date": po.ordered_date,
            "status": "pending",
            "file_url": file_url
        }
        await insert_data(PurchaseOrder, db, **po_data)

        # Insert Ordered Items
        for item in po.ordered_items:
            item_data = {
                "po_id": po.po_id,
                "item_description": item.item_description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price
            }
            await insert_data(OrderedItems, db, **item_data)

        await commit_transaction(db)

        return {"message": f"Purchase Order {po.po_id} uploaded successfully"}

    except SQLAlchemyError as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(err)}")

    except Exception as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}")
    
async def overridePurchaseOrder(po: PurchaseOrderRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Check Vendor Exists
        vendor = await get_data_by_any(Vendor, db, email=po.vendor.email)[0]
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")

        # Check PO Exists
        existing_po = await get_data_by_any(PurchaseOrder, db, po_id=po.po_id)[0]
        if not existing_po:
            raise HTTPException(status_code=404, detail="Purchase Order not found")

        # Validate PO belongs to Vendor
        if existing_po.vendor_id != vendor.id:
            raise HTTPException(status_code=400, detail="PO does not belong to given vendor")

        old_file_url = existing_po.file_url

        # Update PO Fields
        updated_data = {
            "vendor_id": vendor.id,
            "gl_code": po.gl_code,
            "total_amount": po.total_amount,
            "ordered_date": po.ordered_date,
            "file_url": po.file_url
        }

        await update_data_by_any(PurchaseOrder, db, {"po_id": po.po_id}, **updated_data)

        # Delete Old Ordered Items
        await delete_data_by_any(OrderedItems, db, po_id=po.po_id)

        # Insert New Ordered Items
        for item in po.ordered_items:
            item_data = {
                "po_id": po.po_id,
                "item_description": item.item_description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price
            }
            await insert_data(OrderedItems, db, **item_data)

        # Insert Upload History
        history_data = {
            "po_id": po.po_id,
            "old_file_url": old_file_url,
            "new_file_url": po.file_url
        }
        await insert_data(PurchaseOrderUploadHistory, db, **history_data)

        await commit_transaction(db)
        return {"message": f"Purchase Order {po.po_id} overridden successfully"}

    except SQLAlchemyError as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(err)}")

    except Exception as err:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}") 