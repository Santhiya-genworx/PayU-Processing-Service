from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import SecretStr

from src.control.validation_agent.validation_state import AgentState
from src.core.config.settings import settings

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=SecretStr(settings.groq_api_key),
)

_REJECT_PHRASES: list[str] = [
    "VENDOR_MISMATCH",
    "GST_MISMATCH",
    "OVER_INVOICED",
    "ITEM_NOT_IN_PO",
    "ITEM_UNMATCHED",
    "LINE_CALC_ERROR",
    "SUBTOTAL_MISMATCH",
    "TOTAL_MISMATCH",
]

_REVIEW_PHRASES: list[str] = [
    "PARTIAL_DELIVERY",
    "UNIT_PRICE_MISMATCH",
]


def _deterministic_status(messages: list[str]) -> str:
    combined = " ".join(messages)

    if any(p in combined for p in _REJECT_PHRASES):
        return "reject"
    if any(p in combined for p in _REVIEW_PHRASES):
        return "review"
    return "approve"


def _deterministic_confidence(status: str, messages: list[str]) -> float:
    combined = " ".join(messages)

    if status == "approve":
        return 1.00
    if status == "review":
        return 0.85

    reject_hits = sum(1 for p in _REJECT_PHRASES if p in combined)

    if "VENDOR_MISMATCH" in combined or "GST_MISMATCH" in combined:
        return 0.40
    if reject_hits >= 3:
        return 0.40
    if reject_hits == 2:
        return 0.55

    return 0.70


def _scenario(invoices: list[Any], pos: list[Any]) -> str:
    ni, np = len(invoices), len(pos)

    if ni == 1 and np == 0:
        return "1 invoice, no PO"
    if ni == 1 and np == 1:
        return "1 invoice, 1 PO"
    if ni == 1 and np > 1:
        return f"1 invoice, {np} POs"
    if ni > 1 and np == 1:
        return f"{ni} invoices, 1 PO"

    return f"{ni} invoices, {np} POs"


def _get_po_map(pos: list[Any]) -> dict[str, Any]:
    return {po.po_id: po for po in pos}


def _invoice_pos(invoice: Any, po_map: dict[str, Any]) -> list[Any]:
    if not invoice.po_id:
        return []

    ids: list[str] = invoice.po_id if isinstance(invoice.po_id, list) else [invoice.po_id]

    return [po_map[pid] for pid in ids if pid in po_map]


def vendor_match_node(state: AgentState) -> dict[str, list[AIMessage]]:
    invoices = state.get("invoices", [])
    pos = state.get("pos", [])
    messages: list[AIMessage] = []

    if not pos:
        messages.append(AIMessage(content="No PO — vendor match skipped"))
        return {"messages": messages}

    po_map = _get_po_map(pos)

    for invoice in invoices:
        inv_v = invoice.vendor
        invoice_pos = _invoice_pos(invoice, po_map)

        for po in invoice_pos:
            po_v = po.vendor
            prefix = f"[INV {invoice.invoice_id} / PO {po.po_id}]"

            if inv_v.name != po_v.name or inv_v.email != po_v.email:
                messages.append(AIMessage(content=f"{prefix} VENDOR_MISMATCH"))
            elif inv_v.gst_number != po_v.gst_number:
                messages.append(AIMessage(content=f"{prefix} GST_MISMATCH"))
            else:
                messages.append(AIMessage(content=f"{prefix} VENDOR_OK"))

    return {"messages": messages}


async def line_item_match_agent(
    state: AgentState,
) -> dict[str, list[AIMessage]]:
    invoices = state.get("invoices", [])
    pos = state.get("pos", [])

    if not pos:
        return {"messages": [AIMessage(content="No PO — skipped")]}

    po_map = _get_po_map(pos)

    invoices_block = ""
    for inv in invoices:
        inv_items = ", ".join(i.item_description for i in inv.invoice_items)
        invoice_pos = _invoice_pos(inv, po_map)

        po_items = " | ".join(
            f"PO {po.po_id}: " + ", ".join(i.item_description for i in po.ordered_items)
            for po in invoice_pos
        )

        invoices_block += f"{inv.invoice_id}: {inv_items} | {po_items}\n"

    result = await llm.ainvoke(
        [
            SystemMessage(content="Match invoice items to PO items"),
            HumanMessage(content=invoices_block),
        ]
    )

    return {"messages": [AIMessage(content=str(result.content))]}


def price_check_node(state: AgentState) -> dict[str, list[AIMessage]]:
    invoices = state.get("invoices", [])
    messages: list[AIMessage] = []

    for invoice in invoices:
        for item in invoice.invoice_items:
            if item.quantity and item.unit_price:
                expected = round(item.quantity * item.unit_price, 2)
                if expected != round(item.total_price, 2):
                    messages.append(AIMessage(content="LINE_CALC_ERROR"))

    if not messages:
        messages.append(AIMessage(content="PRICE_OK"))

    return {"messages": messages}


def quantity_price_match_agent(
    state: AgentState,
) -> dict[str, list[AIMessage]]:

    invoices = state.get("invoices", [])
    pos = state.get("pos", [])
    messages: list[AIMessage] = []

    if not pos:
        return {"messages": [AIMessage(content="NO_PO")]}

    po_map = _get_po_map(pos)

    def _find_po_item(po: Any, desc: str) -> Any | None:
        for item in po.ordered_items:
            if item.item_description.lower().strip() == desc:
                return item
        return None

    for invoice in invoices:
        invoice_pos = _invoice_pos(invoice, po_map)

        for inv_item in invoice.invoice_items:
            desc = inv_item.item_description.lower().strip()

            found = any(_find_po_item(po, desc) is not None for po in invoice_pos)

            if not found:
                messages.append(AIMessage(content="ITEM_NOT_IN_PO"))

    if not messages:
        messages.append(AIMessage(content="QTY_OK"))

    return {"messages": messages}


def _to_str(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item.strip())
            elif isinstance(item, dict):
                parts.append(str(item))
        return " ".join(parts)

    return str(content)


async def decision_agent(state: AgentState) -> dict[str, Any]:

    messages_raw = state.get("messages", [])

    previous_results: list[str] = [
        _to_str(m.content) if hasattr(m, "content") else str(m) for m in messages_raw
    ]

    status = _deterministic_status(previous_results)
    confidence = _deterministic_confidence(status, previous_results)

    if status == "approve":
        return {
            "output": {
                "status": status,
                "confidence_score": 1.0,
                "command": "Approved",
                "mail_to": None,
                "mail_subject": None,
                "mail_body": None,
            }
        }

    return {
        "output": {
            "status": status,
            "confidence_score": confidence,
            "command": previous_results[0] if previous_results else status,
            "mail_to": None,
            "mail_subject": None,
            "mail_body": None,
        }
    }
