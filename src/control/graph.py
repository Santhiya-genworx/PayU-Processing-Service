from fastapi import HTTPException
from langgraph.graph import END, START, StateGraph
from src.control.router import router
from src.control.agents.extractor_agent import detect_document_type, text_extractor, vision_extractor
from src.control.state import AgentState

workflow = StateGraph(AgentState)

workflow.add_node("type_detector", detect_document_type)
workflow.add_node("text_extractor", text_extractor)
workflow.add_node("vision_extractor", vision_extractor)

workflow.add_conditional_edges(
    START,
    router,
    {
        "text": "type_detector",
        "image": "vision_extractor",
        "end": END
    }
)
workflow.add_edge("vision_extractor", "type_detector")
workflow.add_edge("type_detector", "text_extractor")
workflow.add_edge("text_extractor", END)

graph = workflow.compile()

async def invoke_graph(input: str, file_type: str, document_type: str):
    try:
        state = {
            "raw_text": "",
            "file_type": file_type,
            "document_type": document_type
        }
        if state["file_type"] == "image":
            state["base64_image"] = input
        else: 
            state["raw_text"] = input

        result = await graph.ainvoke(state)
        if document_type == "invoice":
            return result.get("invoice_data")
        elif document_type == "purchase_order":
            return result.get("po_data")
        else:
            raise HTTPException(status_code=400, detail="Invalid document type")
        
    except Exception as e:
        raise