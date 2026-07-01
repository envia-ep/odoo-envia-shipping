from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ecart_app_id = fields.Char(related="company_id.ecart_app_id", readonly=False)
    ecart_client_id = fields.Char(related="company_id.ecart_client_id", readonly=False)
    ecart_base_url = fields.Char(related="company_id.ecart_base_url", readonly=False)
    ecart_oauth_base_url = fields.Char(
        related="company_id.ecart_oauth_base_url",
        readonly=False,
    )
    ecart_auto_confirm_orders = fields.Boolean(
        related="company_id.ecart_auto_confirm_orders",
        readonly=False,
    )
    ecart_fallback_product_id = fields.Many2one(
        related="company_id.ecart_fallback_product_id",
        readonly=False,
    )
    ecart_oauth_redirect_url = fields.Char(
        string="OAuth Redirect URL",
        compute="_compute_ecart_display_urls",
    )
    ecart_oauth_connect_url = fields.Char(
        string="OAuth Connect URL",
        compute="_compute_ecart_display_urls",
    )
    ecart_has_app_credentials = fields.Boolean(compute="_compute_ecart_display_urls")

    @api.depends("company_id", "ecart_app_id")
    def _compute_ecart_display_urls(self):
        for record in self:
            company = record.company_id
            record.ecart_oauth_redirect_url = company._ecart_get_redirect_url()
            record.ecart_oauth_connect_url = company._ecart_get_oauth_url()
            record.ecart_has_app_credentials = bool(
                record.ecart_app_id and record.ecart_client_id
            )

    def action_open_ecart_oauth(self):
        self.ensure_one()
        if not self.ecart_app_id:
            raise UserError(_("Configure the Ecart App ID before connecting a store."))
        url = self.company_id._ecart_get_oauth_url()
        if not url:
            raise UserError(_("Configure the Ecart App ID before connecting a store."))
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def action_open_ecart_stores(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Connected Stores"),
            "res_model": "ecart.store",
            "view_mode": "list,form",
            "domain": [("company_id", "=", self.env.company.id)],
        }
