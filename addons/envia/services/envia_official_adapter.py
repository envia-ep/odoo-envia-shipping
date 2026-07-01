from typing import Any

from odoo import _
from odoo.exceptions import UserError

from .dto import (
    Contact,
    CreateShipmentRequest,
    CreateShipmentResponse,
    QuoteRequest,
    QuoteResponse,
    QuoteService,
    TrackRequest,
    TrackResponse,
    TrackResult,
    TrackingEvent,
)
from .envia_adapter_base import EnviaAdapterBase
from .envia_client import EnviaApiError, EnviaClient


class EnviaOfficialAdapter(EnviaAdapterBase):
    def __init__(self, client: EnviaClient, default_carriers: str = "dhl,fedex,estafeta") -> None:
        self.client = client
        self.default_carriers = [
            carrier.strip()
            for carrier in default_carriers.split(",")
            if carrier.strip()
        ]

    def quote(self, request: QuoteRequest) -> QuoteResponse:
        carriers = self._resolve_carriers(request.carriers)
        services: list[QuoteService] = []
        raw_responses: list[dict[str, Any]] = []
        carrier_errors: list[str] = []

        for carrier in carriers:
            payload = self._build_rate_payload(request, carrier)
            try:
                body = self.client.post("ship/rate/", payload)
            except (UserError, EnviaApiError) as error:
                carrier_errors.append(f"{carrier}: {error}")
                continue
            raw_responses.append(body)
            for index, rate in enumerate(body.get("data") or []):
                services.append(
                    QuoteService(
                        service_id=f"{carrier}:{rate.get('service', index)}",
                        carrier=rate.get("carrier", carrier),
                        carrier_name=rate.get("carrierDescription") or rate.get("carrier", carrier),
                        service_name=rate.get("serviceDescription") or rate.get("service", ""),
                        price=float(rate.get("totalPrice") or rate.get("price") or 0),
                        currency=rate.get("currency", request.currency),
                        estimated_delivery_days=self._parse_delivery_days(
                            rate.get("deliveryEstimate")
                        ),
                    )
                )

        if not services:
            raise UserError(self._build_no_rates_message(request, carrier_errors))

        quote_id = f"official_{request.origin_postal_code}_{request.destination_postal_code}_{len(services)}"
        return QuoteResponse(
            quote_id=quote_id,
            services=services,
            raw={"responses": raw_responses, "carrier_errors": carrier_errors},
        )

    @staticmethod
    def _build_no_rates_message(request: QuoteRequest, carrier_errors: list[str]) -> str:
        lines = [
            "No shipping services available for this route.",
            f"Route: {request.origin_postal_code} {request.origin_state or '?'}, "
            f"{request.origin_country} -> {request.destination_postal_code} "
            f"{request.destination_state or '?'}, {request.destination_country}",
        ]
        if request.origin_country != request.destination_country:
            lines.append(
                "International routes often fail in Envia sandbox. "
                "Try a domestic route first, for example MX 06500 to MX 03100."
            )
        lines.extend(
            [
                "Check that both contacts have street, city, postal code, phone, and email.",
                "Verify that state/province matches the postal code on both sides.",
            ]
        )
        if carrier_errors:
            lines.append("Carrier responses:")
            lines.extend(f"- {error}" for error in carrier_errors[:5])
        return "\n".join(lines)

    def create_shipment(self, request: CreateShipmentRequest) -> CreateShipmentResponse:
        carrier, service = self._parse_service_id(request.service_id, request.carrier, request.service_name)
        payload = {
            "origin": self._contact_to_official_address(request.origin_contact),
            "destination": self._contact_to_official_address(request.destination_contact),
            "packages": [
                {
                    "type": "box",
                    "content": request.package_content or "Shipment",
                    "amount": 1,
                    "declaredValue": sum(item.price * item.quantity for item in request.items) or 0,
                    "lengthUnit": "CM",
                    "weightUnit": "KG",
                    "weight": request.package_weight or 1.0,
                    "dimensions": {
                        "length": request.package_length or 10,
                        "width": request.package_width or 10,
                        "height": request.package_height or 10,
                    },
                }
            ],
            "shipment": {
                "type": 1,
                "carrier": carrier,
                "service": service,
            },
            "settings": {
                "currency": request.items[0].currency if request.items else "MXN",
                "comments": request.order_reference or "",
            },
        }
        body = self.client.post("ship/generate/", payload)
        data = (body.get("data") or [{}])[0]
        return CreateShipmentResponse(
            shipment_id=data.get("shipmentId") or data.get("folio") or "",
            tracking_number=data.get("trackingNumber", ""),
            carrier=data.get("carrier", carrier),
            carrier_name=data.get("carrierDescription") or data.get("carrier", carrier),
            service=data.get("serviceDescription") or data.get("service", service),
            status="created",
            status_description="Label created",
            label_url=data.get("label") or data.get("labelUrl"),
            pricing_total=float(data.get("totalPrice") or 0) or None,
            pricing_currency=data.get("currency"),
            raw=body,
        )

    def track(self, request: TrackRequest) -> TrackResponse:
        body = self.client.post(
            "ship/generaltrack/",
            {"trackingNumbers": request.tracking_numbers},
        )
        results = []
        for entry in body.get("data") or []:
            events = [
                TrackingEvent(
                    timestamp=event.get("timestamp", ""),
                    location=event.get("location"),
                    description=event.get("description", ""),
                    status=event.get("status"),
                )
                for event in entry.get("events", [])
            ]
            results.append(
                TrackResult(
                    tracking_number=entry.get("trackingNumber", ""),
                    status=entry.get("status", ""),
                    carrier=entry.get("carrier"),
                    events=events,
                )
            )
        return TrackResponse(results=results, raw=body)

    def _resolve_carriers(self, carriers: str) -> list[str]:
        if carriers == "all":
            return self.default_carriers or ["dhl"]
        return [carrier.strip() for carrier in carriers.split(",") if carrier.strip()]

    @staticmethod
    def _build_rate_payload(request: QuoteRequest, carrier: str) -> dict[str, Any]:
        origin = EnviaOfficialAdapter._address_from_request(
            request.origin_contact,
            request.origin_postal_code,
            request.origin_country,
            request.origin_state,
        )
        destination = EnviaOfficialAdapter._address_from_request(
            request.destination_contact,
            request.destination_postal_code,
            request.destination_country,
            request.destination_state,
        )
        return {
            "origin": origin,
            "destination": destination,
            "packages": [
                {
                    "type": "box",
                    "content": request.content,
                    "amount": 1,
                    "declaredValue": request.declared_value or 0,
                    "lengthUnit": "CM",
                    "weightUnit": "KG",
                    "weight": request.weight,
                    "dimensions": {
                        "length": request.length,
                        "width": request.width,
                        "height": request.height,
                    },
                }
            ],
            "shipment": {"type": 1, "carrier": carrier},
        }

    @staticmethod
    def _address_from_request(
        contact: Contact | None,
        postal_code: str,
        country: str,
        state: str | None,
    ) -> dict[str, Any]:
        if contact:
            return EnviaOfficialAdapter._contact_to_official_address(contact)
        return {
            "name": "Contact",
            "phone": "0000000000",
            "street": "Street",
            "city": "City",
            "state": state or "",
            "country": country,
            "postalCode": postal_code,
        }

    @staticmethod
    def _contact_to_official_address(contact: Contact) -> dict[str, Any]:
        street = contact.street
        if contact.number:
            street = f"{street} {contact.number}".strip()
        return {
            "name": contact.name,
            "company": contact.company or contact.name,
            "phone": contact.phone,
            "email": contact.email,
            "street": street,
            "city": contact.city,
            "state": contact.state,
            "country": contact.country,
            "postalCode": contact.postal_code,
        }

    @staticmethod
    def _parse_service_id(
        service_id: int | str,
        carrier: str | None,
        service_name: str | None,
    ) -> tuple[str, str]:
        service_text = str(service_id)
        if ":" in service_text:
            parsed_carrier, parsed_service = service_text.split(":", 1)
            return parsed_carrier, parsed_service
        if carrier and service_name:
            return carrier, service_name
        raise UserError(_("Selected service is missing carrier information."))

    @staticmethod
    def _parse_delivery_days(delivery_estimate: str | None) -> int | None:
        if not delivery_estimate:
            return None
        digits = "".join(char for char in delivery_estimate if char.isdigit())
        return int(digits[:1]) if digits else None
