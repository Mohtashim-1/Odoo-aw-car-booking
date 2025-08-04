from odoo import models, fields, api

class CarExtraService(models.Model):
    _name = 'car.extra.service'
    _description = 'Car Extra Service'

    name = fields.Char(string='Service Name', required=True)
    
    def _check_access_rights(self, operation):
        """Override to allow read access for all users"""
        if operation == 'read':
            return True
        return super()._check_access_rights(operation)