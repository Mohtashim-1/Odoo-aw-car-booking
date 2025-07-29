from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError, UserError

class CarBooking(models.Model):
    _name = 'car.booking'
    _description = 'Car Booking'

    # Existing fields (unchanged, included for context)
    flight_no = fields.Char(string='Flight Number')


    location_id = fields.Many2one(
        'stock.location',
        string='Branch',
        domain=[('usage', '=', 'internal')]
    )

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'car_booking_ir_attachments_rel',  # Custom relation table
        'car_booking_id', 'attachment_id',
        string='Attachments',
        domain="[('res_model', '=', 'car.booking')]",
    )

    mis_charges = fields.Float(
        string='Miscellaneous Charges',)

    trip_profile_id = fields.Many2one(
        'trip.profile',
        string='Trip Profile',
        help="Reference to the trip profile created from this booking."
    )


    state = fields.Selection([
        ('draft', 'Draft'),
        ('request', 'Request'),  # ✅ Add this
        ('confirm', 'Confirm'),
        ('scheduled', 'Scheduled'),
        ('departed', 'Departed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Trip Status', default='draft', tracking=True)

    
    booking_type = fields.Selection([
        ('with_driver', 'Car with Driver(Limousine)'),
        ('rental', 'Rental')
    ], string='Type of Booking')
    extra_services = fields.Many2many('car.extra.service', string='Extra Services')
    region = fields.Selection([
        ('north', 'North'),
        ('south', 'South'),
        ('west', 'West'),
        ('east', 'East'),
        ('central', 'Central'),
    ], string='Region')
    city = fields.Many2one('booking.city', string='City', domain="[('region', '=', region)]")
    customer_type = fields.Selection([
        ('company', 'Company'),
        ('individual', 'Individual')
    ], string='Customer Type')
    customer_name = fields.Many2one('res.partner', string='Customer Name')
    mobile = fields.Char(string='Mobile')
    customer_ref_number = fields.Char(string='Customer Ref Number')
    hotel_room_number = fields.Char(string='Hotel Room Number')
    date_of_service = fields.Date(string='Date of Booking')
    from_date = fields.Date(string='From')
    to_date = fields.Date(string='To')
    duration = fields.Float(string='Duration (Days)', compute='_compute_duration', store=True)
    car_id = fields.Many2one('fleet.vehicle', string='Car')
    driver_name = fields.Many2one('res.partner', string='Driver Name')
    mobile_no = fields.Char(string='Driver Mobile No')
    id_no = fields.Char(string='Driver ID No')
    notes = fields.Html(string="Notes")
    project_name = fields.Many2one('project.project', string="Project Name")
    car_no = fields.Char(string='Car No')
    amount = fields.Float(string='Amount')
    attached = fields.Binary(string='Attached')
    trip_lines = fields.One2many('car.booking.trip.line', 'booking_id', string='Trip Lines')
    is_airport = fields.Boolean(string='Airport Booking')
    airport_id = fields.Many2one('car.airport', string='Airport')
    location_from = fields.Char(string='Location From')
    location_to = fields.Char(string='Location To')
    car_booking_lines = fields.One2many('car.booking.line', 'car_booking_id')


    total_tax = fields.Monetary(string="Vat Total Tax", compute='_compute_total_tax', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)

    @api.depends('car_booking_lines.tax_ids', 'car_booking_lines.unit_price', 'car_booking_lines.amount')
    def _compute_total_tax(self):
        for booking in self:
            total_tax = 0.0
            for line in booking.car_booking_lines:
                price = line.unit_price or 0.0
                # taxes = line.tax_ids.compute_all(price, currency=booking.currency_id)
                # total_tax += sum(t['amount'] for t in taxes['taxes'])
                taxes = line.tax_ids.compute_all(price, booking.currency_id, 1, product=None, partner=None)
                total_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
            
            booking.total_tax = total_tax

    booking_date = fields.Datetime(string='Booking Date')
    reservation_status =  fields.Selection([
        ('created', 'Created'),
         ('invoice_released', 'Invoice Released'),
        ('paid', 'Paid'),
        ('active', 'Active'),
        ('finished', 'Finished'),
        ('cancelled', 'Cancelled'),
    ],default='created', string='Reservation Status')



    business_type =  fields.Selection([
        ('corporate', 'Corporate'),
        ('hotels', 'Hotels'),
        ('government', 'Government'),
        ('individuals', 'Individuals'),
        ('rental', 'Rental'),
        ('others', 'Others'),
    ], string='Business Type')

    guest_name = fields.Many2one('res.partner', string='Guest Name')


    @api.onchange('business_type')
    def _onchange_business_type(self):
        domain = []
        if self.business_type == 'corporate':
            domain = [('category_id.name', '=', 'Companies')]
        elif self.business_type == 'hotels':
            domain = [('category_id.name', '=', 'Hotels')]
        elif self.business_type == 'government':
            domain = [('category_id.name', '=', 'Government')]
        elif self.business_type in ['individuals', 'rental', 'others']:
            domain = [('category_id.name', '=', 'Others')]
        return {'domain': {'customer_name': domain}}




    flight_number = fields.Char(string='Flight Number')

    guest_phone = fields.Char(string='Guest Phone')

    service_start_date = fields.Datetime(string='Service Start Date')
    service_end_date = fields.Datetime(string='Service End Date')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)


    @api.onchange('guest_name')
    def _onchange_guest_name(self):
        if self.guest_name:
            self.guest_phone = self.guest_name.phone or ''
        else:
            self.guest_phone = False
    
    @api.onchange('customer_name')
    def _onchange_customer_name(self):
        if self.customer_name:
            self.mobile = self.customer_name.phone or ''
        else:
            self.mobile = False
          
        


    def action_view_invoice(self):
        self.ensure_one()
        return {
            'name': 'Customer Invoice',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'type': 'ir.actions.act_window',
            'context': {'default_move_type': 'out_invoice'},
        }

    def action_create_invoice(self):
        self.ensure_one()

        if not self.car_booking_lines:
            raise UserError("No booking lines to invoice.")
        if not self.customer_name:
            raise UserError("Customer is not set.")

        invoice_lines = []

        for line in self.car_booking_lines:

            # Extra hour line (if provided)
            if line.extra_hour_charges and line.amount:
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id.id,  # Or use a separate "Extra Hour" product
                    'quantity': line.extra_hour_charges,
                    'price_unit': line.amount,
                    'name': f'Extra Hour Charges ({line.extra_hour_charges} hrs)',
                    'car_booking_line_id': line.id,
                }))
            # Main booking line
            else: 
                invoice_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.qty * line.duration,  # Assuming qty is per day
                'price_unit': line.unit_price,
                'name': line.product_id.name,
                'car_booking_line_id': line.id,
                }))

        # Create invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer_name.id,
            'invoice_line_ids': invoice_lines,
            'car_booking_id': self.id,
        })

        self.invoice_id = invoice.id
        self.reservation_status = 'invoice_released'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }


    @api.onchange('service_start_date', 'service_end_date')
    def _check_service_dates(self):
        if self.service_start_date and self.service_end_date:
            if self.service_end_date < self.service_start_date:
                self.service_end_date = False  # Optional: clear the invalid end date
                return {
                    'warning': {
                        'title': "Invalid Date",
                        'message': "Service End Date cannot be earlier than Service Start Date."
                    }
                }

    From = fields.Char(string='From')

    to = fields.Char(string='To')
    # without_vat_price = fields.Float(string='Without Vat Price')

    without_vat_price = fields.Float(
        'Without Vat Price',
        compute='_compute_amounts',
        store=True
    )
    
    vat = fields.Float(
        'VAT (15%)',
        compute='_compute_amounts',
        store=True
    )

    extra_hour_total = fields.Float(
        'Extra Hour Total',
        compute='_compute_amounts',
        store=True
    )

    extra_hour_charges_total = fields.Float(
        'Extra Hour Charges Total',
        compute='_compute_amounts',
        store=True
    )
    
    amount_total = fields.Float(
        'Total Amount',
        compute='_compute_amounts',
        store=True
    )

    payment_type =  fields.Selection([
        ('cash', 'Cash'),
        ('credit', 'Credit'),
        ('bank_transfer', 'Bank Transfer'),
        ('atm', 'ATM'),
        ('cheque', 'Cheque'),
        ('others', 'Others'),
    ], string='Payment')

    # type_of_service = fields.Selection([
    #     ('transfer', 'Transfer'),
    #     ('full_day', 'Full Day'),
    #     ('tawasila', 'Hourly'),
    #     ('complementary', 'Complementary'),
    #     ('round_trip', 'Round Trip'),
    #     ('rental_service', 'Rental Service'),
    #     ('other', 'Other')
    # ], string='Type of Service')

    full_day_type =  fields.Selection([
        ('6hour', '6 Hour'),
        ('12hour', '12 Hour'),
        ('24hour', '24 Hour'),
    ], string='Full Day Type')


    # @api.onchange('type_of_service')
    # def _onchange_type_of_service(self):
    #     if self.type_of_service != 'full_day':
    #         self.full_day_type = False

    year_model_id = fields.Many2one('year.model', string='Year Model')

    year_car_brand_and_type_id = fields.Many2one('year.car.brand.and.type', string='Car Brand_And Type')
    business_point_id = fields.Many2one('business.point', string='Business Point')


    name = fields.Char(string='Booking Ref', readonly=True, copy=False, default='New')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            if vals.get('booking_type') == 'with_driver':
                seq_code = 'car.booking.with_driver'
            elif vals.get('booking_type') == 'rental':
                seq_code = 'car.booking.rental'
            else:
                seq_code = 'car.booking'  # fallback if needed

            vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or '/'
        return super(CarBooking, self).create(vals)
    
    @api.depends('car_booking_lines.amount')
    def _compute_amounts(self):
        for booking in self:
            # Sum all line amounts
            total_lines = sum(line.amount for line in booking.car_booking_lines)
            charges_total = sum(line.extra_hour_charges for line in booking.car_booking_lines if line.extra_hour_charges)
            hour_total = sum(line.extra_hour for line in booking.car_booking_lines if line.extra_hour)
            booking.without_vat_price = total_lines
            booking.vat = total_lines * 0.15  # 15% VAT
            booking.amount_total = (total_lines * 1.15) + booking.mis_charges
            booking.extra_hour_charges_total = charges_total
            booking.extra_hour_total = hour_total

    # @api.model
    # def create(self, vals):
    #     if vals.get('booking_ref', 'New') == 'New':
    #         vals['booking_ref'] = self.env['ir.sequence'].next_by_code('car.booking') or '/'
    #     return super(CarBooking, self).create(vals)
    # branch_id = fields.Many2one('branch', string='Branch')

    # year_model = fields.Selection([
    #     ('full_day', 'Transfer'),
    #     ('full_day', 'Full Day'),
    #     ('tawasila', 'Hourly')
    #     ('full_day', 'Complementary'),
    #     ('full_day', 'Round Trip'),
    #     ('full_day', 'Rental Service'),
    #     ('other', 'Other')
    # ], string='Type of Service')

    # car_brand_and_type = fields.Selection([
    #     ('full_day', 'Transfer'),
    #     ('full_day', 'Full Day'),
    #     ('tawasila', 'Hourly')
    #     ('full_day', 'Complementary'),
    #     ('full_day', 'Round Trip'),
    #     ('full_day', 'Rental Service'),
    #     ('other', 'Other')
    # ], string='Type of Service')

    # business_point = fields.Selection([
    #     ('full_day', 'Transfer'),
    #     ('full_day', 'Full Day'),
    #     ('tawasila', 'Hourly')
    #     ('full_day', 'Complementary'),
    #     ('full_day', 'Round Trip'),
    #     ('full_day', 'Rental Service'),
    #     ('other', 'Other')
    # ], string='Type of Service')

    # branch = fields.Selection([
    #     ('full_day', 'Transfer'),
    #     ('full_day', 'Full Day'),
    #     ('tawasila', 'Hourly')
    #     ('full_day', 'Complementary'),
    #     ('full_day', 'Round Trip'),
    #     ('full_day', 'Rental Service'),
    #     ('other', 'Other')
    # ], string='branch')






    # def action_view_trip_profile(self):
    #     """Return an action to view the associated trip.profile record."""
    #     self.ensure_one()
    #     trip_profile = self.env['trip.profile'].search([('booking_id', '=', self.id)], limit=1)
    #     if not trip_profile:
    #         raise UserError("No Trip Profile found for this booking. Please ensure the booking has been approved and a trip profile has been created.")
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'trip.profile',
    #         'view_mode': 'form',
    #         'res_id': trip_profile.id,
    #         'target': 'current',
    #         'context': self.env.context,
    #     }

    def action_view_trip_profile(self):
        """Return an action to view or create the associated trip.profile record."""
        self.ensure_one()
        
        # Use the direct relationship field instead of searching by booking_id
        if self.trip_profile_id:
            # Open existing trip profile form
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'trip.profile',
                'view_mode': 'form',
                'res_id': self.trip_profile_id.id,
                'target': 'current',
                'context': self.env.context,
            }
        else:
            # Create trip profile first, then open it
            self._create_trip_profile()
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'trip.profile',
                'view_mode': 'form',
                'res_id': self.trip_profile_id.id,
                'target': 'current',
                'context': self.env.context,
            }


    
    def _create_trip_profile(self):
        """Create or update a trip.profile and its trip.vehicle.line lines
        so that it mirrors this booking."""
        for booking in self:
            # -----------------------------------------------------------------
            # 1. PREPARE PROFILE VALUES (FIELD‑BY‑FIELD COPY)
            # -----------------------------------------------------------------
            profile_vals = {
                'name':                booking.name,                 # Booking Ref
                'trip_type':           'individual',                 # default – adjust if you have logic
                'service_type':        'with_driver' if booking.booking_type == 'with_driver' else 'without_driver',
                'departure_datetime':  booking.service_start_date or booking.booking_date,
                'expected_arrival_datetime': booking.service_end_date or booking.service_start_date,
                # 'departure_point_id':  False,
                # 'arrival_point_id':    False,
                'driver_id':           booking.driver_name.id,
                'customer_name':         booking.customer_name.id,
                'guest_name':         booking.guest_name.id,
                'project_id':          booking.project_name.id,
                # --- synced XML/basic fields ---
                'region':              booking.region,
                'booking_type':        booking.booking_type,          # ('airport', 'hotel', …) selection
                'flight_number':       booking.flight_number,
                'location_from':       booking.location_from,
                'location_to':         booking.location_to,
                'location_id':         booking.location_id.id if booking.location_id else False,
                'guest_phone':         booking.guest_phone,
                'invoice_id':          booking.invoice_id.id,
                'customer_ref_number': booking.customer_ref_number,
                'business_type':       booking.business_type,
                'reservation_status':  booking.reservation_status,
                'date_of_service':     booking.date_of_service,
                'payment_type':        booking.payment_type,
                'hotel_room_number':   booking.hotel_room_number,
                'mobile':   booking.mobile,
                'attachment_ids':      [(6, 0, booking.attachment_ids.ids)],
            }

            # -----------------------------------------------------------------
            # 2. FIND OR CREATE TRIP PROFILE
            # -----------------------------------------------------------------
            if booking.trip_profile_id:
                trip_profile = booking.trip_profile_id
                trip_profile.write(profile_vals)
            else:
                trip_profile = self.env['trip.profile'].create(profile_vals)
                booking.trip_profile_id = trip_profile.id

            # -----------------------------------------------------------------
            # 3. CLEAR OLD LINES & RE-CREATE FROM car.booking.line
            # -----------------------------------------------------------------
            trip_profile.vehicle_line_ids.unlink()

            vehicle_lines = []
            for line in booking.car_booking_lines:
                vehicle_lines.append((0, 0, {
                    'trip_id':            trip_profile.id,
                    # ---- field‑for‑field copy ----
                    'name':                 line.name,
                    'vehicle_id':           line.fleet_vehicle_id.id,
                    'driver_id':            line.driver_name.id,
                    'car_model':            line.car_model,
                    'car_model_id':         line.car_model_id.id,
                    'car_year':             line.car_year,
                    'product_id':           line.product_id.id,
                    'product_category_id':  line.product_category_id.id,
                    'qty':                  line.qty,
                    'unit_price':           line.unit_price,
                    'amount':               line.amount,
                    'start_date':           line.start_date,
                    'end_date':             line.end_date,
                    'total_hours':          line.total_hours,
                    'duration':             line.duration,
                    'extra_hour':           line.extra_hour,
                    'extra_hour_charges':   line.extra_hour_charges,
                    'mobile_no':            line.mobile_no,
                    'id_no':                line.id_no,
                    'guest_ids': [(6, 0, line.guest_name.ids if line.guest_name else [])],
                    'notes':                False,
                }))
            trip_profile.write({'vehicle_line_ids': vehicle_lines})

            # -----------------------------------------------------------------
            # 4. OPTIONAL: POST A MESSAGE / LOG
            # -----------------------------------------------------------------
            # booking.message_post(
            #     body=_("Trip Profile <a href=# data-oe-model='trip.profile' data-oe-id='%d'>%s</a> created/updated.") %
            #          (trip_profile.id, trip_profile.name)
            # )

        # ---------------------------------------------------------------------
        # 5. RETURN ACTION TO OPEN THE PROFILE (single record only)
        # ---------------------------------------------------------------------
        # if len(self) == 1:
        #     return {
        #         'type': 'ir.actions.act_window',
        #         'name': ('Trip Profile'),
        #         'res_model': 'trip.profile',
        #         'res_id': self.trip_profile_id.id,
        #         'view_mode': 'form',
        #         'target': 'current',
        #     }
        return True
    
    


    

    def _get_driver_id(self, booking):
        """Map driver_name (res.partner) to driver_id (hr.employee)."""
        if booking.driver_name:
            employee = self.env['hr.employee'].search([('address_home_id', '=', booking.driver_name.id)], limit=1)
            return employee.id if employee else False
        return False

    def _get_contract_id(self, booking):
        """Map project_name or other field to sale.order (contract)."""
        if booking.project_name:
            contract = self.env['sale.order'].search([('project_id', '=', booking.project_name.id)], limit=1)
            return contract.id if contract else False
        return False

    def _get_contract_type(self, booking):
        """Determine contract type based on duration or other logic."""
        if booking.duration:
            if booking.duration <= 1:
                return 'daily'
            elif booking.duration <= 7:
                return 'weekly'
            else:
                return 'monthly'
        return False

    def _map_vehicle_type(self, vehicle):
        """Map fleet.vehicle to vehicle_type in trip.vehicle.line."""
        if vehicle.model_id:
            model_name = vehicle.model_id.name.lower()
            if 'sedan' in model_name:
                return 'sedan'
            elif 'suv' in model_name:
                return 'suv'
            elif 'van' in model_name:
                return 'van'
        return 'other'

    # Rest of the existing methods (unchanged)
    def duplicate_booking(self):
        self.ensure_one()
        new_booking_vals = {
            'customer_name': self.customer_name,
            'state': 'draft',
        }
        new_booking = self.create(new_booking_vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'car.booking',
            'view_mode': 'form',
            'res_id': new_booking.id,
            'target': 'current',
        }

    @api.onchange('region')
    def _onchange_region(self):
        if self.region:
            self.city = False
        return {
            'domain': {
                'city': [('region', '=', self.region)] if self.region else []
            }
        }

    # @api.onchange('type_of_service')
    # def _onchange_type_of_service(self):
    #     if self.type_of_service == 'tawasila':
    #         if not self.trip_lines:
    #             self.trip_lines = [(0, 0, {})]
    #     else:
    #         self.trip_lines = [(5, 0, 0)]

    # @api.onchange('is_airport')
    # def _onchange_is_airport(self):
    #     if not self.is_airport:
    #         self.airport_id = False
    #         self.location_from = False
    #         self.location_to = False

    def action_cancel(self):
        for record in self:
            if record.state in ('draft', 'confirm'):
                record.state = 'cancelled'
                record.reservation_status = 'cancelled'
            else:
                raise ValidationError("Can only cancel bookings in Draft or Confirm for Approval state.")
            
            
    def action_confirm(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'confirm'
                self._create_trip_profile()
            else:
                raise ValidationError("Can only request Confirm from Draft state.")
    
    def action_reset_draft(self):
        for record in self:
            if record.state == 'cancelled':
                record.state = 'draft'
            else:
                raise ValidationError("Can only request Draft from Cancelled state.")


    # def action_request_approval(self):
    #     for record in self:
    #         if record.state == 'draft':
    #             record.state = 'request'
    #         else:
    #             raise ValidationError("Can only request approval from Draft state.")

    @api.depends('car_booking_lines.duration')
    def _compute_duration(self):
        for record in self:
            if record.car_booking_lines:
                total_duration = sum(line.duration for line in record.car_booking_lines if line.duration)
                record.duration = total_duration
            else:
                record.duration = 0.0

    @api.onchange('booking_type')
    def _onchange_booking_type(self):
        if self.booking_type != 'with_driver':
            self.driver_name = False
            self.mobile_no = False
            self.id_no = False

    @api.onchange('customer_type')
    def _onchange_customer_type(self):
        if self.customer_type != 'company':
            self.project_name = False
            self.car_no = False
            self.amount = 0.0
            self.attached = False

class CarBookingTripLine(models.Model):
    _name = 'car.booking.trip.line'
    _description = 'Car Booking Trip Line'

    booking_id = fields.Many2one('car.booking', string='Booking', required=True, ondelete='cascade')
    car_id = fields.Many2one('fleet.vehicle', string='Car', required=True)
    price = fields.Float(string='Price', related='car_id.rental_price', readonly=True)
    trip_date = fields.Date(string='Trip Date', default=fields.Date.today)
    # location_from = fields.Char(string='Location From')
    # location_to = fields.Char(string='Location To')
    trip_time = fields.Datetime(string='Trip Time')
    flight_no = fields.Char(string='Flight Number')

    @api.onchange('car_id')
    def _onchange_car_id(self):
        if self.car_id:
            self.price = self.car_id.rental_price or 0.0
            
class Airport(models.Model):
    _name = 'car.airport'
    _description = 'Airport'

    name = fields.Char(string='Airport Name', required=True)
            
class CarBookingLine(models.Model):
    _name = "car.booking.line"
    
    name = fields.Char(
        string="Name",
    )
    type_of_service_id = fields.Many2one(
        'type.of.service', string="Type of Service",
        help="Type of service for the car booking, e.g., transfer, full day, hourly, etc.")
    

    start_date = fields.Datetime(
        string="Start Date",
        help="Start date of the car booking or service period."
    )
    end_date = fields.Datetime(
        string="End Date",
        help="End date of the car booking or service period."
    )


    total_hours = fields.Float(string="Total Hours", compute="_compute_total_hours", store=True)

    trip_vehicle_line_id = fields.Many2one('trip.vehicle.line', string='Trip Vehicle Line',)


    tax_ids = fields.Many2many('account.tax', string="Vat Taxes")

    @api.depends('start_date', 'end_date')
    def _compute_total_hours(self):
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.total_hours = delta.total_seconds() / 3600.0  # convert seconds to hours
            else:
                record.total_hours = 0.0
    
    car_booking_id = fields.Many2one(
        'car.booking',
        string="Car Booking",
        help="Reference to the main car booking record."
    )
    duration = fields.Float(
        string='Duration (Days)',
        compute='_compute_duration',
        store=True,
        help="Total number of days between start and end date."
    )

    fleet_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Fleet Vehicle',
        help="Select the fleet vehicle assigned for this booking."
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help="Select the product or service associated with this booking line."
    )
    product_category_id = fields.Many2one(
        'product.category',
        string='Product Category',
        help="Category of the selected product or service."
    )
    car_model_id = fields.Many2one('fleet.vehicle.model',
        string='Car Model',
        help="Model name of the car being used."
    )


    car_model = fields.Char(
        string='Car Model',
        help="Model name of the car being used."
    )
    
    car_year = fields.Selection(
    selection=[
        ('2018', '2018'),
        ('2019', '2019'),
        ('2020', '2020'),
        ('2021', '2021'),
        ('2022', '2022'),
        ('2023', '2023'),
        ('2024', '2024'),
        ('2025', '2025'),
    ],
    string='Car Year',
    help="Manufacturing year of the car."
)
    qty = fields.Integer(
    string='Qty',
    default=1,
    help="Quantity of the selected product or service."
)
    unit_price = fields.Float(
        string='Price',
        help="Unit price of the product or service."
    )

    extra_hour = fields.Integer(
        string='Extra Hour',
        help="Extra Hour"
    )
    extra_hour_charges = fields.Float(
        string='Extra Hour Charges',
        help="Extra Hour Charges"
    )
    amount = fields.Float(
        string='Amount',
        help="Total amount (Qty × Unit Price)."
    )

    driver_name = fields.Many2one(
        'res.partner',
        string='Driver Name',
        help="Select the driver assigned to this booking."
    )
    mobile_no = fields.Char(
        string='Driver Mobile No',
        help="Mobile phone number of the assigned driver."
    )
    id_no = fields.Char(
        string='Driver ID No',
        help="Identification number of the driver."
    )


        # ------------------------------------------------------------------
    #  Header / basic info
    # ------------------------------------------------------------------
    flight_no = fields.Char(related='car_booking_id.flight_no', store=True, readonly=True)
    booking_state = fields.Selection(related='car_booking_id.state', store=True, readonly=True)
    booking_date = fields.Datetime(related='car_booking_id.booking_date', store=True, readonly=True)
    reservation_status = fields.Selection(related='car_booking_id.reservation_status', store=True, readonly=True)

    # ------------------------------------------------------------------
    #  Customer & contact
    # ------------------------------------------------------------------
    region = fields.Selection(related='car_booking_id.region', store=True, readonly=True)
    city = fields.Many2one(related='car_booking_id.city', store=True, readonly=True)
    customer_type = fields.Selection(related='car_booking_id.customer_type', store=True, readonly=True)
    customer_name = fields.Many2one(related='car_booking_id.customer_name', store=True, readonly=True)
    mobile = fields.Char(related='car_booking_id.mobile', store=True, readonly=True)
    customer_ref_number = fields.Char(related='car_booking_id.customer_ref_number', store=True, readonly=True)
    hotel_room_number = fields.Char(related='car_booking_id.hotel_room_number', store=True, readonly=True)
    guest_name = fields.Many2one(related='car_booking_id.guest_name', store=True, readonly=True)
    business_type = fields.Selection(related='car_booking_id.business_type', store=True, readonly=True)

    # ------------------------------------------------------------------
    #  Locations
    # ------------------------------------------------------------------
    branch_id = fields.Many2one(related='car_booking_id.location_id', store=True, readonly=True)
    location_from = fields.Char(related='car_booking_id.location_from', store=True, readonly=True)
    location_to = fields.Char(related='car_booking_id.location_to', store=True, readonly=True)
    airport_id = fields.Many2one(related='car_booking_id.airport_id', store=True, readonly=True)

    guest_ids = fields.Many2many(
        'res.partner', string="Guests Name",)


    @api.onchange('driver_name')
    def _onchange_res_partner_id(self):
        if self.driver_name:
            self.id_no = self.driver_name.national_identity_number
            self.mobile_no = self.driver_name.customized_mobile
        else:
            self.id_no = False
            self.mobile_no = False

    @api.onchange('id_no')
    def _onchange_national_identity_number(self):
        if self.id_no:
            partner = self.env['res.partner'].search([
                ('national_identity_number', '=', self.id_no)
            ], limit=1)
            if partner:
                self.driver_name = partner.id
                self.mobile_no = partner.customized_mobile
            else:
                self.driver_name = False
                self.mobile_no = False
        else:
            self.driver_name = False
            self.mobile_no = False

    @api.onchange('mobile_no')
    def _onchange_mobile(self):
        if self.mobile_no:
            partner = self.env['res.partner'].search([
                ('customized_mobile', '=', self.mobile_no)
            ], limit=1)
            if partner:
                self.driver_name = partner.id
                self.id_no = partner.national_identity_number
            else:
                self.driver_name = False
                self.id_no = False
        else:
            self.driver_name = False
            self.id_no = False
    # car_plate_no = fields.Char(
    #     string='Car Plate No',
    #     help="License plate number of the car."
    # )

    @api.onchange('start_date', 'end_date')
    def _onchange_start_end_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            # Reset the invalid end_date or start_date, or just warn
            self.end_date = False  # or self.end_date = self.start_date
            
            return {
                'warning': {
                    'title': "Invalid Date Range",
                    'message': "End Date cannot be earlier than Start Date. Please correct it.",
                }
            }
    # @api.onchange('qty', 'unit_price', 'duration', 'extra_hour_charges', 'extra_hour')
    # def _onchange_amount(self):
    #     amount_val = 0.0
    #     for record in self:
    #         if not record.extra_hour_charges:
    #             if record.qty and record.unit_price and record.duration:
    #                 record.amount = record.qty * record.unit_price * record.duration
    #         else:
    #             amount_val = record.qty * record.unit_price * record.duration
    #             record.amount = (record.extra_hour_charges * record.extra_hour ) + amount_val

    @api.onchange('qty', 'unit_price', 'duration', 'extra_hour_charges', 'extra_hour')
    def _onchange_amount(self):
        for record in self:
            record._compute_amount_values()

    def _compute_amount_values(self):
        for record in self:
            qty = record.qty or 1
            unit_price = record.unit_price or 1
            duration = record.duration or 1
            extra_hour = record.extra_hour or 0
            extra_hour_charges = record.extra_hour_charges or 0

            base_amount = qty * unit_price
            extra_amount = extra_hour * extra_hour_charges if extra_hour else 0
            record.amount = base_amount + extra_amount

    @api.onchange('car_booking_id')
    def _onchange_car_booking_id_date_of_service(self):
        if self.car_booking_id and self.car_booking_id.date_of_service:
            self.name = self.car_booking_id.date_of_service

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        """Compute duration for each line based on start_date and end_date."""
        for record in self:
            if record.start_date and record.end_date:
                start_date = fields.Date.from_string(record.start_date)
                end_date = fields.Date.from_string(record.end_date)
                delta = end_date - start_date
                # Ensure duration is non-negative
                record.duration = max(delta.days, 0)
            else:
                record.duration = 0.0