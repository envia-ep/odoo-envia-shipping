from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.envia.services.envia_client import EnviaClient


@tagged("post_install", "-at_install")
class TestEnviaClient(TransactionCase):
    @patch("odoo.addons.envia.services.envia_client.requests.get")
    def test_test_connection_validates_carrier_list_response(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {"name": "fedex", "description": "FedEx", "active": True},
                    {"name": "dhl", "description": "DHL", "active": True},
                ]
            },
            text='{"data": []}',
        )
        client = EnviaClient("https://api-test.envia.com/", "shipping-token")
        body = client.test_connection(
            queries_base_url="https://queries-test.envia.com/",
            country_code="MX",
        )
        self.assertEqual(len(body["data"]), 2)
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        self.assertEqual(call_kwargs["params"], {"country_code": "MX"})
        self.assertIn("Bearer shipping-token", call_kwargs["headers"]["Authorization"])

    @patch("odoo.addons.envia.services.envia_client.requests.get")
    def test_test_connection_rejects_invalid_token(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=401,
            json=lambda: {"message": "Unauthorized"},
            text='{"message": "Unauthorized"}',
        )
        client = EnviaClient("https://api-test.envia.com/", "bad-token")
        with self.assertRaises(UserError):
            client.test_connection(
                queries_base_url="https://queries-test.envia.com/",
                country_code="MX",
            )

    @patch("odoo.addons.envia.services.envia_client.requests.get")
    def test_test_connection_rejects_unexpected_response_format(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "ok"},
            text='{"status": "ok"}',
        )
        client = EnviaClient("https://api-test.envia.com/", "shipping-token")
        with self.assertRaises(UserError):
            client.test_connection(
                queries_base_url="https://queries-test.envia.com/",
                country_code="MX",
            )

    @patch("odoo.addons.envia.services.envia_client.requests.get")
    def test_get_branches_sends_type_and_zipcode(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "branch_id": "LNT",
                        "reference": "Branch LNT",
                        "address": {
                            "street": "Av. Insurgentes Sur",
                            "city": "Alvaro Obregon",
                            "postalCode": "01000",
                            "state": "CX",
                            "country": "MX",
                        },
                    }
                ]
            },
            text='{"data": []}',
        )
        client = EnviaClient("https://api-test.envia.com/", "shipping-token")
        branches = client.get_branches(
            queries_base_url="https://queries-test.envia.com/",
            carrier="estafeta",
            country_code="MX",
            zipcode="64060",
            search_type=2,
        )
        self.assertEqual(len(branches), 1)
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://queries-test.envia.com/branches/estafeta/MX",
        )
        self.assertEqual(
            mock_get.call_args.kwargs["params"],
            {"type": 2, "zipcode": "64060", "allBranch": False},
        )

    @patch("odoo.addons.envia.services.envia_client.requests.post")
    def test_post_accepts_optional_base_url(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True, "packages": []},
            text='{"success": true}',
        )
        client = EnviaClient("https://api-test.envia.com/", "shipping-token")
        body = client.post(
            "package/dimensions/test/34084",
            {"items": [], "currency": "MXN"},
            base_url="https://ecommerce-private.envia.com/",
        )
        self.assertTrue(body["success"])
        self.assertEqual(
            mock_post.call_args.args[0],
            "https://ecommerce-private.envia.com/package/dimensions/test/34084",
        )

    @patch("odoo.addons.envia.services.envia_client.requests.get")
    def test_get_generic_form_returns_field_list_without_auth(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {
                    "fieldId": "nombre",
                    "dataName": "name",
                    "fieldLabel": "Nombre",
                    "dataType": "text",
                    "visible": True,
                    "rules": {"required": True},
                },
                {
                    "fieldId": "rfc",
                    "dataName": "rfc",
                    "fieldLabel": "RFC",
                    "dataType": "text",
                    "visible": True,
                    "rules": {"required": True},
                },
            ],
            text="[]",
        )
        fields = EnviaClient.get_generic_form(
            "https://queries-test.envia.com/",
            "MX",
            form="address_info",
        )
        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0]["fieldId"], "nombre")
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://queries-test.envia.com/generic-form",
        )
        self.assertEqual(
            mock_get.call_args.kwargs["params"],
            {"country_code": "MX", "form": "address_info"},
        )
        self.assertNotIn("Authorization", mock_get.call_args.kwargs["headers"])

    @patch("odoo.addons.envia.services.envia_client.requests.get")
    def test_get_generic_form_rejects_non_list_payload(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"fields": []},
            text='{"fields": []}',
        )
        with self.assertRaises(UserError):
            EnviaClient.get_generic_form("https://queries-test.envia.com/", "MX")

    @patch("odoo.addons.envia.services.envia_client.requests.get")
    def test_get_states_returns_data_list(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {"name": "Antioquia", "code_2_digits": "AN", "country_code": "CO"},
                ]
            },
            text='{"data": []}',
        )
        states = EnviaClient.get_states("https://queries-test.envia.com/", "CO")
        self.assertEqual(len(states), 1)
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://queries-test.envia.com/state",
        )
        self.assertEqual(mock_get.call_args.kwargs["params"], {"country_code": "CO"})

    @patch("odoo.addons.envia.services.envia_client.requests.get")
    def test_get_provinces_returns_data_list(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [{"name": "ABEJORRAL", "state_code": "AN", "code": "05002000"}]
            },
            text='{"data": []}',
        )
        provinces = EnviaClient.get_provinces("https://queries-test.envia.com/", "AN")
        self.assertEqual(len(provinces), 1)
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://queries-test.envia.com/provinces/AN",
        )

    def test_refine_branches_near_zip_prefers_exact_postal_code(self):
        branches = [
            {"branch_id": "A", "distance": 2, "address": {"postalCode": "67170"}},
            {"branch_id": "B", "distance": 1, "address": {"postalCode": "64000"}},
            {"branch_id": "C", "distance": 3, "address": {"postalCode": "67192"}},
        ]
        refined = EnviaClient.refine_branches_near_zip(branches, "67192")
        self.assertEqual([entry["branch_id"] for entry in refined], ["C"])

    def test_refine_branches_near_zip_falls_back_to_prefix(self):
        branches = [
            {"branch_id": "A", "distance": 2, "address": {"postalCode": "67170"}},
            {"branch_id": "B", "distance": 1, "address": {"postalCode": "64000"}},
        ]
        refined = EnviaClient.refine_branches_near_zip(branches, "67192")
        self.assertEqual([entry["branch_id"] for entry in refined], ["A"])
