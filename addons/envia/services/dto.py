from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdditionalService:
    service: str
    amount: float | None = None


@dataclass
class QuoteRequest:
    origin_postal_code: str
    origin_country: str
    destination_postal_code: str
    destination_country: str
    weight: float
    length: float
    width: float
    height: float
    content: str
    origin_state: str | None = None
    destination_state: str | None = None
    declared_value: float | None = None
    currency: str = "MXN"
    carriers: str = "all"
    additional_services: list[AdditionalService] = field(default_factory=list)
    origin_contact: "Contact | None" = None
    destination_contact: "Contact | None" = None


@dataclass
class QuoteService:
    service_id: int | str
    carrier: str
    carrier_name: str
    service_name: str
    price: float
    currency: str
    estimated_delivery_days: int | None = None
    max_weight: float | None = None
    restrictions: list[str] = field(default_factory=list)
    additional_services_available: list[str] = field(default_factory=list)


@dataclass
class QuoteResponse:
    quote_id: str
    services: list[QuoteService]
    valid_until: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Contact:
    name: str
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone: str
    email: str
    company: str | None = None
    number: str | None = None
    interior_number: str | None = None
    district: str | None = None
    identification_number: str | None = None


@dataclass
class ShipmentItem:
    description: str
    quantity: float
    price: float
    currency: str
    weight: float | None = None
    sku: str | None = None
    product_code: str | None = None
    country_of_manufacture: str | None = None


@dataclass
class CreateShipmentRequest:
    quote_id: str
    service_id: int | str
    origin_contact: Contact
    destination_contact: Contact
    items: list[ShipmentItem] = field(default_factory=list)
    additional_services: list[AdditionalService] = field(default_factory=list)
    order_reference: str | None = None
    print_format: str = "PDF"
    print_size: str = "STOCK_4X6"
    carrier: str | None = None
    service_name: str | None = None
    package_weight: float | None = None
    package_length: float | None = None
    package_width: float | None = None
    package_height: float | None = None
    package_content: str | None = None


@dataclass
class CreateShipmentResponse:
    shipment_id: int | str
    tracking_number: str
    carrier: str
    carrier_name: str
    service: str
    status: str
    status_description: str
    label_url: str | None
    pricing_total: float | None = None
    pricing_currency: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrackingEvent:
    timestamp: str
    location: str | None
    description: str
    status: str | None = None


@dataclass
class TrackResult:
    tracking_number: str
    status: str
    carrier: str | None = None
    events: list[TrackingEvent] = field(default_factory=list)


@dataclass
class TrackRequest:
    tracking_numbers: list[str]
    carrier: str | None = None


@dataclass
class TrackResponse:
    results: list[TrackResult]
    raw: dict[str, Any] = field(default_factory=dict)
