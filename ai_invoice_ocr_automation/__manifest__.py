# -*- coding: utf-8 -*-
# Part of Smart AI Vendor Bill & Invoice OCR Automation.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

{
    'name': 'Smart AI Vendor Bill & Invoice OCR Automation',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'AI Vision OCR (OpenAI & Claude): Auto-Extract Vendor Bills, Line Items, Taxes & Partners with Zero IAP Markup',
    'description': """
Smart AI Vendor Bill & Invoice OCR Automation
==============================================
Tired of paying exorbitant per-page In-App Purchase (IAP) credits for standard Odoo OCR?
This module provides a direct BYOK (Bring Your Own Key) connection to cutting-edge AI vision models
(OpenAI GPT-4o, GPT-4o-mini & Anthropic Claude 3.5 Sonnet) to automate invoice data entry.

Key Enterprise Capabilities:
----------------------------
* **Zero IAP Markup:** Connect your own OpenAI or Anthropic API key. Process invoices for fractions of a cent ($0.005/invoice vs $0.20+ with standard OCR).
* **Multi-Format Ingestion:** Seamlessly parses PDF invoices, scanned paper receipts, PNG, JPEG, and WebP attachments.
* **Deep Table & Line Item Extraction:** Extracts product description, quantities, unit prices, sub-totals, and detects line-item tax percentages.
* **Intelligent Partner Resolver:** Auto-matches existing suppliers by VAT/Tax ID, phone, email, or company name, with draft partner auto-creation options.
* **Tax & Account Resolution:** Automatically maps detected tax percentages to company tax accounts and assigns default expense accounts.
* **Side-by-Side Verification:** Visual split view allowing accountants to review original PDF/receipt directly against extracted draft vendor bill.
* **High-Throughput Batch Processing:** Automated message and file queue processed via background cron to handle bulk monthly accounting batches.
    """,
    'author': 'Enterprise Odoo Solutions',
    'website': 'https://apps.odoo.com',
    'license': 'OPL-1',
    'price': 80.00,
    'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'account',
    ],
    'data': [
        'security/ai_ocr_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/ai_ocr_provider_views.xml',
        'views/ai_ocr_queue_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/ai_invoice_ocr_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
