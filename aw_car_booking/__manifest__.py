{
    'name': 'Car Booking',
    'version': '18.0.0.0.1',
    'depends': ['base','fleet','project',
                 'contacts','account','stock'],
    'data': [
        'security/car_booking_groups.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/user_groups.xml',
        'views/menu.xml',
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
}
