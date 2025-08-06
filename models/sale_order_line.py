from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    car_booking_line_id = fields.Many2one(
        'car.booking.line',
        string='Car Booking Line',
        help='Related car booking line for this order line'
    )

    service_type = fields.Many2one(
        'type.of.service',
        string='Service Type',
        required=True,
        help='Type of car booking service (e.g., Transfer, Full Day, etc.)'
    )

    car_type = fields.Many2one(
        'fleet.vehicle.model',
        string='Car Type',
        required=True,
        help='Type/model of the car for this booking'
    )

    duration = fields.Integer(
        string='Duration (Days)',
        required=True,
        default=1,
        help='Duration of the booking in days'
    )

    additional_charges = fields.Float(
        string='Additional Charges',
        default=0.0,
        help='Extra charges for this booking line'
    )

    date_start = fields.Datetime(
        string='Start Date',
        help='Start date and time of the booking'
    )

    date_end = fields.Datetime(
        string='End Date',
        help='End date and time of the booking'
    )

    # Technical field for price unit
    technical_price_unit = fields.Float(
        string='Technical Price Unit',
        help='Technical field to store the original price unit'
    )

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'duration', 'additional_charges')
    def _compute_amount(self):
        """
        Custom calculation for price_subtotal:
        price_subtotal = duration * product_uom_qty * price_unit + additional_charges - discount + tax_id (percentage)
        """
        for line in self:
            # Check if this is a car booking line (has service_type or car_type)
            is_car_booking = line.service_type or line.car_type or line.car_booking_line_id
            
            if is_car_booking:
                # Custom calculation for car booking lines
                duration = line.duration or 1
                qty = line.product_uom_qty or 0.0
                price_unit = line.price_unit or 0.0
                additional_charges = line.additional_charges or 0.0
                discount = line.discount or 0.0
                
                # Calculate base amount: duration * qty * price_unit
                base_amount = duration * qty * price_unit
                
                # Add additional charges
                subtotal_with_charges = base_amount + additional_charges
                
                # Apply discount
                discount_amount = subtotal_with_charges * (discount / 100.0)
                subtotal_after_discount = subtotal_with_charges - discount_amount
                
                # Calculate taxes
                taxes_res = line.tax_id.compute_all(
                    subtotal_after_discount,
                    line.order_id.currency_id,
                    line.product_uom_qty,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id
                )
                
                # Set the computed values
                line.price_subtotal = subtotal_after_discount
                line.price_tax = taxes_res['total_included'] - taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
                
                # Debug logging
                _logger.info(f'Line {line.id}: duration={duration}, qty={qty}, price_unit={price_unit}, additional_charges={additional_charges}, base_amount={base_amount}, subtotal_with_charges={subtotal_with_charges}, final_subtotal={subtotal_after_discount}')
            else:
                # Use standard calculation for non-car booking lines
                super()._compute_amount()

    @api.onchange('duration', 'product_uom_qty', 'price_unit', 'additional_charges', 'discount')
    def _onchange_car_booking_fields(self):
        """Trigger recalculation when car booking fields change"""
        if self.service_type or self.car_type or self.car_booking_line_id:
            self._compute_amount()
            # Force order totals recalculation
            if self.order_id:
                self.order_id._compute_amounts()

    @api.onchange('product_id')
    def _onchange_product_id(self):
        original_price_unit = self.price_unit
        if self.car_booking_line_id:
            # For car booking lines, handle the onchange manually
            if self.product_id:
                product = self.product_id
                if product.sale_line_warn != 'no-message':
                    if product.sale_line_warn == 'block':
                        self.product_id = False
                        return
                    return {
                        'warning': {
                            'title': _("Warning for %s", product.name),
                            'message': product.sale_line_warn_msg,
                        }
                    }
        else:
            # For regular lines, handle the onchange manually without calling super()
            if self.product_id:
                product = self.product_id
                if product.sale_line_warn != 'no-message':
                    if product.sale_line_warn == 'block':
                        self.product_id = False
                        return
                    return {
                        'warning': {
                            'title': _("Warning for %s", product.name),
                            'message': product.sale_line_warn_msg,
                        }
                    }

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        for line in self:
            if line.car_booking_line_id:
                # For car booking lines, use the booking line's unit price
                booking_line = line.car_booking_line_id
                if booking_line.unit_price:
                    line.price_unit = booking_line.unit_price
                    line.technical_price_unit = booking_line.unit_price
                else:
                    # Fallback to product list price
                    if line.product_id.list_price:
                        line.price_unit = line.product_id.list_price
                        line.technical_price_unit = line.product_id.list_price
            else:
                # Manually reset price unit instead of calling non-existent method
                if line.product_id.list_price:
                    line.price_unit = line.product_id.list_price
                    line.technical_price_unit = line.product_id.list_price

    @api.onchange('car_booking_line_id')
    def _onchange_car_booking_line_id(self):
        if self.car_booking_line_id:
            booking_line = self.car_booking_line_id
            self.service_type = booking_line.type_of_service_id.id if booking_line.type_of_service_id else False
            self.car_type = booking_line.car_model_id.id if booking_line.car_model_id else False
            self.date_start = booking_line.start_date
            self.date_end = booking_line.end_date
            self.additional_charges = booking_line.extra_hour_charges or 0.0
            self.product_uom_qty = booking_line.qty or 1.0
            self.price_unit = booking_line.unit_price or 0.0
            self.technical_price_unit = booking_line.unit_unit or 0.0
            # Set product if not already set
            if not self.product_id and booking_line.product_id:
                self.product_id = booking_line.product_id.id
            # Set UoM if not already set
            if not self.product_uom and booking_line.product_id:
                self.product_uom = booking_line.product_id.uom_id.id

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update({
            'car_booking_line_id': self.car_booking_line_id.id if self.car_booking_line_id else False,
            'service_type': self.service_type.id if self.service_type else False,
            'car_type': self.car_type.id if self.car_type else False,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'additional_charges': self.additional_charges,
        })
        return res 