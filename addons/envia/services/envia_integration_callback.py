from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from odoo import _

from .envia_plugin_setup import get_pending_setup_company_id, lookup_integration_database

CALLBACK_ROUTE = "/envia/integration/callback"
CONNECT_ROUTE = "/envia/integration/connect"
SUCCESS_STATUSES = frozenset({"success", "ok", "connected"})
ODOO_API_KEY_FIELD_NAMES = ("apiKey", "api_key", "odoo_api_key")
ODOO_DATABASE_FIELD_NAMES = ("database", "db")


def _allowed_integration_databases() -> list[str]:
    """List databases for nodb integration routes (list_db is often disabled publicly)."""
    import odoo.http as http
    import odoo.service.db as db_service

    return http.db_filter(db_service.list_dbs(force=True))


def resolve_connect_database(api_key: str, db_query: str | None = None) -> str:
    """Resolve the Odoo database from ?db=, request.db, or the Authorization API key."""
    import odoo.http as http

    database = _extract_database_name(db_query, {})
    if database:
        if database not in http.db_filter([database]):
            raise EnviaIntegrationCallbackError(
                "invalid_database",
                _("Database is not allowed on this server."),
                http_status=403,
            )
        return database

    if http.request and http.request.db and http.request.db in http.db_filter([http.request.db]):
        return http.request.db

    api_key = (api_key or "").strip()
    if not api_key:
        raise EnviaIntegrationCallbackError(
            "missing_authorization",
            _("Integration connect requires the Odoo API key in the Authorization header."),
            http_status=401,
        )

    allowed_databases = _allowed_integration_databases()
    database = lookup_integration_database(api_key)
    if database and database in allowed_databases:
        return database

    database = _find_database_for_connect_api_key(api_key, allowed_databases)
    if database:
        return database

    database = _find_database_for_api_key(api_key, allowed_databases)
    if database:
        return database

    if len(allowed_databases) == 1:
        return allowed_databases[0]

    raise EnviaIntegrationCallbackError(
        "missing_database",
        _("Could not resolve the Odoo database for this API key."),
        http_status=400,
    )


@dataclass(frozen=True)
class EnviaIntegrationCallbackPayload:
    status: str
    hash: str  # Envia shipping API token (api.envia.com Bearer)
    shop: str
    company: int
    user: int
    api_key: str  # Odoo API key generated when connecting with Envia.com
    database: str | None = None  # Optional; resolved from the request when omitted
    message: str | None = None


class EnviaIntegrationCallbackError(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        http_status: int = 400,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.http_status = http_status


def get_integration_database_name(env) -> str:
    """Return the active Odoo database name for the current environment."""
    return env.cr.dbname


def build_callback_url(env) -> str:
    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
    query = urlencode({"db": get_integration_database_name(env)})
    return f"{base_url}{CALLBACK_ROUTE}?{query}"


def build_connect_url(env) -> str:
    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
    query = urlencode({"db": get_integration_database_name(env)})
    return f"{base_url}{CONNECT_ROUTE}?{query}"


def _extract_database_name(
    db_query: str | None,
    payload_data: dict[str, Any],
) -> str:
    if db_query not in (None, False, ""):
        return str(db_query).strip()
    for field_name in ODOO_DATABASE_FIELD_NAMES:
        value = payload_data.get(field_name)
        if value not in (None, False, ""):
            return str(value).strip()
    store = payload_data.get("store") if isinstance(payload_data.get("store"), dict) else {}
    access = store.get("access") if isinstance(store.get("access"), dict) else {}
    for container in (store, access):
        for field_name in ODOO_DATABASE_FIELD_NAMES:
            value = container.get(field_name)
            if value not in (None, False, ""):
                return str(value).strip()
    return ""


def _callback_api_key_candidates(
    header_api_key: str | None,
    payload_data: dict[str, Any],
) -> list[str]:
    """Return unique Odoo API key candidates from the Authorization header and JSON body."""
    candidates: list[str] = []
    for key in ((header_api_key or "").strip(), _extract_odoo_api_key(payload_data)):
        if key and key not in candidates:
            candidates.append(key)
    return candidates


def _find_database_for_connect_api_key(api_key: str, database_names: list[str]) -> str | None:
    """Return the database saved when the user clicked Connect with Envia.com."""
    import odoo
    from odoo import api
    from odoo.modules.registry import Registry

    api_key = (api_key or "").strip()
    if not api_key:
        return None
    for db_name in database_names:
        try:
            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = api.Environment(cr, odoo.SUPERUSER_ID, {})
                if env["res.company"].sudo().search_count(
                    [("envia_integration_api_key", "=", api_key)],
                    limit=1,
                ):
                    return db_name
        except Exception:
            continue
    return None


def _find_database_for_api_key(api_key: str, database_names: list[str]) -> str | None:
    """Return the database that owns the given Odoo API key, if any."""
    import odoo
    from odoo import api
    from odoo.modules.registry import Registry

    api_key = (api_key or "").strip()
    if not api_key:
        return None
    for db_name in database_names:
        try:
            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = api.Environment(cr, odoo.SUPERUSER_ID, {})
                if env["res.users.apikeys"].sudo()._check_credentials(scope="rpc", key=api_key):
                    return db_name
        except Exception:
            continue
    return None


def _find_database_for_api_key_candidates(
    api_keys: list[str],
    database_names: list[str],
) -> str | None:
    for api_key in api_keys:
        database = _find_database_for_connect_api_key(api_key, database_names)
        if database:
            return database
        database = _find_database_for_api_key(api_key, database_names)
        if database:
            return database
    return None


def _odoo_api_key_in_database(api_key: str, database_name: str) -> bool:
    import odoo
    from odoo import api
    from odoo.modules.registry import Registry

    api_key = (api_key or "").strip()
    if not api_key:
        return False
    try:
        registry = Registry(database_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            if env["res.company"].sudo().search_count(
                [("envia_integration_api_key", "=", api_key)],
                limit=1,
            ):
                return True
            return bool(
                env["res.users.apikeys"].sudo()._check_credentials(scope="rpc", key=api_key)
            )
    except Exception:
        return False


def resolve_callback_odoo_api_key(
    header_api_key: str | None,
    payload_data: dict[str, Any],
    database_name: str,
) -> str:
    import odoo.http as http

    if database_name not in http.db_filter([database_name]):
        raise EnviaIntegrationCallbackError(
            "invalid_database",
            _("Integration callback database is not allowed on this server."),
            http_status=403,
        )
    for key in _callback_api_key_candidates(header_api_key, payload_data):
        if _odoo_api_key_in_database(key, database_name):
            return key
    raise EnviaIntegrationCallbackError(
        "missing_api_key",
        _("Integration callback field apiKey (Odoo API key) is required."),
        http_status=401,
    )


def resolve_callback_database(
    db_query: str | None,
    payload_data: dict[str, Any],
    *,
    api_key: str | None = None,
) -> str:
    import odoo.http as http

    database = _extract_database_name(db_query, payload_data)
    if database:
        if database not in http.db_filter([database]):
            raise EnviaIntegrationCallbackError(
                "invalid_database",
                _("Integration callback database is not allowed on this server."),
                http_status=403,
            )
        return database

    allowed_databases = _allowed_integration_databases()
    api_key_candidates = _callback_api_key_candidates(api_key, payload_data)

    for key in api_key_candidates:
        database = lookup_integration_database(key)
        if database and database in allowed_databases:
            return database

    database = _find_database_for_api_key_candidates(api_key_candidates, allowed_databases)
    if database:
        return database

    if len(allowed_databases) == 1:
        return allowed_databases[0]

    if http.request and http.request.db and http.request.db in allowed_databases:
        return http.request.db

    raise EnviaIntegrationCallbackError(
        "missing_database",
        _(
            "Integration callback could not resolve the Odoo database. "
            "It must match the database sent when connecting with Envia.com."
        ),
        http_status=400,
    )


def is_success_status(status: str) -> bool:
    return (status or "").strip().lower() in SUCCESS_STATUSES


def _extract_odoo_api_key(data: dict[str, Any]) -> str:
    for field_name in ODOO_API_KEY_FIELD_NAMES:
        value = data.get(field_name)
        if value not in (None, False, ""):
            return str(value).strip()
    return ""


AUTHORIZATION_SCHEMES = frozenset({"bearer", "token"})


def extract_bearer_api_key(authorization_header: str | None) -> str:
    authorization_header = (authorization_header or "").strip()
    if not authorization_header:
        raise EnviaIntegrationCallbackError(
            "missing_authorization",
            _("Integration callback requires the Odoo API key in the Authorization header."),
            http_status=401,
        )
    parts = authorization_header.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() in AUTHORIZATION_SCHEMES:
        api_key = parts[1].strip()
    else:
        api_key = authorization_header
    if not api_key:
        raise EnviaIntegrationCallbackError(
            "missing_authorization",
            _("Integration callback requires the Odoo API key in the Authorization header."),
            http_status=401,
        )
    return api_key


def parse_callback_payload(
    data: dict[str, Any],
    *,
    bearer_api_key: str | None = None,
) -> EnviaIntegrationCallbackPayload:
    if not isinstance(data, dict):
        raise EnviaIntegrationCallbackError(
            "invalid_payload",
            _("Integration callback body must be a JSON object."),
        )

    missing_fields = [
        field_name
        for field_name in ("status", "hash", "shop", "company", "user")
        if field_name not in data
    ]
    body_api_key = _extract_odoo_api_key(data)
    api_key = (bearer_api_key or "").strip() or body_api_key
    if not api_key:
        missing_fields.append("apiKey")

    if missing_fields:
        raise EnviaIntegrationCallbackError(
            "invalid_payload",
            _("Integration callback is missing required fields: %s") % ", ".join(missing_fields),
        )

    if bearer_api_key and body_api_key and body_api_key != bearer_api_key:
        raise EnviaIntegrationCallbackError(
            "api_key_mismatch",
            _("Integration callback apiKey does not match the Authorization bearer token."),
            http_status=403,
        )

    try:
        company_id = int(data["company"])
        user_id = int(data["user"])
    except (TypeError, ValueError) as error:
        raise EnviaIntegrationCallbackError(
            "invalid_payload",
            _("Integration callback fields company and user must be integers."),
        ) from error

    status = str(data["status"]).strip()
    if not status:
        raise EnviaIntegrationCallbackError(
            "invalid_payload",
            _("Integration callback field status cannot be empty."),
        )

    hash_value = str(data.get("hash") or "").strip()
    shop_value = str(data.get("shop") or "").strip()
    database_value = _extract_database_name(None, data) or None
    message_value = data.get("message")
    message = str(message_value).strip() if message_value not in (None, False, "") else None

    return EnviaIntegrationCallbackPayload(
        status=status,
        hash=hash_value,
        shop=shop_value,
        company=company_id,
        user=user_id,
        api_key=api_key,
        database=database_value,
        message=message,
    )


def authenticate_integration_callback(env, api_key: str) -> int:
    api_key = (api_key or "").strip()
    if not api_key:
        raise EnviaIntegrationCallbackError(
            "missing_api_key",
            _("Integration callback field apiKey (Odoo API key) is required."),
            http_status=401,
        )
    try:
        user_id = env["res.users.apikeys"].sudo()._check_credentials(scope="rpc", key=api_key)
    except Exception as error:
        raise EnviaIntegrationCallbackError(
            "invalid_api_key",
            _("Integration callback apiKey is invalid or expired."),
            http_status=401,
        ) from error
    if not user_id:
        raise EnviaIntegrationCallbackError(
            "invalid_api_key",
            _("Integration callback apiKey is invalid or expired."),
            http_status=401,
        )
    return user_id


def validate_envia_store_credentials(
    database_name: str,
    api_key: str,
    email: str | None = None,
) -> int | None:
    """Validate Odoo API key for Envia.com store setup (legacy /jsonrpc flow)."""
    import odoo
    import odoo.http as http
    from odoo import api
    from odoo.modules.registry import Registry

    database_name = (database_name or "").strip()
    api_key = (api_key or "").strip()
    if not database_name or not api_key:
        return None
    if database_name not in http.db_filter([database_name]):
        return None
    try:
        registry = Registry(database_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            user_id = env["res.users.apikeys"].sudo()._check_credentials(scope="rpc", key=api_key)
            if not user_id:
                return None
            if email and env["res.users"].browse(user_id).login != str(email).strip():
                return None
            return user_id
    except Exception:
        return None


def handle_envia_jsonrpc_request(raw_body: bytes | str, db_query: str | None = None) -> tuple[int, dict]:
    """Answer Envia.com credential checks on POST /jsonrpc without a selected database."""
    import json

    try:
        if isinstance(raw_body, bytes):
            payload = json.loads((raw_body or b"{}").decode("utf-8"))
        else:
            payload = json.loads(raw_body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 400, {"jsonrpc": "2.0", "id": None, "error": {"code": 400, "message": "Invalid JSON"}}

    if not isinstance(payload, dict):
        return 400, {"jsonrpc": "2.0", "id": None, "error": {"code": 400, "message": "Invalid payload"}}

    request_id = payload.get("id")
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    if (
        payload.get("method") != "call"
        or params.get("service") != "common"
        or params.get("method") != "authenticate"
    ):
        return 404, {"jsonrpc": "2.0", "id": request_id, "error": {"code": 404, "message": "Not found"}}

    args = params.get("args") if isinstance(params.get("args"), list) else []
    if len(args) < 3:
        return 400, {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": 400, "message": "Invalid authenticate args"},
        }

    database_name = (db_query or args[0] or "").strip()
    email = str(args[1] or "").strip()
    api_key = str(args[2] or "").strip()
    user_id = validate_envia_store_credentials(database_name, api_key, email)
    if not user_id:
        return 200, {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": 200,
                "message": "Odoo Server Error",
                "data": {"name": "odoo.exceptions.AccessDenied"},
            },
        }
    return 200, {"jsonrpc": "2.0", "id": request_id, "result": user_id}


def handle_envia_xmlrpc_common_request(
    raw_body: bytes | str,
    db_query: str | None = None,
) -> tuple[int, bytes]:
    """Answer Envia.com credential checks on POST /xmlrpc/2/common without a selected database."""
    import xmlrpc.client

    try:
        body = raw_body if isinstance(raw_body, bytes) else (raw_body or "").encode("utf-8")
        params, method_name = xmlrpc.client.loads(body)
    except Exception:
        return 400, xmlrpc.client.dumps(
            xmlrpc.client.Fault(1, "Invalid XML-RPC payload"),
            methodresponse=True,
            allow_none=True,
        )

    if method_name == "version":
        import odoo.release as release

        version_info = {
            "server_version": release.version,
            "server_version_info": release.version_info,
            "server_serie": release.serie,
            "protocol_version": 1,
        }
        return 200, xmlrpc.client.dumps((version_info,), methodresponse=True, allow_none=True)

    if method_name == "authenticate":
        if len(params) < 3:
            return 200, xmlrpc.client.dumps((False,), methodresponse=True, allow_none=True)
        database_name = (db_query or params[0] or "").strip()
        email = str(params[1] or "").strip()
        api_key = str(params[2] or "").strip()
        user_id = validate_envia_store_credentials(database_name, api_key, email)
        return 200, xmlrpc.client.dumps((user_id or False,), methodresponse=True, allow_none=True)

    return 404, xmlrpc.client.dumps(
        xmlrpc.client.Fault(404, f"Method {method_name} not found"),
        methodresponse=True,
        allow_none=True,
    )


def _resolve_integration_callback_company(env, payload: EnviaIntegrationCallbackPayload):
    """Resolve the Odoo company from DB state instead of Envia's company id."""
    company_model = env["res.company"]
    allowed_company_ids = env.user.company_ids.ids

    pending_company_id = get_pending_setup_company_id(env)
    if pending_company_id:
        company = company_model.browse(pending_company_id)
        if company.exists() and company.id in allowed_company_ids:
            return company

    company = company_model.search(
        [("envia_integration_api_key", "=", payload.api_key)],
        limit=1,
    )
    if company and company.id in allowed_company_ids:
        return company

    if payload.shop:
        company = company_model.search([("envia_shop_id", "=", payload.shop)], limit=1)
        if company and company.id in allowed_company_ids:
            return company

    company = company_model.browse(payload.company)
    if company.exists() and company.id in allowed_company_ids:
        return company

    if env.user.company_id and env.user.company_id.id in allowed_company_ids:
        return env.user.company_id

    return company_model.browse()


def apply_integration_callback(
    env,
    payload: EnviaIntegrationCallbackPayload,
    *,
    bearer_api_key: str | None = None,
    resolved_database: str | None = None,
) -> dict[str, Any]:
    if resolved_database and payload.database and payload.database != resolved_database:
        raise EnviaIntegrationCallbackError(
            "database_mismatch",
            _("Integration callback database does not match the selected Odoo database."),
            http_status=400,
        )

    if bearer_api_key and bearer_api_key != payload.api_key:
        raise EnviaIntegrationCallbackError(
            "api_key_mismatch",
            _("Integration callback apiKey does not match the Authorization bearer token."),
            http_status=403,
        )

    if env.user.id != payload.user:
        raise EnviaIntegrationCallbackError(
            "user_mismatch",
            _("Integration callback user does not match the authenticated Odoo API key user."),
            http_status=403,
        )

    company = _resolve_integration_callback_company(env, payload)
    if not company:
        raise EnviaIntegrationCallbackError(
            "company_not_found",
            _("Integration callback company was not found."),
            http_status=404,
        )

    if is_success_status(payload.status):
        if not payload.hash:
            raise EnviaIntegrationCallbackError(
                "invalid_payload",
                _("Integration callback field hash (Envia API token) is required when status is success."),
            )
        return company._envia_apply_integration_callback_success(
            hash_token=payload.hash,
            shop_id=payload.shop,
            api_key=payload.api_key,
        )

    error_message = payload.message or payload.status
    return company._envia_apply_integration_callback_failure(error_message=error_message)
