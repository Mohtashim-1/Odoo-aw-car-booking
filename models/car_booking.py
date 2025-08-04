from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError, UserError
from datetime import timedelta

class CarBooking(models.Model):
    _name = 'car.booking'
    _description = 'Car Booking'

    # Existing fields (unchanged, included for context)


    location_id = fields.Many2one(
        'stock.location',
        string='Branch',
        domain=[('usage', '=', 'internal')],
        default=lambda self: self._get_default_branch()
    )
    
    # Use company branch as the main branch field
    branch_id = fields.Many2one(
        'res.company',
        string='Branch',
        domain="[]",
        default=lambda self: self._get_default_company_branch()
    )
    
    # Company field for multi-company support
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
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
        ('invoiced', 'Invoiced'),
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
    customer_name = fields.Many2one(
        'res.partner', 
        string='Customer Name',
        domain="[('category_id', '=', customer_domain_category_id)]"
    )
    
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
    
    # Computed field to help with domain filtering
    customer_domain_category_id = fields.Many2one(
        'res.partner.category',
        string='Customer Domain Category',
        compute='_compute_customer_domain_category',
        store=False
    )
    
    @api.depends('business_type')
    def _compute_customer_domain_category(self):
        """Compute the category ID for customer domain filtering"""
        for record in self:
            try:
                if record.business_type:
                    category_mapping = {
                        'corporate': 'Companies',
                        'hotels': 'Hotels', 
                        'government': 'Government',
                        'individuals': 'Individuals',
                        'rental': 'Rental',
                        'others': 'Others'
                    }
                    
                    category_name = category_mapping.get(record.business_type)
                    if category_name:
                        category = self.env['res.partner.category'].search([('name', '=', category_name)], limit=1)
                        if not category:
                            category = self.env['res.partner.category'].create({
                                'name': category_name,
                                'color': 1
                            })
                        record.customer_domain_category_id = category.id
                    else:
                        record.customer_domain_category_id = False
                else:
                    record.customer_domain_category_id = False
            except Exception:
                # Handle any errors gracefully during copy operations
                record.customer_domain_category_id = False

    guest_name = fields.Many2one('res.partner', string='Guest Name')







    flight_number = fields.Char(string='Flight Number')

    guest_phone = fields.Char(string='Guest Phone')

    service_start_date = fields.Datetime(string='Service Start Date')
    service_end_date = fields.Datetime(string='Service End Date')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    quotation_id = fields.Many2one('sale.order', string='Quotation', readonly=True, copy=False)


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

    def action_view_quotation(self):
        self.ensure_one()
        return {
            'name': 'Car Booking Quotation',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': self.quotation_id.id,
            'type': 'ir.actions.act_window',
            'context': {'default_car_booking_id': self.id},
        }



    def action_create_quotation(self):
        """Create a quotation (sale order) from car booking"""
        self.ensure_one()

        if not self.car_booking_lines:
            raise UserError("No booking lines to create quotation.")
        if not self.customer_name:
            raise UserError("Customer is not set.")

        # Create sale order lines from car booking lines
        order_lines = []
        
        for line in self.car_booking_lines:
            # Calculate base amount (qty * unit_price * duration)
            base_amount = (line.qty or 1) * (line.unit_price or 0) * (line.duration or 1)
            line.amount = base_amount
            
            # Add extra hour charges if any
            extra_charges = 0.0
            if line.extra_hour and line.extra_hour > 0 and line.extra_hour_charges:
                extra_charges = line.extra_hour * line.extra_hour_charges
            
            # Create order line
            order_line_vals = {
                'product_id': line.product_id.id if line.product_id else False,
                'name': line.product_id.name if line.product_id else f"Car Booking Service - {line.type_of_service_id.name if line.type_of_service_id else 'Service'}",
                'product_uom_qty': (line.qty or 1) * (line.duration or 1),  # Total quantity including duration
                'price_unit': line.unit_price or 0,  # Unit price per day
                'price_subtotal': base_amount,  # Base amount without additional charges
                'price_tax': 0,  # Will be calculated automatically
                'price_total': base_amount,  # Will be calculated automatically
                
                # Copy taxes from car booking line
                'tax_id': [(6, 0, line.tax_ids.ids)] if line.tax_ids else False,
                
                # Car booking specific fields
                'car_booking_line_id': line.id,
                'service_type': line.type_of_service_id.id if line.type_of_service_id else False,
                'car_type': line.car_model_id.id if line.car_model_id else False,
                'date_start': line.start_date,
                'date_end': line.end_date,
                'duration': line.duration,
                'additional_charges': extra_charges,  # Store extra charges separately
            }
            
            order_lines.append((0, 0, order_line_vals))

        # Create sale order (quotation)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer_name.id,
            'car_booking_id': self.id,
            'order_line': order_lines,
            'note': self.notes or '',
            'date_order': fields.Datetime.now(),
            'validity_date': fields.Date.today() + timedelta(days=30),  # 30 days validity
        })

        # Force recalculation of amounts after creation
        sale_order._compute_amounts()
        
        # Force recalculation of line amounts
        for line in sale_order.order_line:
            line._compute_amount()
        
        # Recalculate order totals
        sale_order._compute_amounts()

        # Update reservation status and link quotation
        self.reservation_status = 'invoice_released'
        self.quotation_id = sale_order.id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_car_booking_id': self.id},
        }

    def action_create_invoice(self):
        """Create an invoice from car booking (legacy method)"""
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
                }))
            # Main booking line
            else: 
                invoice_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.qty * line.duration,  # Assuming qty is per day
                'price_unit': line.unit_price,
                'name': line.product_id.name,
                }))

        # Create invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer_name.id,
            'invoice_line_ids': invoice_lines,
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

    def _get_default_branch(self):
        """Get the default branch for the current user"""
        try:
            # Get the current user's default warehouse
            warehouse = self.env.user._get_default_warehouse_id()
            if warehouse and warehouse.lot_stock_id:
                return warehouse.lot_stock_id.id
            return False
        except Exception:
            return False

    def _get_default_company_branch(self):
        """Get the default company branch for the current user"""
        try:
            # Get the current user's company as the branch
            current_company = self.env.company
            return current_company.id
        except Exception:
            return False

    @api.model
    def create(self, vals):
        # Set default branch if not provided
        if not vals.get('location_id'):
            default_branch = self._get_default_branch()
            if default_branch:
                vals['location_id'] = default_branch
        
        # Set default company branch if not provided
        if not vals.get('branch_id'):
            default_branch = self._get_default_company_branch()
            if default_branch:
                vals['branch_id'] = default_branch
        
        # Generate sequence number only when creating the record
        if vals.get('name', 'New') == 'New':
            # Determine sequence code based on booking type
            if vals.get('booking_type') == 'with_driver':
                seq_code = 'car.booking.with_driver'
            elif vals.get('booking_type') == 'rental':
                seq_code = 'car.booking.rental'
            else:
                seq_code = 'car.booking'  # fallback if needed

            # Try to get existing sequence or create new one
            sequence = self.env['ir.sequence'].next_by_code(seq_code)
            if sequence:
                vals['name'] = sequence
            else:
                # If sequence doesn't exist, try to find the highest existing number
                existing_bookings = self.env['car.booking'].search([('name', '!=', 'New')])
                if existing_bookings:
                    # Extract numbers from existing booking names
                    numbers = []
                    for booking in existing_bookings:
                        if booking.name and '/' in booking.name:
                            try:
                                num_part = booking.name.split('/')[-1]
                                numbers.append(int(num_part))
                            except (ValueError, IndexError):
                                continue
                    
                    if numbers:
                        next_number = max(numbers) + 1
                        vals['name'] = f"DSL/{str(next_number).zfill(5)}"
                    else:
                        vals['name'] = "DSL/00001"
                else:
                    vals['name'] = "DSL/00001"
        
        return super(CarBooking, self).create(vals)
    
    @api.depends('car_booking_lines.amount', 'car_booking_lines.extra_hour', 'car_booking_lines.extra_hour_charges')
    def _compute_amounts(self):
        for booking in self:
            # Sum all line amounts
            total_lines = sum(line.amount for line in booking.car_booking_lines)
            
            # Only count extra_hour_charges for lines that have extra_hour > 0
            charges_total = sum(
                line.extra_hour_charges 
                for line in booking.car_booking_lines 
                if line.extra_hour and line.extra_hour > 0 and line.extra_hour_charges
            )
            
            # Sum total extra hours
            hour_total = sum(line.extra_hour for line in booking.car_booking_lines if line.extra_hour and line.extra_hour > 0)
            
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
        print(f"DEBUG: action_view_trip_profile called for booking: {self.name}")
        
        # Use the direct relationship field instead of searching by booking_id
        trip_profile = self.trip_profile_id
        try:
            # Check if trip_profile is a valid record
            if trip_profile and hasattr(trip_profile, 'name') and trip_profile.name and trip_profile.id:
                print(f"DEBUG: Existing trip profile found: {trip_profile.name}")
                # Open existing trip profile form
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'trip.profile',
                    'view_mode': 'form',    
                    'res_id': trip_profile.id,
                    'target': 'current',
                    'context': self.env.context,
                }
        except Exception as e:
            print(f"DEBUG: Error accessing trip_profile_id: {e}")
            # Clear the invalid trip_profile_id
            self.trip_profile_id = False
        
        print(f"DEBUG: No existing trip profile, creating new one")
        # Create trip profile first, then open it
        try:
            print(f"DEBUG: Checking if create_from_booking method exists")
            trip_profile_model = self.env['trip.profile']
            print(f"DEBUG: Trip profile model: {trip_profile_model}")
            print(f"DEBUG: Available methods: {[m for m in dir(trip_profile_model) if 'create_from_booking' in m]}")
            
            trip_profile = trip_profile_model.create_from_booking(self)
            print(f"DEBUG: Created trip profile: {trip_profile.name}")
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'trip.profile',
                'view_mode': 'form',
                'res_id': trip_profile.id,
                'target': 'current',
                'context': self.env.context,
            }
        except Exception as e:
            print(f"DEBUG: Error creating trip profile: {e}")
            # Fallback to old method
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
            # Use the new method that ensures proper saving
            trip_profile = self.env['trip.profile'].create_from_booking_with_save(booking)
            return trip_profile
    
    


    

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

    def action_ensure_partner_categories_exist(self):
        """Ensure that all required partner categories exist"""
        category_mapping = {
            'corporate': 'Companies',
            'hotels': 'Hotels', 
            'government': 'Government',
            'individuals': 'Individuals',
            'rental': 'Rental',
            'others': 'Others'
        }
        
        for business_type, category_name in category_mapping.items():
            category = self.env['res.partner.category'].search([('name', '=', category_name)], limit=1)
            if not category:
                self.env['res.partner.category'].create({
                    'name': category_name,
                    'color': 1
                })
                print(f"Created partner category: {category_name}")
        
        return True

    def action_assign_partners_to_categories(self):
        """Assign partners to appropriate categories based on their business type"""
        self.action_ensure_partner_categories_exist()
        
        # Get all categories
        categories = self.env['res.partner.category'].search([])
        category_dict = {cat.name: cat for cat in categories}
        
        # Get all partners
        partners = self.env['res.partner'].search([])
        assigned_count = 0
        
        for partner in partners:
            # Determine category based on partner name or other criteria
            category_name = None
            
            # Simple logic to categorize partners
            partner_name_lower = partner.name.lower() if partner.name else ''
            
            if any(word in partner_name_lower for word in ['hotel', 'resort', 'inn', 'lodge']):
                category_name = 'Hotels'
            elif any(word in partner_name_lower for word in ['corp', 'company', 'ltd', 'inc', 'llc']):
                category_name = 'Companies'
            elif any(word in partner_name_lower for word in ['gov', 'ministry', 'department', 'authority']):
                category_name = 'Government'
            elif any(word in partner_name_lower for word in ['rental', 'car', 'vehicle']):
                category_name = 'Rental'
            else:
                # Default to Individuals for personal names
                if not partner.is_company:
                    category_name = 'Individuals'
                else:
                    category_name = 'Others'
            
            if category_name and category_name in category_dict:
                category = category_dict[category_name]
                if category not in partner.category_id:
                    partner.category_id = [(4, category.id)]
                    assigned_count += 1
                    print(f"DEBUG: Assigned partner '{partner.name}' to category '{category_name}'")
        
        # Also fix the typo in existing categories
        coorporate_category = self.env['res.partner.category'].search([('name', '=', 'Coorporate')], limit=1)
        if coorporate_category:
            print(f"DEBUG: Found typo category 'Coorporate', renaming to 'Companies'")
            coorporate_category.name = 'Companies'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Partner Categories',
                'message': f'Assigned {assigned_count} partners to appropriate categories.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_test_business_type_filter(self):
        """Test the business type filter functionality"""
        self.ensure_one()
        
        # Test the filter logic
        if self.business_type:
            category_mapping = {
                'corporate': 'Companies',
                'hotels': 'Hotels', 
                'government': 'Government',
                'individuals': 'Individuals',
                'rental': 'Rental',
                'others': 'Others'
            }
            
            category_name = category_mapping.get(self.business_type)
            if category_name:
                category = self.env['res.partner.category'].search([('name', '=', category_name)], limit=1)
                if category:
                    # Count partners in this category
                    partners_in_category = self.env['res.partner'].search_count([('category_id', 'in', [category.id])])
                    
                    # Get some sample partners in this category
                    sample_partners = self.env['res.partner'].search([('category_id', 'in', [category.id])], limit=5)
                    partner_names = [p.name for p in sample_partners]
                    
                    message = f"Business Type: {self.business_type}\nCategory: {category_name}\nPartners in category: {partners_in_category}\nSample partners: {', '.join(partner_names) if partner_names else 'None'}"
                else:
                    message = f"Category '{category_name}' not found. Creating it now..."
                    category = self.env['res.partner.category'].create({
                        'name': category_name,
                        'color': 1
                    })
                    message = f"Created category '{category_name}' with ID {category.id}"
            else:
                message = f"No category mapping found for business type '{self.business_type}'"
        else:
            message = "No business type selected"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Filter Test',
                'message': message,
                'type': 'info',
                'sticky': False,
            }
        }

    def action_trigger_business_type_filter(self):
        """Manually trigger the business type filter"""
        self.ensure_one()
        
        if not self.business_type:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Filter Error',
                    'message': 'Please select a Business Type first.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        print(f"DEBUG: action_trigger_business_type_filter called for business_type: {self.business_type}")
        
        # Manually trigger the onchange
        result = self._onchange_business_type()
        
        # Get the domain
        domain = result.get('domain', {}).get('customer_name', [])
        
        message = f"Filter triggered for Business Type: {self.business_type}\nDomain: {domain}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Filter Triggered',
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_debug_onchange_test(self):
        """Debug the onchange method and show detailed information"""
        self.ensure_one()
        
        print(f"DEBUG: action_debug_onchange_test called")
        print(f"DEBUG: Current business_type: {self.business_type}")
        print(f"DEBUG: Current customer_name: {self.customer_name.name if self.customer_name else 'None'}")
        
        # Test the onchange method
        result = self._onchange_business_type()
        
        # Show all partner categories
        categories = self.env['res.partner.category'].search([])
        category_info = "\n".join([f"- {cat.name} (ID: {cat.id})" for cat in categories[:10]])
        
        # Show sample partners with their categories
        partners = self.env['res.partner'].search([], limit=10)
        partner_info = "\n".join([f"- {partner.name}: {partner.category_id.name if partner.category_id else 'No category'}" for partner in partners])
        
        message = f"""
Business Type: {self.business_type}
Customer Name: {self.customer_name.name if self.customer_name else 'None'}

Onchange Result: {result}

Available Categories:
{category_info}

Sample Partners:
{partner_info}
        """
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Debug Information',
                'message': message,
                'type': 'info',
                'sticky': False,
            }
        }

    def action_check_field_configuration(self):
        """Check the field configuration and view setup"""
        self.ensure_one()
        
        print(f"DEBUG: action_check_field_configuration called")
        
        # Check if the fields exist and are properly configured
        print(f"DEBUG: business_type field exists: {hasattr(self, 'business_type')}")
        print(f"DEBUG: customer_name field exists: {hasattr(self, 'customer_name')}")
        
        if hasattr(self, 'business_type'):
            print(f"DEBUG: business_type value: {self.business_type}")
            print(f"DEBUG: business_type field type: {type(self.business_type)}")
        
        if hasattr(self, 'customer_name'):
            print(f"DEBUG: customer_name value: {self.customer_name}")
            print(f"DEBUG: customer_name field type: {type(self.customer_name)}")
        
        # Check the model fields
        model_fields = self.env['ir.model.fields'].search([
            ('model', '=', 'car.booking'),
            ('name', 'in', ['business_type', 'customer_name'])
        ])
        
        print(f"DEBUG: Model fields found: {[f.name for f in model_fields]}")
        
        # Check if there are any domain restrictions on customer_name
        customer_name_field = self.env['ir.model.fields'].search([
            ('model', '=', 'car.booking'),
            ('name', '=', 'customer_name')
        ], limit=1)
        
        if customer_name_field:
            print(f"DEBUG: customer_name field configuration: {customer_name_field.read()}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Field Configuration Check',
                'message': f'Business Type field exists: {hasattr(self, "business_type")}\nCustomer Name field exists: {hasattr(self, "customer_name")}\nBusiness Type value: {self.business_type}\nCustomer Name value: {self.customer_name.name if self.customer_name else "None"}',
                'type': 'info',
                'sticky': False,
            }
        }

    def action_force_business_type_filter(self):
        """Force trigger the business type filter and apply it immediately"""
        self.ensure_one()
        
        if not self.business_type:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Filter Error',
                    'message': 'Please select a Business Type first.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        print(f"DEBUG: action_force_business_type_filter called for business_type: {self.business_type}")
        
        # Manually trigger the onchange
        result = self._onchange_business_type()
        
        # Get the domain
        domain = result.get('domain', {}).get('customer_name', [])
        
        # Force update the customer_name field domain
        if domain:
            # This will force the field to refresh with the new domain
            self.env.context = dict(self.env.context, force_domain={'customer_name': domain})
        
        message = f"Filter applied for Business Type: {self.business_type}\nDomain: {domain}\nPlease click on Customer Name field to see filtered results."
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Filter Applied',
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def _get_customer_domain(self):
        """Return domain for customer_name based on business_type"""
        if not self.business_type:
            return []
        
        # Define the mapping between business_type and partner category names
        category_mapping = {
            'corporate': 'Companies',
            'hotels': 'Hotels', 
            'government': 'Government',
            'individuals': 'Individuals',
            'rental': 'Rental',
            'others': 'Others'
        }
        
        category_name = category_mapping.get(self.business_type)
        if not category_name:
            return []
        
        # Find the category
        category = self.env['res.partner.category'].search([('name', '=', category_name)], limit=1)
        if not category:
            # Create the category if it doesn't exist
            category = self.env['res.partner.category'].create({
                'name': category_name,
                'color': 1
            })
        
        return [('category_id', 'in', [category.id])]

    @api.onchange('business_type')
    def _onchange_business_type(self):
        """Filter customer_name based on business_type matching partner categories"""
        print(f"DEBUG: _onchange_business_type called with business_type: {self.business_type}")
        
        if self.business_type:
            # Define the mapping between business_type and partner category names
            category_mapping = {
                'corporate': 'Companies',
                'hotels': 'Hotels', 
                'government': 'Government',
                'individuals': 'Individuals',
                'rental': 'Rental',
                'others': 'Others'
            }
            
            category_name = category_mapping.get(self.business_type)
            print(f"DEBUG: Mapped business_type '{self.business_type}' to category '{category_name}'")
            
            if category_name:
                # Find or create the category
                category = self.env['res.partner.category'].search([('name', '=', category_name)], limit=1)
                print(f"DEBUG: Found category: {category.name if category else 'None'}")
                
                if not category:
                    category = self.env['res.partner.category'].create({
                        'name': category_name,
                        'color': 1
                    })
                    print(f"DEBUG: Created new category '{category_name}' with ID {category.id}")
                
                # Clear customer_name if it doesn't match the new category
                if self.customer_name and self.customer_name.category_id != category:
                    print(f"DEBUG: Clearing customer_name '{self.customer_name.name}' as it doesn't match category")
                    self.customer_name = False
                
                # Test the domain to see how many partners match
                domain = [('category_id', 'in', [category.id])]
                matching_partners = self.env['res.partner'].search(domain)
                print(f"DEBUG: Found {len(matching_partners)} partners matching domain")
                for partner in matching_partners[:5]:  # Show first 5 for debugging
                    print(f"DEBUG: Matching partner: {partner.name} (ID: {partner.id})")
                
                # Force field refresh
                return {
                    'value': {
                        'customer_name': False
                    }
                }
        else:
            # If no business_type, show all partners
            print("DEBUG: No business_type selected, showing all partners")
            return {
                'value': {
                    'customer_name': False
                }
            }

    def action_ensure_service_types_before_trip(self):
        """Ensure car booking lines have service types set before creating trip profile"""
        self.ensure_one()
        
        print(f"DEBUG: Ensuring service types for booking: {self.name}")
        updated_count = 0
        
        for booking_line in self.car_booking_lines:
            if not booking_line.type_of_service_id:
                print(f"DEBUG: Booking line {booking_line.id} missing type_of_service_id")
                
                # Try to find appropriate service type based on booking context
                service_type = None
                
                # First try to find by booking type
                if self.booking_type == 'with_driver':
                    service_type = self.env['type.of.service'].search([
                        '|', ('name', 'ilike', 'transfer'),
                        ('name', 'ilike', 'with driver')
                    ], limit=1)
                elif self.booking_type == 'rental':
                    service_type = self.env['type.of.service'].search([
                        '|', ('name', 'ilike', 'rental'),
                        ('name', 'ilike', 'without driver')
                    ], limit=1)
                
                # If not found by booking type, try to find by product
                if not service_type and booking_line.product_id:
                    service_type = self.env['type.of.service'].search([
                        ('name', 'ilike', booking_line.product_id.name)
                    ], limit=1)
                
                # If still not found, get the first available service type
                if not service_type:
                    service_type = self.env['type.of.service'].search([], limit=1)
                
                if service_type:
                    booking_line.type_of_service_id = service_type.id
                    updated_count += 1
                    print(f"DEBUG: Set service type for booking line {booking_line.id}: {service_type.name}")
                else:
                    print(f"DEBUG: No service type found for booking line {booking_line.id}")
        
        if updated_count > 0:
            # Force save the booking lines
            self.car_booking_lines._compute_amount_values()
            print(f"DEBUG: Updated {updated_count} booking lines with service types")
        
        return updated_count

    def action_create_trip_with_service_check(self):
        """Create trip profile with service type verification"""
        self.ensure_one()
        
        # First ensure service types are set in booking lines
        updated_count = self.action_ensure_service_types_before_trip()
        
        # Now create the trip profile
        trip_profile = self._create_trip_profile()
        
        message = f"Trip profile created successfully."
        if updated_count > 0:
            message += f" Updated {updated_count} booking lines with service types."
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'trip.profile',
            'view_mode': 'form',
            'res_id': self.trip_profile_id.id,
            'target': 'current',
            'context': self.env.context,
        }

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
                # Generate sequence number if not already set
                if not record.name or record.name == 'New':
                    # Determine sequence code based on booking type
                    if record.booking_type == 'with_driver':
                        seq_code = 'car.booking.with_driver'
                    elif record.booking_type == 'rental':
                        seq_code = 'car.booking.rental'
                    else:
                        seq_code = 'car.booking'
                    
                    # Try to get existing sequence or create new one
                    sequence = self.env['ir.sequence'].next_by_code(seq_code)
                    if sequence:
                        record.name = sequence
                    else:
                        # If sequence doesn't exist, try to find the highest existing number
                        existing_bookings = self.env['car.booking'].search([('name', '!=', 'New')])
                        if existing_bookings:
                            # Extract numbers from existing booking names
                            numbers = []
                            for booking in existing_bookings:
                                if booking.name and '/' in booking.name:
                                    try:
                                        num_part = booking.name.split('/')[-1]
                                        numbers.append(int(num_part))
                                    except (ValueError, IndexError):
                                        continue
                            
                            if numbers:
                                next_number = max(numbers) + 1
                                record.name = f"DSL/{str(next_number).zfill(5)}"
                            else:
                                record.name = "DSL/00001"
                        else:
                            record.name = "DSL/00001"
                
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
        
        # Set default branch if not already set
        if not self.location_id:
            default_branch = self._get_default_branch()
            if default_branch:
                self.location_id = default_branch
        
        # Set default company branch if not already set
        if not self.branch_id:
            default_branch = self._get_default_company_branch()
            if default_branch:
                self.branch_id = default_branch

    @api.onchange('customer_type')
    def _onchange_customer_type(self):
        if self.customer_type != 'company':
            self.project_name = False
            self.car_no = False
            self.amount = 0.0
            self.attached = False
    
    @api.onchange('location_id')
    def _onchange_location_id(self):
        """Set default branch when form is loaded"""
        if not self.location_id:
            default_branch = self._get_default_branch()
            if default_branch:
                self.location_id = default_branch
    
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        """Set default company branch when form is loaded"""
        if not self.branch_id:
            default_branch = self._get_default_company_branch()
            if default_branch:
                self.branch_id = default_branch

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
    
    extra_hour_total_amount = fields.Float(
        string='Extra Hour Total Amount',
        compute='_compute_extra_hour_total',
        store=True,
        help="Total extra hour charges (Extra Hour × Extra Hour Charges)"
    )
    
    amount = fields.Float(
        string='Amount',
        compute='_compute_amount',
        store=True,
        help="Total amount (Qty × Unit Price × Duration + Extra Charges)."
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
    flight_number = fields.Char(related='car_booking_id.flight_number', store=True, readonly=True)
    booking_state = fields.Selection(related='car_booking_id.state', store=True, readonly=True)
    booking_date = fields.Datetime(related='car_booking_id.booking_date', store=True, readonly=True)
    reservation_status = fields.Selection(related='car_booking_id.reservation_status', store=True, readonly=True)
    booking_type = fields.Selection(related='car_booking_id.booking_type', store=True, readonly=True)
    
    # Custom display field for booking type
    booking_type_display = fields.Char(
        string='Booking Type',
        compute='_compute_booking_type_display',
        store=True,
        help="Custom display for booking type"
    )
    
    @api.depends('booking_type')
    def _compute_booking_type_display(self):
        for record in self:
            if record.booking_type == 'with_driver':
                record.booking_type_display = 'Car with Driver'
            elif record.booking_type == 'rental':
                record.booking_type_display = 'Rental'
            else:
                record.booking_type_display = record.booking_type or ''

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
    branch_id = fields.Many2one(related='car_booking_id.branch_id', store=True, readonly=True)
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

    @api.depends('qty', 'unit_price', 'duration', 'extra_hour', 'extra_hour_charges')
    def _compute_amount(self):
        """Compute amount based on qty * unit_price * duration + extra charges"""
        for record in self:
            qty = record.qty or 1
            unit_price = record.unit_price or 0
            duration = record.duration or 1
            extra_hour = record.extra_hour or 0
            extra_hour_charges = record.extra_hour_charges or 0

            # Calculate base amount: qty * unit_price * duration
            base_amount = qty * unit_price * duration
            extra_amount = extra_hour * extra_hour_charges if extra_hour else 0
            record.amount = base_amount + extra_amount
            
            print(f"DEBUG: Line calculation - qty: {qty}, unit_price: {unit_price}, duration: {duration}")
            print(f"DEBUG: extra_hour: {extra_hour}, extra_hour_charges: {extra_hour_charges}")
            print(f"DEBUG: base_amount: {base_amount}, extra_amount: {extra_amount}, total: {record.amount}")
            print(f"DEBUG: Formula: ({qty} × {unit_price} × {duration}) + ({extra_hour} × {extra_hour_charges}) = {record.amount}")

    @api.depends('extra_hour', 'extra_hour_charges')
    def _compute_extra_hour_total(self):
        """Compute total extra hour charges"""
        for record in self:
            extra_hour = record.extra_hour or 0
            extra_hour_charges = record.extra_hour_charges or 0
            record.extra_hour_total_amount = extra_hour * extra_hour_charges
            print(f"DEBUG: Extra hour total: {extra_hour} × {extra_hour_charges} = {record.extra_hour_total_amount}")

    @api.onchange('qty', 'unit_price', 'duration', 'extra_hour_charges', 'extra_hour')
    def _onchange_amount(self):
        """Recalculate amount when key fields change"""
        for record in self:
            record._compute_amount()

    @api.onchange('product_id', 'car_booking_id')
    def _onchange_auto_set_service_type(self):
        """Auto-set service type based on product or booking type"""
        if self.product_id and not self.type_of_service_id:
            # Try to find service type by product name
            service_type = self.env['type.of.service'].search([
                ('name', 'ilike', self.product_id.name)
            ], limit=1)
            
            if service_type:
                self.type_of_service_id = service_type.id
                print(f"DEBUG: Auto-set service type from product: {service_type.name}")
        
        # If still no service type and we have a booking reference
        if not self.type_of_service_id and self.car_booking_id:
            booking = self.car_booking_id
            service_type = None
            
            # Try to find by booking type
            if booking.booking_type == 'with_driver':
                service_type = self.env['type.of.service'].search([
                    '|', ('name', 'ilike', 'transfer'),
                    ('name', 'ilike', 'with driver')
                ], limit=1)
            elif booking.booking_type == 'rental':
                service_type = self.env['type.of.service'].search([
                    '|', ('name', 'ilike', 'rental'),
                    ('name', 'ilike', 'without driver')
                ], limit=1)
            
            # If still not found, get the first available service type
            if not service_type:
                service_type = self.env['type.of.service'].search([], limit=1)
            
            if service_type:
                self.type_of_service_id = service_type.id
                print(f"DEBUG: Auto-set service type from booking type: {service_type.name}")

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
            print(f"DEBUG: Duration calculated: {record.duration} days")
    
    def _generate_booking_line_name(self):
        """Generate a proper name for car booking line"""
        name_parts = []
        
        # Add car model
        if self.car_model:
            name_parts.append(self.car_model)
        elif self.fleet_vehicle_id:
            name_parts.append(self.fleet_vehicle_id.name)
        else:
            name_parts.append("Vehicle")
        
        # Add driver name
        if self.driver_name:
            name_parts.append(f"- {self.driver_name.name}")
        else:
            name_parts.append("- Driver")
        
        # Add dates if available
        if self.start_date and self.end_date:
            name_parts.append(f"({self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')})")
        
        return " ".join(name_parts)

    def action_test_filter_manually(self):
        """Test the filter manually to see what's happening"""
        self.ensure_one()
        
        if not self.business_type:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Test Error',
                    'message': 'Please select a Business Type first.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Define the mapping
        category_mapping = {
            'corporate': 'Companies',
            'hotels': 'Hotels', 
            'government': 'Government',
            'individuals': 'Individuals',
            'rental': 'Rental',
            'others': 'Others'
        }
        
        category_name = category_mapping.get(self.business_type)
        category = self.env['res.partner.category'].search([('name', '=', category_name)], limit=1)
        
        if not category:
            category = self.env['res.partner.category'].create({
                'name': category_name,
                'color': 1
            })
        
        # Test the domain
        domain = [('category_id', 'in', [category.id])]
        matching_partners = self.env['res.partner'].search(domain)
        
        # Get all partners for comparison
        all_partners = self.env['res.partner'].search([], limit=10)
        
        message = f"""
Business Type: {self.business_type}
Category: {category.name} (ID: {category.id})
Domain: {domain}

Matching Partners ({len(matching_partners)}):
{chr(10).join([f"- {p.name} (ID: {p.id})" for p in matching_partners[:5]])}

All Partners Sample:
{chr(10).join([f"- {p.name}: {p.category_id.name if p.category_id else 'No category'}" for p in all_partners])}
        """
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Manual Filter Test',
                'message': message,
                'type': 'info',
                'sticky': False,
            }
        }

