from odoo import http
from odoo.http import request

class CarBookingController(http.Controller):

    @http.route('/car_booking/car_list', type='json', auth='user')
    def car_list(self):
        cars = request.env['fleet.vehicle'].sudo().search([])
        return [{'id': c.id, 'name': c.display_name} for c in cars]

    @http.route('/car_booking/customer_list', type='json', auth='user')
    def customer_list(self):
        customers = request.env['res.partner'].sudo().search([])
        return [{'id': c.id, 'name': c.name} for c in customers]

    @http.route('/car_booking/services_list', type='json', auth='user')
    def services_list(self):
        services = request.env['car.booking.service'].sudo().search([])
        return [{'id': s.id, 'name': s.name} for s in services]
    
    @http.route('/car_booking/is_operations_user', type='json', auth='user')
    def is_operations_user(self):
        user = request.env.user
        has_group = user.has_group('car_booking.group_operations_approver')
        return {'is_operations': has_group}
    
    @http.route('/car_booking/approve', type='json', auth='user')
    def approve_booking(self, booking_id):
    booking = request.env['car.booking'].sudo().browse(booking_id)
    if not booking:
        return {'error': 'Booking not found'}
    booking.write({'state': 'approved'})
    booking.message_post(body="✅ Booking approved by {}".format(request.env.user.name))
    return {'status': 'approved'}

    @http.route('/car_booking/reject', type='json', auth='user')
    def reject_booking(self, booking_id):
        booking = request.env['car.booking'].sudo().browse(booking_id)
    if not booking:
        return {'error': 'Booking not found'}
    booking.write({'state': 'rejected'})
    booking.message_post(body="❌ Booking rejected by {}".format(request.env.user.name))
    return {'status': 'rejected'}



    @http.route('/car_booking/submit_form', type='json', auth='user')
    def submit_form(self, data):
        return request.env['car.booking'].sudo().create({
            'booking_type': data['bookingType'],
            'customer_type': data['customerType'],
            'region': data['region'],
            'car_id': data['carId'],
            'customer_id': data['customerId'],
            'service_type': data['serviceType'],
            'start_date': data['startDate'],
            'end_date': data['endDate'],
            'from_location': data['fromLocation'],
            'to_location': data['toLocation'],
            'driver_info': data.get('driverInfo'),
            'national_id': data.get('nationalId'),
            'contact_person': data.get('contactPerson'),
            'extra_services': [(6, 0, data['extraServices'])],
        }).id
