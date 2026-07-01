def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_asset
         WHERE path ILIKE '%envia_oauth_integration_popup%'
        """
    )
