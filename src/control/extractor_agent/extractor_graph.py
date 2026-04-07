"""Module defining the extractor graph for processing documents such as invoices and purchase orders. This module utilizes a state graph to orchestrate the flow of data through various agent functions responsible for detecting document types, extracting text, and performing vision-based extraction. The graph is designed to handle both text and image inputs, routing them appropriately based on their file type. The main function, invoke_graph, serves as the entry point for invoking the graph with the necessary input parameters and returns the extracted data in a structured format. The module also includes error handling to manage exceptions that may arise during the extraction process, ensuring that meaningful error messages are provided when issues occur."""

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from src.control.extractor_agent.agents.extractor_agents import (
    detect_document_type,
    text_extractor,
    vision_extractor,
)
from src.control.extractor_agent.extractor_router import router
from src.control.extractor_agent.extractor_state import AgentState
from src.core.exceptions.exceptions import BadRequestException

workflow = StateGraph(AgentState)

workflow.add_node("type_detector", detect_document_type)
workflow.add_node("text_extractor", text_extractor)
workflow.add_node("vision_extractor", vision_extractor)

workflow.add_conditional_edges(
    START, router, {"text": "type_detector", "image": "vision_extractor", "end": END}
)
workflow.add_edge("vision_extractor", "type_detector")
workflow.add_edge("type_detector", "text_extractor")
workflow.add_edge("text_extractor", END)

graph = workflow.compile()


async def invoke_graph(
    input: str,
    file_type: str,
    document_type: str,
) -> dict[str, Any]:
    """Function to invoke the extractor graph with the provided input, file type, and document type. This function initializes the agent state based on the input parameters and then invokes the compiled graph to perform the extraction process. The function handles both text and image inputs, setting up the state accordingly for the graph execution. The result from the graph is processed to return the extracted data in a dictionary format based on the document type (invoice or purchase order). If any errors occur during the graph invocation, they are caught and raised as exceptions with details about the error. Args:   input (str): The raw text or base64-encoded image data to be processed by the graph. file_type (str): The type of the input file, either "text" or "image". document_type (str): The type of document being processed, either "invoice" or "purchase_order". Returns:    A dictionary containing the extracted data from the document, formatted according to the specified schema."""

    state: AgentState = {}
    try:
        if file_type == "image":
            state = {
                "raw_text": "",
                "file_type": file_type,
                "document_type": document_type,
                "base64_image": input,
            }
        else:
            state = {
                "raw_text": input,
                "file_type": file_type,
                "document_type": document_type,
                "base64_image": None,
            }

        result = await graph.ainvoke(cast(Any, state))

        if document_type == "invoice":
            return cast(dict[str, Any], result.get("invoice_data", {}))
        elif document_type == "purchase_order":
            return cast(dict[str, Any], result.get("po_data", {}))
        else:
            raise BadRequestException(detail="Invalid document type")

    except Exception:
        raise
