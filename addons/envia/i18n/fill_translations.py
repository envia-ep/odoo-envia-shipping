#!/usr/bin/env python3
"""Fill Spanish translations for envia PO files."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

TRANSLATIONS: dict[str, str] = {
    "%(carrier)s · %(service)s · %(price).2f %(currency)s": "%(carrier)s · %(service)s · %(price).2f %(currency)s",
    "%(weight)s kg · %(length)s×%(width)s×%(height)s cm · %(content)s": "%(weight)s kg · %(length)s×%(width)s×%(height)s cm · %(content)s",
    "A partner is required to build the shipment contact.": "Se requiere un contacto para construir la información del envío.",
    "API codes sent to Envia": "Códigos API enviados a Envia",
    "API codes sent to Envia:": "Códigos API enviados a Envia:",
    "API Token": "Token de API",
    "Active endpoint": "Endpoint activo",
    "Available rates": "Tarifas disponibles",
    "Back": "Atrás",
    "Base URL": "URL base",
    "Best price: %(carrier)s · %(price).2f %(currency)s": "Mejor precio: %(carrier)s · %(price).2f %(currency)s",
    "Cancel": "Cancelar",
    "Cancelled": "Cancelado",
    "Carrier": "Transportista",
    "Choose a shipping rate to continue.": "Elige una tarifa de envío para continuar.",
    "City": "Ciudad",
    "Click to add carriers...": "Haz clic para añadir transportistas...",
    "Color Index": "Índice de color",
    "Configure an Envia API token before testing the connection.": "Configura un token de API de Envia antes de probar la conexión.",
    "Connect Odoo to Envia.com. Use sandbox for testing and production for live labels.": "Conecta Odoo con Envia.com. Usa sandbox para pruebas y producción para etiquetas reales.",
    "Connection successful": "Conexión exitosa",
    "Configure the Envia API token in Settings > Envia Shipping.": "Configura el token de API de Envia en Ajustes > Envia Shipping.",
    "Continue": "Continuar",
    "Country": "País",
    "Create Envia Label": "Crear etiqueta Envia",
    "Create shipping label": "Crear etiqueta de envío",
    "Created": "Creado",
    "Currency": "Moneda",
    "Days": "Días",
    "Declared Value": "Valor declarado",
    "Default Carriers": "Transportistas predeterminados",
    "Default format and size when generating shipping labels.": "Formato y tamaño predeterminados al generar etiquetas de envío.",
    "Default Origin Contact": "Contacto de origen predeterminado",
    "Default ship-from contact used to prefill the quote wizard.": "Contacto de origen predeterminado para precargar el asistente de cotización.",
    "Delivered": "Entregado",
    "Demo Quote Order": "Pedido de cotización demo",
    "Destination city is required.": "La ciudad de destino es obligatoria.",
    "Destination country is required.": "El país de destino es obligatorio.",
    "Destination postal code is required.": "El código postal de destino es obligatorio.",
    "Destination state must belong to the selected destination country.": "El estado de destino debe pertenecer al país de destino seleccionado.",
    "Dimensions (cm)": "Dimensiones (cm)",
    "Documents": "Documentos",
    "Download Label": "Descargar etiqueta",
    "Draft": "Borrador",
    "Edit Contact": "Editar contacto",
    "Edit contact": "Editar contacto",
    "Envia API connection error: %s": "Error de conexión con la API de Envia: %s",
    "Envia API error (%(status)s): %(message)s": "Error de API de Envia (%(status)s): %(message)s",
    "Envia API returned invalid JSON (HTTP %s).": "La API de Envia devolvió JSON inválido (HTTP %s).",
    "Effective Base URL": "URL base efectiva",
    "Envia API credentials are valid for the selected environment.": "Las credenciales de Envia son válidas para el entorno seleccionado.",
    "Envia Carrier": "Transportista Envia",
    "Envia Shipping": "Envia Shipping",
    "Envia Shipment": "Envío Envia",
    "Envia Shipments": "Envíos Envia",
    "Envia Shipping Quote": "Cotización de envío Envia",
    "Envia label created: %(tracking)s · %(carrier)s": "Etiqueta Envia creada: %(tracking)s · %(carrier)s",
    "Envia rate selected: %(carrier)s · %(service)s · %(price).2f %(currency)s": "Tarifa Envia seleccionada: %(carrier)s · %(service)s · %(price).2f %(currency)s",
    "Envia test data loaded": "Datos de prueba de Envia cargados",
    "Envia: Create Label": "Envia: Crear etiqueta",
    "Envia: Get Rates": "Envia: Obtener tarifas",
    "Envia: Sync Tracking": "Envia: Sincronizar rastreo",
    "Environment": "Entorno",
    "Expired": "Expirado",
    "Failed to download label: %s": "Error al descargar la etiqueta: %s",
    "Fastest: %(carrier)s · %(days)s day(s)": "Más rápido: %(carrier)s · %(days)s día(s)",
    "Format": "Formato",
    "Generate Label": "Generar etiqueta",
    "Generate separate tokens for sandbox and production in Envia.": "Genera tokens separados para sandbox y producción en Envia.",
    "Get Envia rates first and select a carrier before generating the label.": "Obtén tarifas de Envia y selecciona un transportista antes de generar la etiqueta.",
    "Get Rates": "Obtener tarifas",
    "Get shipping rates": "Obtener tarifas de envío",
    "In Transit": "En tránsito",
    "Insufficient Envia account balance.": "Saldo insuficiente en la cuenta de Envia.",
    "Invalid Envia API token. Check Settings > Envia Shipping.": "Token de API de Envia inválido. Revisa Ajustes > Envia Shipping.",
    "Invalid postal code: %s": "Código postal inválido: %s",
    "Label Output": "Salida de etiquetas",
    "Label preferences": "Preferencias de etiqueta",
    "Label Size": "Tamaño de etiqueta",
    "Label created": "Etiqueta creada",
    "Leave empty for default": "Dejar vacío para predeterminado",
    "Leave empty to use the default URL for the selected environment.": "Dejar vacío para usar la URL predeterminada del entorno seleccionado.",
    "Load demo data": "Cargar datos demo",
    "Load Envia test data": "Cargar datos de prueba de Envia",
    "Load test data": "Cargar datos de prueba",
    "Manager": "Administrador",
    "Mexico is not available in this database.": "México no está disponible en esta base de datos.",
    "Missing on contact: %s": "Faltante en el contacto: %s",
    "No Envia activity": "Sin actividad Envia",
    "No address saved on this contact yet.": "Aún no hay dirección guardada en este contacto.",
    "No label is available for this shipment yet.": "Aún no hay etiqueta disponible para este envío.",
    "No shipping services available for this route.": "No hay servicios de envío disponibles para esta ruta.",
    "No rates returned. Go back, verify addresses, and try a domestic MX route in sandbox.": "No se devolvieron tarifas. Regresa, verifica las direcciones e intenta una ruta doméstica MX en sandbox.",
    "Paste your Envia API token": "Pega tu token de API de Envia",
    "Origin city is required.": "La ciudad de origen es obligatoria.",
    "Origin country is required.": "El país de origen es obligatorio.",
    "Origin postal code is required.": "El código postal de origen es obligatorio.",
    "Origin state must belong to the selected origin country.": "El estado de origen debe pertenecer al país de origen seleccionado.",
    "Package": "Paquete",
    "Package dimensions must be greater than zero.": "Las dimensiones del paquete deben ser mayores que cero.",
    "Package weight must be greater than zero.": "El peso del paquete debe ser mayor que cero.",
    "Picking": "Albarán",
    "Postal Code": "Código postal",
    "Postal code": "Código postal",
    "Price": "Precio",
    "Production mode: labels are real and Envia will charge your account.": "Modo producción: las etiquetas son reales y Envia cargará a tu cuenta.",
    "Sandbox mode: safe for testing. Load demo data to try the quote flow quickly.": "Modo sandbox: seguro para pruebas. Carga datos demo para probar el flujo de cotización rápidamente.",
    "Quote": "Cotización",
    "Quoted": "Cotizado",
    "Rate selected": "Tarifa seleccionada",
    "Refresh Tracking": "Actualizar rastreo",
    "Reload": "Recargar",
    "Route details": "Detalles de ruta",
    "Sale Order": "Pedido de venta",
    "Sandbox": "Sandbox",
    "Sandbox for testing. Production creates real labels and charges.": "Sandbox para pruebas. Producción crea etiquetas reales y genera cargos.",
    "Select": "Seleccionar",
    "Select Rate": "Seleccionar tarifa",
    "Select a carrier service before creating the shipment.": "Selecciona un servicio de transportista antes de crear el envío.",
    "Select a contact for this address.": "Selecciona un contacto para esta dirección.",
    "Select a contact to load the address automatically.": "Selecciona un contacto para cargar la dirección automáticamente.",
    "Select a destination state/province.": "Selecciona un estado/provincia de destino.",
    "Selected carriers": "Transportistas seleccionados",
    "Select a ship-from contact": "Selecciona un contacto de origen",
    "Shipping Defaults": "Valores predeterminados de envío",
    "Size": "Tamaño",
    "Select a ship-to contact first.": "Selecciona primero un contacto de destino.",
    "Select a shipping rate": "Selecciona una tarifa de envío",
    "Select an origin state/province.": "Selecciona un estado/provincia de origen.",
    "Selected": "Seleccionado",
    "Selected rate": "Tarifa seleccionada",
    "Selected service is missing carrier information.": "Al servicio seleccionado le falta información del transportista.",
    "Service": "Servicio",
    "Ship From": "Enviar desde",
    "Ship To": "Enviar a",
    "Ship from — %(message)s": "Origen — %(message)s",
    "Ship to — %(message)s": "Destino — %(message)s",
    "Shipment Details": "Detalles del envío",
    "Shipment details": "Detalles del envío",
    "Shipments": "Envíos",
    "State": "Estado",
    "State / province": "Estado / provincia",
    "Test connection": "Probar conexión",
    "Token configured. Generate separate tokens for sandbox and production in Envia.": "Token configurado. Genera tokens separados para sandbox y producción en Envia.",
    "Token required. Generate separate tokens for sandbox and production in Envia.": "Token requerido. Genera tokens separados para sandbox y producción en Envia.",
    "This shipment has no tracking number.": "Este envío no tiene número de rastreo.",
    "To": "Hasta",
    "Tracking timeline": "Línea de tiempo de rastreo",
    "Use MX test route": "Usar ruta de prueba MX",
    "Used": "Usado",
    "User": "Usuario",
    "Weight (kg)": "Peso (kg)",
    "Weight exceeds limit: %s": "El peso excede el límite: %s",
    "What are you shipping?": "¿Qué estás enviando?",
    "city": "ciudad",
    "country": "país",
    "email": "correo electrónico",
    "phone": "teléfono",
    "postal code": "código postal",
    "state matching country": "estado que coincida con el país",
    "street": "calle",
    "Domestic": "Doméstico",
    "International": "Internacional",
    "Ready": "Listo",
    "Incomplete": "Incompleto",
    "Best price": "Mejor precio",
    "Fastest delivery": "Entrega más rápida",
    "Rates found": "Tarifas encontradas",
    "Before requesting rates:": "Antes de solicitar tarifas:",
    "Before requesting rates": "Antes de solicitar tarifas",
    "Selected rate:": "Tarifa seleccionada:",
    "Review the selected rate below. Generating the label will charge the carrier\n                        in production and create a trackable shipment in Odoo.": "Revisa la tarifa seleccionada abajo. Generar la etiqueta cobrará al transportista\n                        en producción y creará un envío rastreable en Odoo.",
    "<i class=\"fa fa-building-o me-1\" title=\"Origin\"/>\n                                        Ship from": "<i class=\"fa fa-building-o me-1\" title=\"Origen\"/>\n                                        Enviar desde",
    "<i class=\"fa fa-map-marker me-1\" title=\"Destination\"/>\n                                        Ship to": "<i class=\"fa fa-map-marker me-1\" title=\"Destino\"/>\n                                        Enviar a",
    "<i class=\"fa fa-shopping-cart text-muted\" title=\"Sale Order\"/>": "<i class=\"fa fa-shopping-cart text-muted\" title=\"Pedido de venta\"/>",
    "<i class=\"fa fa-truck text-muted\" title=\"Picking\"/>": "<i class=\"fa fa-truck text-muted\" title=\"Albarán\"/>",
    "<span class=\"o_envia_stat_label\">Best price</span>": "<span class=\"o_envia_stat_label\">Mejor precio</span>",
    "<span class=\"o_envia_stat_label\">Fastest delivery</span>": "<span class=\"o_envia_stat_label\">Entrega más rápida</span>",
    "<span class=\"o_envia_stat_label\">Quote</span>": "<span class=\"o_envia_stat_label\">Cotización</span>",
    "Values used to prefill the quote wizard.": "Valores usados para precargar el asistente de cotización.",
    "Carriers included when requesting rates.": "Transportistas incluidos al solicitar tarifas.",
    "Carrier code must be unique.": "El código del transportista debe ser único.",
    "<strong>Production mode:</strong>\n                                labels are real and Envia will charge your account.": "<strong>Modo producción:</strong>\n                                las etiquetas son reales y Envia cargará a tu cuenta.",
    "<span>\n                                        <strong>Sandbox mode:</strong>\n                                        safe for testing. Load demo data to try the quote flow quickly.\n                                    </span>": "<span>\n                                        <strong>Modo sandbox:</strong>\n                                        seguro para pruebas. Carga datos demo para probar el flujo de cotización rápidamente.\n                                    </span>",
    "<i class=\"fa fa-check me-1\" title=\"Token configured\"/>": "<i class=\"fa fa-check me-1\" title=\"Token configurado\"/>",
    "<i class=\"fa fa-exclamation-circle me-1\" title=\"Token missing\"/>": "<i class=\"fa fa-exclamation-circle me-1\" title=\"Token faltante\"/>",
    "<span>\n                                <strong>Sandbox tip:</strong>\n                                domestic routes are the most reliable for testing.\n                            </span>": "<span>\n                                <strong>Consejo de sandbox:</strong>\n                                las rutas domésticas son las más confiables para pruebas.\n                            </span>",
    "<span class=\"badge rounded-pill text-bg-success\" invisible=\"not is_domestic_route\">Domestic</span>\n                            <span class=\"badge rounded-pill text-bg-warning\" invisible=\"not is_international_route\">International</span>\n                            <span class=\"badge rounded-pill text-bg-info\" invisible=\"not is_sandbox\">Sandbox</span>": "<span class=\"badge rounded-pill text-bg-success\" invisible=\"not is_domestic_route\">Doméstico</span>\n                            <span class=\"badge rounded-pill text-bg-warning\" invisible=\"not is_international_route\">Internacional</span>\n                            <span class=\"badge rounded-pill text-bg-info\" invisible=\"not is_sandbox\">Sandbox</span>",
    "<span class=\"badge text-bg-success\" invisible=\"not destination_contact_complete\">Ready</span>\n                                    <span class=\"badge text-bg-danger\" invisible=\"destination_contact_complete or not destination_partner_id\">\n                                        Incomplete\n                                    </span>": "<span class=\"badge text-bg-success\" invisible=\"not destination_contact_complete\">Listo</span>\n                                    <span class=\"badge text-bg-danger\" invisible=\"destination_contact_complete or not destination_partner_id\">\n                                        Incompleto\n                                    </span>",
    "<span class=\"badge text-bg-success\" invisible=\"not origin_contact_complete\">Ready</span>\n                                    <span class=\"badge text-bg-danger\" invisible=\"origin_contact_complete or not origin_partner_id\">\n                                        Incomplete\n                                    </span>": "<span class=\"badge text-bg-success\" invisible=\"not origin_contact_complete\">Listo</span>\n                                    <span class=\"badge text-bg-danger\" invisible=\"origin_contact_complete or not origin_partner_id\">\n                                        Incompleto\n                                    </span>",
    "<strong>Before requesting rates:</strong>": "<strong>Antes de solicitar tarifas:</strong>",
    "<strong>Selected rate:</strong>": "<strong>Tarifa seleccionada:</strong>",
    "<strong>Selected rate</strong>": "<strong>Tarifa seleccionada</strong>",
    "<h6 class=\"text-uppercase text-muted fw-bold mb-3\">\n                            <i class=\"fa fa-tags me-1\" title=\"Selected rate\"/>\n                            Selected rate\n                        </h6>": "<h6 class=\"text-uppercase text-muted fw-bold mb-3\">\n                            <i class=\"fa fa-tags me-1\" title=\"Tarifa seleccionada\"/>\n                            Tarifa seleccionada\n                        </h6>",
    "<h6 class=\"text-uppercase text-muted fw-bold mb-2\">\n                            <i class=\"fa fa-cube me-1\" title=\"Package\"/>\n                            Shipment details\n                        </h6>": "<h6 class=\"text-uppercase text-muted fw-bold mb-2\">\n                            <i class=\"fa fa-cube me-1\" title=\"Paquete\"/>\n                            Detalles del envío\n                        </h6>",
    "Administrator required": "Se requiere administrador",
    "Authorize Envia.com to access your Odoo instance.": "Autoriza a Envia.com a acceder a tu instancia de Odoo.",
    "Close": "Cerrar",
    "Complete the Envia.com flow": "Completa el flujo de Envia.com",
    "Complete the Envia.com flow in this window, then confirm the connection in Odoo.": "Completa el flujo de Envia.com en esta ventana y luego confirma la conexión en Odoo.",
    "Confirm in Odoo": "Confirma en Odoo",
    "Connect Store": "Conectar tienda",
    "Connect with Envia.com": "Conectar con Envia.com",
    "Connect your store": "Conecta tu tienda",
    "Connected": "Conectado",
    "Connecting with Envia.com": "Conectando con Envia.com",
    "Connecting...": "Conectando...",
    "Connection failed": "Conexión fallida",
    "Demo quote order": "Pedido de cotización demo",
    "Envia Plugin Connect Wizard": "Asistente de conexión del plugin Envia",
    "Envia Shipping Setup": "Configuración de Envia Shipping",
    "Envia.com Connected": "Envia.com conectado",
    "Envia.com Connection Failed": "Falló la conexión con Envia.com",
    "Envia.com integration": "Integración con Envia.com",
    "Envia.com must reach this public URL to validate your store.": "Envia.com debe poder acceder a esta URL pública para validar tu tienda.",
    "Envia integration verification failed. The test endpoint did not return success.": "Falló la verificación de la integración con Envia. El endpoint de prueba no devolvió éxito.",
    "Go to Quotes": "Ir a Cotizaciones",
    "Integration API Token": "Token de API de integración",
    "Integration Message": "Mensaje de integración",
    "Missing API key for Envia integration.": "Falta la clave API para la integración con Envia.",
    "Not synced — click Refresh token": "No sincronizado — haz clic en Actualizar token",
    "Only an Odoo administrator can connect Envia.com. Please ask your administrator to complete the connection.": "Solo un administrador de Odoo puede conectar Envia.com. Pide a tu administrador que complete la conexión.",
    "Please wait while we connect your store with Envia.com.": "Espera mientras conectamos tu tienda con Envia.com.",
    "Plugin Version": "Versión del plugin",
    "Plugin Version Display": "Versión del plugin (visualización)",
    "Plugin version:": "Versión del plugin:",
    "Quotes": "Cotizaciones",
    "Refresh token": "Actualizar token",
    "Sign in or register in the Envia.com window that opens next.": "Inicia sesión o regístrate en la ventana de Envia.com que se abrirá a continuación.",
    "Sign in or register in the Envia.com tab that opens in your browser.": "Inicia sesión o regístrate en la pestaña de Envia.com que se abre en tu navegador.",
    "Step 2 of 3 · In progress": "Paso 2 de 3 · En progreso",
    "Active": "Activo",
    "Done": "Listo",
    "Tip": "Consejo",
    "Waiting for Envia.com": "Esperando a Envia.com",
    "Odoo is ready": "Odoo está listo",
    "Your store connection request was sent to Envia.com.": "Tu solicitud de conexión de tienda se envió a Envia.com.",
    "Use the Envia.com browser tab to sign in and authorize access.": "Usa la pestaña de Envia.com en tu navegador para iniciar sesión y autorizar el acceso.",
    "Return to Odoo": "Vuelve a Odoo",
    "Close the Envia.com tab when the authorization is complete.": "Cierra la pestaña de Envia.com cuando completes la autorización.",
    "Waiting for Envia.com to save your connection": "Esperando a que Envia.com guarde tu conexión",
    "Open Envia.com": "Abrir Envia.com",
    "Cancel connection": "Cancelar conexión",
    "Open Settings": "Abrir ajustes",
    "OAuth connection window": "Ventana de conexión OAuth",
    "Open Envia.com in a sized pop-up window": "Abrir Envia.com en una ventana emergente",
    "Envia.com did not open. Click Open Envia.com below.": "Envia.com no se abrió. Haz clic en Abrir Envia.com abajo.",
    "Envia.com did not open. Click Open Envia.com below or allow pop-ups for this site.": "Envia.com no se abrió. Haz clic en Abrir Envia.com abajo o permite ventanas emergentes para este sitio.",
    "Store URL": "URL de la tienda",
    "Try again": "Reintentar",
    "Verifying...": "Verificando...",
    "Administration": "Administración",
    "Configuration": "Configuración",
    "Settings": "Ajustes",
    "Welcome to Envia Shipping": "Bienvenido a Envia Shipping",
    "Your Odoo store is connected with Envia.com.": "Tu tienda Odoo está conectada con Envia.com.",
    "Your Odoo store is connected with Envia.com. Click Refresh token to sync the latest connection details.": "Tu tienda Odoo está conectada con Envia.com. Haz clic en Actualizar token para sincronizar los últimos detalles de conexión.",
    "Your Odoo store was connected successfully with Envia.com.": "Tu tienda Odoo se conectó correctamente con Envia.com.",
    "Connect your Odoo store with Envia.com to quote carriers, create labels, and track shipments without leaving Odoo.": "Conecta tu tienda Odoo con Envia.com para cotizar transportistas, crear etiquetas y rastrear envíos sin salir de Odoo.",
    "Return here and click <strong>Continue</strong> to verify the connection.": "Regresa aquí y haz clic en <strong>Continuar</strong> para verificar la conexión.",
    "Odoo updates automatically when Envia saves your connection and shipping token.": "Odoo se actualiza automáticamente cuando Envia guarda tu conexión y tu token de envío.",
    "Envia.com was opened in a new browser tab. Sign in, authorize your store, and close the tab when you are done.": "Envia.com se abrió en una pestaña nueva del navegador. Inicia sesión, autoriza tu tienda y cierra la pestaña cuando termines.",
    "If Envia.com did not open, click Open Envia.com below. This screen updates automatically when Envia saves your API token.": "Si Envia.com no se abrió, haz clic en Abrir Envia.com abajo. Esta pantalla se actualiza automáticamente cuando Envia guarda tu token de API.",
    "When disabled (default), Envia.com opens in a new browser tab. When enabled, opens a smaller pop-up window that may require allowing pop-ups in the browser.": "Si está desactivado (predeterminado), Envia.com se abre en una pestaña nueva. Si está activado, abre una ventana emergente más pequeña que puede requerir permitir ventanas emergentes en el navegador.",
    "By default Envia.com opens in a new browser tab (recommended). Enable this only if you prefer a smaller pop-up window.": "Por defecto Envia.com se abre en una pestaña nueva (recomendado). Actívalo solo si prefieres una ventana emergente más pequeña.",
    "Envia.com": "Envia.com",
    "Quote, create and track Envia.com shipments from Odoo": "Cotiza, crea y rastrea envíos de Envia.com desde Odoo",
    "No API token stored. Click Refresh token to generate and save one.": "No hay token de API guardado. Haz clic en Actualizar token para generar y guardar uno.",
    "No API token stored. Open Connect with Envia.com and click Refresh token.": "No hay token de API guardado. Abre Conectar con Envia.com y haz clic en Actualizar token.",
}


APPEND_ENTRIES: list[tuple[str, str, str]] = [
    (
        "model:ir.module.module,shortdesc:base.module_envia",
        "Envia.com",
        "Envia.com",
    ),
    (
        "model:ir.module.module,summary:base.module_envia",
        "Quote, create and track Envia.com shipments from Odoo",
        "Cotiza, crea y rastrea envíos de Envia.com desde Odoo",
    ),
    (
        "model:ir.ui.menu,name:envia.menu_envia_root",
        "Envia.com",
        "Envia.com",
    ),
    (
        "model:ir.actions.server,name:envia.action_envia_app_entry",
        "Envia.com",
        "Envia.com",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Envia.com",
        "Envia.com",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "API Connection",
        "Conexión API",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Connect Odoo to Envia.com. Use sandbox for testing and production for live labels.",
        "Conecta Odoo con Envia.com. Usa sandbox para pruebas y producción para etiquetas reales.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "<strong>Production mode:</strong>\n                                labels are real and Envia will charge your account.",
        "<strong>Modo producción:</strong>\n                                las etiquetas son reales y Envia cargará a tu cuenta.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "<span>\n                                        <strong>Sandbox mode:</strong>\n                                        safe for testing. Load demo data to try the quote flow quickly.\n                                    </span>",
        "<span>\n                                        <strong>Modo sandbox:</strong>\n                                        seguro para pruebas. Carga datos demo para probar el flujo de cotización rápidamente.\n                                    </span>",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Load demo data",
        "Cargar datos demo",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Token configured",
        "Token configurado",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Token missing",
        "Token faltante",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Token required",
        "Token requerido",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Paste your Envia API token",
        "Pega tu token de API de Envia",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Test connection",
        "Probar conexión",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Active endpoint",
        "Endpoint activo",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Carriers included when requesting rates.",
        "Transportistas incluidos al solicitar tarifas.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Selected carriers",
        "Transportistas seleccionados",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Click to add carriers...",
        "Haz clic para añadir transportistas...",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "API codes sent to Envia:",
        "Códigos API enviados a Envia:",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Shipping Defaults",
        "Valores predeterminados de envío",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Values used to prefill the quote wizard.",
        "Valores usados para precargar el asistente de cotización.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Select a ship-from contact",
        "Selecciona un contacto de origen",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Label Output",
        "Salida de etiquetas",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Default format and size when generating shipping labels.",
        "Formato y tamaño predeterminados al generar etiquetas de envío.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Label preferences",
        "Preferencias de etiqueta",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Format",
        "Formato",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Size",
        "Tamaño",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "<i class=\"fa fa-check me-1\" title=\"Token configured\"/>",
        "<i class=\"fa fa-check me-1\" title=\"Token configurado\"/>",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "<i class=\"fa fa-exclamation-circle me-1\" title=\"Token missing\"/>",
        "<i class=\"fa fa-exclamation-circle me-1\" title=\"Token faltante\"/>",
    ),
    (
        "model:res.groups.privilege,name:envia.res_groups_privilege_envia",
        "Envia Shipping",
        "Envia Shipping",
    ),
    (
        "code:addons/envia/models/res_config_settings.py:0",
        "Connection successful",
        "Conexión exitosa",
    ),
    (
        "code:addons/envia/models/res_config_settings.py:0",
        "Envia API credentials are valid for the selected environment.",
        "Las credenciales de Envia son válidas para el entorno seleccionado.",
    ),
    (
        "code:addons/envia/models/res_config_settings.py:0",
        "Configure an Envia API token before testing the connection.",
        "Configura un token de API de Envia antes de probar la conexión.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Production mode: labels are real and Envia will charge your account.",
        "Modo producción: las etiquetas son reales y Envia cargará a tu cuenta.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Sandbox mode: safe for testing. Load demo data to try the quote flow quickly.",
        "Modo sandbox: seguro para pruebas. Carga datos demo para probar el flujo de cotización rápidamente.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Token configured. Generate separate tokens for sandbox and production in Envia.",
        "Token configurado. Genera tokens separados para sandbox y producción en Envia.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "Token required. Generate separate tokens for sandbox and production in Envia.",
        "Token requerido. Genera tokens separados para sandbox y producción en Envia.",
    ),
    (
        "model:ir.model.fields,field_description:envia.field_res_config_settings__envia_effective_base_url",
        "Active endpoint",
        "Endpoint activo",
    ),
    (
        "model:ir.model.fields,field_description:envia.field_res_config_settings__envia_default_carriers",
        "API codes sent to Envia",
        "Códigos API enviados a Envia",
    ),
    (
        "model:ir.model.fields,field_description:envia.field_res_config_settings__envia_effective_base_url",
        "Effective Base URL",
        "Endpoint activo",
    ),
    (
        "model:ir.model,name:envia.model_envia_carrier",
        "Envia Carrier",
        "Transportista Envia",
    ),
    (
        "model:ir.model.fields,field_description:envia.field_envia_carrier__color",
        "Color Index",
        "Índice de color",
    ),
    (
        "model:ir.model.constraint,message:envia.constraint_envia_carrier_code_unique",
        "Carrier code must be unique.",
        "El código del transportista debe ser único.",
    ),
    (
        "model:ir.ui.menu,name:envia.menu_envia_connect_store",
        "Connect Store",
        "Conectar tienda",
    ),
    (
        "model:ir.actions.server,name:envia.action_envia_connect_store",
        "Connect Store",
        "Conectar tienda",
    ),
    (
        "model:ir.ui.menu,name:envia.menu_envia_quotes",
        "Quotes",
        "Cotizaciones",
    ),
    (
        "model:ir.ui.menu,name:envia.menu_envia_shipments",
        "Shipments",
        "Envíos",
    ),
    (
        "model:ir.ui.menu,name:envia.menu_envia_configuration",
        "Administration",
        "Administración",
    ),
    (
        "model:ir.ui.menu,name:envia.menu_envia_settings",
        "Settings",
        "Ajustes",
    ),
    (
        "model:ir.ui.menu,name:envia.menu_envia_demo_order",
        "Demo quote order",
        "Pedido de cotización demo",
    ),
    (
        "model:ir.model,name:envia.model_envia_plugin_connect_wizard",
        "Envia Plugin Connect Wizard",
        "Asistente de conexión del plugin Envia",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Connect with Envia.com",
        "Conectar con Envia.com",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Welcome to Envia Shipping",
        "Bienvenido a Envia Shipping",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Connect your Odoo store with Envia.com to quote carriers, create labels, and track shipments without leaving Odoo.",
        "Conecta tu tienda Odoo con Envia.com para cotizar transportistas, crear etiquetas y rastrear envíos sin salir de Odoo.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Connect your store",
        "Conecta tu tienda",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Authorize Envia.com to access your Odoo instance.",
        "Autoriza a Envia.com a acceder a tu instancia de Odoo.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Complete the Envia.com flow",
        "Completa el flujo de Envia.com",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Sign in or register in the Envia.com tab that opens in your browser.",
        "Inicia sesión o regístrate en la pestaña de Envia.com que se abre en tu navegador.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Odoo updates automatically when Envia saves your connection and shipping token.",
        "Odoo se actualiza automáticamente cuando Envia guarda tu conexión y tu token de envío.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Confirm in Odoo",
        "Confirma en Odoo",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Step 2 of 3 · In progress",
        "Paso 2 de 3 · En progreso",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Waiting for Envia.com",
        "Esperando a Envia.com",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Envia.com was opened in a new browser tab. Sign in, authorize your store, and close the tab when you are done.",
        "Envia.com se abrió en una pestaña nueva del navegador. Inicia sesión, autoriza tu tienda y cierra la pestaña cuando termines.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Odoo is ready",
        "Odoo está listo",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Your store connection request was sent to Envia.com.",
        "Tu solicitud de conexión de tienda se envió a Envia.com.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Use the Envia.com browser tab to sign in and authorize access.",
        "Usa la pestaña de Envia.com en tu navegador para iniciar sesión y autorizar el acceso.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Return to Odoo",
        "Vuelve a Odoo",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Close the Envia.com tab when the authorization is complete.",
        "Cierra la pestaña de Envia.com cuando completes la autorización.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "If Envia.com did not open, click Open Envia.com below. This screen updates automatically when Envia saves your API token.",
        "Si Envia.com no se abrió, haz clic en Abrir Envia.com abajo. Esta pantalla se actualiza automáticamente cuando Envia guarda tu token de API.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Waiting for Envia.com to save your connection",
        "Esperando a que Envia.com guarde tu conexión",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Open Envia.com",
        "Abrir Envia.com",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Cancel connection",
        "Cancelar conexión",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Open Settings",
        "Abrir ajustes",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "OAuth connection window",
        "Ventana de conexión OAuth",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "By default Envia.com opens in a new browser tab (recommended). Enable this only if you prefer a smaller pop-up window.",
        "Por defecto Envia.com se abre en una pestaña nueva (recomendado). Actívalo solo si prefieres una ventana emergente más pequeña.",
    ),
    (
        "code:addons/envia/models/res_config_settings.py:0",
        "Open Envia.com in a sized pop-up window",
        "Abrir Envia.com en una ventana emergente",
    ),
    (
        "code:addons/envia/models/res_config_settings.py:0",
        "When disabled (default), Envia.com opens in a new browser tab. When enabled, opens a smaller pop-up window that may require allowing pop-ups in the browser.",
        "Si está desactivado (predeterminado), Envia.com se abre en una pestaña nueva. Si está activado, abre una ventana emergente más pequeña que puede requerir permitir ventanas emergentes en el navegador.",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Waiting for Envia.com",
        "Esperando a Envia.com",
    ),
    (
        "code:addons/envia/static/src/js/envia_plugin_connect_wizard_form.js:0",
        "Envia.com did not open. Click Open Envia.com below.",
        "Envia.com no se abrió. Haz clic en Abrir Envia.com abajo.",
    ),
    (
        "code:addons/envia/static/src/js/envia_plugin_connect_wizard_form.js:0",
        "Envia.com did not open. Click Open Envia.com below or allow pop-ups for this site.",
        "Envia.com no se abrió. Haz clic en Abrir Envia.com abajo o permite ventanas emergentes para este sitio.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Sign in or register in the Envia.com window that opens next.",
        "Inicia sesión o regístrate en la ventana de Envia.com que se abrirá a continuación.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Return here and click <strong>Continue</strong> to verify the connection.",
        "Regresa aquí y haz clic en <strong>Continuar</strong> para verificar la conexión.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Store URL",
        "URL de la tienda",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Envia.com must reach this public URL to validate your store.",
        "Envia.com debe poder acceder a esta URL pública para validar tu tienda.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Connecting...",
        "Conectando...",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Please wait while we connect your store with Envia.com.",
        "Espera mientras conectamos tu tienda con Envia.com.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Connected",
        "Conectado",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Plugin version:",
        "Versión del plugin:",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Integration API Token",
        "Token de API de integración",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "No API token stored. Click Refresh token to generate and save one.",
        "No hay token de API guardado. Haz clic en Actualizar token para generar y guardar uno.",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Go to Quotes",
        "Ir a Cotizaciones",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Connection failed",
        "Conexión fallida",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Try again",
        "Reintentar",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Refresh token",
        "Actualizar token",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.view_envia_plugin_connect_wizard_form",
        "Close",
        "Cerrar",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Welcome to Envia Shipping",
        "Bienvenido a Envia Shipping",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Connecting with Envia.com",
        "Conectando con Envia.com",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Envia.com Connected",
        "Envia.com conectado",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Envia.com Connection Failed",
        "Falló la conexión con Envia.com",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Envia Shipping Setup",
        "Configuración de Envia Shipping",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Not synced — click Refresh token",
        "No sincronizado — haz clic en Actualizar token",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Administrator required",
        "Se requiere administrador",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Only an Odoo administrator can connect Envia.com. Please ask your administrator to complete the connection.",
        "Solo un administrador de Odoo puede conectar Envia.com. Pide a tu administrador que complete la conexión.",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Connect with Envia.com",
        "Conectar con Envia.com",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Missing API key for Envia integration.",
        "Falta la clave API para la integración con Envia.",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Envia integration verification failed. The test endpoint did not return success.",
        "Falló la verificación de la integración con Envia. El endpoint de prueba no devolvió éxito.",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Your Odoo store was connected successfully with Envia.com.",
        "Tu tienda Odoo se conectó correctamente con Envia.com.",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Your Odoo store is connected with Envia.com.",
        "Tu tienda Odoo está conectada con Envia.com.",
    ),
    (
        "code:addons/envia/wizards/envia_plugin_connect_wizard.py:0",
        "Your Odoo store is connected with Envia.com. Click Refresh token to sync the latest connection details.",
        "Tu tienda Odoo está conectada con Envia.com. Haz clic en Actualizar token para sincronizar los últimos detalles de conexión.",
    ),
    (
        "code:addons/envia/static/src/js/envia_oauth_integration_popup.js:0",
        "Connect with Envia.com",
        "Conectar con Envia.com",
    ),
    (
        "code:addons/envia/static/src/js/envia_oauth_integration_popup.js:0",
        "Close",
        "Cerrar",
    ),
    (
        "code:addons/envia/static/src/js/envia_oauth_integration_popup.js:0",
        "Continue",
        "Continuar",
    ),
    (
        "code:addons/envia/static/src/js/envia_oauth_integration_popup.js:0",
        "Verifying...",
        "Verificando...",
    ),
    (
        "code:addons/envia/static/src/js/envia_oauth_integration_popup.js:0",
        "Complete the Envia.com flow in this window, then confirm the connection in Odoo.",
        "Completa el flujo de Envia.com en esta ventana y luego confirma la conexión en Odoo.",
    ),
    (
        "code:addons/envia/static/src/js/envia_oauth_integration_popup.js:0",
        "Envia.com integration",
        "Integración con Envia.com",
    ),
    (
        "model_terms:ir.ui.view,arch_db:envia.res_config_settings_view_form_envia",
        "No API token stored. Open Connect with Envia.com and click Refresh token.",
        "No hay token de API guardado. Abre Conectar con Envia.com y haz clic en Actualizar token.",
    ),
]


def _is_code_reference(reference: str) -> bool:
    return reference.startswith("code:")


def _block_has_odoo_python(block: list[str]) -> bool:
    return any(line == "#. odoo-python" for line in block)


def dedupe_po_file(path: Path) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    seen_msgids: set[tuple[str, bool]] = set()
    removed = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("msgid "):
            block_start = index
            while block_start > 0 and lines[block_start - 1].startswith("#"):
                block_start -= 1
            msgid, msgid_end = parse_msg(lines, index)
            msgstr_end = msgid_end
            if msgid_end < len(lines) and lines[msgid_end].startswith("msgstr "):
                _, msgstr_end = parse_msg(lines, msgid_end)
            block = lines[block_start:msgstr_end]
            is_code = _block_has_odoo_python(block)
            if (msgid, is_code) in seen_msgids:
                removed += 1
                index = msgstr_end
                continue
            seen_msgids.add((msgid, is_code))
            output.extend(lines[block_start:msgstr_end])
            index = msgstr_end
            continue
        output.append(line)
        index += 1
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    return removed


def append_missing_entries(path: Path) -> int:
    content = path.read_text(encoding="utf-8")
    existing_msgids: set[str] = set()
    lines = content.splitlines()
    index = 0
    while index < len(lines):
        if lines[index].startswith("msgid "):
            msgid, index = parse_msg(lines, index)
            if index < len(lines) and lines[index].startswith("msgstr "):
                _, index = parse_msg(lines, index)
            existing_msgids.add(msgid)
            continue
        index += 1
    added = 0
    blocks: list[str] = []
    for reference, msgid, msgstr in APPEND_ENTRIES:
        if msgid in existing_msgids or _is_code_reference(reference):
            continue
        blocks.extend(
            [
                "#. module: envia",
                f"#: {reference}",
                *encode_po_string(msgid, header="msgid"),
                *encode_po_string(msgstr, header="msgstr"),
                "",
            ]
        )
        added += 1
    if blocks:
        path.write_text(content.rstrip() + "\n\n" + "\n".join(blocks), encoding="utf-8")
    return added


def ensure_po_references(path: Path) -> int:
    """Attach missing #: references from APPEND_ENTRIES to existing msgid blocks."""
    wanted: dict[str, list[str]] = {}
    for reference, msgid, _msgstr in APPEND_ENTRIES:
        if _is_code_reference(reference):
            continue
        wanted.setdefault(msgid, []).append(reference)

    lines = path.read_text(encoding="utf-8").splitlines()
    result: list[str] = []
    updated = 0
    index = 0
    while index < len(lines):
        if not lines[index].startswith("msgid "):
            result.append(lines[index])
            index += 1
            continue
        block_start = index
        while block_start > 0 and lines[block_start - 1].startswith("#"):
            block_start -= 1
        msgid, msgid_end = parse_msg(lines, index)
        msgstr_end = msgid_end
        if msgid_end < len(lines) and lines[msgid_end].startswith("msgstr "):
            _, msgstr_end = parse_msg(lines, msgid_end)
        block = lines[block_start:msgstr_end]
        if msgid in wanted:
            existing_refs = {line[3:].strip() for line in block if line.startswith("#:")}
            missing_refs = [ref for ref in wanted[msgid] if ref not in existing_refs]
            if missing_refs:
                msgid_offset = index - block_start
                block = block[:msgid_offset] + [f"#: {ref}" for ref in missing_refs] + block[msgid_offset:]
                updated += 1
        result.extend(block)
        index = msgstr_end
    path.write_text("\n".join(result) + "\n", encoding="utf-8")
    return updated


def ensure_code_entries(path: Path) -> int:
    """Ensure Python code translations exist as separate odoo-python blocks."""
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    existing_code_msgids: set[str] = set()
    index = 0
    while index < len(lines):
        if lines[index].startswith("msgid "):
            block_start = index
            while block_start > 0 and lines[block_start - 1].startswith("#"):
                block_start -= 1
            msgid, msgid_end = parse_msg(lines, index)
            msgstr_end = msgid_end
            if msgid_end < len(lines) and lines[msgid_end].startswith("msgstr "):
                _, msgstr_end = parse_msg(lines, msgid_end)
            if _block_has_odoo_python(lines[block_start:msgstr_end]):
                existing_code_msgids.add(msgid)
            index = msgstr_end
            continue
        index += 1

    blocks: list[str] = []
    added = 0
    for reference, msgid, msgstr in APPEND_ENTRIES:
        if not _is_code_reference(reference) or msgid in existing_code_msgids:
            continue
        blocks.extend(
            [
                "#. module: envia",
                "#. odoo-python",
                f"#: {reference}",
                *encode_po_string(msgid, header="msgid"),
                *encode_po_string(msgstr, header="msgstr"),
                "",
            ]
        )
        existing_code_msgids.add(msgid)
        added += 1
    if blocks:
        path.write_text(content.rstrip() + "\n\n" + "\n".join(blocks), encoding="utf-8")
    return added


def decode_po_string(lines: list[str]) -> str:
    parts: list[str] = []
    for line in lines:
        match = re.match(r'"(.*)"\s*$', line)
        if match:
            parts.append(
                match.group(1)
                .replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
            )
    return "".join(parts)


def encode_po_string(value: str, header: str = "msgstr") -> list[str]:
    if not value:
        return [f'{header} ""']
    if "\n" not in value and len(value) < 70:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return [f'{header} "{escaped}"']
    lines = [f'{header} ""']
    chunks = value.split("\n")
    for index, chunk in enumerate(chunks):
        suffix = "\\n" if index < len(chunks) - 1 else ""
        escaped = chunk.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'"{escaped}{suffix}"')
    return lines


def parse_msg(lines: list[str], start: int) -> tuple[str, int]:
    header = lines[start].split(" ", 1)[0]
    if lines[start].endswith('""') and not lines[start].startswith(f'{header} ""'):
        pass
    if lines[start] == f'{header} ""':
        body_lines = []
        index = start + 1
        while index < len(lines) and lines[index].startswith('"'):
            body_lines.append(lines[index])
            index += 1
        return decode_po_string(body_lines), index
    match = re.match(rf'{header} "(.*)"\s*$', lines[start])
    if not match:
        raise ValueError(f"Invalid PO line: {lines[start]}")
    return (
        match.group(1)
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\\\", "\\"),
        start + 1,
    )


def fill_po_file(path: Path, language: str) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    translated = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("msgid "):
            msgid, next_index = parse_msg(lines, index)
            output.extend(lines[index:next_index])
            index = next_index
            if index >= len(lines) or not lines[index].startswith("msgstr "):
                raise ValueError(f"Missing msgstr after msgid near line {index}")
            _, msgstr_end = parse_msg(lines, index)
            translation = TRANSLATIONS.get(msgid)
            if msgid and translation is not None:
                translated += 1
                output.extend(encode_po_string(translation))
            else:
                output.extend(lines[index:msgstr_end])
            index = msgstr_end
            continue
        if line.startswith('"Plural-Forms:'):
            output.append('"Plural-Forms: nplurals=2; plural=(n != 1);\\n"')
            index += 1
            continue
        if line == '"Language-Team: \\n"' and language:
            output.append(f'"Language-Team: Spanish\\n"')
            output.append(f'"Language: {language}\\n"')
            index += 1
            continue
        output.append(line)
        index += 1
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    return translated


def export_pot_file(po_path: Path, pot_path: Path) -> int:
    lines = po_path.read_text(encoding="utf-8").splitlines()
    header_end = 0
    for index, line in enumerate(lines):
        if line.startswith("#. module:"):
            header_end = index
            break
    header = "\n".join(lines[:header_end]).strip() + "\n\n"
    blocks: list[str] = []
    index = header_end
    while index < len(lines):
        if not lines[index].startswith("#. module:"):
            index += 1
            continue
        block_start = index
        while index < len(lines) and not lines[index].startswith("msgid "):
            index += 1
        if index >= len(lines):
            break
        msgid, msgid_end = parse_msg(lines, index)
        msgstr_end = msgid_end
        if msgid_end < len(lines) and lines[msgid_end].startswith("msgstr "):
            _, msgstr_end = parse_msg(lines, msgid_end)
        blocks.extend(
            [
                *lines[block_start:index],
                *encode_po_string(msgid, header="msgid"),
                'msgstr ""',
                "",
            ]
        )
        index = msgstr_end
    pot_path.write_text(header + "\n".join(blocks), encoding="utf-8")
    return len(blocks)


def main() -> None:
    base = Path(__file__).resolve().parent
    es_419 = base / "es_419.po"
    max_po_bytes = 5 * 1024 * 1024
    if es_419.stat().st_size > max_po_bytes:
        raise SystemExit(
            f"{es_419.name} is too large ({es_419.stat().st_size} bytes). "
            "Re-export with: odoo i18n export -d DB -l es_419 -o es_419.po envia"
        )
    deduped = dedupe_po_file(es_419)
    appended = append_missing_entries(es_419)
    merged = ensure_po_references(es_419)
    coded = ensure_code_entries(es_419)
    count = fill_po_file(es_419, "es_419")
    export_pot_file(es_419, base / "envia.pot")
    es = base / "es.po"
    shutil.copy(es_419, es)
    fill_po_file(es, "es_ES")
    print(
        f"Deduped {deduped}, appended {appended}, merged {merged} references, "
        f"added {coded} code entries, filled {count} translations, "
        f"synced pot from {es_419.name}"
    )


if __name__ == "__main__":
    main()
