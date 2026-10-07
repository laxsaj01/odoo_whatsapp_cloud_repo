# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# License: OPL-1.

import json
import re
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WhatsAppMessageQueue(models.Model):
    _name = 'whatsapp.message.queue'
    _description = 'WhatsApp Outbound & Inbound Message Queue'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(
        string='Message Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    account_id = fields.Many2one(
        'whatsapp.account',
        string='WhatsApp Account',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='account_id.company_id',
        store=True,
        readonly=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Recipient Partner',
        tracking=True
    )
    recipient_phone = fields.Char(
        string='Recipient Phone',
        required=True,
        tracking=True,
        help='Recipient phone number with country code in E.164 format (e.g. +923001234567, +971501234567).'
    )

    message_type = fields.Selection(
        [
            ('text', 'Plain Text'),
            ('template', 'Meta Template'),
            ('media', 'Media / Document'),
            ('interactive', 'Interactive Menu / Button'),
        ],
        string='Message Type',
        default='text',
        required=True
    )
    template_id = fields.Many2one(
        'whatsapp.template',
        string='Applied Template'
    )
    message_body = fields.Text(string='Message Content')

    # Media / Attachment Handling
    media_type = fields.Selection(
        [
            ('document', 'Document (PDF/DOC)'),
            ('image', 'Image'),
            ('video', 'Video'),
            ('audio', 'Audio'),
        ],
        string='Media Type'
    )
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Attached File'
    )
    media_url = fields.Char(string='Media URL')
    interactive_payload = fields.Text(string='Interactive Payload (JSON)')

    # Meta Tracking Identifiers
    meta_message_id = fields.Char(
        string='Meta Message ID (WAMID)',
        index=True,
        readonly=True,
        copy=False
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('queued', 'In Queue'),
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('read', 'Read'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        tracking=True,
        index=True
    )

    # Retry and Error Tracking
    retry_count = fields.Integer(string='Retry Count', default=0)
    max_retries = fields.Integer(string='Max Retries', default=3)
    last_error = fields.Text(string='Last Error Trace')
    scheduled_date = fields.Datetime(
        string='Scheduled Send Time',
        default=fields.Datetime.now
    )
    sent_date = fields.Datetime(string='Sent Date', readonly=True)

    # Related ERP Record Binding
    model_name = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related Record ID')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('whatsapp.message.queue') or _('WA-%s') % fields.Datetime.now().strftime('%Y%m%d%H%M%S')
            if 'recipient_phone' in vals and vals['recipient_phone']:
                vals['recipient_phone'] = self._sanitize_phone(vals['recipient_phone'])
        return super().create(vals_list)

    @api.model
    def _sanitize_phone(self, phone):
        """Sanitizes phone number into international format digits without spaces or plus."""
        if not phone:
            return ''
        cleaned = re.sub(r'[\s\-\(\)\+]', '', str(phone))
        return cleaned

    def action_enqueue(self):
        self.write({'state': 'queued'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_retry(self):
        for record in self:
            record.write({
                'state': 'queued',
                'retry_count': 0,
                'last_error': False
            })

    def action_send_now(self):
        """Dispatches the message immediately via Meta Cloud API service."""
        for record in self:
            record._send_single_message()

    def _send_single_message(self):
        self.ensure_one()
        api_service = self.env['whatsapp.api.service']
        account = self.account_id

        if not account or account.state != 'connected':
            error_msg = _("WhatsApp account is missing or not connected.")
            self.write({'state': 'failed', 'last_error': error_msg})
            return False

        clean_to = self._sanitize_phone(self.recipient_phone)
        if not clean_to:
            error_msg = _("Invalid recipient phone number.")
            self.write({'state': 'failed', 'last_error': error_msg})
            return False

        try:
            response = None
            if self.message_type == 'text':
                response = api_service.send_text_message(
                    account=account,
                    to_phone=clean_to,
                    message_text=self.message_body
                )
            elif self.message_type == 'template' and self.template_id:
                # Find related record if available
                rec = None
                if self.model_name and self.res_id:
                    rec = self.env[self.model_name].browse(self.res_id)
                components = self.template_id.render_components(record=rec, custom_header_url=self.media_url)
                response = api_service.send_template_message(
                    account=account,
                    to_phone=clean_to,
                    template_name=self.template_id.name,
                    language_code=self.template_id.language_code,
                    components=components
                )
            elif self.message_type == 'media':
                media_link = self.media_url
                if self.attachment_id and not media_link:
                    # Upload media directly to Meta
                    file_bytes = self.attachment_id.raw
                    m_id = api_service.upload_media(
                        account=account,
                        file_bytes=file_bytes,
                        mime_type=self.attachment_id.mimetype,
                        filename=self.attachment_id.name
                    )
                    media_link = m_id

                response = api_service.send_media_message(
                    account=account,
                    to_phone=clean_to,
                    media_type=self.media_type or 'document',
                    media_id_or_url=media_link,
                    caption=self.message_body,
                    filename=self.attachment_id.name if self.attachment_id else 'Document.pdf'
                )
            elif self.message_type == 'interactive' and self.interactive_payload:
                payload_data = json.loads(self.interactive_payload)
                interactive_type = payload_data.get('type', 'button')
                if interactive_type == 'button':
                    response = api_service.send_interactive_buttons(
                        account=account,
                        to_phone=clean_to,
                        body_text=self.message_body or payload_data.get('body', ''),
                        buttons_list=payload_data.get('buttons', []),
                        header_text=payload_data.get('header'),
                        footer_text=payload_data.get('footer')
                    )
                elif interactive_type == 'list':
                    response = api_service.send_interactive_list(
                        account=account,
                        to_phone=clean_to,
                        body_text=self.message_body or payload_data.get('body', ''),
                        button_label=payload_data.get('button_label', 'Options'),
                        sections_list=payload_data.get('sections', []),
                        header_text=payload_data.get('header'),
                        footer_text=payload_data.get('footer')
                    )

            if response and 'messages' in response:
                wamid = response['messages'][0].get('id')
                self.write({
                    'state': 'sent',
                    'meta_message_id': wamid,
                    'sent_date': fields.Datetime.now(),
                    'last_error': False
                })
                # Log in Chat History
                self.env['whatsapp.chat.history'].create({
                    'account_id': account.id,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'sender_phone': account.display_phone_number or 'Business',
                    'receiver_phone': clean_to,
                    'direction': 'outbound',
                    'message_type': self.message_type,
                    'message_text': self.message_body or _('Template: %s') % (self.template_id.name if self.template_id else ''),
                    'meta_message_id': wamid,
                    'state': 'sent',
                    'model_name': self.model_name,
                    'res_id': self.res_id,
                })
                # Post in related record chatter
                if self.model_name and self.res_id:
                    rel_record = self.env[self.model_name].browse(self.res_id)
                    if hasattr(rel_record, 'message_post'):
                        rel_record.message_post(
                            body=_("<b>WhatsApp Sent</b> to %s: %s") % (clean_to, self.message_body or (self.template_id.name if self.template_id else 'Media File')),
                            subject=_("WhatsApp Notification Sent")
                        )
                return True
            else:
                self.write({
                    'state': 'failed',
                    'last_error': _('Unexpected response format from Meta: %s') % str(response)
                })
                return False

        except Exception as e:
            new_retries = self.retry_count + 1
            is_permanently_failed = new_retries >= self.max_retries
            self.write({
                'retry_count': new_retries,
                'state': 'failed' if is_permanently_failed else 'queued',
                'last_error': str(e)
            })
            _logger.warning("WhatsApp send failed for queue #%s (Attempt %d/%d): %s", self.id, new_retries, self.max_retries, str(e))
            return False

    @api.model
    def _cron_process_queue(self, batch_size=50):
        """Cron dispatcher processing queued messages with rate-limiting safety."""
        queued_records = self.search([
            ('state', '=', 'queued'),
            ('scheduled_date', '<=', fields.Datetime.now())
        ], limit=batch_size, order='sequence desc, id asc' if 'sequence' in self._fields else 'id asc')

        _logger.info("WhatsApp Queue Cron started: processing %d messages.", len(queued_records))
        for msg in queued_records:
            msg._send_single_message()
            # Commit after each message to maintain transactional integrity
            self.env.cr.commit()
