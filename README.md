# Car Booking Module

This module provides comprehensive car booking functionality for Odoo 18.

## Features

### Car Booking Management
- Create and manage car bookings
- Support for different booking types (with driver, rental)
- Multiple regions and business types
- Customer management with contact details
- Service scheduling with start/end dates
- Extra services and charges
- Trip profiles and vehicle assignments

### Sales Order Integration
- **Create Car Booking from Sales Order**: Users can create car bookings directly from sales orders
- **Two Creation Methods**:
  1. **Quick Create**: Direct creation with default values
  2. **Wizard Create**: Guided creation with customizable options
- **Automatic Field Mapping**: Sales order data is automatically mapped to car booking fields
- **Bidirectional Linking**: Sales orders and car bookings are linked for easy navigation

### Invoice Integration
- Generate invoices from car bookings
- Custom invoice templates for car booking services
- Additional charges support
- Tax calculation and management

## Usage

### Creating Car Booking from Sales Order

1. **Navigate to Sales > Orders > Quotations**
2. **Create or open a sales order**
3. **Add products to the order lines**
4. **Click "Create Car Booking" button** in the header:
   - **Quick Create**: Creates car booking with default values
   - **Create Car Booking (Wizard)**: Opens wizard for custom configuration

### Car Booking Creation Wizard

The wizard allows you to configure:
- **Customer Information**: Customer, mobile, service date
- **Booking Details**: Type, region, business type, payment method
- **Options**: Auto-create booking lines from order lines
- **Notes**: Additional information

### Automatic Creation

When confirming a sales order, a car booking is automatically created if:
- Order lines contain car booking specific fields (service_type, car_type)
- Products belong to car/vehicle/transport categories

## Technical Details

### Models
- `car.booking`: Main car booking model
- `car.booking.line`: Individual booking lines
- `sale.order`: Extended with car booking integration
- `sale.order.line`: Extended with car booking fields
- `car.booking.create.wizard`: Wizard for guided creation

### Key Features
- **Field Mapping**: Automatic mapping between sales order and car booking fields
- **Validation**: Prerequisites checking before creation
- **User Experience**: Intuitive wizard interface
- **Flexibility**: Multiple creation methods for different use cases

## Installation

1. Install the module
2. Configure car booking settings
3. Set up product categories for car services
4. Configure service types and car models

## Configuration

### Required Setup
- Product categories for car services
- Service types (Transfer, Full Day, etc.)
- Car models and vehicles
- Customer categories

### Optional Setup
- Custom invoice templates
- Trip profiles
- Extra services
- Business points and regions

## Support

For support and questions, please contact the development team.
