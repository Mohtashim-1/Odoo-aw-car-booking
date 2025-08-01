from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    car_booking_line_id = fields.Many2one(
        'car.booking.line',
        string='Car Booking Line',
        help='Related car booking line for this sales order line'
    )
    
    service_type = fields.Many2one(
        'car.extra.service',
        string='Service Type',
        help='Type of car booking service (e.g., Child Chair, GPS, etc.)'
    )
    
    car_type = fields.Many2one(
        'fleet.vehicle.model',
        string='Car Type',
        help='Type/model of the car for this booking'
    )
    
    additional_charges = fields.Float(
        string='Additional Charges',
        default=0.0,
        help='Extra charges for this booking line'
    )
    
    date_start = fields.Datetime(
        string='Start Date',
        help='Start date and time of the booking'
    )
    
    date_end = fields.Datetime(
        string='End Date', 
        help='End date and time of the booking'
    )
    
    duration = fields.Float(
        string='Duration (Days)',
        compute='_compute_duration',
        store=True,
        help='Duration in days between start and end date'
    )
    
    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for record in self:
            if record.date_start and record.date_end:
                start_date = fields.Date.from_string(record.date_start)
                end_date = fields.Date.from_string(record.date_end)
                delta = end_date - start_date
                record.duration = max(delta.days, 0)
            else:
                record.duration = 0.0
    
    @api.onchange('car_booking_line_id')
    def _onchange_car_booking_line_id(self):
        """Auto-populate fields when car booking line is selected"""
        if self.car_booking_line_id:
            booking_line = self.car_booking_line_id
            
            # Populate fields from car booking line
            self.service_type = booking_line.type_of_service_id.id if booking_line.type_of_service_id else False
            self.car_type = booking_line.car_model_id.id if booking_line.car_model_id else False
            self.date_start = booking_line.start_date
            self.date_end = booking_line.end_date
            self.additional_charges = booking_line.extra_hour_charges or 0.0
            self.product_uom_qty = booking_line.qty or 1.0
            self.price_unit = booking_line.unit_price or 0.0
            
            # Copy taxes from car booking line
            if booking_line.tax_ids:
                self.tax_id = [(6, 0, booking_line.tax_ids.ids)]
            
            # Set product if available
            if booking_line.product_id:
                self.product_id = booking_line.product_id.id
        
    @api.onchange('additional_charges')
    def _onchange_additional_charges(self):
        """Trigger recalculation when additional charges change"""
        # The @api.depends decorator on _compute_amount will handle this automatically
        pass
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Override to preserve price_unit when product changes"""
        # Call parent method first
        super()._onchange_product_id()
        
        # If we have a car_booking_line_id, restore the price_unit from it
        if self.car_booking_line_id and self.car_booking_line_id.unit_price:
            self.price_unit = self.car_booking_line_id.unit_price
    
    @api.onchange('product_uom_qty', 'price_unit')
    def _onchange_product_uom_qty_price_unit(self):
        """Override to include additional charges in calculation"""
        # Call parent method first
        super()._onchange_product_uom_qty_price_unit()
        
        # The @api.depends decorator on _compute_amount will handle additional charges automatically
    
    @api.depends('product_uom_qty', 'price_unit', 'additional_charges', 'tax_id')
    def _compute_amount(self):
        """Override to include additional charges in amount calculation"""
        # First call parent method to set basic fields
        super()._compute_amount()
        
        for line in self:
            # Calculate base subtotal
            base_subtotal = line.product_uom_qty * line.price_unit
            
            # Include additional charges in subtotal
            line.price_subtotal = base_subtotal + (line.additional_charges or 0.0)
            
            # Recalculate tax based on new subtotal (including additional charges)
            if line.tax_id and line.price_subtotal:
                taxes = line.tax_id.compute_all(line.price_subtotal, line.order_id.currency_id, 1, product=line.product_id, partner=line.order_id.partner_id)
                line.price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
            else:
                line.price_tax = 0.0
            
            # Update total
            line.price_total = line.price_subtotal + line.price_tax
    
    def _prepare_invoice_line(self, **optional_values):
        """Override to include car booking fields when creating invoice lines"""
        res = super()._prepare_invoice_line(**optional_values)
        
        # Add car booking fields to the invoice line
        res.update({
            'car_booking_line_id': self.car_booking_line_id.id if self.car_booking_line_id else False,
            'service_type': self.service_type.id if self.service_type else False,
            'car_type': self.car_type.id if self.car_type else False,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'additional_charges': self.additional_charges,
        })
        
        return res
    
    @api.model
    def create(self, vals):
        """Override create to ensure amounts are calculated correctly"""
        # Remove any recursive _compute_amount calls
        return super().create(vals)
    
    def write(self, vals):
        """Override write to ensure amounts are calculated correctly"""
        # Remove any recursive _compute_amount calls
        return super().write(vals) 