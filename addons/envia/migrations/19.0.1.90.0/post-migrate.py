LEGACY_MODULE_XMLID = "module_envia_shipping"
MODULE_XMLID = "module_envia"


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = %s
         WHERE module = 'base'
           AND model = 'ir.module.module'
           AND name = %s
        """,
        (MODULE_XMLID, LEGACY_MODULE_XMLID),
    )
