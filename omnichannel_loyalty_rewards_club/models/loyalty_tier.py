# -*- coding: utf-8 -*-
# Part of Omnichannel Customer Loyalty, Rewards & Cashback Club.
# License: OPL-1.

from odoo import models, fields, api, _


class LoyaltyTier(models.Model):
    _name = 'loyalty.tier'
    _description = 'VIP Loyalty Club Membership Tier'
    _order = 'sequence, min_spend_amount asc'

    name = fields.Char(
        string='Tier Name',
        required=True,
        translate=True,
        help='Name of the VIP tier (e.g. Bronze, Silver, Gold, Platinum).'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Currency',
        readonly=True
    )
    min_spend_amount = fields.Monetary(
        string='Minimum Qualifying Spend',
        required=True,
        default=0.0,
        currency_field='currency_id',
        help='Cumulative lifetime customer spend required to automatically advance into this tier.'
    )
    points_multiplier = fields.Float(
        string='Points Multiplier',
        default=1.0,
        required=True,
        help='Reward multiplier applied to base purchase points (e.g. 1.0 = normal, 1.5 = 50% extra points, 2.0 = double points).'
    )
    color = fields.Integer(string='Color Index', default=0)
    description = fields.Text(string='Tier Benefits Summary')
    partner_count = fields.Integer(
        string='Members Count',
        compute='_compute_partner_count'
    )

    def _compute_partner_count(self):
        partner_obj = self.env['res.partner']
        for tier in self:
            tier.partner_count = partner_obj.search_count([('loyalty_tier_id', '=', tier.id)])

    def action_view_members(self):
        self.ensure_one()
        return {
            'name': _('Tier Members: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('loyalty_tier_id', '=', self.id)],
            'context': {'default_loyalty_tier_id': self.id},
        }
