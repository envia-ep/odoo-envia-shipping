from odoo import _, api, fields, models

from odoo.exceptions import UserError

from ..hooks import load_envia_demo_data
from ..services.envia_oauth_client import EnviaOauthClient
from ..services.envia_plugin_setup import (
    clear_pending_setup,
    get_envia_module_version,
    normalize_envia_plugin_version,
)


class ResCompany(models.Model):
    _inherit = "res.company"

    envia_environment = fields.Selection(
        [
            ("sandbox", "Sandbox"),
            ("production", "Production"),
        ],
        string="Envia Environment",
        default="sandbox",
    )
    envia_api_token = fields.Char(string="Envia API Token")
    envia_base_url = fields.Char(
        string="Envia Base URL",
        help="Leave empty to use the default URL for the selected environment.",
    )
    envia_default_carriers = fields.Char(
        string="Default Carriers",
        default="dhl,fedex,estafeta",
        help="Comma-separated carrier codes used when quoting all carriers.",
    )
    envia_default_carrier_ids = fields.Many2many(
        "envia.carrier",
        string="Default Carriers",
        compute="_compute_envia_default_carrier_ids",
        inverse="_inverse_envia_default_carrier_ids",
        help="Carriers included when requesting rates.",
    )

    @api.depends("envia_default_carriers")
    def _compute_envia_default_carrier_ids(self) -> None:
        carrier_model = self.env["envia.carrier"]
        for company in self:
            codes = company._envia_parse_carrier_codes(company.envia_default_carriers)
            company.envia_default_carrier_ids = carrier_model.search([("code", "in", codes)])

    def _inverse_envia_default_carrier_ids(self) -> None:
        for company in self:
            company.envia_default_carriers = ",".join(company.envia_default_carrier_ids.mapped("code"))

    def _envia_parse_carrier_codes(self, carriers_value: str | bool | None) -> list[str]:
        if not carriers_value:
            return []
        return [code.strip() for code in str(carriers_value).split(",") if code.strip()]
    envia_default_origin_partner_id = fields.Many2one(
        "res.partner",
        string="Default Origin Contact",
    )
    envia_label_format = fields.Selection(
        [
            ("PDF", "PDF"),
            ("ZPL", "ZPL"),
            ("PNG", "PNG"),
        ],
        string="Label Format",
        default="PDF",
    )
    envia_label_size = fields.Selection(
        [
            ("STOCK_4X6", "Stock 4x6"),
            ("PAPER_4X6", "Paper 4x6"),
        ],
        string="Label Size",
        default="STOCK_4X6",
    )
    envia_quote_onboarding_pending = fields.Boolean(
        string="Quote Onboarding Pending",
        default=True,
    )
    envia_oauth_connected = fields.Boolean(
        string="Envia OAuth Connected",
        default=False,
        readonly=True,
        copy=False,
    )
    envia_oauth_last_error = fields.Text(
        string="Envia OAuth Last Error",
        readonly=True,
        copy=False,
    )
    envia_oauth_access_token = fields.Char(
        string="Envia OAuth Access Token",
        readonly=True,
        copy=False,
        groups="base.group_system",
    )
    envia_integration_api_key = fields.Char(
        string="Envia Integration API Key",
        readonly=True,
        copy=False,
        groups="base.group_system",
        help="Plain-text Odoo API key used for the Envia.com integration.",
    )
    envia_plugin_version = fields.Char(
        string="Envia Plugin Version",
        readonly=True,
        copy=False,
    )
    envia_shop_id = fields.Char(
        string="Envia Shop ID",
        readonly=True,
        copy=False,
        help="Store identifier assigned by Envia.com during plugin integration.",
    )
    envia_plugin_version_display = fields.Char(
        string="Envia Plugin Version Display",
        compute="_compute_envia_plugin_version_display",
    )

    @api.depends(
        "envia_plugin_version",
        "envia_oauth_connected",
        "envia_oauth_access_token",
    )
    def _compute_envia_plugin_version_display(self) -> None:
        for company in self:
            if not company.envia_oauth_connected:
                company.envia_plugin_version_display = False
                continue

            version = normalize_envia_plugin_version(company.envia_plugin_version)
            if version:
                company.envia_plugin_version_display = version
            elif not company.envia_oauth_access_token:
                company.envia_plugin_version_display = _("Not synced — click Refresh token")
            else:
                company.envia_plugin_version_display = get_envia_module_version(company.env)

    def _initiate_envia_onboardings(self):
        onboardings = self.env["onboarding.onboarding"].sudo().search(
            [("route_name", "=", "envia_quotes")]
        )
        for company in self:
            onboardings.with_company(company)._search_or_create_progress()

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._initiate_envia_onboardings()
        return companies

    def action_load_envia_demo_data(self):
        load_envia_demo_data(self.env)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Envia test data loaded"),
                "message": _(
                    "My Company, Envia Demo Customer, and a confirmed sale order "
                    "are ready for quoting."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def _envia_get_api_token(self) -> str:
        self.ensure_one()
        return (self.envia_api_token or "").strip()

    def _envia_get_shipping_api_token(self) -> str:
        """Return the Envia shipping API token stored on the company.

        Used for api.envia.com requests (quote, labels, tracking).
        Separate from the OAuth integration JWT (eshop/oauth endpoints).
        """
        self.ensure_one()
        return self._envia_get_api_token()

    def _envia_is_shipping_api_configured(self) -> bool:
        self.ensure_one()
        self.env.cr.execute(
            """
            SELECT COALESCE(TRIM(envia_api_token), '')
              FROM res_company
             WHERE id = %s
            """,
            (self.id,),
        )
        row = self.env.cr.fetchone()
        return bool(row and row[0])

    def _envia_try_sync_shipping_api_token_from_oauth(self) -> bool:
        self.ensure_one()
        if self._envia_is_shipping_api_configured():
            return True

        oauth_token = (self.envia_oauth_access_token or "").strip()
        if not oauth_token:
            return False

        try:
            store_access = EnviaOauthClient(self.env).fetch_store_access(oauth_token)
        except UserError:
            return False

        shipping_token = store_access.get("shipping_api_token")
        if not shipping_token:
            return False

        self.envia_api_token = shipping_token
        return True

    def _envia_apply_integration_callback_success(
        self,
        *,
        hash_token: str,
        shop_id: str,
        api_key: str | None = None,
    ) -> dict:
        """Persist a successful Envia integration callback.

        The callback ``hash`` field is the Envia shipping API token.
        """
        self.ensure_one()
        company_vals = {
            "envia_oauth_connected": True,
            "envia_api_token": hash_token,
            "envia_oauth_last_error": False,
            "envia_shop_id": shop_id or False,
        }
        if api_key:
            company_vals["envia_integration_api_key"] = api_key
        self.write(company_vals)
        clear_pending_setup(self.env)
        return {
            "ok": True,
            "company": self.id,
            "shop": shop_id,
            "shipping_api_configured": self._envia_is_shipping_api_configured(),
        }

    def _envia_apply_integration_callback_failure(self, *, error_message: str) -> dict:
        self.ensure_one()
        self.write(
            {
                "envia_oauth_connected": False,
                "envia_api_token": False,
                "envia_shop_id": False,
                "envia_oauth_last_error": error_message,
            }
        )
        return {
            "ok": False,
            "company": self.id,
            "error": "integration_failed",
            "message": error_message,
        }

    def _envia_get_base_url(self) -> str:
        self.ensure_one()
        if self.envia_base_url:
            return self.envia_base_url.rstrip("/") + "/"
        if self.envia_environment == "production":
            return "https://api.envia.com/"
        return "https://api-test.envia.com/"

    def _envia_get_queries_base_url(self) -> str:
        self.ensure_one()
        if self.envia_environment == "production":
            return "https://queries.envia.com/"
        return "https://queries-test.envia.com/"

    def _envia_default_branch_carrier(self) -> str:
        self.ensure_one()
        codes = self._envia_parse_carrier_codes(self.envia_default_carriers)
        return codes[0] if codes else "estafeta"

    def _envia_default_branch_carrier_id(self) -> int | bool:
        self.ensure_one()
        return self.env["envia.carrier"].search(
            [("code", "=", self._envia_default_branch_carrier())],
            limit=1,
        ).id
