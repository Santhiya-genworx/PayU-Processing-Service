"""This module defines the extractor agents responsible for processing and extracting information from documents such as invoices and purchase orders. The agents utilize a language model (LLM) to classify document types, extract structured data, and perform vision-based text extraction from images. The module includes functions for safely handling text content, formatting validation errors, and converting Pydantic models to dictionaries. The agents are designed to work with an AgentState that holds the relevant information needed for the extraction process, and they raise appropriate exceptions in case of errors during classification or extraction. The module also includes logging for monitoring the extraction process and provides detailed error messages to help identify issues with"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, ValidationError

from src.config.settings import settings
from src.control.extractor_agent.extractor_state import AgentState
from src.core.exceptions.exceptions import BadRequestException
from src.observability.logging.logging_config import logger
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", temperature=0, api_key=settings.gemini_api_key
)


def _safe_text(content: str | list[Any]) -> str:
    """Helper function to safely extract text from the LLM response content, which can be either a string or a list of strings and dictionaries. The function handles both cases and returns a clean, concatenated string output. If the content is a string, it simply returns the stripped version of it. If the content is a list, it iterates through the items, extracting text from strings and converting dictionaries to their string representation, then joins all parts together into a single string. This ensures that the extracted text is properly formatted and free of any extraneous whitespace."""
    if isinstance(content, str):
        return content.strip()
    elif isinstance(content, list):
        parts: list[str] = []
        for c in content:
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, dict):
                parts.append(str(c))
        return " ".join(parts).strip()


async def detect_document_type(state: AgentState) -> dict[str, Any]:
    """Agent function to detect the type of a document based on its raw text content. This function uses a language model (LLM) to classify the document as either an invoice, a purchase order, or unknown. The function constructs a prompt for the LLM that includes the raw text of the document and instructs it to return only one of the specified classifications. The response from the LLM is processed to extract the detected document type, which is then returned in a dictionary format. If any errors occur during the classification process, a BadRequestException is raised with details about the error. Args:   state (AgentState): The current state of the agent, which includes the raw text"""
    try:
        messages = [
            SystemMessage(
                content="""
                You are a document classifier.
                Return ONLY one word: invoice | purchase_order | unknown
            """
            ),
            HumanMessage(content=f"Classify:\n{state['raw_text']}"),
        ]

        response = await llm.ainvoke(messages)
        text = _safe_text(response.content).lower()

        return {"detected_document_type": text}

    except Exception as err:
        raise BadRequestException(detail=str(err)) from err


def format_validation_errors(error: ValidationError) -> str:
    """Helper function to format Pydantic validation errors into a readable string format. This function takes a ValidationError object as input and iterates through the list of errors contained within it. For each error, it constructs a message that includes the path to the field that caused the error, the type of validation error, and the original error message. The messages are collected into a list and then joined together into a single string with newline separators. This formatted string can be used to provide clear and detailed feedback about what went wrong during the validation process, making it easier for developers or users to understand and address the issues with their input data."""
    messages: list[str] = []

    for err in error.errors():
        field_path = " → ".join(str(loc) for loc in err["loc"])
        error_type = err["type"]
        raw_msg = err["msg"]

        if error_type == "missing":
            messages.append(f"{field_path} is required but missing.")
        elif error_type in ("int_parsing", "float_parsing"):
            messages.append(f"{field_path} is not a valid number.")
        elif error_type == "date_parsing":
            messages.append(f"{field_path} has invalid date format.")
        else:
            messages.append(f"{field_path}: {raw_msg}")

    return "\n".join(messages)


def _to_dict(data: BaseModel | dict[str, Any]) -> dict[str, Any]:
    """Helper function to convert a Pydantic BaseModel instance to a dictionary. If the input data is an instance of BaseModel, it uses the model_dump() method to convert it to a dictionary. If the input data is already a dictionary, it simply returns it as is. This function ensures that the output is always in a consistent dictionary format, which can be easily used for further processing or returned in API responses."""
    if isinstance(data, BaseModel):
        return data.model_dump()
    return data


async def text_extractor(state: AgentState) -> dict[str, Any]:
    """Agent function to extract structured data from the raw text of a document using a language model (LLM). This function first checks the detected document type in the agent state and constructs a prompt for the LLM to extract either invoice data or purchase order data accordingly. The LLM is invoked with the appropriate structured output schema (InvoiceRequest or PurchaseOrderRequest) based on the document type. The response from the LLM is processed and returned as a dictionary containing the extracted data. If any validation errors occur during the extraction process, they are caught and formatted into a readable string format, which is then included in a BadRequestException raised to indicate issues with the input data or extraction logic. Args:   state (AgentState): The current state of the agent, which includes the raw text and detected document type needed for extraction. Returns:    A dictionary containing the extracted structured data from the document, formatted according to the specified schema."""
    logger.info("Text Extractor...")

    try:
        document_type = state["document_type"]
        detected_document_type = state["detected_document_type"]

        if detected_document_type == "unknown":
            raise BadRequestException(detail=f"Unknown file type. Expected {document_type}")

        if document_type != detected_document_type:
            raise BadRequestException(
                detail=f"Expected {document_type}, got {detected_document_type}"
            )

        messages = [
            SystemMessage(content="Extract structured financial data."),
            HumanMessage(content=state["raw_text"]),
        ]

        if document_type == "invoice":
            llm_invoice = llm.with_structured_output(InvoiceRequest)

            try:
                response = await llm_invoice.ainvoke(messages)
                return {"invoice_data": _to_dict(response)}

            except Exception as err:
                if isinstance(err, ValidationError):
                    raise BadRequestException(detail=format_validation_errors(err)) from err
                if isinstance(err.__cause__, ValidationError):
                    raise BadRequestException(
                        detail=format_validation_errors(err.__cause__)
                    ) from err
                raise BadRequestException(detail=str(err)) from err

        else:
            llm_po = llm.with_structured_output(PurchaseOrderRequest)

            try:
                response = await llm_po.ainvoke(messages)
                return {"po_data": _to_dict(response)}

            except Exception as err:
                if isinstance(err, ValidationError):
                    raise BadRequestException(detail=format_validation_errors(err)) from err
                if isinstance(err.__cause__, ValidationError):
                    raise BadRequestException(
                        detail=format_validation_errors(err.__cause__)
                    ) from err
                raise BadRequestException(detail=str(err)) from err

    except Exception as err:
        raise Exception(str(err)) from err


async def vision_extractor(state: AgentState) -> dict[str, Any]:
    """Agent function to extract raw text from an image using a language model (LLM) with vision capabilities. This function constructs a prompt for the LLM that includes the base64-encoded image data and instructs it to extract text from the image. The LLM processes the input and returns the extracted text, which is then safely handled and returned in a dictionary format. If any errors occur during the vision extraction process, a generic Exception is raised with details about the error. Args:   state (AgentState): The current state of the agent, which includes the base64-encoded image data needed for vision extraction. Returns:    A dictionary containing the raw text extracted from the image."""
    logger.info("Vision Extractor...")

    try:
        messages = [
            SystemMessage(content="Extract raw text from image."),
            HumanMessage(
                content=[
                    {"type": "text", "text": "Extract text"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{state['base64_image']}"},
                    },
                ]
            ),
        ]

        response = await llm.ainvoke(messages)
        text = _safe_text(response.content)

        return {"raw_text": text}

    except Exception as err:
        raise Exception(f"Vision extraction failed: {str(err)}") from err
