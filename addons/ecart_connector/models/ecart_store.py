from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.ecart_connector.services.ecart_client import EcartClient


class EcartStore(models.Model):
    _name = "ecart.store"
    _description = "Ecart Connected Store"
    _order = "store_name, id"

    name = fields.Char(compute="_compute_name", store=True)
    store_name = fields.Char(required=True)
    store_url = fields.Char(string="Store URL")
    ecommerce = fields.Char(string="Ecommerce Platform", required=True)
    access_token = fields.Char(required=True, groups="base.group_system")
    refresh_token = fields.Char(groups="base.group_system")
    ecart_user_id = fields.Char(string="Ecart User ID")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one("res.partner", string="Linked Customer")
    active = fields.Boolean(default=True)
    last_sync_at = fields.Datetime(readonly=True)
    sale_order_ids = fields.One2many(
        "sale.order",
        "ecart_store_id",
        string="Imported Orders",
    )
    sale_order_count = fields.Integer(compute="_compute_sale_order_count")

    _ecart_store_company_url_unique = models.Constraint(
        "unique(company_id, store_url, ecommerce)",
        "This store is already connected for this company.",
    )

    @api.depends("store_name", "ecommerce")
    def _compute_name(self):
        for store in self:
            platform = store.ecommerce or _("Store")
            store.name = f"{store.store_name or platform} ({platform})"

    def _compute_sale_order_count(self):
        grouped = self.env["sale.order"].read_group(
            [("ecart_store_id", "in", self.ids)],
            ["ecart_store_id"],
            ["ecart_store_id"],
        )
        counts = {
            row["ecart_store_id"][0]: row["ecart_store_id_count"]
            for row in grouped
        }
        for store in self:
            store.sale_order_count = counts.get(store.id, 0)

    def _get_ecart_client(self) -> EcartClient:
        self.ensure_one()
        if not self.access_token:
            raise UserError(_("This store has no access token."))
        return EcartClient(
            self.company_id._ecart_get_base_url(),
            self.access_token,
        )

    def action_test_connection(self):
        self.ensure_one()
        body = self._get_ecart_client().count_orders()
        count = body.get("count") if isinstance(body, dict) else body
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection successful"),
                "message": _("Ecart store is reachable. Orders count: %s")
                % (count if count is not None else _("OK")),
                "type": "success",
                "sticky": False,
            },
        }

    def action_import_orders(self):
        self.ensure_one()
        imported = self.env["ecart.order.import"].import_orders_for_store(self)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Import completed"),
                "message": _("Imported %(count)s order(s).")
                % {"count": len(imported)},
                "type": "success",
                "sticky": False,
            },
        }

    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Imported Orders"),
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("ecart_store_id", "=", self.id)],
        }

    @api.model
    def cron_import_orders(self):
        stores = self.search([("active", "=", True)])
        for store in stores:
            try:
                self.env["ecart.order.import"].import_orders_for_store(store)
            except UserError:
                continue
