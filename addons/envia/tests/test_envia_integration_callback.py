from odoo.tests import tagged
from odoo.tests.common import TransactionCase
import json
import xmlrpc.client


def xmlrpc_request(method_name: str, params: list) -> bytes:
    return xmlrpc.client.dumps(tuple(params), methodname=method_name, allow_none=True)

from odoo.addons.envia.services.envia_integration_callback import (
    EnviaIntegrationCallbackError,
    EnviaIntegrationCallbackPayload,
    apply_integration_callback,
    authenticate_integration_callback,
    build_callback_url,
    extract_bearer_api_key,
    get_integration_database_name,
    handle_envia_jsonrpc_request,
    handle_envia_xmlrpc_common_request,
    is_success_status,
    parse_callback_payload,
    resolve_callback_database,
)
from odoo.addons.envia.services.envia_plugin_setup import (
    generate_integration_credentials,
    lookup_integration_database,
    queue_pending_setup,
)


@tagged("post_install", "-at_install")
class TestEnviaIntegrationCallbackParsing(TransactionCase):
    def test_parse_callback_payload_accepts_required_fields(self):
        payload = parse_callback_payload(
            {
                "status": "success",
                "hash": "envia-api-token-abc",
                "shop": "shop-123",
                "company": self.env.company.id,
                "user": self.env.user.id,
                "database": self.env.cr.dbname,
            },
            bearer_api_key="odoo-generated-api-key",
        )
        self.assertEqual(payload.hash, "envia-api-token-abc")
        self.assertEqual(payload.api_key, "odoo-generated-api-key")
        self.assertEqual(payload.database, self.env.cr.dbname)

    def test_parse_callback_payload_accepts_bearer_without_body_api_key(self):
        payload = parse_callback_payload(
            {
                "status": "success",
                "hash": "token",
                "shop": "shop",
                "company": 1,
                "user": 2,
            },
            bearer_api_key="odoo-generated-api-key",
        )
        self.assertEqual(payload.api_key, "odoo-generated-api-key")

    def test_extract_bearer_api_key_accepts_raw_authorization_value(self):
        self.assertEqual(extract_bearer_api_key("odoo-generated-api-key"), "odoo-generated-api-key")

    def test_extract_bearer_api_key_accepts_bearer_scheme(self):
        self.assertEqual(
            extract_bearer_api_key("Bearer odoo-generated-api-key"),
            "odoo-generated-api-key",
        )

    def test_extract_bearer_api_key_requires_authorization_header(self):
        with self.assertRaises(EnviaIntegrationCallbackError) as error:
            extract_bearer_api_key(None)
        self.assertEqual(error.exception.error_code, "missing_authorization")

    def test_parse_callback_payload_accepts_missing_database(self):
        payload = parse_callback_payload(
            {
                "status": "success",
                "hash": "token",
                "shop": "shop",
                "company": 1,
                "user": 2,
            },
            bearer_api_key="key",
        )
        self.assertIsNone(payload.database)

    def test_is_success_status(self):
        self.assertTrue(is_success_status("success"))
        self.assertFalse(is_success_status("error"))


@tagged("post_install", "-at_install")
class TestEnviaIntegrationCallbackService(TransactionCase):
    def setUp(self):
        super().setUp()
        self.test_user = self.env.ref("base.user_admin")
        self.credentials = generate_integration_credentials(
            self.env,
            self.env.company,
            user=self.test_user,
        )
        self.env.company.sudo().write(
            {"envia_integration_api_key": self.credentials["api_key"]}
        )
        self.env.flush_all()

    def test_authenticate_integration_callback_resolves_user(self):
        user_id = authenticate_integration_callback(self.env, self.credentials["api_key"])
        self.assertEqual(user_id, self.test_user.id)

    def test_authenticate_integration_callback_rejects_invalid_key(self):
        with self.assertRaises(EnviaIntegrationCallbackError) as error:
            authenticate_integration_callback(self.env, "invalid-api-key")
        self.assertEqual(error.exception.error_code, "invalid_api_key")

    def test_apply_integration_callback_stores_api_token_shop_and_odoo_key(self):
        payload = EnviaIntegrationCallbackPayload(
            status="success",
            hash="envia-shipping-api-token-xyz",
            shop="shop-456",
            company=self.env.company.id,
            user=self.env.user.id,
            api_key=self.credentials["api_key"],
            database=self.env.cr.dbname,
            message=None,
        )
        company = self.env.company
        result = apply_integration_callback(
            self.env(user=self.env.user),
            payload,
            resolved_database=self.env.cr.dbname,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(company.envia_api_token, "envia-shipping-api-token-xyz")
        self.assertEqual(company.envia_shop_id, "shop-456")
        self.assertEqual(company.envia_integration_api_key, self.credentials["api_key"])

    def test_apply_integration_callback_resolves_company_from_pending_setup(self):
        queue_pending_setup(self.env, self.env.company)
        payload = EnviaIntegrationCallbackPayload(
            status="success",
            hash="envia-shipping-api-token-xyz",
            shop="shop-456",
            company=5592,
            user=self.env.user.id,
            api_key=self.credentials["api_key"],
            database=self.env.cr.dbname,
            message=None,
        )
        result = apply_integration_callback(
            self.env(user=self.env.user),
            payload,
            resolved_database=self.env.cr.dbname,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["company"], self.env.company.id)

    def test_apply_integration_callback_rejects_database_mismatch(self):
        payload = EnviaIntegrationCallbackPayload(
            status="success",
            hash="envia-token",
            shop="shop-1",
            company=self.env.company.id,
            user=self.env.user.id,
            api_key=self.credentials["api_key"],
            database="other_database",
            message=None,
        )
        with self.assertRaises(EnviaIntegrationCallbackError) as error:
            apply_integration_callback(
                self.env(user=self.env.user),
                payload,
                resolved_database=self.env.cr.dbname,
            )
        self.assertEqual(error.exception.error_code, "database_mismatch")

    def test_apply_integration_callback_rejects_bearer_mismatch(self):
        payload = EnviaIntegrationCallbackPayload(
            status="success",
            hash="envia-token",
            shop="shop-1",
            company=self.env.company.id,
            user=self.env.user.id,
            api_key=self.credentials["api_key"],
            database=self.env.cr.dbname,
            message=None,
        )
        with self.assertRaises(EnviaIntegrationCallbackError) as error:
            apply_integration_callback(
                self.env(user=self.env.user),
                payload,
                bearer_api_key="different-api-key",
                resolved_database=self.env.cr.dbname,
            )
        self.assertEqual(error.exception.error_code, "api_key_mismatch")

    def test_build_callback_url_includes_database_query_param(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url",
            "https://odoo.example.com",
        )
        self.assertEqual(
            build_callback_url(self.env),
            f"https://odoo.example.com/envia/integration/callback?db={self.env.cr.dbname}",
        )
        self.assertEqual(
            get_integration_database_name(self.env),
            self.env.cr.dbname,
        )

    def test_resolve_callback_database_accepts_json_field(self):
        database = resolve_callback_database(None, {"database": self.env.cr.dbname})
        self.assertEqual(database, self.env.cr.dbname)

    def test_resolve_callback_database_accepts_nested_store_access_database(self):
        database = resolve_callback_database(
            None,
            {"store": {"access": {"database": self.env.cr.dbname}}},
        )
        self.assertEqual(database, self.env.cr.dbname)

    def test_resolve_callback_database_uses_bound_connect_database(self):
        self.assertEqual(
            lookup_integration_database(self.credentials["api_key"]),
            self.env.cr.dbname,
        )
        database = resolve_callback_database(
            None,
            {},
            api_key=self.credentials["api_key"],
        )
        self.assertEqual(database, self.env.cr.dbname)

    def test_resolve_callback_database_auto_resolves_single_database(self):
        database = resolve_callback_database(None, {})
        self.assertEqual(database, self.env.cr.dbname)

    def test_resolve_callback_database_auto_resolves_from_api_key(self):
        database = resolve_callback_database(
            None,
            {},
            api_key=self.credentials["api_key"],
        )
        self.assertEqual(database, self.env.cr.dbname)

    def test_resolve_callback_database_auto_resolves_from_body_api_key(self):
        database = resolve_callback_database(
            None,
            {"apiKey": self.credentials["api_key"]},
        )
        self.assertEqual(database, self.env.cr.dbname)

    def test_handle_envia_jsonrpc_request_authenticates_valid_api_key(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "authenticate",
                "args": [
                    self.env.cr.dbname,
                    self.test_user.login,
                    self.credentials["api_key"],
                ],
            },
            "id": 1,
        }
        status_code, response = handle_envia_jsonrpc_request(json.dumps(payload))
        self.assertEqual(status_code, 200)
        self.assertEqual(response["result"], self.test_user.id)

    def test_handle_envia_jsonrpc_request_rejects_invalid_api_key(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "authenticate",
                "args": [self.env.cr.dbname, self.test_user.login, "invalid-api-key"],
            },
            "id": 2,
        }
        status_code, response = handle_envia_jsonrpc_request(json.dumps(payload))
        self.assertEqual(status_code, 200)
        self.assertIn("error", response)
        self.assertNotIn("result", response)

    def test_handle_envia_xmlrpc_common_request_returns_version(self):
        payload = b"""<?xml version="1.0"?>
<methodCall><methodName>version</methodName><params></params></methodCall>"""
        status_code, response = handle_envia_xmlrpc_common_request(payload)
        self.assertEqual(status_code, 200)
        self.assertIn(b"server_version", response)

    def test_handle_envia_xmlrpc_common_request_authenticates_valid_api_key(self):
        payload = xmlrpc_request(
            "authenticate",
            [self.env.cr.dbname, self.test_user.login, self.credentials["api_key"]],
        )
        status_code, response = handle_envia_xmlrpc_common_request(payload)
        self.assertEqual(status_code, 200)
        self.assertIn(str(self.test_user.id).encode(), response)

    def test_handle_envia_xmlrpc_common_request_rejects_invalid_api_key(self):
        payload = xmlrpc_request(
            "authenticate",
            [self.env.cr.dbname, self.test_user.login, "invalid-api-key"],
        )
        status_code, response = handle_envia_xmlrpc_common_request(payload)
        self.assertEqual(status_code, 200)
        self.assertIn(b"<boolean>0</boolean>", response)
