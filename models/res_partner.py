from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    id_no = fields.Char(string='Driver ID No')
    
    # Arabic fields
    name_arabic = fields.Char(string='Name (Arabic)', help='Arabic name for the partner')
    street_arabic = fields.Char(string='Address Line 1 (Arabic)', help='Arabic address line 1')
    street2_arabic = fields.Char(string='Address Line 2 (Arabic)', help='Arabic address line 2')