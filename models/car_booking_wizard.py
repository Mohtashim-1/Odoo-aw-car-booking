from odoo import models, fields, api
from odoo.exceptions import UserError


class CarBookingCreateWizard(models.TransientModel):
    _name = 'car.booking.create.wizard'
    _description = 'Car Booking Creation Wizard'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        readonly=True
    )
    
    customer_name = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        domain="[('is_company', '=', False)]"
    )
    
    mobile = fields.Char(
        string='Mobile',
        help='Customer mobile number'
    )
    
    date_of_service = fields.Date(
        string='Date of Service',
        default=fields.Date.today,
        required=True
    )
    
    booking_type = fields.Selection([
        ('with_driver', 'Car with Driver(Limousine)'),
        ('rental', 'Rental')
    ], string='Type of Booking', default='with_driver', required=True)
    
    region = fields.Selection([
        ('north', 'North'),
        ('south', 'South'),
        ('west', 'West'),
        ('east', 'East'),
        ('central', 'Central'),
    ], string='Region', default='central', required=True)
    
    business_type = fields.Selection([
        ('corporate', 'Corporate'),
        ('hotels', 'Hotels'),
        ('government', 'Government'),
        ('individuals', 'Individuals'),
        ('rental', 'Rental'),
        ('others', 'Others'),
    ], string='Business Type', default='individuals', required=True)
    
    payment_type = fields.Selection([
        ('cash', 'Cash'),
        ('credit', 'Credit'),
        ('bank_transfer', 'Bank Transfer'),
        ('atm', 'ATM'),
        ('cheque', 'Cheque'),
        ('others', 'Others'),
    ], string='Payment Type', default='credit', required=True)
    
    notes = fields.Html(
        string='Notes',
        help='Additional notes for the car booking'
    )
    
    auto_create_lines = fields.Boolean(
        string='Auto-create booking lines from order lines',
        default=True,
        help='Automatically create car booking lines from sales order lines'
    )
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        
        if self.env.context.get('default_sale_order_id'):
            sale_order = self.env['sale.order'].browse(self.env.context['default_sale_order_id'])
            if sale_order.exists():
                res.update({
                    'sale_order_id': sale_order.id,
                    'customer_name': sale_order.partner_id.id,
                    'mobile': sale_order.partner_id.mobile or sale_order.partner_id.phone or '',
                    'date_of_service': sale_order.date_order.date() if sale_order.date_order else fields.Date.today(),
                    'notes': sale_order.note or '',
                })
                
                # Determine business type from partner
                if sale_order.partner_id.is_company:
                    res['business_type'] = 'corporate'
                else:
                    res['business_type'] = 'individuals'
        
        return res
    
    @api.onchange('customer_name')
    def _onchange_customer_name(self):
        """Auto-fill mobile when customer changes"""
        if self.customer_name:
            self.mobile = self.customer_name.mobile or self.customer_name.phone or ''
        else:
            self.mobile = ''
    
    def action_create_car_booking(self):
        """Create the car booking with the specified options"""
        self.ensure_one()
        
        # Validate prerequisites
        if not self.customer_name:
            raise UserError("Please select a customer.")
        
        if not self.sale_order_id:
            raise UserError("Sales order is required.")
        
        # Create car booking
        car_booking_vals = {
            'sale_order_id': self.sale_order_id.id,
            'customer_name': self.customer_name.id,
            'mobile': self.mobile or '',
            'date_of_service': self.date_of_service,
            'state': 'draft',
            'booking_type': self.booking_type,
            'region': self.region,
            'payment_type': self.payment_type,
            'business_type': self.business_type,
            'customer_type': 'company' if self.customer_name.is_company else 'individual',
            'booking_date': fields.Datetime.now(),
            'reservation_status': 'created',
            'notes': self.notes or '',
        }
        
        # Create the car booking
        car_booking = self.env['car.booking'].create(car_booking_vals)
        
        # Link the car booking to the sales order
        self.sale_order_id.car_booking_id = car_booking.id
        
        # Create car booking lines from order lines if requested
        if self.auto_create_lines:
            for order_line in self.sale_order_id.order_line:
                if order_line.product_id:
                    # Determine service dates
                    start_date = order_line.date_start or self.sale_order_id.date_order or fields.Datetime.now()
                    end_date = order_line.date_end or start_date
                    
                    # Calculate duration
                    if start_date and end_date:
                        duration = (end_date - start_date).days + 1
                    else:
                        duration = 1
                    
                    booking_line_vals = {
                        'car_booking_id': car_booking.id,
                        'product_id': order_line.product_id.id,
                        'qty': order_line.product_uom_qty,
                        'unit_price': order_line.price_unit,
                        'amount': order_line.price_subtotal,
                        'start_date': start_date,
                        'end_date': end_date,
                        'duration': duration,
                        'name': order_line.name or order_line.product_id.name,
                        
                        # Map car booking specific fields from order line
                        'type_of_service_id': order_line.service_type.id if order_line.service_type else False,
                        'car_model_id': order_line.car_type.id if order_line.car_type else False,
                        # 'extra_charges': order_line.additional_charges or 0.0,
                    }
                    
                    # Create the booking line
                    booking_line = self.env['car.booking.line'].create(booking_line_vals)
                    
                    # Link the order line to the booking line
                    order_line.car_booking_line_id = booking_line.id
        
        # Return to the created car booking
        return {
            'type': 'ir.actions.act_window',
            'name': 'Car Booking Created',
            'res_model': 'car.booking',
            'view_mode': 'form',
            'res_id': car_booking.id,
            'target': 'current',
            'context': {
                'default_sale_order_id': self.sale_order_id.id,
                'default_customer_name': self.customer_name.id,
            }
        }
    
    def action_cancel(self):
        """Cancel the wizard"""
        return {
            'type': 'ir.actions.act_window_close'
        } 