# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# License: OPL-1.

import secrets
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WhatsAppAccount(models.Model):
    _name = 'whatsapp.account'
    _description = 'Meta WhatsApp Business Account Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id desc'

    name = fields.Char(
        string='Account Name',
        required=True,
        tracking=True,
        help='Descriptive identifier for this WhatsApp account (e.g. Head Office Support, Sales Team).'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True
    )
    active = fields.Boolean(string='Active', default=True)

    # Meta Graph API Credentials
    phone_number_id = fields.Char(
        string='Phone Number ID',
        required=True,
        tracking=True,
        help='Unique Phone Number ID assigned by Meta Business Manager under WhatsApp > API Setup.'
    )
    waba_id = fields.Char(
        string='WhatsApp Business Account (WABA) ID',
        required=True,
        tracking=True,
        help='Meta WhatsApp Business Account ID.'
    )
    app_id = fields.Char(
        string='Meta App ID',
        help='Meta Developer App ID associated with the Cloud API.'
    )
    app_secret = fields.Char(
        string='Meta App Secret',
        help='Meta Developer App Secret used to verify HMAC-SHA256 webhook signatures.'
    )
    access_token = fields.Char(
        string='Permanent Access Token',
        required=True,
        help='Permanent System User Access Token generated in Meta Business Manager with whatsapp_business_messaging & whatsapp_business_management permissions.'
    )
    graph_api_version = fields.Selection(
        [
            ('v20.0', 'Graph API v20.0'),
            ('v21.0', 'Graph API v21.0 (Latest)'),
            ('v22.0', 'Graph API v22.0'),
        ],
        string='Graph API Version',
        default='v21.0',
        required=True
    )

    # Webhook Verification
    webhook_verify_token = fields.Char(
        string='Webhook Verify Token',
        required=True,
        default=lambda self: secrets.token_hex(16),
        copy=False,
        help='Random token configured in Meta App Dashboard > WhatsApp > Configuration > Callback URL verification.'
    )
    webhook_callback_url = fields.Char(
        string='Webhook Callback URL',
        compute='_compute_webhook_callback_url',
        help='Full endpoint URL to paste into Meta Developer Portal.'
    )

    # Operational Status
    state = fields.Selection(
        [
            ('draft', 'Not Verified'),
            ('connected', 'Connected & Active'),
            ('error', 'Connection Error'),
        ],
        string='Status',
        default='draft',
        tracking=True
    )
    display_phone_number = fields.Char(
        string='Verified Phone Number',
        readonly=True,
        help='Phone number retrieved from Meta upon successful connection verification.'
    )
    quality_rating = fields.Selection(
        [
            ('GREEN', 'High (Green)'),
            ('YELLOW', 'Medium (Yellow)'),
            ('RED', 'Low (Red)'),
            ('NA', 'Not Applicable / Unknown'),
        ],
        string='Phone Quality Rating',
        readonly=True,
        default='NA'
    )
    code_verification_status = fields.Char(
        string='Verification Status',
        readonly=True
    )

    # Failover & Queue Settings
    auto_retry_failed = fields.Boolean(
        string='Auto-Retry Failed Messages',
        default=True,
        help='Automatically retry transient failures (HTTP 429, timeout) via scheduled background cron.'
    )
    max_retry_count = fields.Integer(
        string='Maximum Retries',
        default=3,
        help='Maximum attempts before marking message permanently failed.'
    )

    # Relational Links
    template_ids = fields.One2many(
        'whatsapp.template',
        'account_id',
        string='WhatsApp Templates'
    )
    template_count = fields.Integer(
        string='Template Count',
        compute='_compute_template_count'
    )
    queue_count = fields.Integer(
        string='Queued Messages',
        compute='_compute_queue_count'
    )

    @api.depends('template_ids')
    def _compute_template_count(self):
        for record in self:
            record.template_count = len(record.template_ids)

    def _compute_queue_count(self):
        queue_obj = self.env['whatsapp.message.queue']
        for record in self:
            record.queue_count = queue_obj.search_count([
                ('account_id', '=', record.id),
                ('state', 'in', ['draft', 'queued'])
            ])

    def _compute_webhook_callback_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for record in self:
            record.webhook_callback_url = f"{base_url.rstrip('/')}/whatsapp/webhook/{record.id}"

    def action_generate_new_verify_token(self):
        """Regenerate a secure random verify token."""
        for record in self:
            record.webhook_verify_token = secrets.token_hex(16)
        return True

    def action_test_connection(self):
        """Validate credentials against Meta Graph API and update live account state."""
        self.ensure_one()
        api_service = self.env['whatsapp.api.service']
        try:
            result = api_service.test_connection(self)
            self.write({
                'state': 'connected',
                'display_phone_number': result.get('display_phone_number') or self.display_phone_number,
                'quality_rating': result.get('quality_rating') or 'NA',
                'code_verification_status': result.get('code_verification_status') or 'VERIFIED',
            })
            self.message_post(
                body=_("WhatsApp Cloud API connection test succeeded. Verified Number: %s, Quality Rating: %s") % (
                    self.display_phone_number, self.quality_rating
                )
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Succeeded'),
                    'message': _('Successfully connected to Meta WhatsApp Cloud API! Number: %s') % self.display_phone_number,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            self.write({'state': 'error'})
            _logger.error("WhatsApp Connection Test Failed: %s", str(e))
            raise UserError(_("Connection failed with Meta Cloud API:\n\n%s") % str(e))

    def action_sync_templates(self):
        """Fetch and synchronize all approved templates from Meta WABA."""
        self.ensure_one()
        if self.state != 'connected':
            raise UserError(_("Please test and establish a verified connection before synchronizing templates."))
        api_service = self.env['whatsapp.api.service']
        synced_count = api_service.sync_meta_templates(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Template Sync Complete'),
                'message': _('Successfully synchronized %d templates from Meta Cloud API.') % synced_count,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_templates(self):
        self.ensure_one()
        return {
            'name': _('WhatsApp Templates'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.template',
            'view_mode': 'tree,form',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id},
        }

    def action_view_queue(self):
        self.ensure_one()
        return {
            'name': _('Message Queue'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.message.queue',
            'view_mode': 'tree,form',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id},
        }
