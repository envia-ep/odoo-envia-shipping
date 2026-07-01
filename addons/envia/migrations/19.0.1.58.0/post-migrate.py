def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_config_parameter
           SET value = value || '&state=fromPlugin&origin=odoo'
         WHERE key = 'envia.oauth_popup_url'
           AND value IS NOT NULL
           AND value <> ''
           AND value NOT ILIKE '%state=%'
           AND value NOT ILIKE '%origin=%'
        """
    )
