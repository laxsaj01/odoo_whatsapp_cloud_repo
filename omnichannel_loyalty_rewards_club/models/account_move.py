# -*- coding: utf-8 -*-
# Part of Omnichannel Customer Loyalty, Rewards & Cashback Club.
# License: OPL-1.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    loyalty_points_earned = fields.Float(
        string='Points Earned',
        copy=False,
        readonly=True
    )
    loyalty_points_redeemed = fields.Float(
        string='Points Redeemed',
        copy=False,
        readonly=True
    )
    customer_points_balance = fields.Float(
        string='Customer Loyalty Points',
        related='partner_id.loyalty_points_balance',
        readonly=True
    )

    def action_post(self):
        """Accrues points on direct customer invoices not originated from a Sale Order."""
        res = super(AccountMove, self).action_post()
        ledger_obj = self.env['loyalty.points.ledger']
        config = self.env['ir.config_parameter'].sudo()

        earn_ratio = float(config.get_param('omnichannel_loyalty.earn_ratio', 1.0))
        validity_days = int(config.get_param('omnichannel_loyalty.validity_days', 365))

        for move in self.filtered(lambda m: m.is_sale_document(include_receipts=True)):
            # Avoid double-accrual if invoice already originated from a confirmed sale.order
            sale_origins = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            if sale_origins:
                continue

            partner = move.partner_id
            tier = partner.loyalty_tier_id
            multiplier = tier.points_multiplier if tier else 1.0

            qualifying_spend = max(0.0, move.amount_untaxed)
            base_points = qualifying_spend * earn_ratio
            total_earned = round(base_points * multiplier, 2)

            if total_earned > 0:
                exp_date = fields.Date.add(fields.Date.today(), days=validity_days) if validity_days > 0 else False
                ledger_obj.create({
                    'partner_id': partner.id,
                    'company_id': move.company_id.id,
                    'transaction_type': 'earn_purchase',
                    'points': total_earned,
                    'amount_monetary': move.amount_total,
                    'move_id': move.id,
                    'expiration_date': exp_date,
                    'notes': _("Points earned for Invoice %s (Base: %.1f, Tier Multiplier: %.2fx)") % (
                        move.name, base_points, multiplier
                    )
                })
                move.write({'loyalty_points_earned': total_earned})
                partner._update_loyalty_tier()

        return res

    def action_open_loyalty_redeem_wizard(self):
        """Allows redeeming points on draft customer invoices."""
        self.ensure_one()
        if self.state != 'draft' or self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Points can only be redeemed on draft customer invoices."))

        if self.partner_id.loyalty_points_balance <= 0:
            raise UserError(_("Customer %s currently has 0 available loyalty points.") % self.partner_id.name)

        return {
            'name': _('Redeem Customer Loyalty Points'),
            'type': 'ir.actions.act_window',
            'res_model': 'loyalty.points.redeem.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }
