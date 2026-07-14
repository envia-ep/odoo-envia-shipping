from odoo.addons.envia.services.dto import Contact, QuoteRequest, ShipmentItem
from odoo.addons.envia.services.envia_official_adapter import EnviaOfficialAdapter
from odoo.addons.envia.services.payload_mapper import PayloadMapper


def test_build_quote_request_from_values():
    request = PayloadMapper.build_quote_request_from_values(
        {
            "origin_postal_code": "06500",
            "origin_country": "MX",
            "destination_postal_code": "28001",
            "destination_country": "ES",
            "weight": 2.5,
            "content": "Electronics",
            "declared_value": 1500,
            "currency": "MXN",
        }
    )
    assert request.origin_postal_code == "06500"
    assert request.weight == 2.5
    assert request.declared_value == 1500


def test_normalize_package_content_truncates_to_envia_limit():
    long_content = "Classic Brown Jacket " * 10
    normalized = PayloadMapper.normalize_package_content(long_content)
    assert len(normalized) <= PayloadMapper.PACKAGE_CONTENT_MAX_LENGTH


def test_normalize_package_weight():
    assert PayloadMapper.normalize_package_weight(0.0) == 1.0
    assert PayloadMapper.normalize_package_weight(0.05) == 1.0
    assert PayloadMapper.normalize_package_weight(0.10) == 0.10
    assert PayloadMapper.normalize_package_weight(2.5) == 2.5


def test_build_quote_request_from_values_normalizes_low_weight():
    request = PayloadMapper.build_quote_request_from_values(
        {
            "origin_postal_code": "06500",
            "origin_country": "MX",
            "destination_postal_code": "03100",
            "destination_country": "MX",
            "weight": 0.05,
            "content": "Electronics",
            "declared_value": 1500,
            "currency": "MXN",
        }
    )
    assert request.weight == 1.0


def test_checkout_item_product_id_uses_product_product_id():
    request = QuoteRequest(
        origin_postal_code="67192",
        origin_country="MX",
        destination_postal_code="03100",
        destination_country="MX",
        weight=1.0,
        content="Package",
    )
    item = ShipmentItem(
        description="Jacket",
        quantity=1.0,
        price=100.0,
        currency="MXN",
        sku="JKT-001",
        product_id=52,
    )
    checkout_item = EnviaOfficialAdapter._checkout_item_from_shipment_item(
        item, request, 0
    )
    assert checkout_item["productId"] == "52"


def test_partner_address_extras_from_street2_number():
    partner = type("Partner", (), {"street2": "123", "country_id": False})()
    number, district, interior = PayloadMapper._partner_address_extras(partner)
    assert number == "123"
    assert district is None
    assert interior is None


def test_partner_address_extras_from_street2_district():
    partner = type("Partner", (), {"street2": "Centro", "country_id": False})()
    number, district, interior = PayloadMapper._partner_address_extras(partner)
    assert number is None
    assert district == "Centro"
    assert interior is None


def test_checkout_address_includes_district():
    contact = EnviaOfficialAdapter._contact_to_checkout_address(
        Contact(
            name="Shipper",
            street="Av Reforma",
            number="123",
            district="Juarez",
            city="Ciudad de Mexico",
            state="CX",
            postal_code="06600",
            country="MX",
            phone="5555555555",
            email="ship@example.com",
        )
    )
    assert contact["number"] == "123"
    assert contact["district"] == "Juarez"


def test_official_address_includes_district_fallback():
    address = EnviaOfficialAdapter._contact_to_official_address(
        Contact(
            name="Shipper",
            street="Av Reforma",
            number="123",
            district="Nuevo León",
            city="Guadalupe",
            state="NL",
            postal_code="67192",
            country="MX",
            phone="5555555555",
            email="ship@example.com",
        )
    )
    assert address["district"] == "Nuevo León"


def test_resolve_district_falls_back_to_state_name():
    state = type("State", (), {"name": "Ciudad de México"})()
    assert PayloadMapper._resolve_district(state=state) == "Ciudad de México"
    assert PayloadMapper._resolve_district(district="Centro", state=state) == "Centro"


def test_build_checkout_payload_normalizes_package_content():
    request = QuoteRequest(
        origin_postal_code="67192",
        origin_country="MX",
        destination_postal_code="03100",
        destination_country="MX",
        weight=1.0,
        content="Classic Brown Jacket " * 10,
    )
    payload = EnviaOfficialAdapter._build_checkout_payload(request)
    assert len(payload["package"]["content"]) <= PayloadMapper.PACKAGE_CONTENT_MAX_LENGTH
