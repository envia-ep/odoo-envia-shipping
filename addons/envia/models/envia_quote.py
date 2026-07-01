from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EnviaQuote(models.Model):
    _name = "envia.quote"
    _description = "Envia Quote"
    _order = "create_date desc"

    name = fields.Char(default="New", required=True, copy=False)
    quote_id = fields.Char(string="External Quote ID", copy=False)
    sale_order_id = fields.Many2one("sale.order", ondelete="set null")
    picking_id = fields.Many2one("stock.picking", ondelete="set null")
    origin_partner_id = fields.Many2one("res.partner", string="Ship From", ondelete="set null")
    destination_partner_id = fields.Many2one("res.partner", string="Ship To", ondelete="set null")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    origin_postal_code = fields.Char(required=True)
    origin_country = fields.Char(required=True)
    origin_state = fields.Char()
    destination_postal_code = fields.Char(required=True)
    destination_country = fields.Char(required=True)
    destination_state = fields.Char()
    weight = fields.Float(required=True)
    length = fields.Float(required=True)
    width = fields.Float(required=True)
    height = fields.Float(required=True)
    content = fields.Char(required=True)
    declared_value = fields.Float()
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    carriers = fields.Char(default="all")
    valid_until = fields.Datetime()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("quoted", "Quoted"),
            ("expired", "Expired"),
            ("used", "Used"),
        ],
        default="draft",
    )
    service_ids = fields.One2many("envia.quote.service", "quote_id", string="Services")
    selected_service_id = fields.Many2one("envia.quote.service", string="Selected Service")
    shipment_ids = fields.One2many("envia.shipment", "quote_id", string="Shipments")

    @api.model
    def get_quotes_onboarding_data(self):
        onboarding = self.env.ref(
            "envia.onboarding_onboarding_envia_quotes",
            raise_if_not_found=False,
        )
        if not onboarding or onboarding.is_onboarding_closed:
            return False
        if onboarding.current_onboarding_state == "done":
            return False
        ob_vals = onboarding._prepare_rendering_values()
        return {
            "close_method": onboarding.panel_close_action_name,
            "steps": [
                {
                    "id": step.id,
                    "title": step.title,
                    "description": step.description,
                    "state": ob_vals["state"][step.id],
                    "action": step.panel_step_open_action_name,
                }
                for step in ob_vals["steps"]
            ],
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("envia.quote") or "New"
        records = super().create(vals_list)
        pending_companies = records.company_id.filtered("envia_quote_onboarding_pending")
        if pending_companies:
            pending_companies.envia_quote_onboarding_pending = False
        return records

    def action_open_create_shipment_wizard(self):
        self.ensure_one()
        self._check_quote_valid()
        if not self.selected_service_id:
            raise UserError(_("Select a carrier service before creating the shipment."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Generate Label"),
            "res_model": "envia.create.shipment.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_quote_id": self.id,
                "default_sale_order_id": self.sale_order_id.id,
                "default_picking_id": self.picking_id.id,
                "dialog_size": "extra-large",
            },
        }

    def _check_quote_valid(self):
        self.ensure_one()
        if self.valid_until and self.valid_until < fields.Datetime.now():
            self.state = "expired"
            raise UserError(_("This quote has expired. Request a new quote."))

    def _get_shipment_partners(self):
        self.ensure_one()
        origin = self.origin_partner_id
        if not origin:
            origin = self.company_id.envia_default_origin_partner_id or self.company_id.partner_id
        destination = self.destination_partner_id
        if not destination and self.picking_id:
            destination = self.picking_id.partner_id
        elif not destination and self.sale_order_id:
            destination = self.sale_order_id.partner_shipping_id
        if not origin:
            raise UserError(_("Origin address is missing on this quote."))
        if not destination:
            raise UserError(_("Destination address is missing on this quote."))
        return origin, destination

    def action_open_quote_wizard(self):
        return self.env["envia.quote.wizard"].action_open_quote_wizard()

    @api.model
    def create_from_api_response(self, response, values):
        quote = self.create(
            {
                **values,
                "quote_id": response.quote_id,
                "valid_until": self._parse_valid_until(response.valid_until),
                "state": "quoted",
            }
        )
        service_lines = []
        for service in response.services:
            service_lines.append(
                {
                    "quote_id": quote.id,
                    "service_id": str(service.service_id),
                    "carrier": service.carrier,
                    "carrier_name": service.carrier_name,
                    "service_name": service.service_name,
                    "price": service.price,
                    "currency_name": service.currency,
                    "estimated_delivery_days": service.estimated_delivery_days,
                    "max_weight": service.max_weight,
                    "restrictions": "\n".join(service.restrictions),
                    "additional_services_available": ", ".join(service.additional_services_available),
                }
            )
        self.env["envia.quote.service"].create(service_lines)
        return quote

    def _parse_valid_until(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value
        try:
            return fields.Datetime.to_datetime(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return False
