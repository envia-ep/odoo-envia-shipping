from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    envia_quote_ids = fields.One2many("envia.quote", "sale_order_id", string="Envia Quotes")
    envia_shipment_ids = fields.One2many("envia.shipment", "sale_order_id", string="Envia Shipments")
    envia_quote_count = fields.Integer(compute="_compute_envia_counts")
    envia_shipment_count = fields.Integer(compute="_compute_envia_counts")
    envia_can_create_shipment = fields.Boolean(compute="_compute_envia_can_create_shipment")
    envia_status = fields.Selection(
        [
            ("none", "No Envia activity"),
            ("quoted", "Rate selected"),
            ("shipped", "Label created"),
        ],
        compute="_compute_envia_status",
        string="Envia Status",
    )
    envia_summary = fields.Char(compute="_compute_envia_status")

    def _compute_envia_counts(self):
        for order in self:
            order.envia_quote_count = len(order.envia_quote_ids)
            order.envia_shipment_count = len(order.envia_shipment_ids)

    def _compute_envia_can_create_shipment(self):
        for order in self:
            order.envia_can_create_shipment = bool(
                order.envia_quote_ids.filtered(
                    lambda quote: quote.state == "quoted" and quote.selected_service_id
                )
            )

    def _compute_envia_status(self):
        for order in self:
            shipment = order.envia_shipment_ids[:1]
            quote = order.envia_quote_ids.filtered(
                lambda item: item.state == "quoted" and item.selected_service_id
            )[:1]
            if shipment:
                order.envia_status = "shipped"
                order.envia_summary = _(
                    "Envia label created: %(tracking)s · %(carrier)s",
                    tracking=shipment.tracking_number or shipment.name,
                    carrier=shipment.carrier_name or shipment.carrier or _("Carrier"),
                )
            elif quote:
                service = quote.selected_service_id
                order.envia_status = "quoted"
                order.envia_summary = _(
                    "Envia rate selected: %(carrier)s · %(service)s · %(price).2f %(currency)s",
                    carrier=service.carrier_name or service.carrier,
                    service=service.service_name,
                    price=service.price,
                    currency=service.currency_name or order.currency_id.name,
                )
            else:
                order.envia_status = "none"
                order.envia_summary = False

    def action_open_envia_quote_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Ship with Envia"),
            "res_model": "envia.quote.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
            "context": {
                "default_sale_order_id": self.id,
                "default_destination_partner_id": self.partner_shipping_id.id,
            },
        }

    def action_view_envia_quotes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Envia Quotes"),
            "res_model": "envia.quote",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", self.id)],
        }

    def action_view_envia_shipments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Envia Shipments"),
            "res_model": "envia.shipment",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", self.id)],
        }

    def action_create_envia_shipment(self):
        self.ensure_one()
        quote = self.envia_quote_ids.filtered(
            lambda quote: quote.state == "quoted" and quote.selected_service_id
        )[:1]
        if not quote:
            raise UserError(
                _("Get Envia rates first and select a carrier before generating the label.")
            )
        return quote.action_open_create_shipment_wizard()
