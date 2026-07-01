{
    "name": "ECart Connector",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Connect e-commerce stores via ECart API and import orders into Odoo",
    "author": "Alejandro Prado",
    "license": "LGPL-3",
    "depends": ["base", "sale", "sale_stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/ecart_oauth_templates.xml",
        "views/ecart_store_views.xml",
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": True,
}
