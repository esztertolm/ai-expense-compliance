import unittest

from src.expense_audit import (
    build_graph,
    InvoiceAuditState,
    extract_invoice_data,
    route_after_analysis,
)


class InvoiceAuditWorkflowTests(unittest.TestCase):
    def test_extract_invoice_data_finds_red_flags(self):
        invoice_text = (
            "Company: Luxury Restaurant, Date: 2026.07.03 (Friday) 23:45, "
            "Amount: 120000 HUF, Item: 2 x Ribeye steak, 1 bottle of premium wine"
        )
        parsed = extract_invoice_data(invoice_text)

        self.assertEqual(parsed.vendor, "Luxury Restaurant")
        self.assertEqual(parsed.amount, 120000)
        self.assertEqual(parsed.category, "dinner")
        self.assertIn("alcohol", parsed.red_flags)
        self.assertIn("night_meal", parsed.red_flags)

    def test_build_graph_contains_expected_nodes(self):
        graph = build_graph()
        self.assertIsNotNone(graph)
        self.assertEqual(graph.name, "expense_audit_graph")

    def test_route_after_analysis_requires_human_review_when_red_flags_exist(self):
        state: InvoiceAuditState = {
            "invoice_text": "Company: Luxury Restaurant ...",
            "red_flags": ["alcohol"],
        }
        self.assertEqual(route_after_analysis(state), "human_review")


if __name__ == "__main__":
    unittest.main()
