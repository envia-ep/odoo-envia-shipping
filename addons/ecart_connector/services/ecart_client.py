import base64
import hashlib
import hmac
import logging
from typing import Any

import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EcartApiError(UserError):
    """Raised when Ecart API returns an error response."""


class EcartClient:
    def __init__(self, base_url: str, access_token: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.access_token = access_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path.lstrip('/')}"
        _logger.info("Ecart API GET %s", url)
        try:
            response = requests.get(
                url,
                headers=self._headers(),
                params=params or {},
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise UserError(_("Ecart API connection error: %s") % error) from error

        if response.status_code in (401, 403):
            raise UserError(_("Invalid Ecart store access token."))
        if response.status_code == 429:
            raise UserError(_("Ecart API rate limit exceeded. Retry later."))

        try:
            body = response.json()
        except ValueError as error:
            raise UserError(
                _("Ecart API returned invalid JSON (HTTP %s).") % response.status_code
            ) from error

        if response.status_code >= 400:
            message = body.get("message") or body.get("error") or response.text
            raise EcartApiError(
                _("Ecart API error (%(status)s): %(message)s")
                % {"status": response.status_code, "message": message}
            )

        return body

    def list_orders(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.get("api/v2/orders", params=params)

    def count_orders(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.get("api/v2/orders/count", params=params)

    def get_order(self, order_id: str) -> dict[str, Any]:
        return self.get(f"api/v2/orders/{order_id}")

    @staticmethod
    def validate_ecartapi_key(
        app_id: str,
        access_token: str,
        client_id: str,
        ecartapi_key: str,
    ) -> bool:
        if not all([app_id, access_token, client_id, ecartapi_key]):
            return False
        base_string = f"{app_id}&{access_token}"
        digest = hmac.new(
            client_id.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(expected, ecartapi_key)
