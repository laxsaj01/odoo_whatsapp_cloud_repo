# -*- coding: utf-8 -*-
# Part of Custom Tailoring & Bespoke Apparel Suite.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    tailoring_measurement_ids = fields.One2many(
        'tailoring.customer.measurement',
        'partner_id',
        string='Measurement Profiles'
    )
    tailoring_measurement_count = fields.Integer(
        string='Measurements',
        compute='_compute_tailoring_counts'
    )
    tailoring_order_ids = fields.One2many(
        'tailoring.order',
        'partner_id',
        string='Tailoring Orders'
    )
    tailoring_order_count = fields.Integer(
        string='Tailoring Orders',
        compute='_compute_tailoring_counts'
    )

    @api.depends('tailoring_measurement_ids', 'tailoring_order_ids')
    def _compute_tailoring_counts(self):
        for partner in self:
            partner.tailoring_measurement_count = len(partner.tailoring_measurement_ids)
            partner.tailoring_order_count = len(partner.tailoring_order_ids)

    def action_view_measurements(self):
        self.ensure_one()
        return {
            'name': _('Measurements - %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'tailoring.customer.measurement',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_tailoring_orders(self):
        self.ensure_one()
        return {
            'name': _('Bespoke Orders - %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'tailoring.order',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
