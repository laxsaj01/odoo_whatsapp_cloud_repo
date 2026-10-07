# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# License: OPL-1.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WhatsAppSendComposer(models.TransientModel):
    _name = 'whatsapp.send.composer'
    _description = 'Interactive WhatsApp Message Composer'

    account_id = fields.Many2one(
        'whatsapp.account',
        string='Sender WhatsApp Account',
        required=True,
        domain="[('state', '=', 'connected')]"
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Recipient Partner',
        required=True
    )
    recipient_phone = fields.Char(
        string='Recipient Phone',
        required=True,
        help='Ensure number includes country code in E.164 format (e.g. +923001234567).'
    )

    message_type = fields.Selection(
        [
            ('template', 'Approved Meta Template'),
            ('text', 'Custom Text Message'),
            ('media', 'Media Document / Image'),
        ],
        string='Message Type',
        default='template',
        required=True
    )
    template_id = fields.Many2one(
        'whatsapp.template',
        string='Template',
        domain="[('account_id', '=', account_id), ('state', '=', 'approved')]"
    )
    message_body = fields.Text(string='Message Content')
    preview_body = fields.Text(
        string='Dynamic Live Preview',
        compute='_compute_preview_body'
    )

    # Media attachments
    media_type = fields.Selection(
        [
            ('document', 'Document (PDF)'),
            ('image', 'Image'),
        ],
        string='Media Type',
        default='document'
    )
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='File Attachment'
    )

    # Origin context
    model_name = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related Record ID')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.recipient_phone = self.partner_id.mobile or self.partner_id.phone

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.message_body = self.template_id.body_text

    @api.depends('template_id', 'message_body', 'model_name', 'res_id')
    def _compute_preview_body(self):
        for record in self:
            if record.template_id:
                rec = None
                if record.model_name and record.res_id:
                    rec = self.env[record.model_name].browse(record.res_id)
                record.preview_body = record.template_id.render_preview_text(record=rec)
            else:
                record.preview_body = record.message_body or ''

    def action_send_direct(self):
        """Immediately sends the message via Meta Cloud API."""
        self.ensure_one()
        return self._create_queue_record(send_immediately=True)

    def action_enqueue(self):
        """Places message into background queue for scheduled cron processing."""
        self.ensure_one()
        return self._create_queue_record(send_immediately=False)

    def _create_queue_record(self, send_immediately=False):
        if not self.recipient_phone:
            raise UserError(_("Please provide a valid recipient phone number."))

        vals = {
            'account_id': self.account_id.id,
            'partner_id': self.partner_id.id,
            'recipient_phone': self.recipient_phone,
            'message_type': self.message_type,
            'template_id': self.template_id.id if self.message_type == 'template' else False,
            'message_body': self.preview_body if self.message_type == 'template' else self.message_body,
            'media_type': self.media_type if self.message_type == 'media' else False,
            'attachment_id': self.attachment_id.id if self.attachment_id else False,
            'model_name': self.model_name,
            'res_id': self.res_id,
            'state': 'queued',
        }
        queue_rec = self.env['whatsapp.message.queue'].create(vals)

        if send_immediately:
            queue_rec.action_send_now()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('WhatsApp Sent'),
                    'message': _('Message successfully dispatched to %s.') % self.recipient_phone,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Enqueued'),
                    'message': _('Message added to background queue for dispatch.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
