from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ecart_store_id = fields.Many2one(
        "ecart.store",
        string="Ecart Store",
        index=True,
        ondelete="set null",
    )
    ecart_order_id = fields.Char(string="Ecart Order ID", index=True)
    ecart_order_number = fields.Char(string="Ecart Order Number")
    ecart_status = fields.Char(string="Ecart Status")
    ecart_imported_at = fields.Datetime(string="Ecart Imported At", readonly=True)

    _ecart_order_store_unique = models.Constraint(
        "unique(ecart_store_id, ecart_order_id)",
        "This Ecart order was already imported for this store.",
    )
