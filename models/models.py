from odoo import models

class WarehouseProfile(models.Model):
	_name="warehouse.profile"

class VehicleShortage(models.Model):
	_name="vehicle.shortage"

class VehicleReceiptDelivery(models.Model):
	_name="vehicle.receipt.delivery"

class VehicleProfile(models.Model):
	_name="vehicle.profile"


class BookingCity(models.Model):
	_name = "booking.city"


class CarAirport(models.Model):
	_name = "car.airport"


class CarBooking(models.Model):
	_name = "car.booking"


class CarBookingLine(models.Model):
	_name = "car.booking.line"


class CarBookingTripLine(models.Model):
	_name = "car.booking.trip.line"


class CarExtraService(models.Model):
	_name = "car.extra.service"


class FleetVehicle(models.Model):
	_inherit = "fleet.vehicle" 


class ContractCollection(models.Model):
	_name = "contract.collection"


# class OperationPoint(models.Model):
# 	_name = "operation.point"


class OperationDashboard(models.Model):
	_name = "operations.dashboard"


class SystemIntegration(models.Model):
	_name="system.integration"
