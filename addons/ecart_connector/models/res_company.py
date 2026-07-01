from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ecart_app_id = fields.Char(string="Ecart App ID")
    ecart_client_id = fields.Char(string="Ecart Client Id")
    ecart_base_url = fields.Char(
        string="Ecart API Base URL",
        default="https://api.ecartapi.com",
    )
    ecart_oauth_base_url = fields.Char(
        string="Ecart OAuth Base URL",
        default="https://oauth.ecartapi.com",
    )
    ecart_auto_confirm_orders = fields.Boolean(
        string="Auto-confirm Imported Orders",
        default=True,
        help="Confirm sale orders automatically after import so pickings are created for Envia.",
    )
    ecart_fallback_product_id = fields.Many2one(
        "product.product",
        string="Fallback Product",
        help="Used for order lines when the SKU is not found in Odoo.",
    )

    def _ecart_get_base_url(self) -> str:
        self.ensure_one()
        base = (self.ecart_base_url or "https://api.ecartapi.com").rstrip("/")
        return f"{base}/"

    def _ecart_get_oauth_url(self) -> str:
        self.ensure_one()
        if not self.ecart_app_id:
            return ""
        oauth_base = (
            self.ecart_oauth_base_url or "https://oauth.ecartapi.com"
        ).rstrip("/")
        return f"{oauth_base}/{self.ecart_app_id}?nobar=true&state={self.id}"

    def _ecart_get_redirect_url(self) -> str:
        self.ensure_one()
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", "")
            .rstrip("/")
        )
        if not base_url:
            return ""
        return f"{base_url}/ecart/oauth/callback"

    @api.model
    def _ecart_find_company_for_callback(self, app_id: str | None, state: str | None):
        if state and str(state).isdigit():
            company = self.browse(int(state)).exists()
            if company and company.ecart_app_id == app_id:
                return company
        if app_id:
            company = self.search([("ecart_app_id", "=", app_id)], limit=1)
            if company:
                return company
        return self.env.company
