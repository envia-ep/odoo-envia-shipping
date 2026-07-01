import logging
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EnviaIntegration(models.Model):
    _name = "envia.integration"
    _description = "Envia ECart Integration"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Integration User",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
    )
    state = fields.Selection(
        [
            ("draft", "Not Connected"),
            ("connected", "Connected"),
            ("error", "Error"),
        ],
        string="Status",
        default="draft",
        required=True,
    )
    store_url = fields.Char(
        string="Store URL",
        help="Public Odoo URL used by Envia. Defaults to web.base.url.",
    )
    odoo_api_key = fields.Char(
        string="Odoo API Key",
        copy=False,
        groups="base.group_system",
        help="Persistent API key generated for Envia. Stored once at creation.",
    )
    access_token = fields.Char(
        string="ECart Access Token",
        copy=False,
        groups="base.group_system",
    )
    ecart_store_name = fields.Char(string="Store Name", readonly=True)
    ecart_store_url = fields.Char(string="ECart Store URL", readonly=True)
    ecart_ecommerce = fields.Char(string="Platform", readonly=True)
    ecart_user_id = fields.Char(string="ECart User ID", readonly=True)
    integration_date = fields.Datetime(string="Connected On", readonly=True)
    error_message = fields.Text(string="Last Error", readonly=True)

    _sql_constraints = [
        (
            "company_unique",
            "unique(company_id)",
            "Only one Envia integration is allowed per company.",
        ),
    ]

    @api.model
    def _get_store_url(self):
        icp = self.env["ir.config_parameter"].sudo()
        configured_url = icp.get_param("envia_ecart.store_url")
        if configured_url:
            return configured_url.rstrip("/")
        return icp.get_param("web.base.url", "").rstrip("/")

    @api.model
    def _get_oauth_config(self):
        icp = self.env["ir.config_parameter"].sudo()
        return {
            "app_id": icp.get_param(
                "envia_ecart.app_id",
                "j4CVuDzGDiA2sxu0YYOYndiE4XkonsFb",
            ),
            "client_id": icp.get_param("envia_ecart.client_id", ""),
            "oauth_base_url": icp.get_param(
                "envia_ecart.oauth_base_url",
                "https://oauth-deve.herokuapp.com",
            ).rstrip("/"),
        }

    def _ensure_api_key(self):
        self.ensure_one()
        if self.odoo_api_key:
            return self.odoo_api_key

        api_key_name = f"Envia ECart - {self.company_id.name}"
        try:
            plaintext_key = (
                self.env["res.users.apikeys"]
                .sudo()
                .with_user(self.user_id)
                ._generate(None, api_key_name, False)
            )
        except AttributeError as exc:
            raise UserError(
                _(
                    "Your Odoo version does not support programmatic API key "
                    "generation. Please create a persistent API key manually "
                    "and set it on the integration record."
                )
            ) from exc
        except Exception as exc:
            _logger.exception("Failed to generate Envia API key")
            raise UserError(
                _("Could not generate a persistent API key: %s", str(exc))
            ) from exc

        self.sudo().write({"odoo_api_key": plaintext_key})
        return plaintext_key

    def _build_callback_url(self, store_url):
        self.ensure_one()
        db_name = self.env.cr.dbname
        params = {
            "db": db_name,
            "company": str(self.company_id.id),
            "user": str(self.user_id.id),
        }
        return f"{store_url}/envia/integration/callback?{urlencode(params)}"

    def _build_integration_url(self):
        self.ensure_one()
        store_url = (self.store_url or self._get_store_url()).rstrip("/")
        if not store_url:
            raise UserError(
                _(
                    "Store URL is not configured. Set System Parameter "
                    "'web.base.url' or 'envia_ecart.store_url'."
                )
            )

        user = self.user_id
        email = user.login or user.email
        if not email:
            raise UserError(_("The integration user must have a login or email."))

        oauth_config = self._get_oauth_config()
        if not oauth_config["app_id"]:
            raise UserError(_("Envia ECart App ID is not configured."))

        params = {
            "ecommerce": "odoo",
            "state": "fromPlugin",
            "origin": "odoo",
            "url": store_url,
            "database": self.env.cr.dbname,
            "email": email,
            "apiKey": self._ensure_api_key(),
            "callbackUrl": self._build_callback_url(store_url),
            "company": str(self.company_id.id),
            "user": str(self.user_id.id),
        }
        return f"{oauth_config['oauth_base_url']}/{oauth_config['app_id']}?{urlencode(params)}"

    def action_connect_envia(self):
        self.ensure_one()
        integration_url = self._build_integration_url()
        return {
            "type": "ir.actions.act_url",
            "url": integration_url,
            "target": "new",
        }

    def action_regenerate_api_key(self):
        self.ensure_one()
        self.sudo().write({"odoo_api_key": False})
        self._ensure_api_key()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("API Key Regenerated"),
                "message": _("A new persistent API key was generated for Envia."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_reset_integration(self):
        self.write(
            {
                "state": "draft",
                "access_token": False,
                "ecart_store_name": False,
                "ecart_store_url": False,
                "ecart_ecommerce": False,
                "ecart_user_id": False,
                "integration_date": False,
                "error_message": False,
            }
        )
