from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    car_booking_id = fields.Many2one(
        'car.booking',
        string='Car Booking',
        help="Reference to the car booking created from this sales order"
    )

    custom_amount_untaxed = fields.Monetary(
        string='Custom Untaxed Amount',
        compute='_compute_custom_amounts',
        store=True,
        currency_field='currency_id',
        help='Custom untaxed amount including additional charges from order lines'
    )
    custom_amount_tax = fields.Monetary(
        string='Custom Tax Amount',
        compute='_compute_custom_amounts',
        store=True,
        currency_field='currency_id',
        help='Custom tax amount for car booking order lines'
    )
    custom_amount_total = fields.Monetary(
        string='Custom Total Amount',
        compute='_compute_custom_amounts',
        store=True,
        currency_field='currency_id',
        help='Custom total amount including additional charges and tax'
    )

    @api.depends('order_line.price_subtotal', 'order_line.additional_charges', 'order_line.tax_id', 'order_line.price_total')
    def _compute_custom_amounts(self):
        for order in self:
            untaxed = 0.0
            tax = 0.0
            total = 0.0
            for line in order.order_line:
                # Only include lines with car booking fields or additional charges
                if getattr(line, 'service_type', False) or getattr(line, 'car_type', False) or getattr(line, 'additional_charges', 0.0):
                    untaxed += (getattr(line, 'duration', 1) or 1) * line.product_uom_qty * line.price_unit + (getattr(line, 'additional_charges', 0.0) or 0.0)
                    tax += line.price_tax or 0.0
                    total += line.price_total or 0.0
            order.custom_amount_untaxed = untaxed
            order.custom_amount_tax = tax
            order.custom_amount_total = untaxed + tax

    def action_create_car_booking(self):
        """Create a car booking from the sales order"""
        self.ensure_one()
        
        # Check if car booking already exists
        if self.car_booking_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Car Booking',
                'res_model': 'car.booking',
                'view_mode': 'form',
                'res_id': self.car_booking_id.id,
                'target': 'current',
            }
        
        # Validate prerequisites
        if not self.partner_id:
            raise UserError("Please select a customer before creating a car booking.")
        
        if not self.order_line:
            raise UserError("Please add at least one product line before creating a car booking.")
        
        # Create car booking from sales order data
        car_booking_vals = {
            'sale_order_id': self.id,
            'customer_name': self.partner_id.id,
            'mobile': self.partner_id.mobile or self.partner_id.phone or '',
            'date_of_service': self.date_order.date() if self.date_order else fields.Date.today(),
            'state': 'draft',
            'booking_type': 'with_driver',  # Default value
            'region': 'central',  # Default value
            'payment_type': 'credit',  # Default value
            'business_type': 'individuals',  # Default value
            'customer_type': 'individual',  # Default value
            'booking_date': fields.Datetime.now(),
            'reservation_status': 'created',
            'notes': self.note or '',
        }
        
        # Try to determine business type from partner
        if self.partner_id.is_company:
            car_booking_vals['business_type'] = 'corporate'
            car_booking_vals['customer_type'] = 'company'
        else:
            car_booking_vals['business_type'] = 'individuals'
            car_booking_vals['customer_type'] = 'individual'
        
        # Create the car booking
        car_booking = self.env['car.booking'].create(car_booking_vals)
        
        # Link the car booking to the sales order
        self.car_booking_id = car_booking.id
        
        # Create car booking lines from order lines
        for order_line in self.order_line:
            if order_line.product_id:
                # Determine service dates
                start_date = order_line.date_start or self.date_order or fields.Datetime.now()
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
                    'extra_hour_charges': order_line.additional_charges or 0.0,
                }
                
                # Create the booking line
                booking_line = self.env['car.booking.line'].create(booking_line_vals)
                
                # Link the order line to the booking line
                order_line.car_booking_line_id = booking_line.id
        
        # Show success message
        return {
            'type': 'ir.actions.act_window',
            'name': 'Car Booking Created',
            'res_model': 'car.booking',
            'view_mode': 'form',
            'res_id': car_booking.id,
            'target': 'current',
            'context': {
                'default_sale_order_id': self.id,
                'default_customer_name': self.partner_id.id,
            }
        }

    def action_confirm(self):
        """Override action_confirm to automatically create car booking"""
        result = super().action_confirm()
        
        # Create car booking if it doesn't exist and if this is a car booking related order
        if not self.car_booking_id and self._should_create_car_booking():
            self.action_create_car_booking()
        
        return result
    
    def _should_create_car_booking(self):
        """Determine if a car booking should be created from this sales order"""
        # Check if any order line has car booking specific fields
        for line in self.order_line:
            if line.service_type or line.car_type:
                return True
        
        # Check if any product is in a car booking category
        for line in self.order_line:
            if line.product_id and line.product_id.categ_id:
                category_name = line.product_id.categ_id.name.lower()
                if any(keyword in category_name for keyword in ['car', 'vehicle', 'transport', 'booking']):
                    return True
        
        return False

    def action_view_car_booking(self):
        """View the associated car booking"""
        self.ensure_one()
        if self.car_booking_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Car Booking',
                'res_model': 'car.booking',
                'view_mode': 'form',
                'res_id': self.car_booking_id.id,
                'target': 'current',
            }
        else:
            raise UserError("No car booking associated with this sales order.")
    
    def action_create_car_booking_wizard(self):
        """Open wizard to create car booking with options"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Car Booking',
            'res_model': 'car.booking.create.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_customer_name': self.partner_id.id,
                'default_mobile': self.partner_id.mobile or self.partner_id.phone or '',
                'default_date_of_service': self.date_order.date() if self.date_order else fields.Date.today(),
            }
        } 