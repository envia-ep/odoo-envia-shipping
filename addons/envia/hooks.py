import logging

from odoo.tools import config

from .services.envia_plugin_setup import queue_pending_setup

_logger = logging.getLogger(__name__)
LEGACY_MODULE_NAME = "envia_shipping"
MODULE_NAME = "envia"
HTTP_BRIDGE_MODULE = "envia_http"


def _http_bridge_server_wide_modules():
    return config.get("server_wide_modules") or ["web", "base", "web"]


def warn_if_http_bridge_missing(*, at_install: bool = False) -> bool:
    """Return True when envia_http is listed in server_wide_modules."""
    if HTTP_BRIDGE_MODULE in _http_bridge_server_wide_modules():
        return True
    message = (
        "Add %r to server_wide_modules in odoo.conf (local and production) so "
        "POST /envia/integration/callback works without X-Odoo-Database. "
        "Example: server_wide_modules = web,base,%s. "
        "Then restart Odoo and verify with: "
        "curl -X POST https://<your-domain>/envia/integration/callback"
    )
    log = _logger.error if at_install else _logger.warning
    log(message, HTTP_BRIDGE_MODULE, HTTP_BRIDGE_MODULE)
    return False


def post_load():
    warn_if_http_bridge_missing()


def _drop_legacy_branch_carrier_columns(cr):
    """Char columns block Many2one registration on envia.quote.wizard."""
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'envia_quote_wizard'
           AND column_name IN ('origin_branch_carrier', 'destination_branch_carrier')
           AND data_type IN ('character varying', 'text')
        """
    )
    for (column_name,) in cr.fetchall():
        cr.execute(
            f'ALTER TABLE envia_quote_wizard DROP COLUMN IF EXISTS "{column_name}"'
        )


def pre_init_hook(env):
    """Rename a legacy envia_shipping installation to envia before module load."""
    cr = env.cr
    _drop_legacy_branch_carrier_columns(cr)
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = %s
         WHERE module = 'base'
           AND model = 'ir.module.module'
           AND name = %s
        """,
        (f"module_{MODULE_NAME}", f"module_{LEGACY_MODULE_NAME}"),
    )
    cr.execute("SELECT 1 FROM ir_module_module WHERE name = %s", (LEGACY_MODULE_NAME,))
    if not cr.fetchone():
        return

    cr.execute(
        "SELECT 1 FROM ir_module_module WHERE name = %s AND id != (SELECT id FROM ir_module_module WHERE name = %s LIMIT 1)",
        (MODULE_NAME, LEGACY_MODULE_NAME),
    )
    if cr.fetchone():
        return

    cr.execute(
        "UPDATE ir_module_module SET name = %s WHERE name = %s",
        (MODULE_NAME, LEGACY_MODULE_NAME),
    )
    cr.execute(
        "UPDATE ir_module_module_dependency SET name = %s WHERE name = %s",
        (MODULE_NAME, LEGACY_MODULE_NAME),
    )
    cr.execute(
        "UPDATE ir_model_data SET module = %s WHERE module = %s",
        (MODULE_NAME, LEGACY_MODULE_NAME),
    )
    cr.execute(
        """
        UPDATE ir_config_parameter
           SET key = REPLACE(key, %s, %s)
         WHERE key LIKE %s
        """,
        (f"{LEGACY_MODULE_NAME}.", f"{MODULE_NAME}.", f"{LEGACY_MODULE_NAME}.%"),
    )
    cr.execute(
        """
        UPDATE ir_asset
           SET path = REPLACE(path, %s, %s)
         WHERE path LIKE %s
        """,
        (f"{LEGACY_MODULE_NAME}/", f"{MODULE_NAME}/", f"{LEGACY_MODULE_NAME}/%"),
    )
    cr.execute(
        """
        UPDATE ir_ui_view
           SET arch_db = REPLACE(arch_db::text, %s, %s)::jsonb
         WHERE arch_db::text LIKE %s
        """,
        (f"{LEGACY_MODULE_NAME}.", f"{MODULE_NAME}.", f"%{LEGACY_MODULE_NAME}.%"),
    )
    cr.execute(
        """
        UPDATE ir_act_window
           SET context = REPLACE(context, %s, %s)
         WHERE context LIKE %s
        """,
        (LEGACY_MODULE_NAME, MODULE_NAME, f"%{LEGACY_MODULE_NAME}%"),
    )
    cr.execute(
        """
        UPDATE ir_cron
           SET code = REPLACE(code, %s, %s)
         WHERE code LIKE %s
        """,
        (LEGACY_MODULE_NAME, MODULE_NAME, f"%{LEGACY_MODULE_NAME}%"),
    )


def _get_mexico_states(env):
    mexico = env.ref("base.mx")
    state_origin = env.ref("base.state_mx_nl", raise_if_not_found=False)
    state_destination = env.ref("base.state_mx_df", raise_if_not_found=False)
    if not state_origin:
        state_origin = env["res.country.state"].search(
            [("country_id", "=", mexico.id), ("code", "in", ["NLE", "NL"])],
            limit=1,
        )
    if not state_destination:
        state_destination = env["res.country.state"].search(
            [("country_id", "=", mexico.id), ("code", "in", ["CMX", "CX", "DIF"])],
            limit=1,
        )
    return mexico, state_origin, state_destination


def load_envia_demo_data(env):
    mexico, state_origin, state_destination = _get_mexico_states(env)
    company = env.ref("base.main_company")
    origin_partner = env.ref("base.main_partner")

    origin_partner.write(
        {
            "street": origin_partner.street or "Aurora Boreal 301",
            "city": "Guadalupe",
            "zip": "67192",
            "country_id": mexico.id,
            "state_id": state_origin.id if state_origin else False,
            "phone": origin_partner.phone or "8121211454",
            "email": origin_partner.email or "malcom.prado@envia.com",
        }
    )
    company.write(
        {
            "country_id": mexico.id,
            "envia_default_origin_partner_id": origin_partner.id,
            "envia_environment": "sandbox",
        }
    )

    customer = env.ref("envia.envia_demo_customer", raise_if_not_found=False)
    if not customer:
        customer = env["res.partner"].search([("name", "=", "Envia Demo Customer")], limit=1)
    if not customer:
        customer = env["res.partner"].create(
            {
                "name": "Envia Demo Customer",
                "street": "Av. Insurgentes Sur 1234",
                "city": "Ciudad de Mexico",
                "zip": "03100",
                "country_id": mexico.id,
                "state_id": state_destination.id if state_destination else False,
                "phone": "5551234567",
                "email": "demo.customer@envia.test",
            }
        )

    carlos = env["res.partner"].search([("name", "=", "Carlos Garcia")], limit=1)
    if carlos:
        carlos.write(
            {
                "street": "Av. Reforma 222",
                "city": "Ciudad de Mexico",
                "zip": "03100",
                "country_id": mexico.id,
                "state_id": state_destination.id if state_destination else False,
                "phone": carlos.phone or "5559876543",
                "email": carlos.email or "carlos.garcia@example.com",
            }
        )

    demo_order = env["sale.order"].search([("client_order_ref", "=", "ENVIA-DEMO-QUOTE")], limit=1)
    if demo_order:
        return

    product = env.ref("product.product_product_4", raise_if_not_found=False)
    if not product:
        product = env["product.product"].search([("sale_ok", "=", True)], limit=1)
    if not product:
        return

    order = env["sale.order"].create(
        {
            "partner_id": customer.id,
            "partner_invoice_id": customer.id,
            "partner_shipping_id": customer.id,
            "client_order_ref": "ENVIA-DEMO-QUOTE",
            "order_line": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_qty": 1.0,
                    },
                )
            ],
        }
    )
    order.action_confirm()


def post_init_hook(env):
    warn_if_http_bridge_missing(at_install=True)
    load_envia_demo_data(env)
    company = env.ref("base.main_company")
    if not company._envia_is_shipping_api_configured():
        queue_pending_setup(env)
    env["onboarding.onboarding"].sudo().search(
        [("route_name", "=", "envia_quotes")]
    ).with_company(company)._search_or_create_progress()
