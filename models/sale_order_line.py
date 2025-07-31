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
            
            # Set product if available
            if booking_line.product_id:
                self.product_id = booking_line.product_id.id
    
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