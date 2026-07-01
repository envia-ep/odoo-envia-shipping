from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services.dto import Contact
from ..services.envia_client import EnviaClient
from ..services.envia_geocodes_client import EnviaGeocodesClient
from ..services.payload_mapper import PayloadMapper, get_envia_adapter


class EnviaQuoteWizardBranch(models.TransientModel):
    _name = "envia.quote.wizard.branch"
    _description = "Envia Quote Wizard Branch Option"
    _order = "distance asc, name asc"

    wizard_id = fields.Many2one("envia.quote.wizard", required=True, ondelete="cascade")
    side = fields.Selection(
        [("origin", "Origin"), ("destination", "Destination")],
        required=True,
    )
    external_id = fields.Char()
    name = fields.Char(required=True)
    street = fields.Char()
    city = fields.Char()
    zip = fields.Char(string="Postal Code")
    distance = fields.Float(string="Distance (km)", digits=(16, 1))
    state_code = fields.Char()
    country_code = fields.Char()
    carrier = fields.Char()
    phone = fields.Char()
    email = fields.Char()
    is_selected = fields.Boolean()

    def action_select_branch(self):
        self.ensure_one()
        siblings = getattr(self.wizard_id, f"{self.side}_branch_line_ids")
        siblings.write({"is_selected": False})
        self.is_selected = True
        prefix = self.side
        country = self.env["res.country"].search([("code", "=", self.country_code)], limit=1)
        state = self.env["res.country.state"].search(
            [
                ("country_id", "=", country.id),
                ("code", "=", self.state_code),
            ],
            limit=1,
        ) if country and self.state_code else self.env["res.country.state"]
        self.wizard_id.write(
            {
                f"{prefix}_postal_code": self.zip or getattr(self.wizard_id, f"{prefix}_postal_code"),
                f"{prefix}_city": self.city or getattr(self.wizard_id, f"{prefix}_city"),
                f"{prefix}_country_id": country.id if country else getattr(self.wizard_id, f"{prefix}_country_id").id,
                f"{prefix}_state_id": state.id if state else False,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "envia.quote.wizard",
            "view_mode": "form",
            "res_id": self.wizard_id.id,
            "target": "current",
        }


class EnviaQuoteWizardService(models.TransientModel):
    _name = "envia.quote.wizard.service"
    _description = "Envia Quote Wizard Service Line"
    _order = "price asc"

    wizard_id = fields.Many2one("envia.quote.wizard", required=True, ondelete="cascade")
    service_id = fields.Char(required=True)
    carrier = fields.Char()
    carrier_name = fields.Char()
    service_name = fields.Char()
    price = fields.Float()
    currency_name = fields.Char()
    estimated_delivery_days = fields.Integer()
    is_selected = fields.Boolean()

    def action_choose_service(self):
        self.ensure_one()
        self.wizard_id.service_line_ids.write({"is_selected": False})
        self.is_selected = True
        return {
            "type": "ir.actions.act_window",
            "res_model": "envia.quote.wizard",
            "view_mode": "form",
            "res_id": self.wizard_id.id,
            "target": "current",
        }


class EnviaQuoteWizard(models.TransientModel):
    _name = "envia.quote.wizard"
    _description = "Envia Quote Wizard"

    step = fields.Selection(
        [
            ("address", "Shipment Details"),
            ("rates", "Select Rate"),
        ],
        default="address",
        required=True,
    )
    sale_order_id = fields.Many2one("sale.order", readonly=True)
    picking_id = fields.Many2one("stock.picking", readonly=True)
    origin_partner_id = fields.Many2one("res.partner", string="Ship From")
    destination_partner_id = fields.Many2one("res.partner", string="Ship To")
    origin_location_type = fields.Selection(
        [("address", "Address"), ("branch", "Branch")],
        string="Origin Type",
        default="address",
        required=True,
    )
    destination_location_type = fields.Selection(
        [("address", "Address"), ("branch", "Branch")],
        string="Destination Type",
        default="address",
        required=True,
    )
    origin_branch_carrier_id = fields.Many2one(
        "envia.carrier",
        string="Origin Carrier",
        domain="[('active', '=', True)]",
    )
    destination_branch_carrier_id = fields.Many2one(
        "envia.carrier",
        string="Destination Carrier",
        domain="[('active', '=', True)]",
    )
    origin_branch_line_ids = fields.One2many(
        "envia.quote.wizard.branch",
        "wizard_id",
        domain=[("side", "=", "origin")],
    )
    destination_branch_line_ids = fields.One2many(
        "envia.quote.wizard.branch",
        "wizard_id",
        domain=[("side", "=", "destination")],
    )
    origin_postal_code = fields.Char(string="Postal Code")
    origin_city = fields.Char(string="City")
    origin_country_id = fields.Many2one("res.country", string="Country")
    origin_state_id = fields.Many2one(
        "res.country.state",
        string="State",
        domain="[('country_id', '=', origin_country_id)]",
    )
    destination_postal_code = fields.Char(string="Postal Code")
    destination_city = fields.Char(string="City")
    destination_country_id = fields.Many2one("res.country", string="Country")
    destination_state_id = fields.Many2one(
        "res.country.state",
        string="State",
        domain="[('country_id', '=', destination_country_id)]",
    )
    weight = fields.Float(string="Weight (kg)", required=True, default=1.0)
    length = fields.Float(string="Length (cm)", required=True, default=30.0)
    width = fields.Float(string="Width (cm)", required=True, default=20.0)
    height = fields.Float(string="Height (cm)", required=True, default=15.0)
    content = fields.Char(required=True, default="General merchandise")
    declared_value = fields.Float(string="Declared Value")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    quote_id = fields.Many2one("envia.quote", readonly=True)
    service_line_ids = fields.One2many("envia.quote.wizard.service", "wizard_id")
    route_summary = fields.Char(compute="_compute_route_summary")
    origin_address_warning = fields.Char(compute="_compute_address_warnings")
    destination_address_warning = fields.Char(compute="_compute_address_warnings")
    origin_address_preview = fields.Char(compute="_compute_address_previews")
    destination_address_preview = fields.Char(compute="_compute_address_previews")
    origin_contact_complete = fields.Boolean(compute="_compute_contact_status")
    destination_contact_complete = fields.Boolean(compute="_compute_contact_status")
    selected_service_label = fields.Char(compute="_compute_selected_service_label")
    service_count = fields.Integer(compute="_compute_service_count")
    can_get_rates = fields.Boolean(compute="_compute_form_state")
    validation_summary = fields.Text(compute="_compute_form_state")
    is_international_route = fields.Boolean(compute="_compute_route_flags")
    is_domestic_route = fields.Boolean(compute="_compute_route_flags")
    is_sandbox = fields.Boolean(compute="_compute_route_flags")
    is_standalone = fields.Boolean(compute="_compute_is_standalone")
    cheapest_rate_label = fields.Char(compute="_compute_rate_highlights")
    fastest_delivery_label = fields.Char(compute="_compute_rate_highlights")
    origin_branch_count = fields.Integer(compute="_compute_branch_ui_state")
    destination_branch_count = fields.Integer(compute="_compute_branch_ui_state")
    origin_selected_branch_label = fields.Char(compute="_compute_branch_ui_state")
    destination_selected_branch_label = fields.Char(compute="_compute_branch_ui_state")

    @api.depends(
        "origin_branch_line_ids",
        "origin_branch_line_ids.is_selected",
        "origin_branch_line_ids.name",
        "destination_branch_line_ids",
        "destination_branch_line_ids.is_selected",
        "destination_branch_line_ids.name",
    )
    def _compute_branch_ui_state(self):
        for wizard in self:
            wizard.origin_branch_count = len(wizard.origin_branch_line_ids)
            wizard.destination_branch_count = len(wizard.destination_branch_line_ids)
            origin_selected = wizard.origin_branch_line_ids.filtered("is_selected")[:1]
            destination_selected = wizard.destination_branch_line_ids.filtered("is_selected")[:1]
            wizard.origin_selected_branch_label = origin_selected.name if origin_selected else False
            wizard.destination_selected_branch_label = (
                destination_selected.name if destination_selected else False
            )

    def _branch_lines(self, side):
        self.ensure_one()
        return (
            self.origin_branch_line_ids
            if side == "origin"
            else self.destination_branch_line_ids
        )

    @api.depends(
        "origin_postal_code",
        "origin_country_id",
        "origin_state_id",
        "destination_postal_code",
        "destination_country_id",
        "destination_state_id",
    )
    def _compute_route_summary(self):
        for wizard in self:
            origin = wizard._format_route_point(
                wizard.origin_postal_code,
                wizard.origin_state_id,
                wizard.origin_country_id,
            )
            destination = wizard._format_route_point(
                wizard.destination_postal_code,
                wizard.destination_state_id,
                wizard.destination_country_id,
            )
            wizard.route_summary = f"{origin} → {destination}" if origin and destination else ""

    @api.depends("origin_partner_id", "destination_partner_id", "origin_location_type", "destination_location_type")
    def _compute_address_warnings(self):
        for wizard in self:
            wizard.origin_address_warning = False
            wizard.destination_address_warning = False
            if wizard.origin_location_type == "address":
                wizard.origin_address_warning = wizard._partner_missing_message(
                    wizard.origin_partner_id
                )
            if wizard.destination_location_type == "address":
                wizard.destination_address_warning = wizard._partner_missing_message(
                    wizard.destination_partner_id
                )

    @api.depends("origin_partner_id", "destination_partner_id")
    def _compute_address_previews(self):
        for wizard in self:
            wizard.origin_address_preview = wizard._format_address_preview(wizard.origin_partner_id)
            wizard.destination_address_preview = wizard._format_address_preview(
                wizard.destination_partner_id
            )

    @api.depends("origin_partner_id", "destination_partner_id")
    def _compute_contact_status(self):
        for wizard in self:
            wizard.origin_contact_complete = not bool(
                wizard._partner_missing_message(wizard.origin_partner_id)
            )
            wizard.destination_contact_complete = not bool(
                wizard._partner_missing_message(wizard.destination_partner_id)
            )

    @api.depends(
        "origin_address_warning",
        "destination_address_warning",
        "origin_postal_code",
        "destination_postal_code",
        "origin_city",
        "destination_city",
        "origin_country_id",
        "destination_country_id",
        "origin_state_id",
        "destination_state_id",
        "weight",
        "length",
        "width",
        "height",
    )
    def _compute_form_state(self):
        for wizard in self:
            errors = wizard._collect_validation_errors()
            wizard.can_get_rates = not errors
            wizard.validation_summary = "\n".join(f"• {error}" for error in errors) if errors else False

    @api.depends("origin_country_id", "destination_country_id")
    def _compute_route_flags(self):
        company = self.env.company
        for wizard in self:
            wizard.is_international_route = bool(
                wizard.origin_country_id
                and wizard.destination_country_id
                and wizard.origin_country_id != wizard.destination_country_id
            )
            wizard.is_domestic_route = bool(
                wizard.origin_country_id
                and wizard.destination_country_id
                and wizard.origin_country_id == wizard.destination_country_id
            )
            wizard.is_sandbox = company.envia_environment == "sandbox"

    @api.depends("sale_order_id", "picking_id")
    def _compute_is_standalone(self):
        for wizard in self:
            wizard.is_standalone = not wizard.sale_order_id and not wizard.picking_id

    @api.depends("service_line_ids", "service_line_ids.price", "service_line_ids.estimated_delivery_days")
    def _compute_rate_highlights(self):
        for wizard in self:
            lines = wizard.service_line_ids
            if not lines:
                wizard.cheapest_rate_label = False
                wizard.fastest_delivery_label = False
                continue
            cheapest = min(lines, key=lambda line: line.price or 0.0)
            wizard.cheapest_rate_label = _(
                "Best price: %(carrier)s · %(price).2f %(currency)s",
                carrier=cheapest.carrier_name or cheapest.carrier,
                price=cheapest.price,
                currency=cheapest.currency_name or wizard.currency_id.name,
            )
            with_eta = lines.filtered(lambda line: line.estimated_delivery_days)
            if with_eta:
                fastest = min(with_eta, key=lambda line: line.estimated_delivery_days)
                wizard.fastest_delivery_label = _(
                    "Fastest: %(carrier)s · %(days)s day(s)",
                    carrier=fastest.carrier_name or fastest.carrier,
                    days=fastest.estimated_delivery_days,
                )
            else:
                wizard.fastest_delivery_label = False

    @api.depends("service_line_ids", "service_line_ids.is_selected")
    def _compute_selected_service_label(self):
        for wizard in self:
            selected = wizard.service_line_ids.filtered("is_selected")[:1]
            if not selected:
                wizard.selected_service_label = False
                continue
            wizard.selected_service_label = _(
                "%(carrier)s · %(service)s · %(price).2f %(currency)s",
                carrier=selected.carrier_name or selected.carrier,
                service=selected.service_name,
                price=selected.price,
                currency=selected.currency_name or wizard.currency_id.name,
            )

    @api.depends("service_line_ids")
    def _compute_service_count(self):
        for wizard in self:
            wizard.service_count = len(wizard.service_line_ids)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        company = self.env.company
        origin_partner = company.envia_default_origin_partner_id or company.partner_id
        defaults["origin_partner_id"] = origin_partner.id
        if origin_partner:
            defaults.update(
                self._build_address_defaults(origin_partner, "origin", company.country_id)
            )
        destination_partner_id = self.env.context.get("default_destination_partner_id")
        if destination_partner_id:
            destination_partner = self.env["res.partner"].browse(destination_partner_id)
            defaults.update(self._build_address_defaults(destination_partner, "destination"))
        sale_order_id = self.env.context.get("default_sale_order_id")
        if sale_order_id:
            sale_order = self.env["sale.order"].browse(sale_order_id)
            defaults["content"] = ", ".join(
                sale_order.order_line.filtered(lambda line: not line.display_type).mapped("name")
            )[:255] or "General merchandise"
            defaults["declared_value"] = sale_order.amount_total
        if not defaults.get("origin_country_id") and company.country_id:
            defaults["origin_country_id"] = company.country_id.id
        default_carrier_id = company._envia_default_branch_carrier_id()
        defaults.setdefault("origin_branch_carrier_id", default_carrier_id)
        defaults.setdefault("destination_branch_carrier_id", default_carrier_id)
        return defaults

    @api.model
    def _default_branch_carrier_id(self):
        return self.env.company._envia_default_branch_carrier_id()

    def _branch_carrier_code(self, side):
        carrier = getattr(self, f"{side}_branch_carrier_id")
        return carrier.code if carrier else ""

    @api.model_create_multi
    def create(self, vals_list):
        company = self.env.company
        for vals in vals_list:
            origin_partner_id = vals.get("origin_partner_id")
            if origin_partner_id:
                partner = self.env["res.partner"].browse(origin_partner_id)
                self._merge_address_defaults(
                    vals,
                    self._build_address_defaults(partner, "origin", company.country_id),
                )
            elif not vals.get("origin_country_id") and company.country_id:
                vals["origin_country_id"] = company.country_id.id

            destination_partner_id = vals.get("destination_partner_id")
            if destination_partner_id:
                partner = self.env["res.partner"].browse(destination_partner_id)
                self._merge_address_defaults(
                    vals,
                    self._build_address_defaults(partner, "destination"),
                )
        return super().create(vals_list)

    @staticmethod
    def _merge_address_defaults(vals, address_defaults):
        for field_name, value in address_defaults.items():
            if field_name not in vals or not vals.get(field_name):
                vals[field_name] = value

    def _build_address_defaults(self, partner, prefix, fallback_country=None):
        if not partner:
            return {}
        country = partner.country_id or fallback_country
        state = partner.state_id
        if state and country and state.country_id != country:
            state = self.env["res.country.state"]
        return {
            f"{prefix}_postal_code": partner.zip or "",
            f"{prefix}_city": partner.city or "",
            f"{prefix}_country_id": country.id if country else False,
            f"{prefix}_state_id": state.id if state else False,
        }

    @staticmethod
    def _format_address_preview(partner):
        if not partner:
            return False
        parts = [
            partner.street,
            partner.street2,
            " ".join(filter(None, [partner.zip, partner.city])),
            partner.state_id.name if partner.state_id else False,
            partner.country_id.name if partner.country_id else False,
        ]
        preview = ", ".join(filter(None, parts))
        return preview or _("No address saved on this contact yet.")

    @staticmethod
    def _partner_missing_message(partner):
        if not partner:
            return _("Select a contact to load the address automatically.")
        missing = []
        if not partner.street:
            missing.append(_("street"))
        if not partner.city:
            missing.append(_("city"))
        if not partner.zip:
            missing.append(_("postal code"))
        if not partner.country_id:
            missing.append(_("country"))
        if partner.country_id and partner.state_id and partner.state_id.country_id != partner.country_id:
            missing.append(_("state matching country"))
        if not partner.phone and not getattr(partner, "mobile", False):
            missing.append(_("phone"))
        if not partner.email:
            missing.append(_("email"))
        if not missing:
            return False
        return _("Missing on contact: %s") % ", ".join(missing)

    @staticmethod
    def _format_route_point(postal_code, state, country):
        if not postal_code or not country:
            return ""
        state_code = state.code if state else "?"
        return f"{postal_code} {state_code}, {country.code}"

    def _apply_partner_address(self, partner, prefix):
        if not partner:
            return
        fallback_country = self.env.company.country_id if prefix == "origin" else None
        values = self._build_address_defaults(partner, prefix, fallback_country)
        for field_name, value in values.items():
            setattr(self, field_name, value)

    @api.onchange("origin_partner_id")
    def _onchange_origin_partner_id(self):
        self._apply_partner_address(self.origin_partner_id, "origin")

    @api.onchange("destination_partner_id")
    def _onchange_destination_partner_id(self):
        self._apply_partner_address(self.destination_partner_id, "destination")

    @api.onchange("origin_country_id")
    def _onchange_origin_country_id(self):
        if self.origin_state_id and self.origin_state_id.country_id != self.origin_country_id:
            self.origin_state_id = False

    @api.onchange("destination_country_id")
    def _onchange_destination_country_id(self):
        if self.destination_state_id and self.destination_state_id.country_id != self.destination_country_id:
            self.destination_state_id = False

    @api.onchange("origin_postal_code", "origin_country_id", "origin_location_type")
    def _onchange_origin_postal_code(self):
        self._apply_geocode("origin")

    @api.onchange("destination_postal_code", "destination_country_id", "destination_location_type")
    def _onchange_destination_postal_code(self):
        self._apply_geocode("destination")

    @api.onchange("origin_location_type")
    def _onchange_origin_location_type(self):
        if self.origin_location_type == "branch":
            if not self.origin_branch_carrier_id:
                self.origin_branch_carrier_id = self._default_branch_carrier_id()
        else:
            self._branch_lines("origin").write({"is_selected": False})

    @api.onchange("destination_location_type")
    def _onchange_destination_location_type(self):
        if self.destination_location_type == "branch":
            if not self.destination_branch_carrier_id:
                self.destination_branch_carrier_id = self._default_branch_carrier_id()
        else:
            self._branch_lines("destination").write({"is_selected": False})

    def action_lookup_origin_zipcode(self):
        self.ensure_one()
        self._apply_geocode("origin", force=True)
        return self._reopen_wizard()

    def action_lookup_destination_zipcode(self):
        self.ensure_one()
        self._apply_geocode("destination", force=True)
        return self._reopen_wizard()

    def action_load_origin_branches(self):
        self.ensure_one()
        self._load_branches("origin")
        return self._reopen_wizard()

    def action_load_destination_branches(self):
        self.ensure_one()
        self._load_branches("destination")
        return self._reopen_wizard()

    def _resolve_state_from_geocode(self, country, state_payload):
        if not country or not state_payload:
            return self.env["res.country.state"]
        codes = []
        iso_code = state_payload.get("iso_code") or ""
        if iso_code and "-" in iso_code:
            codes.append(iso_code.split("-")[-1])
        code_payload = state_payload.get("code") or {}
        for key in ("3digit", "2digit", "1digit"):
            value = code_payload.get(key)
            if value:
                codes.append(value)
        if not codes:
            return self.env["res.country.state"]
        return self.env["res.country.state"].search(
            [("country_id", "=", country.id), ("code", "in", codes)],
            limit=1,
        )

    def _apply_geocode(self, prefix, force=False):
        country = getattr(self, f"{prefix}_country_id")
        zipcode = getattr(self, f"{prefix}_postal_code")
        if not country or not zipcode:
            return
        zipcode = zipcode.strip()
        if not force and len(zipcode) < 4:
            return
        entries = EnviaGeocodesClient().lookup_zipcode(country.code, zipcode)
        if not entries:
            if force:
                raise UserError(_("No Envia geocode match for postal code %s.") % zipcode)
            return
        entry = entries[0]
        locality = entry.get("locality")
        if locality:
            setattr(self, f"{prefix}_city", locality)
        state = self._resolve_state_from_geocode(country, entry.get("state") or {})
        if state:
            setattr(self, f"{prefix}_state_id", state.id)

    def _load_branches(self, side):
        company = self.env.company
        token = company._envia_get_shipping_api_token()
        if not token:
            raise UserError(_("Configure your Envia shipping API token in Settings first."))
        carrier = getattr(self, f"{side}_branch_carrier_id")
        country = getattr(self, f"{side}_country_id")
        zipcode = getattr(self, f"{side}_postal_code")
        if not carrier:
            raise UserError(_("Select a carrier to search branches."))
        if not country:
            raise UserError(_("Select a country before loading branches."))
        if not zipcode or not zipcode.strip():
            raise UserError(_("Enter a postal code before loading branches."))
        zipcode = zipcode.strip()
        self._apply_geocode(side)
        state = getattr(self, f"{side}_state_id")
        city = getattr(self, f"{side}_city")
        client = EnviaClient(company._envia_get_base_url(), token)
        branches = client.get_branches(
            queries_base_url=company._envia_get_queries_base_url(),
            carrier=carrier.code,
            country_code=country.code,
            zipcode=zipcode,
            search_type=1 if side == "origin" else 2,
            city=city.strip() if city else None,
            state_code=state.code if state else None,
        )
        if not branches:
            raise UserError(
                _("No branches returned for %(carrier)s near this route.")
                % {"carrier": carrier.display_name}
            )
        self._branch_lines(side).unlink()
        lines = []
        for index, entry in enumerate(branches):
            if not isinstance(entry, dict):
                continue
            address = entry.get("address")
            address_data = address if isinstance(address, dict) else {}
            lines.append(
                {
                    "wizard_id": self.id,
                    "side": side,
                    "external_id": str(
                        entry.get("id")
                        or entry.get("branch_id")
                        or entry.get("branchId")
                        or index
                    ),
                    "name": (
                        entry.get("reference")
                        or entry.get("name")
                        or entry.get("description")
                        or entry.get("branch_id")
                        or carrier.code
                    ),
                    "street": (
                        address_data.get("address")
                        or address_data.get("street")
                        or entry.get("street")
                        or ""
                    ),
                    "city": (
                        address_data.get("city")
                        or address_data.get("locality")
                        or entry.get("city")
                        or entry.get("locality")
                        or ""
                    ),
                    "zip": (
                        address_data.get("postalCode")
                        or address_data.get("zipcode")
                        or entry.get("zipcode")
                        or entry.get("zip_code")
                        or entry.get("postalCode")
                        or ""
                    ),
                    "distance": entry.get("distance"),
                    "state_code": (
                        address_data.get("state")
                        or entry.get("state")
                        or entry.get("state_code")
                        or ""
                    ),
                    "country_code": (
                        address_data.get("country")
                        or entry.get("country_code")
                        or country.code
                    ),
                    "carrier": carrier.code,
                    "phone": entry.get("phone") or "",
                    "email": entry.get("email") or "",
                }
            )
        self.env["envia.quote.wizard.branch"].create(lines)

    def _get_selected_branch(self, side):
        return self._branch_lines(side).filtered("is_selected")[:1]

    def action_reload_origin_address(self):
        self.ensure_one()
        self._apply_partner_address(self.origin_partner_id, "origin")
        return self._reopen_wizard()

    def action_reload_destination_address(self):
        self.ensure_one()
        self._apply_partner_address(self.destination_partner_id, "destination")
        return self._reopen_wizard()

    def action_open_origin_partner(self):
        self.ensure_one()
        if not self.origin_partner_id:
            raise UserError(_("Select a ship-from contact first."))
        return self._open_partner_action(self.origin_partner_id)

    def action_open_destination_partner(self):
        self.ensure_one()
        if not self.destination_partner_id:
            raise UserError(_("Select a ship-to contact first."))
        return self._open_partner_action(self.destination_partner_id)

    def action_fill_sandbox_test_route(self):
        self.ensure_one()
        mexico = self.env.ref("base.mx", raise_if_not_found=False)
        if not mexico:
            raise UserError(_("Mexico is not available in this database."))
        origin_state = self.env.ref("base.state_mx_nl", raise_if_not_found=False)
        if not origin_state:
            origin_state = self.env["res.country.state"].search(
                [("country_id", "=", mexico.id), ("code", "in", ["NLE", "NL"])],
                limit=1,
            )
        destination_state = self.env.ref("base.state_mx_df", raise_if_not_found=False)
        if not destination_state:
            destination_state = self.env["res.country.state"].search(
                [("country_id", "=", mexico.id), ("code", "in", ["CMX", "CX", "DIF"])],
                limit=1,
            )
        self.write(
            {
                "origin_postal_code": "67192",
                "origin_city": "Guadalupe",
                "origin_country_id": mexico.id,
                "origin_state_id": origin_state.id if origin_state else False,
                "destination_postal_code": "03100",
                "destination_city": "Ciudad de Mexico",
                "destination_country_id": mexico.id,
                "destination_state_id": destination_state.id if destination_state else False,
            }
        )
        return self._reopen_wizard()

    @staticmethod
    def _open_partner_action(partner):
        return {
            "type": "ir.actions.act_window",
            "name": _("Edit Contact"),
            "res_model": "res.partner",
            "view_mode": "form",
            "res_id": partner.id,
            "target": "new",
        }

    def action_back_to_address(self):
        self.ensure_one()
        self.step = "address"
        return self._reopen_wizard()

    @api.model
    def _get_wizard_window_action(self, res_id=None):
        action = {
            "type": "ir.actions.act_window",
            "name": _("Ship with Envia"),
            "res_model": self._name,
            "view_mode": "form",
            "target": "current",
        }
        if res_id:
            action["res_id"] = res_id
        return action

    @api.model
    def action_open_quote_wizard(self):
        return self._get_wizard_window_action()

    def _reopen_wizard(self):
        self.ensure_one()
        return self._get_wizard_window_action(self.id)

    def action_discard(self):
        return self.env.ref("envia.action_envia_quote").read()[0]

    def _build_branch_contact(self, branch, country, state):
        company_partner = self.env.company.partner_id
        phone = branch.phone or company_partner.phone or company_partner.mobile or "5555555555"
        email = branch.email or company_partner.email or "shipping@company.com"
        return Contact(
            name=branch.name,
            street=branch.street or branch.name,
            city=branch.city or "",
            state=branch.state_code or (state.code if state else ""),
            postal_code=branch.zip or "",
            country=branch.country_code or country.code,
            phone=phone,
            email=email,
        )

    def _build_contact_for_side(self, side):
        prefix = side
        country = getattr(self, f"{prefix}_country_id")
        state = getattr(self, f"{prefix}_state_id")
        postal_code = getattr(self, f"{prefix}_postal_code")
        city = getattr(self, f"{prefix}_city")
        location_type = getattr(self, f"{prefix}_location_type")
        if location_type == "branch":
            branch = self._get_selected_branch(side)
            if not branch:
                label = _("origin") if side == "origin" else _("destination")
                raise UserError(_("Select a %(side)s branch.") % {"side": label})
            return self._build_branch_contact(branch, country, state)
        partner = getattr(self, f"{prefix}_partner_id")
        return self._build_side_contact(partner, postal_code, city, country, state)

    def _build_side_contact(self, partner, postal_code, city, country, state):
        if not partner:
            raise UserError(_("Select a contact for this address."))
        contact = PayloadMapper.partner_to_contact(partner)
        contact.postal_code = postal_code or contact.postal_code
        contact.city = city or contact.city
        contact.country = country.code
        contact.state = state.code if state else ""
        missing = []
        if not contact.street:
            missing.append(_("street"))
        if not contact.city:
            missing.append(_("city"))
        if not contact.postal_code:
            missing.append(_("postal code"))
        if not contact.phone:
            missing.append(_("phone"))
        if not contact.email:
            missing.append(_("email"))
        if missing:
            raise UserError(
                _("Complete contact %(name)s before quoting: %(fields)s")
                % {"name": partner.name, "fields": ", ".join(missing)}
            )
        return contact

    def _collect_validation_errors(self):
        self.ensure_one()
        errors = []
        if self.origin_location_type == "address":
            if self.origin_address_warning:
                errors.append(
                    _("Ship from — %(message)s", message=self.origin_address_warning)
                )
            if not self.origin_partner_id:
                errors.append(_("Ship from contact is required."))
            if not self.origin_city:
                errors.append(_("Origin city is required."))
            if self.origin_country_id and self.origin_country_id.state_ids and not self.origin_state_id:
                errors.append(_("Select an origin state/province."))
        else:
            if not self.origin_branch_carrier_id:
                errors.append(_("Select an origin carrier."))
            if not self._get_selected_branch("origin"):
                errors.append(_("Select an origin branch."))
        if self.destination_location_type == "address":
            if self.destination_address_warning:
                errors.append(
                    _("Ship to — %(message)s", message=self.destination_address_warning)
                )
            if not self.destination_partner_id:
                errors.append(_("Ship to contact is required."))
            if not self.destination_city:
                errors.append(_("Destination city is required."))
            if self.destination_country_id and self.destination_country_id.state_ids and not self.destination_state_id:
                errors.append(_("Select a destination state/province."))
        else:
            if not self.destination_branch_carrier_id:
                errors.append(_("Select a destination carrier."))
            if not self._get_selected_branch("destination"):
                errors.append(_("Select a destination branch."))
        if not self.origin_postal_code:
            errors.append(_("Origin postal code is required."))
        if not self.destination_postal_code:
            errors.append(_("Destination postal code is required."))
        if not self.origin_country_id:
            errors.append(_("Origin country is required."))
        if not self.destination_country_id:
            errors.append(_("Destination country is required."))
        if self.origin_state_id and self.origin_state_id.country_id != self.origin_country_id:
            errors.append(_("Origin state must belong to the selected origin country."))
        if self.destination_state_id and self.destination_state_id.country_id != self.destination_country_id:
            errors.append(_("Destination state must belong to the selected destination country."))
        if self.weight <= 0:
            errors.append(_("Package weight must be greater than zero."))
        if min(self.length, self.width, self.height) <= 0:
            errors.append(_("Package dimensions must be greater than zero."))
        return errors

    def _validate_before_quote(self):
        self.ensure_one()
        errors = self._collect_validation_errors()
        if errors:
            raise UserError("\n".join(errors))

    def _get_quote_carriers(self):
        self.ensure_one()
        carriers = []
        for side in ("origin", "destination"):
            if getattr(self, f"{side}_location_type") != "branch":
                continue
            branch = self._get_selected_branch(side)
            carrier = (
                (branch.carrier if branch else False)
                or self._branch_carrier_code(side)
                or ""
            ).strip().lower()
            if carrier and carrier not in carriers:
                carriers.append(carrier)
        if carriers:
            return ",".join(carriers)
        company = self.env.company
        return company.envia_default_carriers or "all"

    def action_get_quote(self):
        self.ensure_one()
        self._validate_before_quote()
        company = self.env.company
        origin_contact = self._build_contact_for_side("origin")
        destination_contact = self._build_contact_for_side("destination")
        mapper = PayloadMapper()
        request = mapper.build_quote_request_from_values(
            {
                "origin_postal_code": self.origin_postal_code,
                "origin_country": self.origin_country_id.code,
                "origin_state": self.origin_state_id.code if self.origin_state_id else "",
                "destination_postal_code": self.destination_postal_code,
                "destination_country": self.destination_country_id.code,
                "destination_state": self.destination_state_id.code if self.destination_state_id else "",
                "weight": self.weight,
                "length": self.length,
                "width": self.width,
                "height": self.height,
                "content": self.content,
                "declared_value": self.declared_value,
                "currency": self.currency_id.name,
                "carriers": self._get_quote_carriers(),
                "origin_contact": origin_contact,
                "destination_contact": destination_contact,
            }
        )
        adapter = get_envia_adapter(company)
        response = adapter.quote(request)
        quote = self.env["envia.quote"].create_from_api_response(
            response,
            {
                "sale_order_id": self.sale_order_id.id,
                "picking_id": self.picking_id.id,
                "origin_partner_id": self.origin_partner_id.id,
                "destination_partner_id": self.destination_partner_id.id,
                "origin_postal_code": self.origin_postal_code,
                "origin_country": self.origin_country_id.code,
                "origin_state": self.origin_state_id.code if self.origin_state_id else "",
                "destination_postal_code": self.destination_postal_code,
                "destination_country": self.destination_country_id.code,
                "destination_state": self.destination_state_id.code if self.destination_state_id else "",
                "weight": self.weight,
                "length": self.length,
                "width": self.width,
                "height": self.height,
                "content": self.content,
                "declared_value": self.declared_value,
                "currency_id": self.currency_id.id,
                "carriers": self._get_quote_carriers(),
            },
        )
        self.write({"quote_id": quote.id, "step": "rates"})
        self.service_line_ids.unlink()
        lines = []
        for service in quote.service_ids:
            lines.append(
                {
                    "wizard_id": self.id,
                    "service_id": service.service_id,
                    "carrier": service.carrier,
                    "carrier_name": service.carrier_name,
                    "service_name": service.service_name,
                    "price": service.price,
                    "currency_name": service.currency_name,
                    "estimated_delivery_days": service.estimated_delivery_days,
                }
            )
        self.env["envia.quote.wizard.service"].create(lines)
        return self._reopen_wizard()

    def action_confirm_selection(self):
        self.ensure_one()
        selected = self.service_line_ids.filtered("is_selected")[:1]
        if not selected:
            raise UserError(_("Choose a shipping rate to continue."))
        service = self.quote_id.service_ids.filtered(lambda line: line.service_id == selected.service_id)[:1]
        if service:
            service.action_select_service()
        return self.quote_id.action_open_create_shipment_wizard()
