from langchain_core.messages import HumanMessage, SystemMessage
from src.core.config.settings import settings
from src.control.state import AgentState
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    api_key=settings.gemini_api_key
)

async def text_extractor(state: AgentState):
    """
    Agent which reads text input and converts into structured json
    """

    print("Text Extractor...")
    try:
        messages = [
            SystemMessage(
                content="""
                    You are a precise financial document extractor. 
                    Extract data strictly according to the provided schema. 
                    Do not hallucinate missing values.
                """
            ),
            HumanMessage(
                content=f"""
                    Extract structured data from the following document:
                    {state["raw_text"]}
                """
            )
        ]

        if state["document_type"] == "invoice":
            llm_invoice = llm.with_structured_output(InvoiceRequest)
            response = await llm_invoice.ainvoke(messages)
            return {
                "invoice_data": response.model_dump()
            }
        else:
            llm_po = llm.with_structured_output(PurchaseOrderRequest)
            response = await llm_po.ainvoke(messages)
            return {
                "po_data": response.model_dump()
            }

    except Exception as err:
        raise Exception(f"Text extraction failed. {str(err)}")

async def vision_extractor(state: AgentState):
    """
    Agent which extracts raw text from an image using vision model
    """

    print("Vision Extractor...")
    try:
        messages = [
            SystemMessage(
                content="""
                    You are a financial document OCR assistant.
                    Extract all readable text from the image.
                    Only return plain text.
                    Do NOT generate JSON, do NOT attempt tool calls.
                    Do not summarize or hallucinate.
                """
            ),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Extract all readable text from this document image."
                    },
                    {
                        "type": "image_url",
                        "image_url": { "url": f"data:image/jpeg;base64,{state["base64_image"]}" }
                    }
                ]
            )
        ]

        response = await llm.ainvoke(messages)
        return {
            "raw_text": response.content.strip()
        }

    except Exception as err:
        raise Exception(f"Vision extraction failed: {str(err)}")