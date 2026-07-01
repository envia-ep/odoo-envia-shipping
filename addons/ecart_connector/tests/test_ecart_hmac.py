import base64
import hashlib
import hmac

from odoo.tests.common import TransactionCase

from odoo.addons.ecart_connector.services.ecart_client import EcartClient


class TestEcartHmac(TransactionCase):
    def test_validate_ecartapi_key_valid(self):
        app_id = "my-app-id"
        access_token = "store-token-123"
        client_id = "client-secret"
        key = self._compute_key(app_id, access_token, client_id)
        self.assertTrue(
            EcartClient.validate_ecartapi_key(app_id, access_token, client_id, key)
        )

    def test_validate_ecartapi_key_invalid(self):
        self.assertFalse(
            EcartClient.validate_ecartapi_key("app", "token", "secret", "wrong")
        )

    @staticmethod
    def _compute_key(app_id, access_token, client_id):
        base_string = f"{app_id}&{access_token}"
        digest = hmac.new(
            client_id.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")
