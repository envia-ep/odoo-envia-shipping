from odoo import _, api, fields, models

from ..hooks import load_envia_demo_data


class EnviaQuoteOnboardingWizard(models.TransientModel):
    _name = "envia.quote.onboarding.wizard"
    _description = "Envia Quote Onboarding Wizard"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    is_sandbox = fields.Boolean(compute="_compute_is_sandbox")

    @api.depends("company_id", "company_id.envia_environment")
    def _compute_is_sandbox(self) -> None:
        for wizard in self:
            wizard.is_sandbox = wizard.company_id._envia_is_sandbox()

    def _dismiss(self) -> None:
        self.ensure_one()
        self.company_id.envia_quote_onboarding_pending = False

    def action_open_demo_order(self):
        self.ensure_one()
        self._dismiss()
        if self.is_sandbox:
            load_envia_demo_data(self.env)
        return self.env.ref("envia.action_envia_demo_sale_order").read()[0]

    def action_go_to_quotes(self):
        self.ensure_one()
        self._dismiss()
        return self.env["ir.actions.act_window"]._for_xml_id("envia.action_envia_config_settings")

    @api.model
    def get_entry_action(self):
        company = self.env.company
        company.envia_quote_onboarding_pending = False
        return self.env["ir.actions.act_window"]._for_xml_id("envia.action_envia_config_settings")
