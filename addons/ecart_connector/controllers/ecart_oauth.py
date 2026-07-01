import logging

from odoo import http
from odoo.http import request

from odoo.addons.ecart_connector.services.ecart_client import EcartClient

_logger = logging.getLogger(__name__)


class EcartOAuthController(http.Controller):
    @http.route(
        "/ecart/oauth/callback",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        sitemap=False,
    )
    def oauth_callback(self, **kwargs):
        access_token = kwargs.get("access_token")
        ecartapi_key = kwargs.get("ecartapi_key")
        ecommerce = kwargs.get("ecommerce")
        store_url = kwargs.get("url")
        store_name = kwargs.get("name") or ecommerce or "Ecart Store"
        refresh_token = kwargs.get("refreshToken")
        ecart_user_id = kwargs.get("userId")
        state = kwargs.get("state")

        if not access_token or not ecartapi_key:
            return request.render(
                "ecart_connector.ecart_oauth_error",
                {"error_message": "Missing access_token or ecartapi_key in the callback URL."},
                status=400,
            )

        company = request.env["res.company"].sudo()._ecart_find_company_for_callback(
            kwargs.get("app_id"),
            state,
        )
        if not company or not company.ecart_app_id or not company.ecart_client_id:
            return request.render(
                "ecart_connector.ecart_oauth_error",
                {"error_message": "No company is configured with Ecart credentials."},
                status=400,
            )

        if not EcartClient.validate_ecartapi_key(
            company.ecart_app_id,
            access_token,
            company.ecart_client_id,
            ecartapi_key,
        ):
            _logger.warning("Invalid ecartapi_key for company %s", company.id)
            return request.render(
                "ecart_connector.ecart_oauth_error",
                {"error_message": "Invalid Ecart integration signature."},
                status=403,
            )

        store_model = request.env["ecart.store"].sudo()
        existing = store_model.search(
            [
                ("company_id", "=", company.id),
                ("store_url", "=", store_url or False),
                ("ecommerce", "=", ecommerce or False),
            ],
            limit=1,
        )
        values = {
            "store_name": store_name,
            "store_url": store_url,
            "ecommerce": ecommerce or "unknown",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "ecart_user_id": ecart_user_id,
            "company_id": company.id,
            "active": True,
        }
        if existing:
            existing.write(values)
            store = existing
        else:
            store = store_model.create(values)

        return request.redirect(
            f"/web#action=ecart_connector.action_ecart_store&id={store.id}&view_type=form"
        )
