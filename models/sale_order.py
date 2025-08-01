from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    car_booking_id = fields.Many2one(
        'car.booking',
        string='Car Booking',
        help='Related car booking for this sales order'
    )
    
    @api.depends('order_line.price_subtotal', 'order_line.additional_charges', 'order_line.tax_id')
    def _compute_amounts(self):
        """Override to include additional charges in total calculations"""
        super()._compute_amounts()
        
        # Recalculate totals to include additional charges
        for order in self:
            total_untaxed = 0.0
            total_tax = 0.0
            
            for line in order.order_line:
                # Use the line's price_subtotal (which already includes additional charges)
                total_untaxed += line.price_subtotal
                total_tax += line.price_tax
            
            # Update order totals
            order.amount_untaxed = total_untaxed
            order.amount_tax = total_tax
            order.amount_total = total_untaxed + total_tax
    
    @api.model
    def create(self, vals):
        """Override create to ensure amounts are calculated correctly"""
        # Remove recursive calls to avoid infinite loops
        return super().create(vals)
    
    def write(self, vals):
        """Override write to ensure amounts are calculated correctly"""
        # Remove recursive calls to avoid infinite loops
        return super().write(vals) 