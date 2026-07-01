{
    "name": "Envia ECart Integration",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Connect Odoo with Envia via ECart API OAuth flow",
    "description": """
        Integrates Odoo with Envia/ECart API using the OAuth plugin flow.
        Dynamically builds the integration URL with store URL, database,
        user email, and a non-expiring Odoo API key.
    """,
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/envia_integration_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": True,
}
