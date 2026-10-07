# -*- coding: utf-8 -*-
# Part of Smart AI Vendor Bill & Invoice OCR Automation.
# License: OPL-1.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AiOcrQueue(models.Model):
    _name = 'ai.ocr.queue'
    _description = 'Asynchronous AI OCR Processing Queue'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(
        string='Queue Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Source Document',
        required=True,
        ondelete='cascade'
    )
    file_name = fields.Char(related='attachment_id.name', string='Filename', readonly=True)
    provider_id = fields.Many2one(
        'ai.ocr.provider',
        string='AI Engine Profile',
        required=True,
        domain="[('state', '=', 'connected')]"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    move_id = fields.Many2one(
        'account.move',
        string='Generated Vendor Bill',
        readonly=True
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('queued', 'In Queue'),
            ('processing', 'Processing (AI Vision)'),
            ('done', 'Completed'),
            ('failed', 'Extraction Failed'),
        ],
        string='Status',
        default='queued',
        tracking=True,
        index=True
    )
    confidence_score = fields.Float(string='Confidence Score', readonly=True)
    raw_json = fields.Text(string='Extracted JSON Payload', readonly=True)
    error_log = fields.Text(string='Processing Error Log', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ai.ocr.queue') or _('OCR-%s') % fields.Datetime.now().strftime('%Y%m%d%H%M%S')
        return super().create(vals_list)

    def action_retry(self):
        self.write({'state': 'queued', 'error_log': False})

    def action_process_now(self):
        """Immediately triggers AI extraction and creates vendor bill."""
        for record in self:
            record._process_single_queue()

    def _process_single_queue(self):
        self.ensure_one()
        self.write({'state': 'processing'})
        ocr_service = self.env['ai.ocr.service']

        try:
            # 1. Extract JSON via AI Service
            file_bytes = self.attachment_id.raw
            ocr_data = ocr_service.extract_document_data(
                provider=self.provider_id,
                file_bytes=file_bytes,
                mime_type=self.attachment_id.mimetype or 'application/pdf',
                filename=self.attachment_id.name
            )

            # 2. Create or Update Vendor Bill
            move = self.move_id
            if not move:
                journal = self.env['account.journal'].search([
                    ('type', '=', 'purchase'),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
                move_vals = {
                    'move_type': 'in_invoice',
                    'journal_id': journal.id if journal else False,
                    'company_id': self.company_id.id,
                    'ocr_queue_id': self.id,
                }
                move = self.env['account.move'].create(move_vals)
                self.write({'move_id': move.id})

            # Attach original document to the vendor bill
            self.attachment_id.write({
                'res_model': 'account.move',
                'res_id': move.id,
            })

            # 3. Populate bill fields and line items
            auto_partner = self.env['ir.config_parameter'].sudo().get_param('ai_invoice_ocr.auto_create_partner', True)
            ocr_service.populate_vendor_bill(move=move, ocr_data=ocr_data, auto_create_partner=auto_partner)

            self.write({
                'state': 'done',
                'confidence_score': ocr_data.get('confidence_score', 0.95),
                'raw_json': str(ocr_data),
                'error_log': False
            })

            move.message_post(
                body=_("<b>AI OCR Completed:</b> Extracted using %s (%s). Confidence: %.1f%%") % (
                    self.provider_id.name, self.provider_id.model_name, (self.confidence_score * 100)
                )
            )
            return True

        except Exception as e:
            _logger.exception("OCR Queue Processing failed for #%s: %s", self.id, str(e))
            self.write({
                'state': 'failed',
                'error_log': str(e)
            })
            return False

    @api.model
    def _cron_process_queue(self, limit=10):
        """Processes queued documents in background batch."""
        queued_records = self.search([('state', '=', 'queued')], limit=limit, order='id asc')
        _logger.info("AI OCR Queue Cron started: %d items to process.", len(queued_records))
        for item in queued_records:
            item._process_single_queue()
            self.env.cr.commit()

    def action_view_move(self):
        self.ensure_one()
        if self.move_id:
            return {
                'name': _('Generated Vendor Bill'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.move_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False
