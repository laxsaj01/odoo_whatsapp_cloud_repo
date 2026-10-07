# -*- coding: utf-8 -*-
# Part of Omnichannel Customer Loyalty, Rewards & Cashback Club.
# License: OPL-1.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LoyaltyPointsLedger(models.Model):
    _name = 'loyalty.points.ledger'
    _description = 'Customer Loyalty Points Transaction Ledger'
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Transaction Ref',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        index=True,
        ondelete='cascade'
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
    transaction_type = fields.Selection(
        [
            ('earn_purchase', 'Purchase Points Accrual'),
            ('earn_signup', 'Welcome / First Purchase Bonus'),
            ('earn_birthday', 'Birthday Celebration Reward'),
            ('earn_referral', 'Referral Advocate Reward'),
            ('redeem_order', 'Quotation / Order Redemption'),
            ('redeem_invoice', 'Invoice Checkout Redemption'),
            ('refund_reversal', 'Order Cancellation / Return Reversal'),
            ('expire_expired', 'Points Validity Expiration'),
            ('manual_adjustment', 'Manager Manual Adjustment'),
        ],
        string='Transaction Type',
        required=True,
        default='earn_purchase'
    )
    points = fields.Float(
        string='Points Delta',
        required=True,
        help='Signed points value (+ for earnings, - for redemptions and deductions).'
    )
    amount_monetary = fields.Monetary(
        string='Associated Monetary Value',
        currency_field='currency_id',
        help='Financial value of order or cash-equivalent discount applied.'
    )
    order_id = fields.Many2one(
        'sale.order',
        string='Related Sales Order',
        ondelete='set null'
    )
    move_id = fields.Many2one(
        'account.move',
        string='Related Invoice',
        ondelete='set null'
    )
    notes = fields.Text(string='Transaction Reason / Notes')
    expiration_date = fields.Date(
        string='Valid Until',
        help='Date after which these specific earned points expire.'
    )
    is_expired = fields.Boolean(string='Expired', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('loyalty.points.ledger') or _('LP-%s') % fields.Datetime.now().strftime('%Y%m%d%H%M%S')
        records = super().create(vals_list)
        for record in records:
            record.partner_id._compute_loyalty_balances()
            record.partner_id._update_loyalty_tier()
        return records
