from odoo import models, fields

class ResParner(models.Model):
    _inherit = 'res.partner'

    id_no = fields.Char(string='Driver ID No')