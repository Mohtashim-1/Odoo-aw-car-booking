from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    car_booking_id = fields.Many2one(
        'car.booking',
        string='Car Booking',
        help='Related car booking for this invoice'
    )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    car_booking_line_id = fields.Many2one(
        'car.booking.line',
        string='Car Booking Line',
        help='Related car booking line for this invoice line'
    ) 