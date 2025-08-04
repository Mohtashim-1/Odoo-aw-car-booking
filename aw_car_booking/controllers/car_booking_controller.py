from odoo import http
from odoo.http import request
import json

class CarBookingController(http.Controller):

    @http.route('/car_booking/submit', type='json', auth='user')
    def submit_booking(self, **kwargs):
        try:
            booking_data = kwargs  # Get all data passed in the request
            # Process the booking data
            # You can create or update records in your models here
            booking_record = request.env['car.booking'].create({
                'booking_type': booking_data.get('booking_type'),
                'customer_type': booking_data.get('customer_type'),
                'customer_id': booking_data.get('customer_id'),
                'car_id': booking_data.get('car_id'),
                'start_date': booking_data.get('start_date'),
                'end_date': booking_data.get('end_date'),
                'driver_info': booking_data.get('driver_info'),
            })

            return json.dumps({
                'status': 'success',
                'message': 'Booking successfully created!',
                'booking_id': booking_record.id,
            })
        except Exception as e:
            return json.dumps({
                'status': 'error',
                'message': str(e),
            })
