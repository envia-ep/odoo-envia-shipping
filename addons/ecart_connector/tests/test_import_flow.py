from unittest.mock import patch

from .common import EcartConnectorTestCase


class TestEcartImportFlow(EcartConnectorTestCase):
    def test_import_orders_from_api(self):
        store = self._create_store()
        payload = {"orders": [self._sample_order_payload()]}
        with patch(
            "odoo.addons.ecart_connector.services.ecart_client.EcartClient.list_orders",
            return_value=payload,
        ):
            imported = self.env["ecart.order.import"].import_orders_for_store(store)
        self.assertEqual(len(imported), 1)
        self.assertEqual(imported.ecart_order_id, "1001")
        self.assertTrue(store.last_sync_at)
