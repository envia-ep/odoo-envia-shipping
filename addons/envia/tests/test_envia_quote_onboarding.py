from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestEnviaQuoteOnboarding(TransactionCase):
    def test_get_quotes_onboarding_data_returns_steps(self):
        onboarding = self.env.ref("envia.onboarding_onboarding_envia_quotes")
        onboarding.with_company(self.env.company)._search_or_create_progress()
        data = self.env["envia.quote"].get_quotes_onboarding_data()
        self.assertTrue(data)
        self.assertEqual(len(data["steps"]), 4)
        self.assertEqual(data["steps"][0]["action"], "action_open_step_envia_connect")

    def test_onboarding_step_actions_return_window_actions(self):
        action = self.env["onboarding.onboarding.step"].action_open_step_envia_connect()
        self.assertEqual(action.get("type"), "ir.actions.act_window")

        action = self.env["onboarding.onboarding.step"].action_open_step_envia_demo_order()
        self.assertEqual(action.get("res_model"), "sale.order")

        action = self.env["onboarding.onboarding.step"].action_open_step_envia_get_rates()
        self.assertEqual(action.get("res_model"), "envia.quote.wizard")
        self.assertEqual(action.get("views"), [(False, "form")])
