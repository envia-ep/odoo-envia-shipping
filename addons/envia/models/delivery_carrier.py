from odoo import _, fields, models
from odoo.exceptions import UserError

from ..services.envia_official_adapter import EnviaOfficialAdapter
from ..services.payload_mapper import PayloadMapper, get_envia_adapter


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("envia", "Envia.com")],
        ondelete={"envia": "set default"},
    )

    def envia_rate_shipment(self, order):
        self.ensure_one()
        try:
            request = PayloadMapper.build_quote_request_from_sale_order(order)
            response = get_envia_adapter(order.company_id).quote(request)
            service = EnviaOfficialAdapter._pick_cheapest_service(response.services)
            if not service:
                return {
                    "success": False,
                    "price": 0.0,
                    "error_message": _("No Envia rates available for this order."),
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
                    order.date_order or fields.Date.context_today(self),
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
                "error_message": str(error),
                "warning_message": False,
            }
