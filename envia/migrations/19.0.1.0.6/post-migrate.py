def migrate(cr, version):
    """Drop Envia-only tracking timeline (model + cron). Core URL is enough."""
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    cron = env.ref("envia.ir_cron_envia_tracking_sync", raise_if_not_found=False)
    if cron:
        cron.unlink()
    # Orphan table after model removal; safe if already gone.
    cr.execute("DROP TABLE IF EXISTS envia_tracking_event CASCADE")
