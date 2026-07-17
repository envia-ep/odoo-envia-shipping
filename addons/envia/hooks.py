import logging

from odoo.tools import config
from psycopg2 import sql

from .services.envia_plugin_setup import queue_pending_setup

_logger = logging.getLogger(__name__)
LEGACY_MODULE_NAME = "envia_shipping"
MODULE_NAME = "envia"
HTTP_BRIDGE_MODULE = "envia_http"
_ENVIA_PRODUCT_TEMPLATE_FIELDS = (
    "dimensional_uom_id",
    "product_length",
    "product_width",
    "product_height",
    "envia_volumetric_weight",
)


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


def _cleanup_envia_product_dimension_artifacts(cr):
    """Drop legacy envia dimension views/fields left after removing product_template.py."""
    cr.execute(
        """
        DELETE FROM ir_ui_view v
         WHERE v.model = 'product.template'
           AND (
               v.arch_db::text LIKE '%%dimensional_uom_id%%'
               OR v.arch_db::text LIKE '%%envia_shipping%%'
               OR v.arch_db::text LIKE '%%envia_volumetric_weight%%'
           )
           AND (
               EXISTS (
                   SELECT 1
                     FROM ir_model_data imd
                    WHERE imd.model = 'ir.ui.view'
                      AND imd.res_id = v.id
                      AND imd.module = %s
               )
               OR NOT EXISTS (
                   SELECT 1
                     FROM ir_model_data imd
                    WHERE imd.model = 'ir.ui.view'
                      AND imd.res_id = v.id
               )
           )
           AND NOT EXISTS (
               SELECT 1
                 FROM ir_model_data imd
                WHERE imd.model = 'ir.ui.view'
                  AND imd.res_id = v.id
                  AND imd.module = 'product_dimension'
           )
        """,
        (MODULE_NAME,),
    )
    for field_name in _ENVIA_PRODUCT_TEMPLATE_FIELDS:
        cr.execute(
            """
            SELECT f.id
              FROM ir_model_fields f
              JOIN ir_model m ON m.id = f.model_id
              JOIN ir_model_data imd
                ON imd.model = 'ir.model.fields'
               AND imd.res_id = f.id
             WHERE m.model = 'product.template'
               AND f.name = %s
               AND imd.module = %s
            """,
            (field_name, MODULE_NAME),
        )
        row = cr.fetchone()
        if not row:
            continue
        field_id = row[0]
        cr.execute(
            "DELETE FROM ir_model_data WHERE model = 'ir.model.fields' AND res_id = %s",
            (field_id,),
        )
        cr.execute("DELETE FROM ir_model_fields WHERE id = %s", (field_id,))
        cr.execute(
            sql.SQL("ALTER TABLE product_template DROP COLUMN IF EXISTS {}").format(
                sql.Identifier(field_name)
            )
        )


def pre_init_hook(env):
    """Rename a legacy envia_shipping installation to envia before module load."""
    cr = env.cr
    _drop_legacy_branch_carrier_columns(cr)
    _cleanup_envia_product_dimension_artifacts(cr)
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
    warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
    company.write(
        {
            "country_id": mexico.id,
            "envia_default_origin_warehouse_id": warehouse.id if warehouse else False,
            "envia_environment": "sandbox",
            "envia_default_carrier": True,
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


def _envia_installed_spanish_langs(cr) -> list[str]:
    cr.execute(
        """
        SELECT code
          FROM res_lang
         WHERE active = TRUE
           AND code LIKE 'es%%'
        """
    )
    return [row[0] for row in cr.fetchall()]


def _sync_envia_settings_field_translations(cr):
    """Odoo 19 stores field labels in ir_model_fields JSON; sync Spanish langs on upgrade."""
    labels = {
        "envia_default_carrier": (
            "Usar Envia como método de envío predeterminado",
            "Preselecciona Envia.com al agregar envío en pedidos de venta.",
        ),
        "envia_enable_branches": (
            "Habilitar sucursales",
            "Permite rutas con sucursal al cotizar. Si está desactivado, solo hay entrega a domicilio.",
        ),
    }
    for lang in _envia_installed_spanish_langs(cr):
        for field_name, (es_label, es_help) in labels.items():
            cr.execute(
                """
                UPDATE ir_model_fields f
                   SET field_description = jsonb_set(
                           COALESCE(f.field_description, '{}'::jsonb),
                           ARRAY[%(lang)s],
                           to_jsonb(%(es_label)s::text)
                       ),
                       help = jsonb_set(
                           COALESCE(f.help, '{}'::jsonb),
                           ARRAY[%(lang)s],
                           to_jsonb(%(es_help)s::text)
                       )
                 FROM ir_model m
                WHERE f.model_id = m.id
                  AND m.model IN ('res.company', 'res.config.settings')
                  AND f.name = %(field_name)s
                """,
                {
                    "field_name": field_name,
                    "lang": lang,
                    "es_label": es_label,
                    "es_help": es_help,
                },
            )


def _envia_settings_view_terms_es() -> dict[str, str]:
    return {
        "Allow branch routes when quoting. When disabled, only home delivery is available.": (
            "Permite rutas con sucursal al cotizar. Si está desactivado, solo hay entrega a domicilio."
        ),
        "API key Envia.com uses to call back into Odoo. Generate it here and copy it into your Envia.com integration setup.": (
            "Clave API que Envia.com usa para llamar a Odoo. Genérala aquí y cópiala en la "
            "configuración de integración de Envia.com."
        ),
        "Add origin address": "Agregar dirección de origen",
        "Bearer token for api.envia.com (quoting, labels, tracking). Saved automatically by Envia.com during integration.": (
            "Token Bearer para api.envia.com (cotización, etiquetas, rastreo). Se guarda automáticamente "
            "durante la integración con Envia.com."
        ),
        "Carriers requested when quoting all Envia rates.": (
            "Transportistas solicitados al cotizar todas las tarifas de Envia."
        ),
        "Connect your store with Envia.com. Only administrators can refresh the integration token.": (
            "Conecta tu tienda con Envia.com. Solo los administradores pueden actualizar el token de integración."
        ),
        "Connected": "Conectado",
        "Connection": "Conexión",
        "Create and link the shop origin address in Envia.": (
            "Crea y vincula la dirección de origen de la tienda en Envia."
        ),
        "Default carriers": "Transportistas predeterminados",
        "Default origin and carriers used when quoting from sales orders and Add shipping.": (
            "Origen y transportistas predeterminados al cotizar desde pedidos de venta y Agregar envío."
        ),
        "Default origin used when quoting from sales orders and Add shipping.": (
            "Origen predeterminado al cotizar desde pedidos de venta y Agregar envío."
        ),
        "Default ship-from address": "Dirección de origen predeterminada",
        "Default ship-from warehouse": "Almacén de origen predeterminado",
        "Enable branch pickup and delivery": "Habilitar sucursales",
        "Envia shipping token": "Token de envío Envia",
        "Generate a key to configure the Envia.com callback.": (
            "Genera una clave para configurar el callback de Envia.com."
        ),
        "Generate API key": "Generar clave API",
        "Link your Odoo store with Envia.com and manage integration credentials.": (
            "Vincula tu tienda Odoo con Envia.com y gestiona las credenciales de integración."
        ),
        "Linked contact:": "Contacto vinculado:",
        "Module": "Módulo",
        "No token stored yet. Complete the Envia.com connection or wait for the integration callback.": (
            "Aún no hay token guardado. Completa la conexión con Envia.com o espera el callback de integración."
        ),
        "Not connected": "No conectado",
        "Odoo API key": "Clave API de Odoo",
        "Open the Envia address form, save a new origin address, and set it as the shop default.": (
            "Abre el formulario de dirección de Envia, guarda una nueva dirección de origen y "
            "defínela como predeterminada de la tienda."
        ),
        "Origin address": "Dirección de origen",
        "Origin for Envia quotes. Must include street, city, postal code, country, phone and email. Destination comes from the customer delivery address on the order.": (
            "Origen para cotizaciones Envia. Debe incluir calle, ciudad, código postal, país, teléfono y "
            "correo. El destino proviene de la dirección de entrega del cliente en el pedido."
        ),
        "Origin for Envia quotes. Uses the warehouse address (linked contact). Must include street, city, postal code, country, phone and email. Destination comes from the customer delivery address on the order.": (
            "Origen para cotizaciones Envia. Usa la dirección del almacén (contacto vinculado). Debe "
            "incluir calle, ciudad, código postal, país, teléfono y correo. El destino proviene de la "
            "dirección de entrega del cliente en el pedido."
        ),
        "Plugin": "Plugin",
        "Pre-select Envia.com in Add shipping on sale orders.": (
            "Preselecciona Envia.com al agregar envío en pedidos de venta."
        ),
        "Refresh token": "Actualizar token",
        "Shipping defaults": "Valores predeterminados de envío",
        "Test connection": "Probar conexión",
        "Use Envia as default shipping method": "Usar Envia como método de envío predeterminado",
    }


def _sync_envia_settings_view_translations(env) -> None:
    """Odoo 19: push settings view terms directly; the main es_419.po is too large to import reliably."""
    view = env.ref("envia.res_config_settings_view_form_envia", raise_if_not_found=False)
    if not view:
        return
    terms_es = _envia_settings_view_terms_es()
    for lang in _envia_installed_spanish_langs(env.cr):
        view.update_field_translations("arch_db", {lang: terms_es})


def post_init_hook(env):
    warn_if_http_bridge_missing(at_install=True)
    _sync_envia_settings_field_translations(env.cr)
    _sync_envia_settings_view_translations(env)
    load_envia_demo_data(env)
    company = env.ref("base.main_company")
    if not company._envia_is_shipping_api_configured():
        queue_pending_setup(env)
    env["onboarding.onboarding"].sudo().search(
        [("route_name", "=", "envia_quotes")]
    ).with_company(company)._search_or_create_progress()
