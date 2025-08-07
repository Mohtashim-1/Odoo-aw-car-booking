from . import fleet_vehicle
from . import car_booking
from . import booking_cities
from . import car_extra_service

from . import year_model
from . import year_car_brand_and_type
from . import business_point
from . import type_of_service
from . import trip_profile
from . import res_partner
from . import res_company
from . import res_users

# Conditional imports based on module availability
try:
    from . import account_move
    from . import account_move_line
except ImportError:
    pass

try:
    from . import sale_order
    from . import sale_order_line
    from . import car_booking_wizard
except ImportError:
    pass

