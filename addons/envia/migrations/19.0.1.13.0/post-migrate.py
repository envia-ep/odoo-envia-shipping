def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    icp = env["ir.config_parameter"].sudo()
    icp.set_param("envia.pending_plugin_setup", "")
    if not icp.get_param("envia.pending_plugin_setup_company_id"):
        icp.set_param(
            "envia.pending_plugin_setup_company_id",
            str(env.ref("base.main_company").id),
        )
