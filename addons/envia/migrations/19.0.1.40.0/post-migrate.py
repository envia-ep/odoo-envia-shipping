def migrate(cr, version):
    cr.execute(
        """
        UPDATE res_company
           SET envia_api_token = NULL
         WHERE envia_oauth_connected = true
           AND COALESCE(envia_oauth_access_token, '') <> ''
           AND envia_api_token = envia_oauth_access_token
        """
    )
