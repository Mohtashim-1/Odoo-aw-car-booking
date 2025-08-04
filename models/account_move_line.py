from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # service_type = fields.Many2one(
    #     'type.of.service',
    #     string='Service Type',
    #     compute='_compute_service_type_from_trip',
    #     store=True,
    #     help='Type of car booking service (e.g., Transfer, Full Day, Hourly, etc.)'
    # )

    service_type_id = fields.Many2one(
        'type.of.service',
        string='Service Type',
        help='Service type copied from car booking for invoice creation'
    )

    car_type = fields.Many2one(
        'fleet.vehicle.model',
        string='Car Type',
        help='Type/model of the car for this booking'
    )
    
    trip_vehicle_line_id = fields.Many2one(
        'trip.vehicle.line',
        string='Trip Vehicle Line',
        help='Reference to trip vehicle line for fetching service type'
    )
    
    @api.depends('trip_vehicle_line_id')
    def _compute_service_type_from_trip(self):
        """Compute service_type from trip vehicle line"""
        for record in self:
            if record.trip_vehicle_line_id and record.trip_vehicle_line_id.service_type_id:
                record.service_type_id = record.trip_vehicle_line_id.service_type_id
            else:   
                record.service_type_id = False

    additional_charges = fields.Float(
        string='Additional Charges',
        default=0.0,
        help='Extra charges for this invoice line'
    )
    
    # Override price_total to include additional charges
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_totals',
        store=True,
        help='Total including additional charges'
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
                delta = record.date_end - record.date_start
                record.duration = delta.days + delta.seconds / 86400
            else:
                record.duration = 0.0

    def _compute_totals(self):
        """Override standard _compute_totals to include additional charges"""
        for line in self:
            # Base price calculation
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            
            # Calculate subtotal including additional charges
            subtotal = line.quantity * price + (line.additional_charges or 0.0)
            
            # Set price_subtotal to include additional charges
            line.price_subtotal = subtotal
            
            # Compute taxes
            taxes_res = line.tax_ids.compute_all(
                price,
                line.currency_id,
                line.quantity,
                product=line.product_id,
                partner=line.partner_id,
            )
            
            # Set price_total to include additional charges
            tax_amount = sum(t.get('amount', 0.0) for t in taxes_res.get('taxes', []))
            line.price_total = subtotal + tax_amount
            
            print(f"DEBUG: Line {line.id} - price_subtotal: {line.price_subtotal}, price_total: {line.price_total}, additional_charges: {line.additional_charges}")
    
    @api.onchange('quantity', 'price_unit', 'additional_charges')
    def _onchange_amounts(self):
        """Force recompute when key fields change"""
        for line in self:
            line._compute_totals()
    
    @api.model
    def _compute_totals_after_standard(self):
        """Called after standard _compute_totals to fix price_total"""
        for line in self:
            if line.additional_charges:
                # Recalculate price_total to include additional charges
                base_subtotal = line.quantity * line.price_unit
                additional_charges = line.additional_charges or 0.0
                total_with_charges = base_subtotal + additional_charges
                line.price_total = total_with_charges
                print(f"DEBUG: Fixed line {line.id} price_total to {total_with_charges}")
    


