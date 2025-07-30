from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    id_no = fields.Char(string='Driver ID No')