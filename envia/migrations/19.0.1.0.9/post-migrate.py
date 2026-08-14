def migrate(cr, version):
    """Ensure Generate Envia Label is usable without hunting Settings flags."""
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.company"].search([("envia_enable_labels", "=", False)]).write(
        {"envia_enable_labels": True}
    )
