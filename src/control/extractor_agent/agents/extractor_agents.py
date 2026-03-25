from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, ValidationError

from src.control.extractor_agent.extractor_state import AgentState
from src.core.config.settings import settings
from src.core.exceptions.exceptions import BadRequestException
from src.observability.logging.logging_config import logger
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", temperature=0, api_key=settings.gemini_api_key
)


def _safe_text(content: str | list[Any]) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for c in content:
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, dict):
                parts.append(str(c))
        return " ".join(parts).strip()


async def detect_document_type(state: AgentState) -> dict[str, Any]:
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
    if isinstance(data, BaseModel):
        return data.model_dump()
    return data


async def text_extractor(state: AgentState) -> dict[str, Any]:
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
