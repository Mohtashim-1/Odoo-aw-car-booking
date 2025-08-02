from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    show_car_booking = fields.Boolean(
        string='Show Car Booking',
        default=False,
        compute='_compute_show_car_booking',
        store=False,
        help='Check this box to show Car Booking menu to this user'
    )
    
    def _compute_show_car_booking(self):
        """Compute the field value based on group membership"""
        car_booking_user_group = self.env.ref('aw_car_booking.group_car_booking_user', raise_if_not_found=False)
        car_booking_manager_group = self.env.ref('aw_car_booking.group_car_booking_manager', raise_if_not_found=False)
        
        for user in self:
            user.show_car_booking = (
                (car_booking_user_group and car_booking_user_group in user.groups_id) or
                (car_booking_manager_group and car_booking_manager_group in user.groups_id)
            )
    
    @api.onchange('show_car_booking')
    def _onchange_show_car_booking(self):
        """Handle checkbox changes to assign/unassign groups"""
        car_booking_user_group = self.env.ref('aw_car_booking.group_car_booking_user', raise_if_not_found=False)
        car_booking_manager_group = self.env.ref('aw_car_booking.group_car_booking_manager', raise_if_not_found=False)
        
        for user in self:
            if user.show_car_booking:
                # Add user to car booking user group
                if car_booking_user_group and car_booking_user_group not in user.groups_id:
                    user.groups_id = [(4, car_booking_user_group.id)]
            else:
                # Remove user from car booking groups
                if car_booking_user_group and car_booking_user_group in user.groups_id:
                    user.groups_id = [(3, car_booking_user_group.id)]
                if car_booking_manager_group and car_booking_manager_group in user.groups_id:
                    user.groups_id = [(3, car_booking_manager_group.id)] 