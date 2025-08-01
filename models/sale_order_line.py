from odoo import models, fields, api
from odoo.tools.translate import _


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
            self.technical_price_unit = booking_line.unit_price or 0.0
            
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
    
    @api.onchange('car_booking_line_id')
    def _onchange_car_booking_line_id_update(self):
        """Ensure price is preserved when car booking line is updated"""
        if self.car_booking_line_id and self.car_booking_line_id.unit_price:
            self.price_unit = self.car_booking_line_id.unit_price
            self.technical_price_unit = self.car_booking_line_id.unit_price
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Override to preserve price_unit when product changes for car booking lines"""
        # Store the original price_unit before any changes
        original_price_unit = self.price_unit
        
        # If this is a car booking line, don't call parent method to avoid price reset
        if self.car_booking_line_id:
            # Only call the warning method from parent, not the price reset method
            if self.product_id:
                product = self.product_id
                if product.sale_line_warn != 'no-message':
                    if product.sale_line_warn == 'block':
                        self.product_id = False
                        return
                    return {
                        'warning': {
                            'title': _("Warning for %s", product.name),
                            'message': product.sale_line_warn_msg,
                        }
                    }
            
            # For car booking lines, always preserve the original price
            if self.car_booking_line_id.unit_price:
                self.price_unit = self.car_booking_line_id.unit_price
                self.technical_price_unit = self.car_booking_line_id.unit_price
            elif original_price_unit and original_price_unit > 0:
                self.price_unit = original_price_unit
                self.technical_price_unit = original_price_unit
        else:
            # For regular lines, call parent method as usual
            super()._onchange_product_id()
    

    
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        """Override to prevent price reset for car booking lines"""
        for line in self:
            # Don't compute the price for deleted lines.
            if not line.order_id:
                continue
            
            # For car booking lines, preserve the price and don't recompute
            if line.car_booking_line_id:
                # If we have a car booking line, preserve the existing price
                if line.car_booking_line_id.unit_price and line.price_unit != line.car_booking_line_id.unit_price:
                    line.price_unit = line.car_booking_line_id.unit_price
                    line.technical_price_unit = line.car_booking_line_id.unit_price
                continue
            
            # For regular lines, use the standard logic
            # check if the price has been manually set or there is already invoiced amount.
            # if so, the price shouldn't change as it might have been manually edited.
            if (
                (line.technical_price_unit != line.price_unit and not line.env.context.get('force_price_recomputation'))
                or line.qty_invoiced > 0
                or (line.product_id.expense_policy == 'cost' and line.is_expense)
            ):
                continue
            line = line.with_context(sale_write_from_compute=True)
            if not line.product_uom or not line.product_id:
                line.price_unit = 0.0
                line.technical_price_unit = 0.0
            else:
                line._reset_price_unit()
    
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'additional_charges')
    def _compute_amount(self):
        """Override to include additional charges in amount calculation"""
        for line in self:
            # Calculate base subtotal (price_unit * quantity)
            base_subtotal = line.product_uom_qty * line.price_unit
            
            # Add additional charges to the subtotal
            line.price_subtotal = base_subtotal + (line.additional_charges or 0.0)
            
            # Calculate tax based on the subtotal (including additional charges)
            if line.tax_id and line.price_subtotal:
                taxes = line.tax_id.compute_all(
                    line.price_subtotal, 
                    line.order_id.currency_id, 
                    1, 
                    product=line.product_id, 
                    partner=line.order_id.partner_id
                )
                line.price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
            else:
                line.price_tax = 0.0
            
            # Update total
            line.price_total = line.price_subtotal + line.price_tax
    
    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """Override to ensure tax computation uses the correct price_subtotal"""
        self.ensure_one()
        
        # Use the computed price_subtotal which includes additional charges
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            **{
                'tax_ids': self.tax_id,
                'quantity': self.product_uom_qty,
                'partner_id': self.order_id.partner_id,
                'currency_id': self.order_id.currency_id or self.order_id.company_id.currency_id,
                'rate': self.order_id.currency_rate,
                'price_unit': self.price_subtotal / self.product_uom_qty if self.product_uom_qty else self.price_unit,
                **kwargs,
            },
        )
    
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
        """Override create to ensure amounts are calculated correctly and prices are preserved"""
        # For car booking lines, ensure price is set correctly
        if vals.get('car_booking_line_id'):
            car_booking_line = self.env['car.booking.line'].browse(vals['car_booking_line_id'])
            if car_booking_line and car_booking_line.unit_price:
                vals['price_unit'] = car_booking_line.unit_price
                vals['technical_price_unit'] = car_booking_line.unit_price
        
        return super().create(vals)
    
    def write(self, vals):
        """Override write to ensure amounts are calculated correctly and prices are preserved"""
        # For car booking lines, ensure price is preserved
        if self.car_booking_line_id and self.car_booking_line_id.unit_price:
            # Don't allow price_unit to be changed for car booking lines
            if 'price_unit' in vals:
                vals['price_unit'] = self.car_booking_line_id.unit_price
            if 'technical_price_unit' in vals:
                vals['technical_price_unit'] = self.car_booking_line_id.unit_price
        
        return super().write(vals) 