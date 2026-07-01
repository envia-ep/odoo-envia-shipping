from odoo.addons.envia.services.payload_mapper import PayloadMapper


def test_build_quote_request_from_values():
    request = PayloadMapper.build_quote_request_from_values(
        {
            "origin_postal_code": "06500",
            "origin_country": "MX",
            "destination_postal_code": "28001",
            "destination_country": "ES",
            "weight": 2.5,
            "length": 30,
            "width": 20,
            "height": 15,
            "content": "Electronics",
            "declared_value": 1500,
            "currency": "MXN",
        }
    )
    assert request.origin_postal_code == "06500"
    assert request.weight == 2.5
    assert request.declared_value == 1500
