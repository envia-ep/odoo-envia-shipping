from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestChooseDeliveryApply(TransactionCase):
    def test_apply_selected_envia_quote_applies_delivery_line(self):
        partner = self.env.company.partner_id
        product = self.env["product.product"].search([("sale_ok", "=", True)], limit=1)
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 1.0})],
            }
        )
        quote = self.env["envia.quote"].create(
            {
                "sale_order_id": order.id,
                "origin_postal_code": "67192",
                "destination_postal_code": "03100",
                "weight": 1.0,
                "content": "Test",
                "state": "quoted",
            }
        )
        service = self.env["envia.quote.service"].create(
            {
                "quote_id": quote.id,
                "service_id": "estafeta:ground",
                "carrier": "estafeta",
                "service_name": "Estafeta Terrestre",
                "price": 123.45,
                "is_selected": True,
            }
        )
        quote.selected_service_id = service.id
        wizard = self.env["envia.quote.wizard"].create({"sale_order_id": order.id})
        with patch(
            "odoo.addons.envia.wizards.envia_quote_wizard.EnviaQuoteWizard._perform_get_quote",
            return_value=False,
        ):
            wizard.action_apply_shipping_to_order()
        shipping_line = order.order_line.filtered("is_delivery")
        self.assertEqual(len(shipping_line), 1)
        self.assertEqual(shipping_line.price_unit, 123.45)

