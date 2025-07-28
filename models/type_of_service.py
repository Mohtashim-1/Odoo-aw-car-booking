from odoo import models, fields

class TypeOfService(models.Model):
    _name = 'type.of.service'

    name = fields.Char(string='Type of Service', required=True, translate=True)