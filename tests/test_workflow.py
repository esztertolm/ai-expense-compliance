import unittest

from src.expense_audit import (
    InvoiceAuditState,
    analyze_invoice,
    build_graph,
    route_after_analysis,
)


class InvoiceAuditWorkflowTests(unittest.TestCase):
    def test_build_graph_contains_expected_nodes(self):
        graph = build_graph()
        self.assertIsNotNone(graph)
        self.assertEqual(graph.name, "expense_audit_graph")

    def test_route_after_analysis_requires_human_review_when_red_flags_exist(self):
        state: InvoiceAuditState = {
            "invoice_text": "Company: Luxury Restaurant ...",
            "red_flags": ["Compliance Policy Violation: Alcohol detected on invoice."],
        }
        self.assertEqual(route_after_analysis(state), "human_review")

    def test_analyze_invoice_flags_alcohol_and_high_amount(self):
        invoice_text = (
            "Company: Luxury Restaurant, Date: 2026.07.03, "
            "Amount: 120000 HUF, Item: 2 x Ribeye steak, 1 bottle of premium wine"
        )
        state = analyze_invoice({"invoice_text": invoice_text})

        self.assertEqual(state["extracted_data"]["vendor"], "Luxury Restaurant")
        self.assertEqual(state["extracted_data"]["amount"], 120000)
        self.assertEqual(state["status"], "pending_review")
        self.assertTrue(any("Alcohol" in flag for flag in state["red_flags"]))
        self.assertTrue(any("Approval Limit Exceeded" in flag for flag in state["red_flags"]))

    def test_analyze_invoice_parses_generic_amount_and_date(self):
        invoice_text = (
            "Vendor: Blue Bistro, Date: 2026-07-05, Amount: 75,500 EUR, Item: dinner"
        )
        state = analyze_invoice({"invoice_text": invoice_text})

        self.assertEqual(state["extracted_data"]["vendor"], "Blue Bistro")
        self.assertEqual(state["extracted_data"]["amount"], 75500)
        self.assertEqual(state["extracted_data"]["date"], "2026-07-05")
        self.assertEqual(state["status"], "pending_review")


if __name__ == "__main__":
    unittest.main()
