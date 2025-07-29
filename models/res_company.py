from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    image_field_1 = fields.Binary(
        string='Header Image',
        help='Image to be displayed in the header of reports'
    )
    
    image_field_2 = fields.Binary(
        string='Footer Image', 
        help='Image to be displayed in the footer of reports'
    ) 