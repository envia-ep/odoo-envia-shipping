# Envia.com Quote and Shipping

Odoo 19 package for live shipping rates with [Envia.com](https://envia.com).

## Layout

```
envia_com_quote_and_shipping/
├── envia/        # Envia.com Quote and Shipping
└── envia_http/   # Server-wide OAuth / integration bridge
```

Put `envia_com_quote_and_shipping/` on your Odoo `addons_path`, install **envia**, then set:

```ini
server_wide_modules = web,base,envia_http
```

Supported on **Odoo.sh** and **on-premise**. Not compatible with standard Odoo Online (SaaS).

## License

Proprietary — © 2026 Envia.com. All rights reserved.
