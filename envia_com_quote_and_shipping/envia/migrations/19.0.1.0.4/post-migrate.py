def migrate(cr, version):
    """Rename the Envia delivery product label on existing databases."""
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    product = env.ref("envia.product_envia_shipping", raise_if_not_found=False)
    if product and product.name == "Shipping":
        product.name = "Shipping - Envia.com"
