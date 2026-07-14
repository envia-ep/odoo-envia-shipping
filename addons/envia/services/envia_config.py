from __future__ import annotations

import os

from odoo import _
from odoo.exceptions import UserError

ENVIA_ENVIRONMENT_ENV = "ENVIA_ENVIRONMENT"
ENVIA_ENVIRONMENT_PARAM = "envia.environment"
API_BASE_URL_ENV = "ENVIA_API_BASE_URL"
QUERIES_BASE_URL_ENV = "ENVIA_QUERIES_BASE_URL"
CHECKOUT_PATH_ENV = "ENVIA_CHECKOUT_PATH"

SANDBOX_API_BASE_URL = "https://api-test.envia.com/"
PRODUCTION_API_BASE_URL = "https://api.envia.com/"
SANDBOX_QUERIES_BASE_URL = "https://queries-test.envia.com/"
PRODUCTION_QUERIES_BASE_URL = "https://queries.envia.com/"
DEFAULT_CHECKOUT_PATH = "v2/checkout/odoo/{shop_id}"


def get_envia_environment_from_env() -> str | None:
    value = os.environ.get(ENVIA_ENVIRONMENT_ENV, "").strip().lower()
    if value in ("sandbox", "production"):
        return value
    return None


def get_envia_environment_from_config(env) -> str | None:
    value = env["ir.config_parameter"].sudo().get_param(ENVIA_ENVIRONMENT_PARAM, "")
    value = (value or "").strip().lower()
    if value in ("sandbox", "production"):
        return value
    return None


def resolve_envia_environment(company) -> str:
    if env_value := get_envia_environment_from_env():
        return env_value
    if company.envia_environment:
        return company.envia_environment
    if config_value := get_envia_environment_from_config(company.env):
        return config_value
    raise UserError(
        _(
            "Envia environment is not configured. Set system parameter %s "
            "(module data) or company Envia Environment in Settings."
        )
        % ENVIA_ENVIRONMENT_PARAM
    )


def is_envia_sandbox(company) -> bool:
    return resolve_envia_environment(company) == "sandbox"


def oauth_registration_sandbox() -> bool:
    # ponytail: OAuth/eshop registration keeps sandbox=false; ENVIA_ENVIRONMENT
    # only switches api.envia.com vs api-test (shipping API).
    return False


def _normalize_base_url(url: str) -> str:
    return url.rstrip("/") + "/"


def get_envia_api_base_url_from_env() -> str | None:
    value = os.environ.get(API_BASE_URL_ENV, "").strip()
    return _normalize_base_url(value) if value else None


def get_envia_queries_base_url_from_env() -> str | None:
    value = os.environ.get(QUERIES_BASE_URL_ENV, "").strip()
    return _normalize_base_url(value) if value else None


def get_envia_checkout_path(shop_id: str) -> str:
    template = os.environ.get(CHECKOUT_PATH_ENV, "").strip() or DEFAULT_CHECKOUT_PATH
    return template.format(shop_id=shop_id)


def get_envia_api_base_url(company) -> str:
    env_url = get_envia_api_base_url_from_env()
    if env_url:
        return env_url
    if company.envia_base_url:
        return _normalize_base_url(company.envia_base_url)
    if resolve_envia_environment(company) == "production":
        return PRODUCTION_API_BASE_URL
    return SANDBOX_API_BASE_URL


def get_envia_queries_base_url(company) -> str:
    env_url = get_envia_queries_base_url_from_env()
    if env_url:
        return env_url
    if resolve_envia_environment(company) == "production":
        return PRODUCTION_QUERIES_BASE_URL
    return SANDBOX_QUERIES_BASE_URL
