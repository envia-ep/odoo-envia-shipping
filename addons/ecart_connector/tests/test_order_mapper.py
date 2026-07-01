from odoo.addons.ecart_connector.services.order_mapper import EcartOrderMapper

from .common import EcartConnectorTestCase


class TestEcartOrderMapper(EcartConnectorTestCase):
    def test_import_order_creates_sale_order(self):
        store = self._create_store()
        payload = self._sample_order_payload()
        order = EcartOrderMapper(self.env).import_order_payload(store, payload)
        self.assertTrue(order.exists())
        self.assertEqual(order.ecart_order_id, "1001")
        self.assertEqual(order.partner_shipping_id.city, "Ciudad de Mexico")
        self.assertEqual(len(order.order_line), 1)

    def test_import_order_is_idempotent(self):
        store = self._create_store()
        payload = self._sample_order_payload()
        mapper = EcartOrderMapper(self.env)
        first = mapper.import_order_payload(store, payload)
        second = mapper.import_order_payload(store, payload)
        self.assertEqual(first.id, second.id)
