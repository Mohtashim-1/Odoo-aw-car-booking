from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    custom_amount_untaxed = fields.Monetary(string='Custom Untaxed Amount', compute='_compute_custom_amounts', store=True, currency_field='currency_id')
    custom_amount_tax = fields.Monetary(string='Custom VAT Taxes', compute='_compute_custom_amounts', store=True, currency_field='currency_id')
    custom_amount_total = fields.Monetary(string='Custom Total', compute='_compute_custom_amounts', store=True, currency_field='currency_id')

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.tax_id')
    def _compute_custom_amounts(self):
        for order in self:
            # Sum up all custom line subtotals
            custom_untaxed = sum(order.order_line.mapped('price_subtotal'))
            # Find the tax rate (assume all lines have the same tax rate for simplicity)
            tax_rate = 0.0
            for line in order.order_line:
                if line.tax_id:
                    # Take the first tax's amount (percentage)
                    tax_rate = line.tax_id[0].amount
                    break
            custom_tax = custom_untaxed * (tax_rate / 100.0)
            custom_total = custom_untaxed + custom_tax
            order.custom_amount_untaxed = custom_untaxed
            order.custom_amount_tax = custom_tax
            order.custom_amount_total = custom_total 