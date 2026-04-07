from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentCountsResponse(BaseModel):
    """Pydantic model representing the response structure for document counts. This model includes fields for the total number of documents, the number of approved documents, pending documents, reviewed documents, rejected documents, total invoices, and total purchase orders. The model serves as a structured format for returning aggregated counts of various document types in the system, allowing for easy serialization and validation of the response data when retrieving document counts through the API."""

    total: int
    approved: int
    pending: int
    reviewed: int
    rejected: int
    total_invoices: int
    total_pos: int

    model_config = ConfigDict(from_attributes=True)


class RecentActivityItem(BaseModel):
    """Pydantic model representing an item in the recent activity list. This model includes fields for the matching group ID, associated invoices, purchase orders, status, and other relevant information. The model serves as a structured format for representing recent activity on documents, allowing for easy serialization and validation of the response data when retrieving recent activity through the API. Each item in the recent activity list provides insights into the latest updates and changes made to matching groups, including the status of the group and the total amount across all invoices in the group."""

    group_id: int
    invoices: list[str]
    pos: list[str]
    status: str
    is_po_matched: bool | None
    total_amount: float
    invoice_date: str | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonthlyVolumeItem(BaseModel):
    """Pydantic model representing an item in the monthly volume list. This model includes fields for the month, the number of invoices, and the number of purchase orders for that month. The model serves as a structured format for representing monthly volume data, allowing for easy serialization and validation of the response data when retrieving monthly volume through the API. Each item in the monthly volume list provides insights into the number of documents processed in each month, helping to analyze trends and patterns in document processing over time."""

    month: str
    invoices: int
    po: int

    model_config = ConfigDict(from_attributes=True)


class MonthlyAmountItem(BaseModel):
    """Pydantic model representing an item in the monthly amount list. This model includes fields for the month and the total amount across all invoices for that month. The model serves as a structured format for representing monthly amount data, allowing for easy serialization and validation of the response data when retrieving monthly amount through the API. Each item in the monthly amount list provides insights into the total financial volume of documents processed in each month, helping to analyze trends and patterns in document processing and financial activity over time."""

    month: str
    amount: float

    model_config = ConfigDict(from_attributes=True)


class QuickStatsResponse(BaseModel):
    """Pydantic model representing the response structure for quick statistics. This model includes fields for the number of invoices processed this month, the number of purchase orders processed this month, the number of active associates, and the percentage change in amount compared to the previous month. The model serves as a structured format for returning key performance indicators and metrics related to document processing in the system, allowing for easy serialization and validation of the response data when retrieving quick statistics through the API. These statistics provide insights into the current state of document processing and financial activity within the system."""

    invoices_this_month: int
    po_this_month: int
    active_associates: int
    amount_change_pct: float

    model_config = ConfigDict(from_attributes=True)


class InvoiceStatsResponse(BaseModel):
    """Pydantic model representing the response structure for invoice statistics. This model includes fields for the total number of invoices, the number of approved invoices, pending invoices, reviewed invoices, rejected invoices, and the total value of all invoices. The model serves as a structured format for returning aggregated statistics about invoices in the system, allowing for easy serialization and validation of the response data when retrieving invoice statistics through the API. These statistics provide insights into the overall status and financial volume of invoices processed within the system."""

    total_invoices: int
    approved: int
    pending: int
    reviewed: int
    rejected: int
    total_value: float

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderStatsResponse(BaseModel):
    """Pydantic model representing the response structure for purchase order statistics. This model includes fields for the total number of purchase orders, the number of pending purchase orders, completed purchase orders, cancelled purchase orders, and the total value of all purchase orders. The model serves as a structured format for returning aggregated statistics about purchase orders in the system, allowing for easy serialization and validation of the response data when retrieving purchase order statistics through the API. These statistics provide insights into the overall status and financial volume of purchase orders processed within the system."""

    total_pos: int
    pending: int
    completed: int
    cancelled: int
    total_value: float

    model_config = ConfigDict(from_attributes=True)


class VendorResponse(BaseModel):
    """Pydantic model representing the response structure for vendor information. This model includes fields for the vendor ID, name, email, mobile number, and address. The model serves as a structured format for returning vendor details, allowing for easy serialization and validation of the response data when retrieving vendor information through the API. This information provides insights into the vendors associated with invoices and purchase orders in the system, which can be used for communication and relationship management purposes."""

    name: str | None
    email: str | None
    mobile_number: str | None
    address: str | None

    model_config = ConfigDict(from_attributes=True)


class InvoiceMatchingInvoice(BaseModel):
    """Pydantic model representing an invoice in the context of invoice matching. This model includes fields for the invoice ID, invoice date, due date, total amount, subtotal, tax amount, currency code, and associated vendor information. The model serves as a structured format for representing invoices that are being matched with purchase orders, allowing for easy serialization and validation of the response data when retrieving invoice matching results through the API. Each invoice included in the invoice matching results provides insights into its details and associated vendor information, which can be used to assess the matching status and make informed decisions about invoice processing."""

    invoice_id: str
    invoice_date: datetime | None
    due_date: datetime | None
    total_amount: float
    subtotal: float
    tax_amount: float
    currency_code: str

    vendor: VendorResponse | None

    model_config = ConfigDict(from_attributes=True)


class InvoiceMatchingPO(BaseModel):
    """Pydantic model representing a purchase order in the context of invoice matching. This model includes fields for the purchase order ID, the total amount of the purchase order, the currency code, the status of the purchase order, and the ordered date. The model serves as a structured format for representing purchase orders that are being matched with invoices, allowing for easy serialization and validation of the response data when retrieving invoice matching results through the API. Each purchase order included in the invoice matching results provides insights into its details and status, which can be used to assess the matching status and make informed decisions about invoice processing."""

    po_id: str
    total_amount: float
    currency_code: str
    status: str
    ordered_date: datetime | None

    model_config = ConfigDict(from_attributes=True)


class InvoiceMatchingResponse(BaseModel):
    """Pydantic model representing the response structure for invoice matching results. This model includes fields for the matching group ID, associated invoices, purchase orders, status, decision, confidence score, and other relevant information. The model serves as a structured format for returning the results of invoice matching operations, allowing for easy serialization and validation of the response data when retrieving invoice matching results through the API. Each response provides insights into the matching status of invoices and purchase orders, including any decisions made and the confidence level of those decisions."""

    group_id: int

    invoices: list[InvoiceMatchingInvoice]
    pos: list[InvoiceMatchingPO]

    invoice_ids: list[str]
    po_ids: list[str]

    matching_status: str
    decision: str | None
    confidence_score: float | None

    is_po_matched: bool | None

    command: str | None
    mail_to: str | None
    mail_subject: str | None
    mail_body: str | None

    matched_at: datetime | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QueueResponse(BaseModel):
    """Pydantic model representing the response structure for queue information. This model includes fields for the number of documents currently in the processing queue and the average processing time per document. The model serves as a structured format for returning information about the processing queue, allowing for easy serialization and validation of the response data when retrieving queue information through the API. This information provides insights into the current workload and performance of the document processing system."""

    status: str
    file_id: str

    model_config = ConfigDict(from_attributes=True)


class CommonResponse(BaseModel):
    """Pydantic model representing the response structure for health check information. This model includes fields for the status of the service, the version of the application, and the current timestamp. The model serves as a structured format for returning health check information, allowing for easy serialization and validation of the response data when performing health checks on the API. This information provides insights into the operational status and versioning of the service, which can be used for monitoring and maintenance purposes."""

    message: str

    model_config = ConfigDict(from_attributes=True)
