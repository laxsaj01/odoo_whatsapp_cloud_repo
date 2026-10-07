# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# License: OPL-1.

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    whatsapp_delivery_status = fields.Selection(
        [
            ('not_sent', 'Not Sent'),
            ('sent', 'Sent via WhatsApp'),
            ('failed', 'Dispatch Failed'),
        ],
        string='WhatsApp Delivery Status',
        default='not_sent',
        copy=False,
        readonly=True
    )

    def action_send_whatsapp_delivery(self):
        """Interactive manual trigger for delivery tracking notification."""
        self.ensure_one()
        phone = self.partner_id.mobile or self.partner_id.phone

        account = self.env['whatsapp.account'].search([
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'connected')
        ], limit=1)

        template = self.env['whatsapp.template'].search([
            ('model', '=', 'stock.picking'),
            ('state', '=', 'approved')
        ], limit=1)

        tracking_info = self.carrier_tracking_ref or self.name
        body = _('Hello %(name)s, your order %(ref)s has been dispatched! Tracking Reference: %(track)s') % {
            'name': self.partner_id.name,
            'ref': self.origin or self.name,
            'track': tracking_info
        }

        return {
            'name': _('Send WhatsApp Delivery Update'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.send.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_recipient_phone': phone,
                'default_model_name': 'stock.picking',
                'default_res_id': self.id,
                'default_account_id': account.id if account else False,
                'default_template_id': template.id if template else False,
                'default_message_body': body,
            }
        }

    def button_validate(self):
        """Override delivery validation to auto-send shipping notice."""
        res = super(StockPicking, self).button_validate()
        auto_send = self.env['ir.config_parameter'].sudo().get_param('whatsapp_cloud_suite.auto_stock_validate', True)

        if auto_send:
            for picking in self.filtered(lambda p: p.picking_type_code == 'outgoing'):
                try:
                    picking._auto_send_whatsapp_delivery()
                except Exception as e:
                    _logger.error("Auto WhatsApp delivery notification failed for %s: %s", picking.name, str(e))
        return res

    def _auto_send_whatsapp_delivery(self):
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

        tracking_info = self.carrier_tracking_ref or self.name
        body = _('Hello %(name)s, great news! Your delivery for %(origin)s is on its way. Tracking No: %(track)s') % {
            'name': self.partner_id.name,
            'origin': self.origin or self.name,
            'track': tracking_info
        }

        queue_vals = {
            'account_id': account.id,
            'partner_id': self.partner_id.id,
            'recipient_phone': phone,
            'message_type': 'text',
            'message_body': body,
            'model_name': 'stock.picking',
            'res_id': self.id,
            'state': 'queued'
        }
        queue_msg = self.env['whatsapp.message.queue'].create(queue_vals)
        queue_msg.action_send_now()
        self.write({'whatsapp_delivery_status': 'sent'})
