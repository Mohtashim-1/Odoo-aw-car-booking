from odoo import models, fields

class BookingCity(models.Model):
    _name = 'booking.city'
    _description = 'Booking City'

    name = fields.Char(string='City Name')

    region = fields.Selection([
        ('north', 'North'),
        ('south', 'South'),
        ('west', 'West'),
        ('east', 'East'),
        ('central', 'Central'),
    ], string='Region')