from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from src.control.validation_agent.agents.validation_agents import (
    decision_agent,
    line_item_match_agent,
    price_check_node,
    quantity_price_match_agent,
    vendor_match_node,
)
from src.control.validation_agent.validation_router import router
from src.control.validation_agent.validation_state import AgentState
from src.schemas.graph_output_schema import GraphResult
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest

workflow = StateGraph(AgentState)

workflow.add_node("vendor_match", vendor_match_node)
workflow.add_node("line_item_match", line_item_match_agent)
workflow.add_node("price_check", price_check_node)
workflow.add_node("quantity_price_match", quantity_price_match_agent)
workflow.add_node("decision_agent", decision_agent)

workflow.add_conditional_edges(
    START, router, {"skip_po": "price_check", "match_po": "vendor_match"}
)
workflow.add_edge("vendor_match", "line_item_match")
workflow.add_edge("line_item_match", "price_check")

workflow.add_conditional_edges(
    "price_check",
    router,
    {"skip_po": "decision_agent", "match_po": "quantity_price_match"},
)

workflow.add_edge("quantity_price_match", "decision_agent")
workflow.add_edge("decision_agent", END)

graph = workflow.compile()


async def invoke_graph(
    invoice_data: list[InvoiceRequest],
    po_data: list[PurchaseOrderRequest],
) -> GraphResult:
    try:
        state: AgentState = {
            "invoices": invoice_data,
            "pos": po_data,
        }

        result = await graph.ainvoke(cast(Any, state))

        return cast(GraphResult, result)

    except Exception:
        raise
