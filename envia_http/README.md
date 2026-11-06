# Envia HTTP Bridge

**Optional** server-wide Odoo module for **multi-database on-premise** installs.
Exposes Envia integration endpoints **before** a database is selected.

On **Odoo.sh** (and other single-database setups), install only `envia` — this
bridge is not required. `envia` no longer depends on `envia_http`.

## When to use

Use this module if Envia.com must call Odoo without `X-Odoo-Database` / before
a DB is selected (typical multi-DB on-premise).

## Installation (on-premise multi-DB)

1. Put `envia` and `envia_http` on the same Odoo `addons_path`.
2. Add this module to `server_wide_modules` in `odoo.conf`:

```ini
server_wide_modules = web,base,envia_http
```

3. Restart Odoo.
4. Install `envia_http`, then install **Envia.com** (`envia`).

## Routes

| Route | Purpose |
| --- | --- |
| `POST /envia/integration/callback` | Receives the Envia.com integration result after OAuth |
| `POST /envia/integration/connect` | Starts the Envia.com plugin connection handshake |
| `POST /jsonrpc` | JSON-RPC proxy used by Envia.com to validate the Odoo store |
| `POST /xmlrpc/2/common` | XML-RPC common proxy for store validation |
| `POST /xmlrpc/2/object` | XML-RPC object proxy for integration calls without a selected database |

Each route delegates to the `envia` module when it is installed. If `envia` is
missing from the addons path, the bridge returns HTTP 503.

## Verify

```bash
curl -X POST https://<your-domain>/envia/integration/callback
```

Expect a JSON error response (not 404) when the bridge is loaded server-wide.
