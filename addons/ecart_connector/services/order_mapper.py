import logging
from typing import Any

from odoo import _, api, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EcartOrderMapper:
    def __init__(self, env) -> None:
        self.env = env

    def import_order_payload(self, store, order_payload: dict[str, Any]):
        order_id = str(order_payload.get("id") or "")
        if not order_id:
            raise UserError(_("Ecart order payload is missing an id."))

        existing = self.env["sale.order"].search(
            [
                ("ecart_store_id", "=", store.id),
                ("ecart_order_id", "=", order_id),
            ],
            limit=1,
        )
        if existing:
            return existing

        partner = self._get_or_create_customer(order_payload)
        shipping_partner = self._get_or_create_address_partner(
            order_payload.get("shippingAddress") or {},
            partner,
            f"{partner.name} (Shipping)",
        )
        currency = self._resolve_currency(order_payload.get("currency"))

        order_vals = {
            "partner_id": partner.id,
            "partner_shipping_id": shipping_partner.id,
            "partner_invoice_id": partner.id,
            "company_id": store.company_id.id,
            "ecart_store_id": store.id,
            "ecart_order_id": order_id,
            "ecart_order_number": (
                order_payload.get("number")
                or order_payload.get("name")
                or order_id
            ),
            "ecart_status": self._extract_ecart_status(order_payload),
            "ecart_imported_at": fields.Datetime.now(),
            "origin": (
                f"Ecart:{store.ecommerce}/"
                f"{order_payload.get('number') or order_id}"
            ),
            "order_line": self._build_order_lines(store, order_payload, currency),
        }
        if currency:
            order_vals["currency_id"] = currency.id

        date_order = self._parse_datetime(
            (order_payload.get("dates") or {}).get("createdAt")
        )
        if date_order:
            order_vals["date_order"] = date_order

        sale_order = self.env["sale.order"].create(order_vals)
        if store.company_id.ecart_auto_confirm_orders:
            sale_order.action_confirm()
        return sale_order

    def _build_order_lines(self, store, order_payload, currency):
        lines = []
        items = order_payload.get("items") or []
        if not items:
            raise UserError(
                _("Ecart order %(order)s has no line items.")
                % {
                    "order": order_payload.get("number") or order_payload.get("id"),
                }
            )

        for item in items:
            product = self._resolve_product(store, item)
            quantity = float(item.get("quantity") or 1)
            price = float(item.get("price") or 0)
            line_vals = {
                "product_id": product.id,
                "product_uom_qty": quantity,
                "price_unit": price,
                "name": item.get("name") or product.display_name,
            }
            if currency:
                line_vals["currency_id"] = currency.id
            lines.append((0, 0, line_vals))
        return lines

    def _resolve_product(self, store, item):
        sku = (item.get("sku") or "").strip()
        product = self.env["product.product"]
        if sku:
            product = product.search([("default_code", "=", sku)], limit=1)
        if not product:
            product = store.company_id.ecart_fallback_product_id
        if not product:
            raise UserError(
                _("No product found for SKU %(sku)s and no fallback product is configured.")
                % {"sku": sku or _("(empty)")}
            )
        return product

    def _get_or_create_customer(self, order_payload):
        customer = order_payload.get("customer") or {}
        email = (
            (customer.get("email") or order_payload.get("email") or "")
            .strip()
        )
        name = self._format_name(
            customer.get("firstName"),
            customer.get("lastName"),
            email or _("Ecart Customer"),
        )
        partner = self.env["res.partner"]
        if email:
            partner = partner.search([("email", "=ilike", email)], limit=1)
        if not partner:
            partner = partner.create(
                {
                    "name": name,
                    "email": email or False,
                    "phone": customer.get("phone") or False,
                    "type": "contact",
                }
            )
        return partner

    def _get_or_create_address_partner(
        self, address_payload, parent_partner, label
    ):
        if not address_payload:
            return parent_partner

        country = self._resolve_country(address_payload.get("country"))
        state = self._resolve_state(country, address_payload.get("state"))
        partner_vals = {
            "name": label,
            "parent_id": parent_partner.id,
            "type": "delivery",
            "street": (
                address_payload.get("address1")
                or address_payload.get("street")
                or False
            ),
            "street2": address_payload.get("address2") or False,
            "city": address_payload.get("city") or False,
            "zip": (
                address_payload.get("postalCode")
                or address_payload.get("zip")
                or False
            ),
            "phone": address_payload.get("phone") or parent_partner.phone,
            "email": parent_partner.email,
            "country_id": country.id if country else False,
            "state_id": state.id if state else False,
        }
        existing = self.env["res.partner"].search(
            [
                ("parent_id", "=", parent_partner.id),
                ("type", "=", "delivery"),
                ("street", "=", partner_vals["street"]),
                ("zip", "=", partner_vals["zip"]),
            ],
            limit=1,
        )
        if existing:
            existing.write(partner_vals)
            return existing
        return self.env["res.partner"].create(partner_vals)

    def _resolve_country(self, country_code):
        if not country_code:
            return self.env["res.country"]
        return self.env["res.country"].search(
            [("code", "=", str(country_code).upper())],
            limit=1,
        )

    def _resolve_state(self, country, state_code):
        if not country or not state_code:
            return self.env["res.country.state"]
        return self.env["res.country.state"].search(
            [
                ("country_id", "=", country.id),
                ("code", "=", str(state_code).upper()),
            ],
            limit=1,
        )

    def _resolve_currency(self, currency_code):
        if not currency_code:
            return self.env.company.currency_id
        return self.env["res.currency"].search(
            [("name", "=", str(currency_code).upper())],
            limit=1,
        )

    @staticmethod
    def _extract_ecart_status(order_payload):
        status = order_payload.get("status") or {}
        if isinstance(status, dict):
            return status.get("ecartapi") or status.get("status") or False
        return str(status)

    @staticmethod
    def _format_name(first_name, last_name, fallback):
        parts = [part for part in (first_name, last_name) if part]
        return " ".join(parts) if parts else fallback

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return False
        from odoo.fields import Datetime

        try:
            return Datetime.to_datetime(value)
        except (ValueError, TypeError):
            return False
