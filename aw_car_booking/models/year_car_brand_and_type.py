from odoo import models, fields

class YearCarBrandAndType(models.Model):
    _name = 'year.car.brand.and.type'
    _description = 'year Car Brand And Type'

    name = fields.Char(string='Year Car Brand And Type')