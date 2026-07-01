def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_ui_menu
           SET name = jsonb_set(name, '{es_419}', '"Envia.com"')
         WHERE id IN (
            SELECT res_id
              FROM ir_model_data
             WHERE module = 'envia'
               AND name = 'menu_envia_root'
               AND model = 'ir.ui.menu'
         )
        """
    )
