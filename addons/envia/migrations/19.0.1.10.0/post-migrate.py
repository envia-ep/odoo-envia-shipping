from odoo import SUPERUSER_ID, api


def migrate(cr, version) -> None:
    env = api.Environment(cr, SUPERUSER_ID, {})
    module = env["ir.module.module"].search([("name", "=", "envia")], limit=1)
    if not module:
        return
    module.with_context(overwrite=True)._update_translations(["es_419", "es_ES"])
