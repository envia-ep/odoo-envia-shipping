from odoo import fields, models


class EnviaTrackingEvent(models.Model):
    _name = "envia.tracking.event"
    _description = "Envia Tracking Event"
    _order = "event_timestamp desc, id desc"

    shipment_id = fields.Many2one("envia.shipment", required=True, ondelete="cascade")
    event_timestamp = fields.Datetime(string="Timestamp")
    location = fields.Char()
    description = fields.Text(required=True)
    status = fields.Char()
