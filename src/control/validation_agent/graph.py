from typing import Literal, Optional
from fastapi import HTTPException
from langgraph.graph import END, START, StateGraph
from src.data.models.invoice_model import Decision
from src.data.clients.database import AsyncSessionLocal
from src.data.repositories.base_repository import insert_data, update_data_by_any
from src.control.validation_agent.router import router
from src.control.validation_agent.agents.agents import decision_agent, line_item_match_node, price_check_node, quantity_price_match_node, vendor_match_node
from src.schemas.purchase_order_schema import PurchaseOrderRequest
from src.schemas.invoice_schema import InvoiceRequest
from src.control.validation_agent.state import AgentState
from sqlalchemy.ext.asyncio import AsyncSession

workflow = StateGraph(AgentState)

workflow.add_node("vendor_match", vendor_match_node)
workflow.add_node("line_item_match", line_item_match_node)
workflow.add_node("price_check", price_check_node)
workflow.add_node("quantity_price_match", quantity_price_match_node)
workflow.add_node("decision_agent", decision_agent)

workflow.add_conditional_edges(
    START,
    router,
    {
        "skip_po": "price_check",
        "match_po": "vendor_match"
    }
)
workflow.add_edge("vendor_match", "line_item_match")
workflow.add_edge("line_item_match", "price_check")
workflow.add_conditional_edges(
    "price_check",
    router,
    {
        "skip_po": "decision_agent",
        "match_po": "quantity_price_match"
    }
)
workflow.add_edge("quantity_price_match", "decision_agent")
workflow.add_edge("decision_agent", END)

graph = workflow.compile()

async def invoke_graph(invoice_data: InvoiceRequest, po_data: Optional[PurchaseOrderRequest] = None):
    try:
        state = {
            "invoice": invoice_data,
            "po": po_data
        }
        result = await graph.ainvoke(state)
        return {**result["output"], "invoice_id": invoice_data.invoice_id}
        
    except Exception as e:
        raise