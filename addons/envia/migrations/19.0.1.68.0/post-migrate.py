from odoo.addons.envia.services.envia_plugin_setup import PENDING_SETUP_PARAM


def migrate(cr, version):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT 1
              FROM res_company
             WHERE COALESCE(TRIM(envia_api_token), '') <> ''
        )
        """
    )
    if cr.fetchone()[0]:
        cr.execute(
            """
            DELETE FROM ir_config_parameter
             WHERE key = %s
            """,
            (PENDING_SETUP_PARAM,),
        )
