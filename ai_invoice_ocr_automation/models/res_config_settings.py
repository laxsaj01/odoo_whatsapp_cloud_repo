# -*- coding: utf-8 -*-
# Part of Smart AI Vendor Bill & Invoice OCR Automation.
# License: OPL-1.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_ocr_default_provider_id = fields.Many2one(
        'ai.ocr.provider',
        string='Default AI OCR Engine',
        config_parameter='ai_invoice_ocr.default_provider_id',
        domain="[('company_id', '=', company_id), ('state', '=', 'connected')]",
        help='Primary AI model utilized for scanning incoming bills and invoices.'
    )
    ai_ocr_auto_create_partner = fields.Boolean(
        string='Auto-Create Unmatched Vendors',
        config_parameter='ai_invoice_ocr.auto_create_partner',
        default=True,
        help='Automatically create a new draft vendor contact if the supplier is not found in Odoo.'
    )
    ai_ocr_auto_post_bill = fields.Boolean(
        string='Auto-Confirm Verified Bills',
        config_parameter='ai_invoice_ocr.auto_post_bill',
        default=False,
        help='Automatically confirm and post bills if confidence score exceeds 95% (recommended: keep false for review).'
    )
