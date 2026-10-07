# -*- coding: utf-8 -*-
# Part of Omnichannel Customer Loyalty, Rewards & Cashback Club.
# License: OPL-1.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class LoyaltyPointsRedeemWizard(models.TransientModel):
    _name = 'loyalty.points.redeem.wizard'
    _description = 'Interactive Customer Loyalty Points Redemption Wizard'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        readonly=True
    )
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
    available_points = fields.Float(
        string='Available Balance',
        related='partner_id.loyalty_points_balance',
        readonly=True
    )
    order_id = fields.Many2one('sale.order', string='Sale Order')
    move_id = fields.Many2one('account.move', string='Invoice')
    order_amount_total = fields.Monetary(
        string='Order Total',
        compute='_compute_order_total',
        currency_field='currency_id'
    )
    max_redeemable_points = fields.Float(
        string='Max Redeemable Points',
        compute='_compute_limits'
    )
    points_to_redeem = fields.Float(
        string='Points to Redeem',
        required=True,
        default=0.0
    )
    discount_amount = fields.Monetary(
        string='Discount Cash Value',
        compute='_compute_discount',
        currency_field='currency_id'
    )

    @api.depends('order_id', 'move_id')
    def _compute_order_total(self):
        for wiz in self:
            if wiz.order_id:
                wiz.order_amount_total = wiz.order_id.amount_total
            elif wiz.move_id:
                wiz.order_amount_total = wiz.move_id.amount_total
            else:
                wiz.order_amount_total = 0.0

    @api.depends('available_points', 'order_amount_total')
    def _compute_limits(self):
        config = self.env['ir.config_parameter'].sudo()
        redeem_ratio = float(config.get_param('omnichannel_loyalty.redeem_ratio', 0.10))
        max_pct = float(config.get_param('omnichannel_loyalty.max_redemption_percent', 50.0)) / 100.0

        for wiz in self:
            if redeem_ratio > 0 and wiz.order_amount_total > 0:
                max_cash_allowed = wiz.order_amount_total * max_pct
                points_cap = max_cash_allowed / redeem_ratio
                wiz.max_redeemable_points = min(wiz.available_points, points_cap)
            else:
                wiz.max_redeemable_points = wiz.available_points

    @api.depends('points_to_redeem')
    def _compute_discount(self):
        config = self.env['ir.config_parameter'].sudo()
        redeem_ratio = float(config.get_param('omnichannel_loyalty.redeem_ratio', 0.10))
        for wiz in self:
            wiz.discount_amount = round(wiz.points_to_redeem * redeem_ratio, 2)

    def action_confirm_redemption(self):
        """Deducts points from wallet and appends discount line to target document."""
        self.ensure_one()
        if self.points_to_redeem <= 0:
            raise ValidationError(_("Please specify a positive number of points to redeem."))

        if self.points_to_redeem > self.available_points:
            raise ValidationError(_("Customer only has %.1f points available.") % self.available_points)

        if self.points_to_redeem > self.max_redeemable_points:
            raise ValidationError(_("Redemption exceeds maximum allowed limit of %.1f points.") % self.max_redeemable_points)

        ledger_obj = self.env['loyalty.points.ledger']

        # 1. Apply to Sale Order
        if self.order_id:
            order = self.order_id
            discount_line_vals = {
                'order_id': order.id,
                'name': _("Loyalty Rewards Discount (-%.1f Points)") % self.points_to_redeem,
                'price_unit': -abs(self.discount_amount),
                'product_uom_qty': 1.0,
            }
            self.env['sale.order.line'].create(discount_line_vals)

            ledger_obj.create({
                'partner_id': self.partner_id.id,
                'company_id': self.company_id.id,
                'transaction_type': 'redeem_order',
                'points': -abs(self.points_to_redeem),
                'amount_monetary': self.discount_amount,
                'order_id': order.id,
                'notes': _("Redeemed %.1f points for %s discount on Order %s") % (
                    self.points_to_redeem, self.discount_amount, order.name
                )
            })
            order.write({
                'loyalty_points_redeemed': order.loyalty_points_redeemed + self.points_to_redeem,
                'loyalty_discount_amount': order.loyalty_discount_amount + self.discount_amount
            })

        # 2. Apply to Invoice
        elif self.move_id:
            move = self.move_id
            discount_line_vals = {
                'move_id': move.id,
                'name': _("Loyalty Rewards Discount (-%.1f Points)") % self.points_to_redeem,
                'price_unit': -abs(self.discount_amount),
                'quantity': 1.0,
            }
            self.env['account.move.line'].create(discount_line_vals)

            ledger_obj.create({
                'partner_id': self.partner_id.id,
                'company_id': self.company_id.id,
                'transaction_type': 'redeem_invoice',
                'points': -abs(self.points_to_redeem),
                'amount_monetary': self.discount_amount,
                'move_id': move.id,
                'notes': _("Redeemed %.1f points for %s discount on Invoice %s") % (
                    self.points_to_redeem, self.discount_amount, move.name
                )
            })
            move.write({
                'loyalty_points_redeemed': move.loyalty_points_redeemed + self.points_to_redeem
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Points Redeemed!'),
                'message': _('Successfully redeemed %.1f points (%s discount applied).') % (
                    self.points_to_redeem, self.discount_amount
                ),
                'type': 'success',
                'sticky': False,
            }
        }
