from typing import Any, Optional, TypedDict
from pydantic import BaseModel, Field

class InvoiceAuditState(TypedDict, total=False):
    invoice_text: str
    invoice_image: Optional[str]
    extracted_data: dict[str, Any]
    red_flags: list[str]
    audit_decision: dict[str, Any]
    needs_human_review: bool
    status: str
    final_message: str

class ExtractedInvoice(BaseModel):
    """Extracted invoice data and automated compliance check flags."""
    vendor: str = Field(description="Name of the company or restaurant issuing the invoice.")
    date: str = Field(description="Date of the invoice in YYYY-MM-DD format.")
    amount: int = Field(description="The absolute final gross total amount (grand total) that the employee actually paid.")
    category: str = Field(description="Expense category (e.g., meals, travel, software, accommodation).")
    has_alcohol: bool = Field(description="True if alcohol (wine, beer, cocktails, any other alcoholic beverage) or any alcoholic brand names (e.g. Dreher) is on the invoice.")
    is_weekend_or_late: bool = Field(description="True if the date falls on a weekend, or the transaction occurred late at night (after 22:00).")