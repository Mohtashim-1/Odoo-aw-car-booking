from odoo import models, fields

class BusinessPoint(models.Model):
    _name = 'business.point'
    _description = 'Business Point'

    name = fields.Char(string='Business Point')