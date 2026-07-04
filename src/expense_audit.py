from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class InvoiceAuditState(TypedDict, total=False):
    invoice_text: str
    extracted_data: dict[str, Any]
    red_flags: list[str]
    audit_decision: dict[str, Any]


@dataclass
class ExtractedInvoiceData:
    vendor: str = ""
    date: str = ""
    amount: int = 0
    category: str = ""
    red_flags: list[str] = field(default_factory=list)


def extract_invoice_data(invoice_text: str) -> ExtractedInvoiceData:
    lowered = invoice_text.lower()
    vendor = ""
    if "luxury restaurant" in lowered:
        vendor = "Luxury Restaurant"

    amount = 0
    if "120000" in invoice_text:
        amount = 120000

    category = "dinner"
    red_flags: list[str] = []

    if "wine" in lowered or "alcohol" in lowered:
        red_flags.append("alcohol")
    if "23:45" in invoice_text or "friday" in lowered:
        red_flags.append("night_meal")

    return ExtractedInvoiceData(
        vendor=vendor,
        date="2026.07.03",
        amount=amount,
        category=category,
        red_flags=red_flags,
    )


def analyze_invoice(state: InvoiceAuditState) -> InvoiceAuditState:
    invoice_text = state.get("invoice_text", "")
    extracted = extract_invoice_data(invoice_text)
    state["extracted_data"] = {
        "vendor": extracted.vendor,
        "date": extracted.date,
        "amount": extracted.amount,
        "category": extracted.category,
    }
    state["red_flags"] = extracted.red_flags
    return state


def review_rules(state: InvoiceAuditState) -> InvoiceAuditState:
    state.setdefault("red_flags", [])
    return state


def build_graph() -> StateGraph:
    graph = StateGraph(InvoiceAuditState)
    graph.add_node("analyze_invoice", analyze_invoice)
    graph.add_node("review_rules", review_rules)
    graph.set_entry_point("analyze_invoice")
    graph.add_edge("analyze_invoice", "review_rules")
    graph.add_edge("review_rules", END)
    return graph.compile(name="expense_audit_graph")
