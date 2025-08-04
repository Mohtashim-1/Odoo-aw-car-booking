from odoo import models, api, fields


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    rental_price = fields.Float(string='Rental Price')