def migrate(env):
    icp = env["ir.config_parameter"].sudo()
    popup_url = icp.get_param("envia.oauth_popup_url")
    if popup_url and "ecommerce=Odoo" in popup_url:
        icp.set_param(
            "envia.oauth_popup_url",
            popup_url.replace("ecommerce=Odoo", "ecommerce=odoo"),
        )
