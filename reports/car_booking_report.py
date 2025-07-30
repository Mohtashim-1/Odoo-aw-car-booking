# -*- coding: utf-8 -*-
from odoo import api, models
import base64

class CarBookingReport(models.AbstractModel):
    _name = 'report.car_booking.car_booking_quotation_template'
    _description = 'Car Booking Quotation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['sale.order'].browse(docids)
        
        # Generate QR codes for each document
        qr_codes = {}
        for doc in docs:
            try:
                # Generate QR code using Odoo's barcode service
                qr_data = self.env['ir.actions.report'].barcode(
                    barcode_type='QR',
                    value=doc.name,
                    width=120,
                    height=120,
                    humanreadable=1
                )
                qr_codes[doc.id] = 'data:image/png;base64,' + base64.b64encode(qr_data).decode()
            except Exception as e:
                # If QR generation fails, set to None
                qr_codes[doc.id] = None
        
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': docs,
            'qr_codes': qr_codes,
        } 