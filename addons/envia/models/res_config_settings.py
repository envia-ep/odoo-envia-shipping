from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services.envia_client import EnviaClient
from ..services.envia_integration_callback import build_callback_url, get_integration_database_name
from ..services.envia_oauth_client import EnviaOauthClient
from ..services.envia_plugin_setup import (
    clear_pending_setup,
    generate_integration_credentials,
    get_envia_module_version,
    normalize_envia_plugin_version,
)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    envia_environment = fields.Selection(related="company_id.envia_environment", readonly=False)
    envia_api_token = fields.Char(related="company_id.envia_api_token", readonly=True)
    envia_base_url = fields.Char(related="company_id.envia_base_url", readonly=False)
    envia_default_carriers = fields.Char(related="company_id.envia_default_carriers", readonly=True)
    envia_default_carrier_ids = fields.Many2many(related="company_id.envia_default_carrier_ids", readonly=False)
    envia_default_origin_partner_id = fields.Many2one(
        related="company_id.envia_default_origin_partner_id",
        readonly=False,
    )
    envia_label_format = fields.Selection(related="company_id.envia_label_format", readonly=False)
    envia_label_size = fields.Selection(related="company_id.envia_label_size", readonly=False)
    envia_effective_base_url = fields.Char(
        string="Active endpoint",
        compute="_compute_envia_settings_display",
    )
    envia_is_sandbox = fields.Boolean(compute="_compute_envia_settings_display")
    envia_is_production = fields.Boolean(compute="_compute_envia_settings_display")
    envia_has_api_token = fields.Boolean(compute="_compute_envia_settings_display")
    envia_oauth_connected = fields.Boolean(related="company_id.envia_oauth_connected", readonly=True)
    envia_plugin_version = fields.Char(related="company_id.envia_plugin_version", readonly=True)
    envia_plugin_version_display = fields.Char(
        string="Envia Plugin Version Display",
        compute="_compute_envia_plugin_version_display",
        readonly=True,
    )
    envia_integration_api_key = fields.Char(
        string="Envia Integration API Key",
        compute="_compute_envia_integration_api_key",
        readonly=True,
    )
    envia_api_token_display = fields.Char(
        string="Envia Shipping API Token (stored)",
        compute="_compute_envia_api_token_display",
        readonly=True,
    )
    envia_oauth_integration_url = fields.Char(
        string="OAuth Integration URL",
        config_parameter="envia.oauth_integration_url",
    )
    envia_oauth_popup_url = fields.Char(
        string="OAuth Popup URL",
        config_parameter="envia.oauth_popup_url",
    )
    envia_oauth_use_sized_popup = fields.Boolean(
        string="Open Envia.com in a sized pop-up window",
        config_parameter="envia.oauth_use_sized_popup",
        help=(
            "When disabled (default), Envia.com opens in a new browser tab. "
            "When enabled, opens a smaller pop-up window that may require "
            "allowing pop-ups in the browser."
        ),
    )
    envia_eshop_test_url = fields.Char(
        string="Eshop Test URL",
        config_parameter="envia.eshop_test_url",
    )
    envia_eshop_accesses_me_url = fields.Char(
        string="Eshop Accesses Me URL",
        config_parameter="envia.eshop_accesses_me_url",
    )
    envia_integration_callback_url = fields.Char(
        string="Integration Callback URL",
        compute="_compute_envia_integration_callback_url",
        readonly=True,
    )
    envia_integration_database_name = fields.Char(
        string="Odoo Database Name",
        compute="_compute_envia_integration_database_name",
        readonly=True,
    )
    envia_shop_id = fields.Char(related="company_id.envia_shop_id", readonly=True)
    envia_integration_info_display = fields.Char(
        string="Integration Info",
        compute="_compute_envia_integration_info_display",
        readonly=True,
    )

    @api.depends(
        "envia_oauth_connected",
        "envia_plugin_version",
        "envia_shop_id",
    )
    def _compute_envia_integration_info_display(self) -> None:
        for record in self:
            if not record.envia_oauth_connected:
                record.envia_integration_info_display = False
                continue
            version = (
                normalize_envia_plugin_version(record.envia_plugin_version)
                or get_envia_module_version(record.env)
            )
            store_id = (record.envia_shop_id or "").strip() or "—"
            record.envia_integration_info_display = (
                f"Version: {version} | Origin: Odoo | StoreID: {store_id}"
            )

    @api.depends_context("uid")
    def _compute_envia_integration_callback_url(self) -> None:
        for record in self:
            record.envia_integration_callback_url = build_callback_url(record.env)

    @api.depends_context("uid")
    def _compute_envia_integration_database_name(self) -> None:
        for record in self:
            record.envia_integration_database_name = get_integration_database_name(record.env)

    @api.depends(
        "envia_environment",
        "envia_api_token",
        "envia_base_url",
        "company_id",
    )
    def _compute_envia_settings_display(self) -> None:
        for record in self:
            company = record.company_id
            record.envia_effective_base_url = company._envia_get_base_url() if company else ""
            record.envia_is_sandbox = record.envia_environment == "sandbox"
            record.envia_is_production = record.envia_environment == "production"
            record.envia_has_api_token = record.company_id._envia_is_shipping_api_configured()

    @api.depends(
        "envia_oauth_connected",
        "envia_plugin_version",
        "company_id.envia_oauth_access_token",
    )
    def _compute_envia_plugin_version_display(self) -> None:
        for record in self:
            if not record.envia_oauth_connected:
                record.envia_plugin_version_display = False
                continue

            version = normalize_envia_plugin_version(record.envia_plugin_version)
            if version:
                record.envia_plugin_version_display = version
            elif not record.company_id.envia_oauth_access_token:
                record.envia_plugin_version_display = _("Not synced — click Refresh token")
            else:
                record.envia_plugin_version_display = get_envia_module_version(record.env)

    @api.depends("company_id.envia_integration_api_key")
    def _compute_envia_integration_api_key(self) -> None:
        for record in self:
            if record.env.user.has_group("base.group_system"):
                record.envia_integration_api_key = record.company_id.envia_integration_api_key
            else:
                record.envia_integration_api_key = False

    @api.depends("company_id.envia_api_token")
    def _compute_envia_api_token_display(self) -> None:
        for record in self:
            if record.env.user.has_group("base.group_system"):
                record.envia_api_token_display = record.company_id.envia_api_token
            else:
                record.envia_api_token_display = False

    def action_generate_envia_integration_api_key(self):
        self.ensure_one()
        if not self.env.user.has_group("base.group_system"):
            raise UserError(_("Only administrators can generate the Envia integration API key."))
        credentials = generate_integration_credentials(self.env, self.company_id)
        self.company_id.envia_integration_api_key = credentials["api_key"]
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("API key generated"),
                "message": _(
                    "Copy the Odoo API key below and share it with Envia.com for the "
                    "integration callback."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def set_values(self):
        super().set_values()
        for settings in self:
            if settings.company_id._envia_is_shipping_api_configured():
                clear_pending_setup(self.env)

    @api.model
    def get_envia_adapter(self):
        company = self.env.company
        return self.env["envia.shipment"]._get_envia_adapter(company)

    def action_test_envia_connection(self):
        self.ensure_one()
        company = self.company_id
        token = company._envia_get_shipping_api_token()
        if not token:
            raise UserError(
                _(
                    "Paste your Envia shipping API token in Settings > Envia Shipping > "
                    "API Connection. Sandbox tokens come from "
                    "https://shipping-test.envia.com/settings/developers"
                )
            )
        country_code = company.country_id.code or "MX"
        body = EnviaClient(
            company._envia_get_base_url(),
            token,
        ).test_connection(
            queries_base_url=company._envia_get_queries_base_url(),
            country_code=country_code,
        )
        carrier_count = len(body.get("data") or [])
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection successful"),
                "message": _(
                    "Envia accepted the token for %(country)s and returned "
                    "%(count)s active carrier(s)."
                )
                % {"country": country_code, "count": carrier_count},
                "type": "success",
                "sticky": False,
            },
        }

    def action_load_envia_demo_data(self):
        self.ensure_one()
        return self.company_id.action_load_envia_demo_data()

    def action_open_envia_plugin_connect_wizard(self):
        self.ensure_one()
        return self.env["envia.plugin.connect.wizard"].action_open_connect_wizard()
