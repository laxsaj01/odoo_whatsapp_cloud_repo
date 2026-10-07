# -*- coding: utf-8 -*-
# Part of Omnichannel Customer Loyalty, Rewards & Cashback Club.
# License: OPL-1.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    loyalty_points_earned = fields.Float(
        string='Points Earned',
        copy=False,
        readonly=True,
        help='Reward points accrued upon confirmation of this order.'
    )
    loyalty_points_redeemed = fields.Float(
        string='Points Redeemed',
        copy=False,
        readonly=True,
        help='Points deducted from customer wallet to fund discount.'
    )
    loyalty_discount_amount = fields.Monetary(
        string='Loyalty Cash Discount',
        copy=False,
        readonly=True
    )
    loyalty_tier_id = fields.Many2one(
        'loyalty.tier',
        string='Customer Tier',
        related='partner_id.loyalty_tier_id',
        readonly=True
    )
    customer_points_balance = fields.Float(
        string='Available Loyalty Points',
        related='partner_id.loyalty_points_balance',
        readonly=True
    )

    def action_confirm(self):
        """Override confirmation to calculate reward points and handle referral bonuses."""
        res = super(SaleOrder, self).action_confirm()
        ledger_obj = self.env['loyalty.points.ledger']
        config = self.env['ir.config_parameter'].sudo()

        earn_ratio = float(config.get_param('omnichannel_loyalty.earn_ratio', 1.0))
        validity_days = int(config.get_param('omnichannel_loyalty.validity_days', 365))
        referral_bonus = float(config.get_param('omnichannel_loyalty.referral_bonus', 50.0))

        for order in self:
            partner = order.partner_id
            tier = partner.loyalty_tier_id
            multiplier = tier.points_multiplier if tier else 1.0

            # Net qualifying spend for earning points (excluding loyalty discount)
            qualifying_spend = max(0.0, order.amount_untaxed)
            base_points = qualifying_spend * earn_ratio
            total_earned = round(base_points * multiplier, 2)

            if total_earned > 0:
                exp_date = fields.Date.add(fields.Date.today(), days=validity_days) if validity_days > 0 else False
                ledger_obj.create({
                    'partner_id': partner.id,
                    'company_id': order.company_id.id,
                    'transaction_type': 'earn_purchase',
                    'points': total_earned,
                    'amount_monetary': order.amount_total,
                    'order_id': order.id,
                    'expiration_date': exp_date,
                    'notes': _("Points earned for Order %s (Base: %.1f, Tier Multiplier: %.2fx)") % (
                        order.name, base_points, multiplier
                    )
                })
                order.write({'loyalty_points_earned': total_earned})

            # Check Referral Program on customer's first completed order
            if partner.referred_by_id and referral_bonus > 0:
                previous_orders = self.search_count([
                    ('partner_id', '=', partner.id),
                    ('state', 'in', ['sale', 'done']),
                    ('id', '!=', order.id)
                ])
                if previous_orders == 0:
                    # Reward the advocate
                    ledger_obj.create({
                        'partner_id': partner.referred_by_id.id,
                        'company_id': order.company_id.id,
                        'transaction_type': 'earn_referral',
                        'points': referral_bonus,
                        'amount_monetary': 0.0,
                        'notes': _("Referral reward for introducing new customer %s (Order %s)") % (
                            partner.name, order.name
                        )
                    })
                    # Reward the new customer
                    ledger_obj.create({
                        'partner_id': partner.id,
                        'company_id': order.company_id.id,
                        'transaction_type': 'earn_signup',
                        'points': referral_bonus,
                        'amount_monetary': 0.0,
                        'notes': _("Welcome bonus on first completed purchase (Referred by %s)") % (
                            partner.referred_by_id.name
                        )
                    })

            partner._update_loyalty_tier()

        return res

    def action_open_loyalty_redeem_wizard(self):
        """Opens modal to redeem customer loyalty points as discount line on quotation."""
        self.ensure_one()
        if self.state not in ('draft', 'sent'):
            raise UserError(_("Points can only be redeemed on draft quotations before confirmation."))

        if self.partner_id.loyalty_points_balance <= 0:
            raise UserError(_("Customer %s currently has 0 available loyalty points.") % self.partner_id.name)

        return {
            'name': _('Redeem Customer Loyalty Points'),
            'type': 'ir.actions.act_window',
            'res_model': 'loyalty.points.redeem.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }
