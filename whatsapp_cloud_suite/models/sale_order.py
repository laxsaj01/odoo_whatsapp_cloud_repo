# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# License: OPL-1.

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    whatsapp_status = fields.Selection(
        [
            ('not_sent', 'Not Sent'),
            ('sent', 'Sent via WhatsApp'),
            ('failed', 'Delivery Failed'),
        ],
        string='WhatsApp Status',
        default='not_sent',
        copy=False,
        readonly=True
    )

    def action_send_whatsapp(self):
        """Opens WhatsApp composer wizard with quotation/order details preloaded."""
        self.ensure_one()
        template = self.env['whatsapp.template'].search([
            ('model', '=', 'sale.order'),
            ('state', '=', 'approved')
        ], limit=1)

        default_account = self.company_id.whatsapp_default_account_id if hasattr(self.company_id, 'whatsapp_default_account_id') else False
        if not default_account:
            default_account = self.env['whatsapp.account'].search([
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'connected')
            ], limit=1)

        return {
            'name': _('Send WhatsApp Message'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.send.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_recipient_phone': self.partner_id.mobile or self.partner_id.phone,
                'default_model_name': 'sale.order',
                'default_res_id': self.id,
                'default_account_id': default_account.id if default_account else False,
                'default_template_id': template.id if template else False,
            }
        }

    def action_confirm(self):
        """Override order confirmation to trigger automated WhatsApp confirmation."""
        res = super(SaleOrder, self).action_confirm()
        auto_send = self.env['ir.config_parameter'].sudo().get_param('whatsapp_cloud_suite.auto_sale_confirm', True)

        if auto_send:
            for order in self:
                try:
                    order._auto_send_whatsapp_confirmation()
                except Exception as e:
                    _logger.error("Auto WhatsApp confirmation failed for order %s: %s", order.name, str(e))
        return res

    def _auto_send_whatsapp_confirmation(self):
        self.ensure_one()
        phone = self.partner_id.mobile or self.partner_id.phone
        if not phone:
            return

        account = self.env['whatsapp.account'].search([
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'connected')
        ], limit=1)
        if not account:
            return

        template = self.env['whatsapp.template'].search([
            ('account_id', '=', account.id),
            ('model', '=', 'sale.order'),
            ('state', '=', 'approved')
        ], limit=1)

        body_msg = _(
            "Hello %(name)s, thank you for your order! Your Order %(order_ref)s of %(currency)s %(amount)s is confirmed and being prepared."
        ) % {
            'name': self.partner_id.name,
            'order_ref': self.name,
            'currency': self.currency_id.symbol,
            'amount': f"{self.amount_total:,.2f}"
        }

        queue_vals = {
            'account_id': account.id,
            'partner_id': self.partner_id.id,
            'recipient_phone': phone,
            'message_type': 'template' if template else 'text',
            'template_id': template.id if template else False,
            'message_body': body_msg,
            'model_name': 'sale.order',
            'res_id': self.id,
            'state': 'queued'
        }
        queue_msg = self.env['whatsapp.message.queue'].create(queue_vals)
        queue_msg.action_send_now()
        self.write({'whatsapp_status': 'sent'})
