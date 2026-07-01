from odoo import fields, models


class EnviaQuoteService(models.Model):
    _name = "envia.quote.service"
    _description = "Envia Quote Service Option"
    _order = "price asc"

    quote_id = fields.Many2one("envia.quote", required=True, ondelete="cascade")
    service_id = fields.Char(string="Service ID", required=True)
    carrier = fields.Char(required=True)
    carrier_name = fields.Char()
    service_name = fields.Char(required=True)
    price = fields.Float(required=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    currency_name = fields.Char()
    estimated_delivery_days = fields.Integer()
    max_weight = fields.Float()
    restrictions = fields.Text()
    additional_services_available = fields.Text()
    is_selected = fields.Boolean()

    def action_select_service(self):
        self.ensure_one()
        self.quote_id.service_ids.write({"is_selected": False})
        self.is_selected = True
        self.quote_id.write({"selected_service_id": self.id, "state": "quoted"})
        return True
