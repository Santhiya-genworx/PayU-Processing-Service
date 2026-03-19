from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship
from src.data.clients.database import Base

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    address = Column(String(255), nullable=False)
    country_code = Column(String(3), nullable=False)
    mobile_number = Column(String(20), nullable=False)
    gst_number = Column(String(15), nullable=False, unique=True)
    bank_name = Column(String(255), nullable=False)
    account_holder_name = Column(String(255), nullable=False)
    account_number = Column(String(50), nullable=False)
    ifsc_code = Column(String(20), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    invoices = relationship("Invoice", back_populates="vendor")
    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")