from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    envia_ecart_app_id = fields.Char(
        string="Envia ECart App ID",
        config_parameter="envia_ecart.app_id",
        default="j4CVuDzGDiA2sxu0YYOYndiE4XkonsFb",
    )
    envia_ecart_client_id = fields.Char(
        string="Envia ECart Client ID",
        config_parameter="envia_ecart.client_id",
        help="Used to validate the ecartapi_key HMAC on the OAuth callback.",
    )
    envia_ecart_oauth_base_url = fields.Char(
        string="Envia OAuth Base URL",
        config_parameter="envia_ecart.oauth_base_url",
        default="https://oauth-deve.herokuapp.com",
    )
    envia_ecart_store_url = fields.Char(
        string="Envia Store URL Override",
        config_parameter="envia_ecart.store_url",
        help=(
            "Public URL of this Odoo instance for Envia. "
            "If empty, web.base.url is used."
        ),
    )
