from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.http import request

from ..services.payload_mapper import PayloadMapper, get_envia_adapter
from ..services.website_pickup import WebsitePickupService


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("envia", "Envia.com")],
        ondelete={"envia": "set default"},
    )
    envia_use_locations = fields.Boolean(
        string="Envia Pickup Locations",
        compute="_compute_envia_use_locations",
        help="Native pickup block stays off; Envia Ship/Pickup panel owns website UX.",
    )

    @api.depends("delivery_type", "company_id.envia_enable_branches")
    def _compute_envia_use_locations(self):
        # Custom Ship|Pickup panel owns the UX; keep native pickup block off.
        for carrier in self:
            carrier.envia_use_locations = False

    def envia_rate_shipment(self, order):
        """Return Odoo delivery rate dict for delivery_type=envia (rate-only)."""
        self.ensure_one()
        quote = order._get_active_envia_quote()
        if quote and quote.selected_service_id:
            price = order._envia_shipping_unit_price(quote)
            return {
                "success": True,
                "price": price,
                "error_message": False,
                "warning_message": False,
            }
        try:
            request = PayloadMapper.build_quote_request_from_sale_order(order)
            adapter = get_envia_adapter(order.company_id)
            response = adapter.quote(request)
            service = adapter.pick_cheapest_service(response.services)
            if not service:
                return {
                    "success": False,
                    "price": 0.0,
                    "error_message": _(
                        "No Envia rates available for this order."
                    ),
                    "warning_message": False,
                }
            price = service.price
            rate_currency = self.env["res.currency"].search(
                [("name", "=", service.currency)],
                limit=1,
            )
            if rate_currency and rate_currency != order.currency_id:
                price = rate_currency._convert(
                    price,
                    order.currency_id,
                    order.company_id,
                    fields.Date.context_today(self),
                )
            warning = False
            if len(response.services) > 1:
                warning = _(
                    "Cheapest Envia rate: %(carrier)s - %(service)s",
                    carrier=service.carrier_name,
                    service=service.service_name,
                )
            return {
                "success": True,
                "price": price,
                "error_message": False,
                "warning_message": warning,
            }
        except UserError as error:
            return {
                "success": False,
                "price": 0.0,
                # Keep translated Lazy string from UserError (not str()).
                "error_message": error.args[0] if error.args else error,
                "warning_message": False,
            }

    def _envia_get_close_locations(self, partner_address, **kwargs):
        """Pickup points for the native Website location selector (list + Leaflet)."""
        self.ensure_one()
        order = request.cart
        if not order:
            return []
        try:
            options = WebsitePickupService(self.env).list_pickup_options(order.sudo())
        except UserError:
            return []
        return [
            {
                "id": option["id"],
                "name": option.get("name") or option.get("branch_code"),
                "street": option.get("street") or option.get("address") or "",
                "city": option.get("city") or "",
                "zip_code": option.get("zip") or "",
                "state": option.get("state_code") or "",
                "country_code": option.get("country_code") or "",
                "latitude": option.get("lat") or 0.0,
                "longitude": option.get("lng") or 0.0,
                "additional_data": {"envia_option": option},
                "opening_hours": {},
            }
            for option in options
        ]
