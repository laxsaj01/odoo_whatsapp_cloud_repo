# -*- coding: utf-8 -*-
# Part of Smart AI Vendor Bill & Invoice OCR Automation.
# License: OPL-1.

import logging
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AiOcrProvider(models.Model):
    _name = 'ai.ocr.provider'
    _description = 'AI Vision OCR Engine Provider Configuration'
    _inherit = ['mail.thread']
    _order = 'is_default desc, id desc'

    name = fields.Char(
        string='Provider Profile Name',
        required=True,
        tracking=True,
        help='Identifier for this AI engine profile (e.g. OpenAI GPT-4o Vision, Anthropic Claude).'
    )
    provider = fields.Selection(
        [
            ('openai', 'OpenAI (GPT-4o / GPT-4o-mini)'),
            ('anthropic', 'Anthropic (Claude 3.5 Sonnet)'),
            ('gemini', 'Google (Gemini 1.5 Pro / Flash)'),
        ],
        string='AI Engine Architecture',
        default='openai',
        required=True,
        tracking=True
    )
    api_key = fields.Char(
        string='API Secret Key',
        required=True,
        help='Your private API key from OpenAI Platform, Anthropic Console, or Google AI Studio.'
    )
    model_name = fields.Selection(
        [
            ('gpt-4o', 'GPT-4o (Highest Accuracy & Speed)'),
            ('gpt-4o-mini', 'GPT-4o-mini (Ultra Low Cost: ~$0.003/bill)'),
            ('claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet (State of the Art)'),
            ('gemini-1.5-flash', 'Gemini 1.5 Flash (Ultra Fast)'),
            ('gemini-1.5-pro', 'Gemini 1.5 Pro (Deep Document Reasoning)'),
        ],
        string='Vision Model',
        default='gpt-4o',
        required=True
    )
    is_default = fields.Boolean(
        string='Default Provider',
        default=False,
        help='Default engine utilized for automated vendor bill scanning.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    state = fields.Selection(
        [
            ('draft', 'Not Verified'),
            ('connected', 'Connected & Verified'),
            ('error', 'Authentication Error'),
        ],
        string='Status',
        default='draft',
        tracking=True
    )
    last_test_date = fields.Datetime(string='Last Verified At', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_default'):
                self.search([('company_id', '=', vals.get('company_id', self.env.company.id))]).write({'is_default': False})
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('is_default'):
            self.search([
                ('id', '!=', self.id),
                ('company_id', '=', vals.get('company_id', self.company_id.id))
            ]).write({'is_default': False})
        return super().write(vals)

    def action_test_connection(self):
        """Verifies API key credentials against the selected provider."""
        self.ensure_one()
        if not self.api_key:
            raise UserError(_("Please provide a valid API Secret Key."))

        headers = {}
        payload = {}
        test_url = ''

        try:
            if self.provider == 'openai':
                test_url = 'https://api.openai.com/v1/models'
                headers = {'Authorization': f'Bearer {self.api_key.strip()}'}
                resp = requests.get(test_url, headers=headers, timeout=15)
            elif self.provider == 'anthropic':
                test_url = 'https://api.anthropic.com/v1/messages'
                headers = {
                    'x-api-key': self.api_key.strip(),
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json'
                }
                payload = {
                    'model': 'claude-3-5-sonnet-20241022',
                    'max_tokens': 5,
                    'messages': [{'role': 'user', 'content': 'ping'}]
                }
                resp = requests.post(test_url, headers=headers, json=payload, timeout=15)
            elif self.provider == 'gemini':
                test_url = f'https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key.strip()}'
                resp = requests.get(test_url, timeout=15)

            if resp.ok:
                self.write({
                    'state': 'connected',
                    'last_test_date': fields.Datetime.now()
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Succeeded'),
                        'message': _('Successfully authenticated with %s (%s)!') % (self.provider.upper(), self.model_name),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                self.write({'state': 'error'})
                err_msg = resp.text
                try:
                    err_json = resp.json()
                    err_msg = err_json.get('error', {}).get('message') or resp.text
                except Exception:
                    pass
                raise UserError(_("Authentication failed with %s [Status %d]:\n\n%s") % (self.provider.upper(), resp.status_code, err_msg))

        except requests.exceptions.RequestException as e:
            self.write({'state': 'error'})
            raise UserError(_("Network error connecting to %s: %s") % (self.provider.upper(), str(e)))
