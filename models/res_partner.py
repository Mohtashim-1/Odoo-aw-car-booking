from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    id_no = fields.Char(string='Driver ID No')
    customized_mobile = fields.Char(string='Customized Mobile')
    national_identity_number = fields.Char(string='National Identity Number')