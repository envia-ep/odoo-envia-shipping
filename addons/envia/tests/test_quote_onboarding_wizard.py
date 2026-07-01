from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestEnviaQuoteOnboardingWizard(TransactionCase):
    def test_app_entry_shows_quote_onboarding_when_configured(self):
        self.env.company.write(
            {
                "envia_api_token": "envia-shipping-token-test",
                "envia_quote_onboarding_pending": True,
            }
        )
        action = self.env["envia.plugin.connect.wizard"].action_envia_app_entry()
        self.assertEqual(action["res_model"], "envia.quote.onboarding.wizard")
        self.assertEqual(action["target"], "current")

    def test_app_entry_skips_quote_onboarding_when_completed(self):
        self.env.company.write(
            {
                "envia_api_token": "envia-shipping-token-test",
                "envia_quote_onboarding_pending": False,
            }
        )
        action = self.env["envia.plugin.connect.wizard"].action_envia_app_entry()
        self.assertEqual(action["res_model"], "envia.quote")

    def test_dismiss_on_go_to_quotes(self):
        wizard = self.env["envia.quote.onboarding.wizard"].create(
            {"company_id": self.env.company.id}
        )
        action = wizard.action_go_to_quotes()
        self.assertFalse(self.env.company.envia_quote_onboarding_pending)
        self.assertEqual(action["res_model"], "envia.quote.wizard")
        self.assertEqual(action["target"], "current")

    def test_standalone_quote_wizard_opens_without_sale_order(self):
        action = self.env["envia.quote.wizard"].action_open_quote_wizard()
        self.assertEqual(action["res_model"], "envia.quote.wizard")
        self.assertEqual(action["target"], "current")
        wizard = self.env["envia.quote.wizard"].create(
            self.env["envia.quote.wizard"].default_get([])
        )
        self.assertFalse(wizard.sale_order_id)
        self.assertFalse(wizard.picking_id)
        self.assertTrue(wizard.is_standalone)

    def test_demo_order_dismisses_onboarding(self):
        self.env.company.write({"envia_environment": "sandbox"})
        wizard = self.env["envia.quote.onboarding.wizard"].create(
            {"company_id": self.env.company.id}
        )
        action = wizard.action_open_demo_order()
        self.assertFalse(self.env.company.envia_quote_onboarding_pending)
        self.assertEqual(action["res_model"], "sale.order")

    def test_first_quote_dismisses_onboarding(self):
        self.env.company.write({"envia_quote_onboarding_pending": True})
        self.env["envia.quote"].create(
            {
                "origin_postal_code": "67192",
                "origin_country": "MX",
                "destination_postal_code": "03100",
                "destination_country": "MX",
                "weight": 1.0,
                "length": 10.0,
                "width": 10.0,
                "height": 10.0,
                "content": "Test package",
            }
        )
        self.assertFalse(self.env.company.envia_quote_onboarding_pending)

    def test_get_quote_carriers_uses_selected_branch_carrier(self):
        self.env.company.envia_default_carriers = "dhl,fedex,estafeta"
        mexico = self.env.ref("base.mx")
        dhl = self.env.ref("envia.envia_carrier_dhl")
        wizard = self.env["envia.quote.wizard"].create(
            {
                "origin_location_type": "branch",
                "origin_branch_carrier_id": dhl.id,
                "origin_country_id": mexico.id,
                "destination_location_type": "address",
            }
        )
        wizard.env["envia.quote.wizard.branch"].create(
            {
                "wizard_id": wizard.id,
                "side": "origin",
                "name": "Branch DHL",
                "carrier": "dhl",
                "is_selected": True,
            }
        )
        self.assertEqual(wizard._get_quote_carriers(), "dhl")
