# -*- coding: utf-8 -*-
# Part of Omnichannel Customer Loyalty, Rewards & Cashback Club.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

{
    'name': 'Omnichannel Customer Loyalty & Rewards Club',
    'version': '17.0.1.0.0',
    'category': 'Sales/Point of Sale/Marketing',
    'summary': 'VIP Tiered Club, Purchase Points, Birthday Bonuses, Referral Program & Cash-Equivalent Wallet Redemption',
    'description': """
Omnichannel Customer Loyalty & Rewards Club
===========================================
Maximize customer retention and repeat purchase lifetime value (LTV) with a comprehensive,
enterprise-grade loyalty and rewards points suite for Odoo.

Key Enterprise Capabilities:
----------------------------
* **Tiered VIP Membership:** Bronze, Silver, Gold, and Platinum tiers with automated progression based on lifetime spend.
* **Tier Points Multipliers:** Higher tier members earn bonus multipliers (e.g., Gold earns 1.5x, Platinum earns 2.0x points).
* **Multi-Channel Accrual:** Earn points automatically on confirmed Sales Orders, Invoices, and Retail transactions.
* **Referral Program:** Referral codes reward both the advocate and the new customer upon their first completed purchase.
* **Automated Birthday Rewards:** Scheduled cron job auto-credits birthday bonus points with celebratory email notices.
* **Seamless Wallet Redemption:** 1-Click modal wizard to redeem accumulated points directly as currency discounts on Quotations and Invoices.
* **Complete Immutable Audit Ledger:** Every point earned, spent, refunded, or expired is tracked in an auditable transaction journal.
* **Automated Points Expiration:** Background cron safely expires obsolete points based on custom validity periods.
    """,
    'author': 'Enterprise Odoo Solutions',
    'website': 'https://apps.odoo.com',
    'license': 'OPL-1',
    'price': 80.00,
    'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'account',
    ],
    'data': [
        'security/loyalty_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/loyalty_default_tiers.xml',
        'views/loyalty_tier_views.xml',
        'views/loyalty_points_ledger_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/loyalty_points_redeem_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
