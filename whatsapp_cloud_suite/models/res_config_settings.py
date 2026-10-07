# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# License: OPL-1.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    whatsapp_default_account_id = fields.Many2one(
        'whatsapp.account',
        string='Default WhatsApp Account',
        config_parameter='whatsapp_cloud_suite.default_account_id',
        domain="[('company_id', '=', company_id), ('state', '=', 'connected')]",
        help='Default Meta Cloud account used for automated business notifications.'
    )
    whatsapp_auto_sale_confirm = fields.Boolean(
        string='Auto WhatsApp on Quotation Confirmation',
        config_parameter='whatsapp_cloud_suite.auto_sale_confirm',
        default=True,
        help='Automatically send WhatsApp confirmation message when a quotation is confirmed.'
    )
    whatsapp_auto_invoice_validate = fields.Boolean(
        string='Auto WhatsApp PDF Invoice on Post',
        config_parameter='whatsapp_cloud_suite.auto_invoice_validate',
        default=True,
        help='Automatically render and dispatch PDF invoice on WhatsApp upon invoice posting.'
    )
    whatsapp_auto_stock_validate = fields.Boolean(
        string='Auto WhatsApp on Delivery Order Validation',
        config_parameter='whatsapp_cloud_suite.auto_stock_validate',
        default=True,
        help='Automatically send dispatch and tracking notification when stock delivery is validated.'
    )
    whatsapp_enable_bot = fields.Boolean(
        string='Enable Interactive WhatsApp Bot',
        config_parameter='whatsapp_cloud_suite.enable_bot',
        default=True,
        help='Activate auto-replies for Catalog and Order triggers from WhatsApp incoming messages.'
    )
