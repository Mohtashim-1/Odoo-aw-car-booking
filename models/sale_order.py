from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    car_booking_id = fields.Many2one(
        'car.booking',
        string='Car Booking',
        help='Related car booking for this sales order'
    ) 