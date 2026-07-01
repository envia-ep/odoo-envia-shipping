from odoo import _, api, models

from ..hooks import load_envia_demo_data


class OnboardingOnboardingStep(models.Model):
    _inherit = "onboarding.onboarding.step"

    @api.model
    def action_open_step_envia_connect(self):
        return self.env["envia.plugin.connect.wizard"].action_open_connect_wizard()

    @api.model
    def action_open_step_envia_demo_order(self):
        order = self.env["sale.order"].search(
            [("client_order_ref", "=", "ENVIA-DEMO-QUOTE")],
            limit=1,
        )
        if not order:
            load_envia_demo_data(self.env)
            order = self.env["sale.order"].search(
                [("client_order_ref", "=", "ENVIA-DEMO-QUOTE")],
                limit=1,
            )
        self.action_validate_step("envia.onboarding_onboarding_step_demo_order")
        if not order:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Demo order unavailable"),
                    "message": _("Load Envia test data from the Envia.com menu first."),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Demo Quote Order"),
            "res_model": "sale.order",
            "res_id": order.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    @api.model
    def action_open_step_envia_get_rates(self):
        order = self.env["sale.order"].search(
            [("client_order_ref", "=", "ENVIA-DEMO-QUOTE")],
            limit=1,
        )
        if not order:
            load_envia_demo_data(self.env)
            order = self.env["sale.order"].search(
                [("client_order_ref", "=", "ENVIA-DEMO-QUOTE")],
                limit=1,
            )
        if not order:
            return self.action_open_step_envia_demo_order()
        return order.action_open_envia_quote_wizard()

    @api.model
    def action_open_step_envia_create_label(self):
        quote = self.env["envia.quote"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("selected_service_id", "!=", False),
                ("state", "=", "quoted"),
            ],
            limit=1,
            order="create_date desc",
        )
        if quote:
            return quote.action_open_create_shipment_wizard()
        quote = self.env["envia.quote"].search(
            [("company_id", "=", self.env.company.id), ("state", "=", "quoted")],
            limit=1,
            order="create_date desc",
        )
        if quote:
            return {
                "type": "ir.actions.act_window",
                "name": _("Envia Quote"),
                "res_model": "envia.quote",
                "res_id": quote.id,
                "view_mode": "form",
                "views": [(False, "form")],
                "target": "current",
            }
        return self.action_open_step_envia_get_rates()
