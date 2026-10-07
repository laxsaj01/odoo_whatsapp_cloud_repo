# -*- coding: utf-8 -*-
# Part of Omnichannel Customer Loyalty, Rewards & Cashback Club.
# License: OPL-1.

import secrets
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    loyalty_points_balance = fields.Float(
        string='Loyalty Points Balance',
        compute='_compute_loyalty_balances',
        store=True,
        tracking=True,
        help='Current spendable reward points balance.'
    )
    lifetime_points_earned = fields.Float(
        string='Lifetime Points Earned',
        compute='_compute_loyalty_balances',
        store=True,
        help='Cumulative sum of all points awarded since account inception.'
    )
    lifetime_points_redeemed = fields.Float(
        string='Lifetime Points Redeemed',
        compute='_compute_loyalty_balances',
        store=True,
        help='Cumulative sum of all points spent on orders and discounts.'
    )
    loyalty_tier_id = fields.Many2one(
        'loyalty.tier',
        string='VIP Club Tier',
        tracking=True,
        help='Current membership tier determining promotional reward multipliers.'
    )
    loyalty_tier_name = fields.Char(related='loyalty_tier_id.name', string='Tier Name', readonly=True)
    birthday = fields.Date(string='Birthday Date', help='Date used to trigger automated annual birthday bonus points.')
    referral_code = fields.Char(
        string='Unique Referral Code',
        copy=False,
        readonly=True,
        default=lambda self: secrets.token_hex(4).upper(),
        help='Unique sharing code for customer referral rewards.'
    )
    referred_by_id = fields.Many2one(
        'res.partner',
        string='Referred By',
        domain="[('id', '!=', id)]",
        help='Advocate customer who referred this contact.'
    )
    loyalty_ledger_ids = fields.One2many(
        'loyalty.points.ledger',
        'partner_id',
        string='Loyalty Transactions'
    )
    ledger_count = fields.Integer(
        string='Transactions Count',
        compute='_compute_ledger_count'
    )

    @api.depends('loyalty_ledger_ids.points')
    def _compute_loyalty_balances(self):
        for partner in self:
            earned = 0.0
            redeemed = 0.0
            balance = 0.0
            for tx in partner.loyalty_ledger_ids:
                if tx.points > 0:
                    earned += tx.points
                else:
                    redeemed += abs(tx.points)
                balance += tx.points
            partner.lifetime_points_earned = earned
            partner.lifetime_points_redeemed = redeemed
            partner.loyalty_points_balance = max(0.0, balance)

    def _compute_ledger_count(self):
        ledger_obj = self.env['loyalty.points.ledger']
        for partner in self:
            partner.ledger_count = ledger_obj.search_count([('partner_id', '=', partner.id)])

    def _update_loyalty_tier(self):
        """Automatically updates customer's tier based on lifetime verified spend."""
        tier_obj = self.env['loyalty.tier']
        for partner in self:
            # Calculate total paid/confirmed sales spend
            orders = self.env['sale.order'].search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['sale', 'done'])
            ])
            total_spend = sum(orders.mapped('amount_total'))

            qualifying_tier = tier_obj.search([
                ('company_id', 'in', [False, partner.company_id.id if partner.company_id else self.env.company.id]),
                ('min_spend_amount', '<=', total_spend)
            ], order='min_spend_amount desc', limit=1)

            if qualifying_tier and partner.loyalty_tier_id != qualifying_tier:
                partner.write({'loyalty_tier_id': qualifying_tier.id})
                partner.message_post(
                    body=_("🎉 Congratulations! Member has progressed to <b>%s</b> VIP Tier (Lifetime Spend: %s).") % (
                        qualifying_tier.name, total_spend
                    )
                )

    def action_view_loyalty_ledger(self):
        self.ensure_one()
        return {
            'name': _('Loyalty Points Ledger: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'loyalty.points.ledger',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
