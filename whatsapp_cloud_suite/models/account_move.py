# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# License: OPL-1.

import base64
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    whatsapp_invoice_status = fields.Selection(
        [
            ('not_sent', 'Not Sent'),
            ('sent', 'Invoice Sent via WhatsApp'),
            ('failed', 'Sending Failed'),
        ],
        string='WhatsApp Invoice Status',
        default='not_sent',
        copy=False,
        readonly=True
    )

    def _render_invoice_pdf_attachment(self):
        """Renders QWeb PDF invoice in-memory and returns an ir.attachment record."""
        self.ensure_one()
        report = self.env.ref('account.account_invoices', raise_if_not_found=False)
        if not report:
            report = self.env['ir.actions.report'].search([('model', '=', 'account.move')], limit=1)

        pdf_content, _ = report._render_qweb_pdf(report.id, [self.id])
        filename = f"{self.name.replace('/', '_')}.pdf"

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'raw': pdf_content,
            'res_model': 'account.move',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        return attachment

    def action_send_whatsapp_invoice(self):
        """Interactive manual trigger to send invoice PDF over WhatsApp."""
        self.ensure_one()
        attachment = self._render_invoice_pdf_attachment()

        account = self.env['whatsapp.account'].search([
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'connected')
        ], limit=1)

        template = self.env['whatsapp.template'].search([
            ('model', '=', 'account.move'),
            ('state', '=', 'approved')
        ], limit=1)

        phone = self.partner_id.mobile or self.partner_id.phone

        return {
            'name': _('Send WhatsApp Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.send.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_recipient_phone': phone,
                'default_model_name': 'account.move',
                'default_res_id': self.id,
                'default_account_id': account.id if account else False,
                'default_template_id': template.id if template else False,
                'default_attachment_id': attachment.id,
                'default_message_type': 'media',
                'default_media_type': 'document',
                'default_message_body': _('Dear %(name)s, please find attached your Invoice %(ref)s for %(currency)s %(amount)s.') % {
                    'name': self.partner_id.name,
                    'ref': self.name,
                    'currency': self.currency_id.symbol,
                    'amount': f"{self.amount_total:,.2f}"
                }
            }
        }

    def action_post(self):
        """Override invoice validation to auto-send invoice PDF via WhatsApp."""
        res = super(AccountMove, self).action_post()
        auto_send = self.env['ir.config_parameter'].sudo().get_param('whatsapp_cloud_suite.auto_invoice_validate', True)

        if auto_send:
            for move in self.filtered(lambda m: m.is_invoice(include_receipts=True)):
                try:
                    move._auto_send_whatsapp_invoice()
                except Exception as e:
                    _logger.error("Auto WhatsApp invoice dispatch failed for invoice %s: %s", move.name, str(e))
        return res

    def _auto_send_whatsapp_invoice(self):
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

        attachment = self._render_invoice_pdf_attachment()

        caption = _('Dear %(name)s, your invoice %(ref)s for %(currency)s %(amount)s is ready. Please find the attached PDF.') % {
            'name': self.partner_id.name,
            'ref': self.name,
            'currency': self.currency_id.symbol,
            'amount': f"{self.amount_total:,.2f}"
        }

        queue_vals = {
            'account_id': account.id,
            'partner_id': self.partner_id.id,
            'recipient_phone': phone,
            'message_type': 'media',
            'media_type': 'document',
            'attachment_id': attachment.id,
            'message_body': caption,
            'model_name': 'account.move',
            'res_id': self.id,
            'state': 'queued'
        }
        queue_msg = self.env['whatsapp.message.queue'].create(queue_vals)
        queue_msg.action_send_now()
        self.write({'whatsapp_invoice_status': 'sent'})
