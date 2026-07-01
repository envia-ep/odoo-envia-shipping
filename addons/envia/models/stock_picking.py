from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    envia_quote_ids = fields.One2many("envia.quote", "picking_id", string="Envia Quotes")
    envia_shipment_ids = fields.One2many("envia.shipment", "picking_id", string="Envia Shipments")
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
        for picking in self:
            picking.envia_quote_count = len(picking.envia_quote_ids)
            picking.envia_shipment_count = len(picking.envia_shipment_ids)

    def _compute_envia_can_create_shipment(self):
        for picking in self:
            quote = picking.envia_quote_ids.filtered(
                lambda quote: quote.state == "quoted" and quote.selected_service_id
            )[:1]
            if not quote and picking.sale_id:
                quote = picking.sale_id.envia_quote_ids.filtered(
                    lambda quote: quote.state == "quoted" and quote.selected_service_id
                )[:1]
            picking.envia_can_create_shipment = bool(quote)

    def _compute_envia_status(self):
        for picking in self:
            shipment = picking.envia_shipment_ids[:1]
            quote = picking.envia_quote_ids.filtered(
                lambda item: item.state == "quoted" and item.selected_service_id
            )[:1]
            if not quote and picking.sale_id:
                quote = picking.sale_id.envia_quote_ids.filtered(
                    lambda item: item.state == "quoted" and item.selected_service_id
                )[:1]
            if shipment:
                picking.envia_status = "shipped"
                picking.envia_summary = _(
                    "Envia label created: %(tracking)s · %(carrier)s",
                    tracking=shipment.tracking_number or shipment.name,
                    carrier=shipment.carrier_name or shipment.carrier or _("Carrier"),
                )
            elif quote:
                service = quote.selected_service_id
                picking.envia_summary = _(
                    "Envia rate selected: %(carrier)s · %(service)s · %(price).2f %(currency)s",
                    carrier=service.carrier_name or service.carrier,
                    service=service.service_name,
                    price=service.price,
                    currency=service.currency_name or picking.company_id.currency_id.name,
                )
                picking.envia_status = "quoted"
            else:
                picking.envia_status = "none"
                picking.envia_summary = False

    def action_open_envia_quote_wizard(self):
        self.ensure_one()
        sale_order = self.sale_id
        return {
            "type": "ir.actions.act_window",
            "name": _("Ship with Envia"),
            "res_model": "envia.quote.wizard",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_picking_id": self.id,
                "default_sale_order_id": sale_order.id if sale_order else False,
                "default_destination_partner_id": self.partner_id.id,
            },
        }

    def action_view_envia_quotes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Envia Quotes"),
            "res_model": "envia.quote",
            "view_mode": "list,form",
            "domain": [("picking_id", "=", self.id)],
        }

    def action_view_envia_shipments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Envia Shipments"),
            "res_model": "envia.shipment",
            "view_mode": "list,form",
            "domain": [("picking_id", "=", self.id)],
        }

    def action_create_envia_shipment(self):
        self.ensure_one()
        quote = self.envia_quote_ids.filtered(
            lambda quote: quote.state == "quoted" and quote.selected_service_id
        )[:1]
        if not quote and self.sale_id:
            quote = self.sale_id.envia_quote_ids.filtered(
                lambda quote: quote.state == "quoted" and quote.selected_service_id
            )[:1]
        if not quote:
            raise UserError(
                _("Get Envia rates first and select a carrier before generating the label.")
            )
        return quote.with_context(default_picking_id=self.id).action_open_create_shipment_wizard()
