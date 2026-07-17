import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services.dto import CreateShipmentRequest, TrackRequest
from ..services.envia_client import EnviaClient
from ..services.envia_official_adapter import EnviaOfficialAdapter
from ..services.payload_mapper import PayloadMapper, get_envia_adapter

_logger = logging.getLogger(__name__)


class EnviaShipment(models.Model):
    _name = "envia.shipment"
    _description = "Envia Shipment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(default="New", required=True, copy=False)
    quote_id = fields.Many2one("envia.quote", ondelete="set null")
    selected_service_id = fields.Many2one("envia.quote.service")
    sale_order_id = fields.Many2one("sale.order", ondelete="set null")
    picking_id = fields.Many2one("stock.picking", ondelete="set null")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    external_shipment_id = fields.Char(string="External Shipment ID")
    tracking_number = fields.Char(tracking=True)
    carrier = fields.Char()
    carrier_name = fields.Char()
    service_name = fields.Char()
    status = fields.Char(tracking=True)
    status_description = fields.Text()
    label_url = fields.Char()
    label_attachment_id = fields.Many2one("ir.attachment", string="Label PDF")
    pricing_total = fields.Float()
    pricing_currency_id = fields.Many2one("res.currency")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("created", "Created"),
            ("in_transit", "In Transit"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )
    tracking_event_ids = fields.One2many("envia.tracking.event", "shipment_id")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("envia.shipment") or "New"
        return super().create(vals_list)

    @api.model
    def _get_envia_adapter(self, company):
        return get_envia_adapter(company)

    def action_track_shipment(self):
        for shipment in self:
            shipment._sync_tracking()
        return True

    def action_open_label(self):
        self.ensure_one()
        if self.label_attachment_id:
            return {
                "type": "ir.actions.act_url",
                "url": f"/web/content/{self.label_attachment_id.id}?download=true",
                "target": "self",
            }
        if self.label_url:
            return {
                "type": "ir.actions.act_url",
                "url": self.label_url,
                "target": "new",
            }
        raise UserError(_("No label is available for this shipment yet."))

    def _sync_tracking(self):
        self.ensure_one()
        if not self.tracking_number:
            raise UserError(_("This shipment has no tracking number."))
        adapter = self._get_envia_adapter(self.company_id)
        response = adapter.track(TrackRequest(tracking_numbers=[self.tracking_number], carrier=self.carrier))
        if not response.results:
            return
        result = response.results[0]
        self.write(
            {
                "status": result.status,
                "state": self._map_tracking_state(result.status),
            }
        )
        self._replace_tracking_events(result.events)

    def _replace_tracking_events(self, events):
        self.tracking_event_ids.unlink()
        event_vals = []
        for event in events:
            event_vals.append(
                {
                    "shipment_id": self.id,
                    "event_timestamp": self._parse_event_timestamp(event.timestamp),
                    "location": event.location,
                    "description": event.description,
                    "status": event.status,
                }
            )
        if event_vals:
            self.env["envia.tracking.event"].create(event_vals)

    @staticmethod
    def _parse_event_timestamp(value):
        if not value:
            return False
        try:
            return fields.Datetime.to_datetime(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _map_tracking_state(status: str) -> str:
        normalized = (status or "").lower()
        if "deliver" in normalized:
            return "delivered"
        if "transit" in normalized or "picked" in normalized or "route" in normalized:
            return "in_transit"
        if "cancel" in normalized:
            return "cancelled"
        return "created"

    def _download_label_attachment(self, label_url: str):
        self.ensure_one()
        if not label_url:
            return
        token = self.company_id._envia_get_shipping_api_token()
        client = EnviaClient(self.company_id._envia_get_base_url(), token or "")
        content = client.get_binary(label_url)
        attachment = self.env["ir.attachment"].create(
            {
                "name": f"{self.tracking_number or self.name}_label.pdf",
                "type": "binary",
                "datas": base64.b64encode(content),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/pdf",
            }
        )
        self.label_attachment_id = attachment.id

    @api.model
    def create_from_api_response(self, response, quote, picking=None):
        currency = False
        if response.pricing_currency:
            currency = self.env["res.currency"].search(
                [("name", "=", response.pricing_currency)], limit=1
            )
        shipment = self.create(
            {
                "quote_id": quote.id,
                "selected_service_id": quote.selected_service_id.id,
                "sale_order_id": quote.sale_order_id.id,
                "picking_id": picking.id if picking else quote.picking_id.id,
                "external_shipment_id": str(response.shipment_id) if response.shipment_id else False,
                "tracking_number": response.tracking_number,
                "carrier": response.carrier,
                "carrier_name": response.carrier_name,
                "service_name": response.service,
                "status": response.status,
                "status_description": response.status_description,
                "label_url": response.label_url,
                "pricing_total": response.pricing_total,
                "pricing_currency_id": currency.id if currency else False,
                "state": "created",
            }
        )
        if response.label_url:
            shipment._download_label_attachment(response.label_url)
        if shipment.picking_id and response.tracking_number:
            if hasattr(shipment.picking_id, "carrier_tracking_ref"):
                shipment.picking_id.carrier_tracking_ref = response.tracking_number
        quote.state = "used"
        return shipment

    @api.model
    def _cron_sync_tracking(self):
        shipments = self.search(
            [
                ("state", "in", ["created", "in_transit"]),
                ("tracking_number", "!=", False),
            ]
        )
        for shipment in shipments:
            try:
                shipment._sync_tracking()
            except UserError as error:
                _logger.warning("Tracking sync failed for %s: %s", shipment.name, error)
            except Exception as error:
                _logger.exception("Unexpected tracking sync failure for %s", shipment.name)

    @api.model
    def action_create_shipment_from_quote(self, quote):
        quote._validate_label_generation()
        selected = quote.selected_service_id
        sale_order = quote.sale_order_id
        picking = quote.picking_id or (sale_order.picking_ids[:1] if sale_order else False)
        mapper = PayloadMapper()
        request = CreateShipmentRequest(
            quote_id=quote.quote_id,
            service_id=selected.service_id,
            origin_contact=quote._build_shipment_contact("origin"),
            destination_contact=quote._build_shipment_contact("destination"),
            items=mapper.sale_lines_to_items(sale_order) if sale_order else [],
            order_reference=sale_order.name if sale_order else quote.name,
            print_format=quote.company_id.envia_label_format,
            print_size=quote.company_id.envia_label_size,
            carrier=selected.carrier,
            service_name=selected.service_name,
            package_weight=quote.weight,
            package_content=quote.content,
            weight_unit=PayloadMapper.envia_weight_unit(quote.env),
        )
        expected_drop_off = EnviaOfficialAdapter._expected_drop_off(
            request.origin_contact,
            request.destination_contact,
        )
        if (
            expected_drop_off is not None
            and selected.drop_off
            and selected.drop_off != expected_drop_off
        ):
            raise UserError(
                _(
                    "The selected rate is not valid for this pickup route. "
                    "Reload branches and generate the label again."
                )
            )
        adapter = self._get_envia_adapter(quote.company_id)
        response = adapter.create_shipment(request)
        return self.create_from_api_response(response, quote, picking=picking)
