import json
import logging

import odoo
from odoo import api, http
from odoo.http import request
from odoo.modules.registry import Registry

from ..services.envia_integration_callback import (
    CONNECT_ROUTE,
    EnviaIntegrationCallbackError,
    _extract_odoo_api_key,
    apply_integration_callback,
    authenticate_integration_callback,
    extract_bearer_api_key,
    get_integration_database_name,
    parse_callback_payload,
    resolve_callback_database,
    resolve_callback_odoo_api_key,
    resolve_connect_database,
)

_logger = logging.getLogger(__name__)


class EnviaIntegrationController(http.Controller):
    @http.route(
        "/envia/integration/callback",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def integration_callback(self, **kwargs):
        try:
            raw_body = request.httprequest.data.decode("utf-8") if request.httprequest.data else ""
            payload_data = json.loads(raw_body) if raw_body else {}
            body_api_key = _extract_odoo_api_key(payload_data)
            authorization = request.httprequest.headers.get("Authorization")
            header_api_key = None
            if authorization:
                try:
                    header_api_key = extract_bearer_api_key(authorization)
                except EnviaIntegrationCallbackError:
                    if not body_api_key:
                        raise
            elif not body_api_key:
                extract_bearer_api_key(None)
            db_name = resolve_callback_database(
                kwargs.get("database") or kwargs.get("db"),
                payload_data,
                api_key=header_api_key,
            )
            odoo_api_key = resolve_callback_odoo_api_key(
                header_api_key,
                payload_data,
                db_name,
            )
            payload = parse_callback_payload(payload_data, bearer_api_key=odoo_api_key)
            result = self._process_integration_callback(
                db_name,
                payload,
                bearer_api_key=odoo_api_key,
            )
            status_code = 200 if result.get("ok") else 422
            return request.make_json_response(result, status=status_code)
        except json.JSONDecodeError:
            return request.make_json_response(
                {
                    "ok": False,
                    "error": "invalid_json",
                    "message": "Request body must be valid JSON.",
                },
                status=400,
            )
        except EnviaIntegrationCallbackError as error:
            return request.make_json_response(
                {
                    "ok": False,
                    "error": error.error_code,
                    "message": error.message,
                },
                status=error.http_status,
            )
        except Exception as error:
            _logger.exception("Envia integration callback failed")
            return request.make_json_response(
                {
                    "ok": False,
                    "error": "internal_error",
                    "message": str(error),
                },
                status=500,
            )

    @staticmethod
    def _process_integration_callback(
        db_name: str,
        payload,
        *,
        bearer_api_key: str | None,
    ) -> dict:
        if (
            request.db
            and request.db == db_name
            and getattr(request, "env", None) is not None
            and get_integration_database_name(request.env) == db_name
        ):
            callback_env = request.env(
                user=authenticate_integration_callback(request.env, payload.api_key)
            )
            result = apply_integration_callback(
                callback_env,
                payload,
                bearer_api_key=bearer_api_key,
                resolved_database=get_integration_database_name(callback_env),
            )
            request.env.cr.commit()
            return result

        registry = Registry(db_name)
        with registry.cursor() as cr:
            bootstrap_env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            user_id = authenticate_integration_callback(bootstrap_env, payload.api_key)
            callback_env = api.Environment(cr, user_id, {})
            result = apply_integration_callback(
                callback_env,
                payload,
                bearer_api_key=bearer_api_key,
                resolved_database=get_integration_database_name(callback_env),
            )
            cr.commit()
        return result

    @http.route(
        CONNECT_ROUTE,
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def integration_connect(self, **kwargs):
        try:
            raw_body = request.httprequest.data.decode("utf-8") if request.httprequest.data else ""
            data = json.loads(raw_body) if raw_body else {}
            api_key = extract_bearer_api_key(request.httprequest.headers.get("Authorization"))
            db_name = resolve_connect_database(
                api_key,
                kwargs.get("db") or kwargs.get("database"),
            )
            result = self._process_integration_connect(db_name, data, api_key)
            return request.make_json_response(result, status=200)
        except json.JSONDecodeError:
            return request.make_json_response(
                {"ok": False, "error": "invalid_json", "message": "Request body must be valid JSON."},
                status=400,
            )
        except EnviaIntegrationCallbackError as error:
            return request.make_json_response(
                {"ok": False, "error": error.error_code, "message": error.message},
                status=error.http_status,
            )
        except Exception as error:
            _logger.exception("Envia integration connect failed")
            return request.make_json_response(
                {"ok": False, "error": "internal_error", "message": str(error)},
                status=500,
            )

    @staticmethod
    def _process_integration_connect(db_name: str, data: dict, api_key: str) -> dict:
        required_fields = ("status", "hash", "shop", "company", "user")
        missing = [name for name in required_fields if name not in data]
        if missing:
            raise EnviaIntegrationCallbackError(
                "invalid_payload",
                "Missing required fields: %s" % ", ".join(missing),
            )
        try:
            company_id = int(data["company"])
        except (TypeError, ValueError) as error:
            raise EnviaIntegrationCallbackError(
                "invalid_payload",
                "Field company must be an integer.",
            ) from error

        if (
            request.db
            and request.db == db_name
            and getattr(request, "env", None) is not None
            and get_integration_database_name(request.env) == db_name
        ):
            env = request.env(user=authenticate_integration_callback(request.env, api_key))
            company = env["res.company"].browse(company_id)
            if not company.exists():
                raise EnviaIntegrationCallbackError(
                    "company_not_found",
                    "Company was not found.",
                    http_status=404,
                )
            if str(data["status"]).strip().lower() not in {"success", "ok", "connected"}:
                raise EnviaIntegrationCallbackError(
                    "integration_failed",
                    str(data.get("message") or data["status"]),
                    http_status=422,
                )
            company.write(
                {
                    "envia_oauth_connected": True,
                    "envia_api_token": str(data["hash"]).strip(),
                    "envia_shop_id": str(data["shop"]).strip(),
                    "envia_oauth_last_error": False,
                    "envia_integration_api_key": api_key,
                }
            )
            request.env.cr.commit()
            return {"ok": True, "company": company.id, "shop": str(data["shop"]).strip()}

        registry = Registry(db_name)
        with registry.cursor() as cr:
            bootstrap_env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            user_id = authenticate_integration_callback(bootstrap_env, api_key)
            env = api.Environment(cr, user_id, {})
            company = env["res.company"].browse(company_id)
            if not company.exists():
                raise EnviaIntegrationCallbackError(
                    "company_not_found",
                    "Company was not found.",
                    http_status=404,
                )
            if str(data["status"]).strip().lower() not in {"success", "ok", "connected"}:
                raise EnviaIntegrationCallbackError(
                    "integration_failed",
                    str(data.get("message") or data["status"]),
                    http_status=422,
                )
            company.write(
                {
                    "envia_oauth_connected": True,
                    "envia_api_token": str(data["hash"]).strip(),
                    "envia_shop_id": str(data["shop"]).strip(),
                    "envia_oauth_last_error": False,
                    "envia_integration_api_key": api_key,
                }
            )
            cr.commit()
            return {"ok": True, "company": company.id, "shop": str(data["shop"]).strip()}

