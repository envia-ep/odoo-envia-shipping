# Envia.com Quote and Shipping

Odoo 19 addon that connects your store with [Envia.com](https://envia.com)
for live carrier rates on sales orders (native **Add shipping** flow).

## Description

| Technical name | Display name | Role |
| --- | --- | --- |
| `envia` | Envia.com Quote and Shipping | Main application: UI, settings, OAuth wizards, quotes, and `delivery.carrier` rates. |

From Apps / Odoo.sh, install only **Envia.com** (`envia`). Standard Odoo
dependencies install automatically.

### `envia`

- **Category:** Inventory/Delivery
- **Application:** yes (`application: True`)
- **Depends:** `base`, `mail`, `onboarding`, `sale`, `stock`, `sale_stock`,
  `delivery`, `website_sale` (and related delivery apps)

**Features**

- OAuth connection between Odoo and Envia.com (plugin / welcome wizard).
- Live shipping rates from Envia.com inside **Add shipping** on sale orders.
- Compare carrier services (DHL, FedEx, Estafeta, Paquetexpress, and more).
- Home delivery and branch pickup/drop-off routes.
- Default origin address and preferred carriers in Settings.
- Package weight from product master data for accurate quotes.
- Shipping API token stored via the Envia.com integration callback.

Label creation and tracking are **not** included in this version.

## Installation

### Odoo.sh / Apps Store

1. Use **Deploy on Odoo.sh** from Apps (or put this repo on the project git).
2. Update Apps List → install **Envia.com** (`envia`) only.

### On-premise

1. Put `envia/` on the Odoo `addons_path`.
2. Install **Envia.com** (`envia`) from Apps.

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
| Odoo Online (odoo.com SaaS) | No — no custom addons |

## Authors

Envia.com

## License

LGPL-3 — © 2026 Envia.com.
