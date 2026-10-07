# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

{
    'name': 'WhatsApp Business Cloud API Enterprise Suite',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools/Sales/Marketing',
    'summary': 'Meta WhatsApp Cloud API: 2-Way Chat, Auto PDF Invoicing, Order Updates, Interactive Bot & Discuss Channel Sync',
    'description': """
WhatsApp Business Cloud API Enterprise Suite
============================================
Seamless, zero-middleman integration with the official Meta WhatsApp Business Cloud API.
Save thousands of dollars on third-party gateways (Twilio, Gupshup, 360dialog) by connecting
directly to Meta's Cloud API infrastructure.

Key Enterprise Features:
------------------------
* **Zero Middleman:** Direct Meta Graph API (v20+) connection with zero per-message markup.
* **Multi-Company Support:** Distinct WABA accounts, Phone Numbers, and Tokens per company.
* **Meta Template Sync:** Bi-directional sync of templates, status tracking, and dynamic parameters.
* **Auto PDF Invoices:** Auto-renders QWeb invoices in-memory and dispatches them with interactive buttons.
* **Sales & Logistics Triggers:** Automated order confirmations, quotation sharing, and tracking links.
* **2-Way Conversational Engine:** Inbound webhook router linking WhatsApp directly to Odoo Discuss.
* **Interactive Conversational Bot:** Automated menu triggers, catalog display, and draft quotation generation.
* **High-Concurrency Queue Engine:** Ir.cron backed message queue with exponential backoff and error tracking.
* **Secure Webhooks:** HMAC-SHA256 signature verification for complete payload integrity.
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
        'stock',
    ],
    'data': [
        'security/whatsapp_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/whatsapp_default_templates.xml',
        'views/whatsapp_account_views.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_message_queue_views.xml',
        'views/whatsapp_chat_history_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/whatsapp_send_composer_views.xml',
        'views/menu_views.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
