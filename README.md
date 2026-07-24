# Envia.com Quote and Shipping

Odoo 19 addons package that connects your store with [Envia.com](https://envia.com)
for live carrier rates on sales orders (native **Add shipping** flow).

## Description

The package contains two installable addons that must stay on the same
`addons_path`:

| Technical name | Display name | Role |
| --- | --- | --- |
| `envia` | Envia.com Quote and Shipping | Main application: UI, settings, OAuth wizards, quotes, and `delivery.carrier` rates. |
| `envia_http` | Envia HTTP Bridge | Hidden technical bridge: HTTP/RPC entry points loaded **before** a database is selected. |

`envia` depends on `envia_http`. From Apps, install only **Envia.com** (`envia`);
Odoo installs `envia_http` and other Python dependencies automatically.
That is **not** enough for OAuth: a server administrator must also list
`envia_http` in `server_wide_modules` and restart Odoo so nodb routes exist.

### `envia`

- **Category:** Inventory/Delivery
- **Application:** yes (`application: True`)
- **Depends:** `base`, `mail`, `onboarding`, `sale`, `stock`, `sale_stock`,
  `delivery`, `website_sale`, `envia_http`

**Features**

- OAuth connection between Odoo and Envia.com (plugin / welcome wizard).
- Live shipping rates from Envia.com inside **Add shipping** on sale orders.
- Compare carrier services (DHL, FedEx, Estafeta, Paquetexpress, and more).
- Home delivery and branch pickup/drop-off routes.
- Default origin address and preferred carriers in Settings.
- Package weight from product master data for accurate quotes.
- Shipping API token stored via the Envia.com integration callback.

Label creation and tracking are **not** included in this version.

### `envia_http`

- **Category:** Hidden
- **Application:** no
- **Depends:** `web`
- **Load mode:** must appear in `server_wide_modules` (see Installation)

Exposes Envia integration endpoints before a database is selected. Routes
delegate to `envia` when that module is installed; otherwise they return HTTP
503. Full route list and verification steps:
[`envia_http/README.md`](envia_http/README.md).

## Installation

1. Put this repository root on the Odoo `addons_path`:

   ```
   <repository root>/
   ├── envia/
   └── envia_http/
   ```

2. In `odoo.conf`, add the HTTP bridge to `server_wide_modules` and restart Odoo:

   ```ini
   server_wide_modules = web,base,envia_http
   ```

3. In Apps, install **Envia.com** (`envia`) only.

## Configuration

1. Open **Envia.com → Settings** (or the welcome / connect wizard).
2. Generate the Odoo API key and complete the Envia.com OAuth connection.
3. Set the default ship-from (origin) address and preferred carriers.
4. On products, set **weight** (Inventory tab) before quoting; missing values
   fall back to 1 kg.

This package uses Envia.com **production** API hosts by default. Developers may
override with `ENVIA_ENVIRONMENT=sandbox` and related `ENVIA_*` environment
variables (see `docker-compose.yml`).

## Usage

1. Open a confirmed quotation / sales order.
2. Use **Add shipping** and select the Envia.com carrier.
3. Compare returned rates and apply the chosen service to the order.

## Compatibility

| Platform | Supported |
| --- | --- |
| Odoo 19 on-premise (Community / Enterprise) | Yes |
| Odoo.sh | Yes |
| Odoo Online (odoo.com SaaS) | No — requires `server_wide_modules` / custom addons |

## Authors

Envia.com

## License

Proprietary — © 2026 Envia.com. All rights reserved.
