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
