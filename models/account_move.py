from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    car_booking_id = fields.Many2one(
        'car.booking',
        string='Car Booking',
        help='Related car booking for this invoice'
    )
    
    booking_ref = fields.Char(
        string='Booking Reference',
        help='Reference to the original car booking'
    )
    
    # Invoice-specific fields for car booking
    service_type = fields.Many2one(
        'car.extra.service',
        string='Service Type',
        help='Type of car booking service'
    )
    
    car_type = fields.Many2one(
        'fleet.vehicle.model',
        string='Car Type',
        help='Type/model of the car for this booking'
    )
    
    additional_charges = fields.Float(
        string='Additional Charges',
        default=0.0,
        help='Extra charges for this invoice'
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
    
    # Override the fields to be computed and stored
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_amounts_with_charges',
        store=True,
        help='Computed untaxed amount including additional charges'
    )
    
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts_with_charges',
        store=True,
        help='Computed total amount including additional charges'
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

    @api.depends('line_ids.price_subtotal', 'line_ids.additional_charges')
    def _compute_amounts_with_charges(self):
        """Compute amounts including additional charges"""
        for move in self:
            if move.is_invoice(True):
                # Calculate total from line subtotals (which already include additional charges)
                untaxed_amount = sum(move.line_ids.mapped('price_subtotal'))
                total_amount = untaxed_amount + move.amount_tax
                
                # Force update the amounts
                move.amount_untaxed = untaxed_amount
                move.amount_total = total_amount
                
                print(f"DEBUG: _compute_amounts_with_charges - untaxed_amount={untaxed_amount}, total_amount={total_amount}")
            else:
                move.amount_untaxed = 0.0
                move.amount_total = 0.0

    @api.onchange('line_ids.price_subtotal')
    def _onchange_line_subtotals(self):
        """Update invoice totals when line subtotals change"""
        for move in self:
            if move.is_invoice(True):
                untaxed_amount = sum(move.line_ids.mapped('price_subtotal'))
                move.amount_untaxed = untaxed_amount
                move.amount_total = untaxed_amount + move.amount_tax
                print(f"DEBUG: Invoice onchange - untaxed_amount={untaxed_amount}, amount_total={move.amount_total}")


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    car_booking_line_id = fields.Many2one(
        'car.booking.line',
        string='Car Booking Line',
        help='Related car booking line for this invoice line'
    )
    
    # Invoice line specific fields for car booking
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
    
    additional_charges = fields.Monetary(
        string='Additional Charges',
        default=0.0,
        help='Extra charges for this invoice line'
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
        compute='_compute_duration_line',
        store=True,
        help='Duration in days between start and end date'
    )
    
    # Override price_subtotal to include additional_charges
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_price_subtotal_with_charges',
        store=True,
        help='Subtotal including additional charges'
    )
    
    @api.depends('date_start', 'date_end')
    def _compute_duration_line(self):
        for record in self:
            if record.date_start and record.date_end:
                start_date = fields.Date.from_string(record.date_start)
                end_date = fields.Date.from_string(record.date_end)
                delta = end_date - start_date
                record.duration = max(delta.days, 0)
            else:
                record.duration = 0.0
    
    @api.depends('quantity', 'price_unit', 'additional_charges')
    def _compute_price_subtotal_with_charges(self):
        """Compute price_subtotal including additional charges"""
        for line in self:
            # Calculate base subtotal
            base_subtotal = line.quantity * line.price_unit
            # Add additional charges
            additional_charges = line.additional_charges or 0.0
            line.price_subtotal = base_subtotal + additional_charges
            print(f"DEBUG: _compute_price_subtotal_with_charges - Line {line.name} - quantity={line.quantity}, price_unit={line.price_unit}, additional_charges={additional_charges}, price_subtotal={line.price_subtotal}")
    
    @api.onchange('quantity', 'price_unit', 'additional_charges')
    def _onchange_price_subtotal(self):
        """Update price_subtotal when quantity, price_unit, or additional_charges change"""
        for line in self:
            base_subtotal = line.quantity * line.price_unit
            additional_charges = line.additional_charges or 0.0
            line.price_subtotal = base_subtotal + additional_charges
            print(f"DEBUG: onchange - Line {line.name} - quantity={line.quantity}, price_unit={line.price_unit}, additional_charges={additional_charges}, price_subtotal={line.price_subtotal}")
    
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
            self.quantity = booking_line.qty or 1.0
            self.price_unit = booking_line.unit_price or 0.0
            
            # Set product if available
            if booking_line.product_id:
                self.product_id = booking_line.product_id.id
    
    def action_fix_invoice_totals(self):
        """Directly fix invoice totals by summing line amounts"""
        for move in self:
            if move.is_invoice(True):
                total_untaxed = 0.0
                
                for line in move.line_ids:
                    # Calculate line amount including additional charges
                    line_amount = (line.quantity * line.price_unit) + (line.additional_charges or 0.0)
                    total_untaxed += line_amount
                    
                    # Update line subtotal
                    line.write({'price_subtotal': line_amount})
                
                # Update invoice totals
                move.write({
                    'amount_untaxed': total_untaxed,
                    'amount_total': total_untaxed + move.amount_tax
                })
                
                print(f"DEBUG: Fixed invoice {move.id} - untaxed_amount={total_untaxed}, total_amount={total_untaxed + move.amount_tax}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Invoice totals fixed. Untaxed Amount: {total_untaxed}',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_recalculate_totals(self):
        """Recalculate invoice totals by summing the Amount column values"""
        for move in self:
            if move.is_invoice(True):
                total_untaxed = 0.0
                
                # Sum the Amount column values directly
                for line in move.line_ids:
                    # Get the amount as displayed in the Amount column
                    line_amount = line.price_subtotal
                    total_untaxed += line_amount
                    print(f"DEBUG: Line {line.name} - amount={line_amount}")
                
                print(f"DEBUG: Total calculated: {total_untaxed}")
                
                # Update invoice totals
                move.write({
                    'amount_untaxed': total_untaxed,
                    'amount_total': total_untaxed + move.amount_tax
                })
                
                print(f"DEBUG: Invoice updated - amount_untaxed={move.amount_untaxed}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def action_force_update_line_subtotals(self):
        """Force update all line subtotals to include additional charges"""
        for move in self:
            if move.is_invoice(True):
                total_untaxed = 0.0
                
                for line in move.line_ids:
                    # Calculate line amount including additional charges
                    base_subtotal = line.quantity * line.price_unit
                    additional_charges = line.additional_charges or 0.0
                    new_subtotal = base_subtotal + additional_charges
                    
                    print(f"DEBUG: Line {line.name} - quantity={line.quantity}, price_unit={line.price_unit}, additional_charges={additional_charges}")
                    print(f"DEBUG: Line calculation - base_subtotal={base_subtotal}, additional_charges={additional_charges}, new_subtotal={new_subtotal}")
                    
                    # Update line subtotal
                    line.write({'price_subtotal': new_subtotal})
                    total_untaxed += new_subtotal
                
                print(f"DEBUG: Total untaxed calculated: {total_untaxed}")
                
                # Update invoice totals
                move.write({
                    'amount_untaxed': total_untaxed,
                    'amount_total': total_untaxed + move.amount_tax
                })
                
                print(f"DEBUG: Invoice updated - amount_untaxed={move.amount_untaxed}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Line subtotals updated to include additional charges. Total: {total_untaxed}',
                'type': 'success',
                'sticky': False,
            }
        }

