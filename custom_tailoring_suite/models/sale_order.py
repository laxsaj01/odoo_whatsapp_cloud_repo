# -*- coding: utf-8 -*-
# Part of Custom Tailoring & Bespoke Apparel Suite.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tailoring_order_ids = fields.One2many(
        'tailoring.order',
        'sale_order_id',
        string='Bespoke Tailoring Orders'
    )
    tailoring_order_count = fields.Integer(
        string='Tailoring Orders',
        compute='_compute_tailoring_order_count'
    )

    @api.depends('tailoring_order_ids')
    def _compute_tailoring_order_count(self):
        for order in self:
            order.tailoring_order_count = len(order.tailoring_order_ids)

    def action_view_tailoring_orders(self):
        self.ensure_one()
        return {
            'name': _('Bespoke Tailoring Orders - %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'tailoring.order',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    tailoring_order_id = fields.Many2one(
        'tailoring.order',
        string='Linked Tailoring Job',
        readonly=True
    )
    is_bespoke_item = fields.Boolean(
        string='Custom Tailored Garment',
        default=False,
        help='Flag to indicate this item requires bespoke tailoring workshop processing'
    )

    def action_create_tailoring_job(self):
        self.ensure_one()
        # Find default garment type or first available
        garment_type = self.env['tailoring.garment.type'].search([], limit=1)
        # Find measurement for partner
        measurement = self.env['tailoring.customer.measurement'].search([
            ('partner_id', '=', self.order_id.partner_id.id)
        ], limit=1)

        job = self.env['tailoring.order'].create({
            'partner_id': self.order_id.partner_id.id,
            'sale_order_id': self.order_id.id,
            'sale_line_id': self.id,
            'garment_type_id': garment_type.id if garment_type else False,
            'measurement_id': measurement.id if measurement else False,
            'delivery_date': self.order_id.commitment_date or fields.Date.today(),
            'customer_notes': self.name,
        })
        self.tailoring_order_id = job.id
        return {
            'name': _('Bespoke Job Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'tailoring.order',
            'res_id': job.id,
            'view_mode': 'form',
        }
