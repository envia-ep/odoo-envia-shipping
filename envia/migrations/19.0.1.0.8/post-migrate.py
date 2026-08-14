def migrate(cr, version):
    """Labels are manual (Generate on DO); stop auto-send on Validate."""
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    carriers = env["delivery.carrier"].search([("delivery_type", "=", "envia")])
    carriers.write({"integration_level": "rate"})
    # Enable for quote wizard UX; picking Generate no longer depends on this flag.
    env["res.company"].search([]).write({"envia_enable_labels": True})
