from odoo import models, fields

class CarExtraService(models.Model):
    _name = 'car.extra.service'
    _description = 'Car Extra Service'

    name = fields.Char(string='Service Name', required=True)