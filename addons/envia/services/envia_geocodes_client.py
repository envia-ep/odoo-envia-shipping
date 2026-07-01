import logging
from typing import Any

import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GEOCODES_BASE_URL = "https://geocodes.envia.com/"


class EnviaGeocodesClient:
    def lookup_zipcode(self, country_code: str, zipcode: str) -> list[dict[str, Any]]:
        country_code = (country_code or "").strip().upper()
        zipcode = (zipcode or "").strip()
        if not country_code or not zipcode:
            return []
        url = f"{GEOCODES_BASE_URL}zipcode/{country_code}/{zipcode}"
        _logger.info("Envia Geocodes GET %s", url)
        try:
            response = requests.get(url, timeout=30)
        except requests.RequestException as error:
            raise UserError(_("Envia Geocodes connection error: %s") % error) from error
        if response.status_code == 404:
            return []
        if response.status_code >= 400:
            raise UserError(
                _("Envia Geocodes error (HTTP %(status)s).") % {"status": response.status_code}
            )
        body = response.json()
        if isinstance(body, list):
            return body
        data = body.get("data")
        return data if isinstance(data, list) else []
