# -*- coding: utf-8 -*-
# Part of Omnichannel Customer Loyalty, Rewards & Cashback Club.
# License: OPL-1.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    loyalty_earn_ratio = fields.Float(
        string='Base Earn Ratio (Points per $1 spend)',
        config_parameter='omnichannel_loyalty.earn_ratio',
        default=1.0,
        help='How many base points are awarded for every 1 unit of local currency spent.'
    )
    loyalty_redeem_ratio = fields.Float(
        string='Redeem Cash Value ($ per Point)',
        config_parameter='omnichannel_loyalty.redeem_ratio',
        default=0.10,
        help='Cash equivalent value of 1 loyalty point (e.g. 0.10 means 100 points = $10 discount).'
    )
    loyalty_welcome_bonus = fields.Float(
        string='Welcome Bonus Points',
        config_parameter='omnichannel_loyalty.welcome_bonus',
        default=50.0,
        help='Bonus points credited to new accounts upon signup or first purchase.'
    )
    loyalty_birthday_bonus = fields.Float(
        string='Annual Birthday Bonus Points',
        config_parameter='omnichannel_loyalty.birthday_bonus',
        default=100.0,
        help='Points awarded automatically on the customer birthday via scheduled background cron.'
    )
    loyalty_referral_bonus = fields.Float(
        string='Referral Reward Points',
        config_parameter='omnichannel_loyalty.referral_bonus',
        default=50.0,
        help='Points rewarded to both advocate and new customer upon first completed order.'
    )
    loyalty_validity_days = fields.Integer(
        string='Points Validity Duration (Days)',
        config_parameter='omnichannel_loyalty.validity_days',
        default=365,
        help='Number of days before unredeemed points expire (set 0 for lifetime validity).'
    )
    loyalty_max_redemption_percent = fields.Float(
        string='Maximum Redemption Cap (% of Order)',
        config_parameter='omnichannel_loyalty.max_redemption_percent',
        default=50.0,
        help='Maximum percentage of order total that can be funded using loyalty points.'
    )
