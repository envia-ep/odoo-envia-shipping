# Odoo Live Shipping Rates

Odoo 19 integration with [Envia.com](https://envia.com) for live shipping rate quotes, shipment creation, label generation, and tracking.

## Overview

This repository provides a local development environment and a custom Odoo application module that connects your store to Envia.com shipping services.

**Planned capabilities:**

- OAuth connection to Envia.com
- Multi-carrier shipping rate quotes
- Shipment creation and label download
- Shipment tracking (manual and scheduled sync)
- Guided onboarding for first-time setup

## Tech Stack

| Component    | Version        |
| ------------ | -------------- |
| Odoo         | 19             |
| PostgreSQL   | 16             |
| Orchestration| Docker Compose |

## Repository Structure

```
.
├── addons/           # Custom Odoo modules
├── config/           # Odoo server configuration
├── docker-compose.yml
└── README.md
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

## Getting Started

> Full setup instructions and the integration module are delivered via feature branches and merged into `main` through pull requests.

1. Clone the repository.
2. Check out the relevant feature branch.
3. Start the stack:

   ```bash
   docker compose up -d
   ```

4. Open Odoo at [http://localhost:8069](http://localhost:8069).

## Production (Envia OAuth callback)

The Envia integration callback must work without a logged-in session and without `X-Odoo-Database`. Configure this **the same way locally and in production**:

1. Keep `server_wide_modules = web,base,envia_http` in `config/odoo.conf` (see the file).
2. Restart Odoo after any config change.
3. Set **web.base.url** to your public HTTPS domain.
4. Verify: `curl -X POST https://your-domain/envia/integration/callback` must return **401**, not **404**.

The `envia` module stays uninstallable from Apps; only the tiny `envia_http` bridge is server-wide.

## Branching

| Branch   | Purpose                                      |
| -------- | -------------------------------------------- |
| `main`   | Stable baseline                              |
| Feature  | Active development (e.g. `PROJ-5144`)        |

Changes are integrated into `main` via pull request after review.

## License

[LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.html)

## Author

Alejandro Prado
