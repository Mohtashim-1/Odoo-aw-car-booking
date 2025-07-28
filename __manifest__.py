{
    'name': 'Car Booking',
    'version': '18.0',
    'depends': ['base','fleet','project',
                 'contacts', 'account','stock','fleet_operations'],
    'data': [
        'security/car_booking_groups.xml',
        'security/ir.model.access.csv',
        'views/car_booking_views.xml',
        'data/car_extra_service_data.xml',
        'views/car_extra_service_view.xml',
        'views/booking_cities.xml',
        'views/fleet_vehicle.xml',
        'views/car_airport.xml',
        'views/car_booking_line_view.xml',
        # 'security/car_booking_security.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
