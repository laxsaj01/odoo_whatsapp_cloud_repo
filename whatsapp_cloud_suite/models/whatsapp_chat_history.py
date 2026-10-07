# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# License: OPL-1.

from odoo import models, fields, api, _


class WhatsAppChatHistory(models.Model):
    _name = 'whatsapp.chat.history'
    _description = 'WhatsApp Live Chat History & Audit Trail'
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Subject',
        compute='_compute_name',
        store=True
    )
    account_id = fields.Many2one(
        'whatsapp.account',
        string='WhatsApp Account',
        required=True,
        ondelete='cascade'
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
        string='Customer / Contact',
        index=True
    )
    sender_phone = fields.Char(string='Sender Number', required=True)
    receiver_phone = fields.Char(string='Receiver Number', required=True)
    direction = fields.Selection(
        [
            ('inbound', 'Inbound (Received)'),
            ('outbound', 'Outbound (Sent)'),
        ],
        string='Direction',
        required=True,
        default='outbound'
    )
    message_type = fields.Selection(
        [
            ('text', 'Text'),
            ('template', 'Template'),
            ('document', 'Document'),
            ('image', 'Image'),
            ('video', 'Video'),
            ('audio', 'Audio'),
            ('location', 'Location'),
            ('interactive', 'Interactive Menu'),
            ('button_reply', 'Button Response'),
            ('list_reply', 'List Selection'),
        ],
        string='Message Type',
        default='text'
    )
    message_text = fields.Text(string='Message Content')
    media_url = fields.Char(string='Media URL')
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Stored Attachment'
    )
    meta_message_id = fields.Char(
        string='Meta Message ID (WAMID)',
        index=True
    )
    state = fields.Selection(
        [
            ('received', 'Received'),
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('read', 'Read (Blue Tick)'),
            ('failed', 'Failed'),
        ],
        string='Delivery Status',
        default='sent',
        index=True
    )

    # CRM / ERP Context Reference
    model_name = fields.Char(string='Source Model')
    res_id = fields.Integer(string='Source Record ID')
    channel_id = fields.Many2one(
        'discuss.channel',
        string='Linked Discuss Channel'
    )

    @api.depends('direction', 'sender_phone', 'receiver_phone', 'message_type')
    def _compute_name(self):
        for record in self:
            dir_label = "IN" if record.direction == 'inbound' else "OUT"
            target = record.sender_phone if record.direction == 'inbound' else record.receiver_phone
            record.name = f"[{dir_label}] {target} ({record.message_type or 'text'})"

    def action_open_record(self):
        self.ensure_one()
        if self.model_name and self.res_id:
            return {
                'name': _('Source Record'),
                'type': 'ir.actions.act_window',
                'res_model': self.model_name,
                'res_id': self.res_id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False
