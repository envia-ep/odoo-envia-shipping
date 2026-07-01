from odoo import _
from odoo.exceptions import UserError

from ..services.dto import Contact, QuoteRequest, ShipmentItem
from ..services.envia_client import EnviaClient
from ..services.envia_official_adapter import EnviaOfficialAdapter


class PayloadMapper:
    @staticmethod
    def partner_to_contact(partner) -> Contact:
        if not partner:
            raise UserError(_("A partner is required to build the shipment contact."))
        street = partner.street or ""
        return Contact(
            name=partner.name or "",
            company=partner.commercial_company_name or partner.name,
            street=street,
            number=partner.street2 or None,
            city=partner.city or "",
            state=partner.state_id.code if partner.state_id else "",
            postal_code=partner.zip or "",
            country=partner.country_id.code if partner.country_id else "",
            phone=partner.phone or getattr(partner, "mobile", "") or "",
            email=partner.email or "",
            identification_number=partner.vat or None,
        )

    @staticmethod
    def build_quote_request_from_values(values: dict) -> QuoteRequest:
        return QuoteRequest(
            origin_postal_code=values["origin_postal_code"],
            origin_country=values["origin_country"],
            origin_state=values.get("origin_state") or None,
            destination_postal_code=values["destination_postal_code"],
            destination_country=values["destination_country"],
            destination_state=values.get("destination_state") or None,
            weight=float(values["weight"]),
            length=float(values["length"]),
            width=float(values["width"]),
            height=float(values["height"]),
            content=values["content"],
            declared_value=float(values["declared_value"]) if values.get("declared_value") else None,
            currency=values.get("currency") or "MXN",
            carriers=values.get("carriers") or "all",
            origin_contact=values.get("origin_contact"),
            destination_contact=values.get("destination_contact"),
        )

    @staticmethod
    def sale_lines_to_items(order) -> list[ShipmentItem]:
        items = []
        for line in order.order_line.filtered(lambda line: not line.display_type):
            items.append(
                ShipmentItem(
                    description=line.name,
                    quantity=line.product_uom_qty,
                    price=line.price_unit,
                    currency=order.currency_id.name,
                    weight=line.product_id.weight or None,
                    sku=line.product_id.default_code or None,
                    product_code=getattr(line.product_id, "envia_product_code", None),
                    country_of_manufacture=PayloadMapper._product_country_of_origin(line.product_id),
                )
            )
        return items

    @staticmethod
    def _product_country_of_origin(product) -> str | None:
        country = getattr(product, "country_of_origin", None)
        if country:
            return country.code
        template_country = getattr(product.product_tmpl_id, "country_of_origin", None)
        return template_country.code if template_country else None


def get_envia_adapter(company):
    company.ensure_one()
    token = company._envia_get_shipping_api_token()
    if not token:
        raise UserError(
            _(
                "Paste your Envia shipping API token in Settings > Envia Shipping > "
                "API Connection. Sandbox tokens come from "
                "https://shipping-test.envia.com/settings/developers"
            )
        )
    client = EnviaClient(company._envia_get_base_url(), token)
    return EnviaOfficialAdapter(client, default_carriers=company.envia_default_carriers or "dhl,fedex,estafeta")
