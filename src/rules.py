from src.schemas import ExtractedInvoice

def check_compliance_rules(invoice: ExtractedInvoice) -> list[str]:
    """Applies corporate policies and returns a list of red flags."""
    red_flags = []
    if invoice.has_alcohol:
        red_flags.append("Compliance Policy Violation: Alcohol detected on invoice.")
    if invoice.is_weekend_or_late:
        red_flags.append("Audit Warning: Expense incurred during weekend or late night.")
    if invoice.amount >= 50000:
        red_flags.append("Approval Limit Exceeded: Amount is 50,000 or higher.")
    return red_flags