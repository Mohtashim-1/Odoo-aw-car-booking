from odoo import models, fields

class yearModel(models.Model):
    _name = 'year.model'
    _description = 'Year Model'

    name = fields.Char(string='Year Model Name')