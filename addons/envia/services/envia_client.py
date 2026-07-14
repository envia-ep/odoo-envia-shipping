import json
import logging
from typing import Any

import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EnviaApiError(UserError):
    """Raised when Envia API returns an error response."""


class EnviaClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: int = 60,
        *,
        use_bearer_auth: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.token = token
        self.timeout = timeout
        self.use_bearer_auth = use_bearer_auth

    def _headers(self) -> dict[str, str]:
        authorization = self.token
        if self.use_bearer_auth and not authorization.lower().startswith("bearer "):
            authorization = f"Bearer {authorization}"
        return {
            "Authorization": authorization,
            "Content-Type": "application/json",
        }

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any] | list[Any]:
        url = f"{self.base_url}{path.lstrip('/')}"
        _logger.info("Envia API POST %s", url)
        _logger.info("Envia API POST %s payload=%s", url, json.dumps(payload, ensure_ascii=False))
        try:
            response = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise UserError(_("Envia API connection error: %s") % error) from error

        if response.status_code in (401, 403):
            if not self.use_bearer_auth:
                raise UserError(
                    _(
                        "Envia OAuth session is invalid or expired. "
                        "Open Settings > Envia Shipping and click Refresh token."
                    )
                )
            raise UserError(_("Invalid Envia API token. Check Settings > Envia Shipping."))

        if response.status_code == 404 and not self.use_bearer_auth:
            raise UserError(
                _(
                    "Envia eshop quote endpoint was not found (HTTP 404). "
                    "Refresh the OAuth connection or contact Envia support."
                )
            )

        if response.status_code == 402:
            raise UserError(_("Insufficient Envia account balance."))

        try:
            body = response.json()
        except json.JSONDecodeError as error:
            raise UserError(
                _("Envia API returned invalid JSON (HTTP %s).") % response.status_code
            ) from error

        if response.status_code >= 400:
            message = self._response_error_message(body, response)
            error_code = body.get("error", "") if isinstance(body, dict) else ""
            if error_code == "INVALID_POSTAL_CODE":
                raise UserError(_("Invalid postal code: %s") % message)
            if error_code == "NO_RATES_AVAILABLE":
                raise UserError(_("No shipping services available for this route."))
            if error_code == "WEIGHT_EXCEEDS_LIMIT":
                raise UserError(_("Weight exceeds limit: %s") % message)
            raise EnviaApiError(_("Envia API error (%(status)s): %(message)s") % {
                "status": response.status_code,
                "message": message,
            })

        _logger.info("Envia API POST %s response=%s", url, json.dumps(body, ensure_ascii=False))
        return body

    @staticmethod
    def _response_error_message(body, response) -> str:
        if isinstance(body, dict):
            return body.get("message") or body.get("error") or response.text
        if isinstance(body, list) and body:
            first = body[0]
            if isinstance(first, dict):
                return first.get("message") or first.get("error") or response.text
        return response.text

    def get(
        self,
        path: str,
        *,
        base_url: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url_base = (base_url or self.base_url).rstrip("/") + "/"
        url = f"{url_base}{path.lstrip('/')}"
        _logger.info("Envia API GET %s params=%s", url, params)
        try:
            response = requests.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise UserError(_("Envia API connection error: %s") % error) from error

        if response.status_code in (401, 403):
            if not self.use_bearer_auth:
                raise UserError(
                    _(
                        "Envia OAuth session is invalid or expired. "
                        "Open Settings > Envia Shipping and click Refresh token."
                    )
                )
            raise UserError(_("Invalid Envia API token. Check Settings > Envia Shipping."))

        try:
            body = response.json()
        except json.JSONDecodeError as error:
            raise UserError(
                _("Envia API returned invalid JSON (HTTP %s).") % response.status_code
            ) from error

        if response.status_code >= 400:
            message = self._response_error_message(body, response)
            raise EnviaApiError(_("Envia API error (%(status)s): %(message)s") % {
                "status": response.status_code,
                "message": message,
            })

        return body

    def get_branches(
        self,
        *,
        queries_base_url: str,
        carrier: str,
        country_code: str,
        zipcode: str,
        search_type: int = 1,
        city: str | None = None,
        state_code: str | None = None,
    ) -> list[dict[str, Any]]:
        path = f"branches/{carrier}/{country_code}"
        params: dict[str, Any] = {
            "type": search_type,
            "zipcode": zipcode,
            "allBranch": False,
        }
        if city:
            params["locality"] = city
        if state_code:
            params["state"] = state_code
        body = self.get(path, base_url=queries_base_url, params=params)
        if isinstance(body, list):
            branches = body
        else:
            data = body.get("data")
            branches = data if isinstance(data, list) else []
        return self.refine_branches_near_zip(branches, zipcode)

    @staticmethod
    def refine_branches_near_zip(
        branches: list[dict[str, Any]],
        zipcode: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        zipcode = (zipcode or "").strip()
        if not zipcode or not branches:
            return branches

        def branch_zip(entry: dict[str, Any]) -> str:
            address = entry.get("address") or {}
            return (address.get("postalCode") or address.get("zipcode") or "").strip()

        def distance_value(entry: dict[str, Any]) -> float:
            try:
                return float(entry.get("distance") or 9999)
            except (TypeError, ValueError):
                return 9999.0

        exact = [entry for entry in branches if branch_zip(entry) == zipcode]
        if exact:
            return sorted(exact, key=distance_value)[:limit]

        for prefix_len in (5, 3):
            if len(zipcode) < prefix_len:
                continue
            prefix = zipcode[:prefix_len]
            by_prefix = [entry for entry in branches if branch_zip(entry).startswith(prefix)]
            if by_prefix:
                return sorted(by_prefix, key=distance_value)[:limit]

        nearby = sorted(branches, key=distance_value)
        if nearby and nearby[0].get("distance") is not None:
            within = [entry for entry in nearby if distance_value(entry) <= 15]
            return (within or nearby)[:limit]
        return nearby[:limit]

    def test_connection(self, *, queries_base_url: str, country_code: str = "MX") -> dict[str, Any]:
        """Validate the shipping token against Envia Queries API."""
        body = self.get(
            "carrier",
            base_url=queries_base_url,
            params={"country_code": country_code},
        )
        carriers = body.get("data")
        if not isinstance(carriers, list):
            raise UserError(_("Envia API returned an unexpected response format."))
        return body

    def get_binary(self, url: str) -> bytes:
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as error:
            raise UserError(_("Failed to download label: %s") % error) from error
        return response.content
