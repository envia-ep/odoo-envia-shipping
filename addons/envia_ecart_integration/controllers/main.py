import base64
import hashlib
import hmac
import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class EnviaIntegrationController(http.Controller):
    @http.route(
        "/envia/integration/callback",
        type="http",
        auth="public",
        csrf=False,
        methods=["GET"],
    )
    def envia_integration_callback(self, **kwargs):
        access_token = kwargs.get("access_token")
        ecartapi_key = kwargs.get("ecartapi_key")
        company_id = kwargs.get("company")
        user_id = kwargs.get("user")

        if not access_token:
            return request.make_response(
                "Missing access_token.",
                headers=[("Content-Type", "text/plain")],
                status=400,
            )

        icp = request.env["ir.config_parameter"].sudo()
        app_id = icp.get_param(
            "envia_ecart.app_id",
            "j4CVuDzGDiA2sxu0YYOYndiE4XkonsFb",
        )
        client_id = icp.get_param("envia_ecart.client_id", "")

        if client_id and ecartapi_key:
            if not self._validate_ecartapi_key(
                app_id, client_id, access_token, ecartapi_key
            ):
                _logger.warning("Invalid ecartapi_key received on Envia callback")
                return request.make_response(
                    "Invalid integration signature.",
                    headers=[("Content-Type", "text/plain")],
                    status=403,
                )
        elif ecartapi_key and not client_id:
            _logger.warning(
                "ecartapi_key received but envia_ecart.client_id is not configured"
            )

        integration = self._find_integration(company_id)
        if not integration:
            return request.make_response(
                "Integration record not found for this company.",
                headers=[("Content-Type", "text/plain")],
                status=404,
            )

        values = {
            "state": "connected",
            "access_token": access_token,
            "ecart_store_name": kwargs.get("name"),
            "ecart_store_url": kwargs.get("url"),
            "ecart_ecommerce": kwargs.get("ecommerce"),
            "ecart_user_id": kwargs.get("userId"),
            "integration_date": fields.Datetime.now(),
            "error_message": False,
        }
        if user_id:
            try:
                values["user_id"] = int(user_id)
            except (TypeError, ValueError):
                pass

        integration.sudo().write(values)

        db_name = request.session.db or kwargs.get("db", "")
        redirect_url = (
            f"/web?db={db_name}#action=envia_ecart_integration.action_envia_integration"
        )
        return request.redirect(redirect_url)

    def _find_integration(self, company_id):
        EnviaIntegration = request.env["envia.integration"].sudo()
        if company_id:
            try:
                integration = EnviaIntegration.search(
                    [("company_id", "=", int(company_id))],
                    limit=1,
                )
                if integration:
                    return integration
            except (TypeError, ValueError):
                pass
        return EnviaIntegration.search([], limit=1)

    @staticmethod
    def _validate_ecartapi_key(app_id, client_id, access_token, ecartapi_key):
        base_string = f"{app_id}&{access_token}"
        digest = hmac.new(
            client_id.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_key = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(expected_key, ecartapi_key)
