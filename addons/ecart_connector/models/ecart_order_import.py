import logging
from typing import Any

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.ecart_connector.services.order_mapper import EcartOrderMapper

_logger = logging.getLogger(__name__)


class EcartOrderImport(models.AbstractModel):
    _name = "ecart.order.import"
    _description = "Ecart Order Import Service"

    @api.model
    def import_orders_for_store(self, store, manual: bool = True):
        store.ensure_one()
        params = self._build_import_params(store)
        client = store._get_ecart_client()
        mapper = EcartOrderMapper(self.env)
        imported_orders = self.env["sale.order"]
        page = 1
        max_pages = 20

        while page <= max_pages:
            request_params = dict(params)
            request_params["page"] = page
            body = client.list_orders(request_params)
            orders = self._extract_orders(body)
            if not orders:
                break

            for order_payload in orders:
                try:
                    with self.env.cr.savepoint():
                        sale_order = mapper.import_order_payload(store, order_payload)
                        imported_orders |= sale_order
                except UserError as error:
                    _logger.warning(
                        "Skipped Ecart order %s for store %s: %s",
                        order_payload.get("id"),
                        store.id,
                        error,
                    )

            if len(orders) < int(params.get("limit", 50)):
                break
            page += 1

        store.last_sync_at = fields.Datetime.now()
        return imported_orders

    @staticmethod
    def _extract_orders(body: dict[str, Any] | list) -> list[dict[str, Any]]:
        if isinstance(body, list):
            return body
        if isinstance(body, dict):
            for key in ("orders", "data", "results", "items"):
                value = body.get(key)
                if isinstance(value, list):
                    return value
            if body.get("id"):
                return [body]
        return []

    def _build_import_params(self, store):
        params = {
            "limit": 50,
            "status[ecartapi]": "paid",
            "fulfillmentStatus": "unfulfilled",
        }
        if store.last_sync_at:
            params["updatedAt[from]"] = fields.Datetime.to_string(store.last_sync_at)
        return params
