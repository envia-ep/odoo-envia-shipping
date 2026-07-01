from odoo.tests.common import TransactionCase


class EcartConnectorTestCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "Ecart Fallback Product",
                "default_code": "ECART-FALLBACK",
                "type": "consu",
            }
        )
        cls.company = cls.env.company
        cls.company.write(
            {
                "ecart_fallback_product_id": cls.product.id,
                "ecart_auto_confirm_orders": False,
            }
        )

    def _create_store(self):
        return self.env["ecart.store"].create(
            {
                "store_name": "Demo Store",
                "store_url": "https://demo.example.com",
                "ecommerce": "Shopify",
                "access_token": "test-token",
                "company_id": self.company.id,
            }
        )

    @staticmethod
    def _sample_order_payload():
        return {
            "id": "1001",
            "number": "SO-1001",
            "currency": "MXN",
            "email": "buyer@example.com",
            "status": {"ecartapi": "paid"},
            "dates": {"createdAt": "2026-06-22T10:00:00Z"},
            "customer": {
                "firstName": "Luis",
                "lastName": "Perez",
                "email": "buyer@example.com",
                "phone": "+525511111111",
            },
            "shippingAddress": {
                "address1": "Insurgentes Sur 123",
                "city": "Ciudad de Mexico",
                "postalCode": "03100",
                "country": "MX",
                "state": "CX",
            },
            "items": [
                {
                    "sku": "ECART-FALLBACK",
                    "name": "Demo item",
                    "quantity": 2,
                    "price": 100.0,
                }
            ],
        }
