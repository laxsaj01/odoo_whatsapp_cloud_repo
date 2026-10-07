# -*- coding: utf-8 -*-
# Part of Smart AI Vendor Bill & Invoice OCR Automation.
# License: OPL-1.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    ocr_status = fields.Selection(
        [
            ('not_scanned', 'Not Scanned'),
            ('scanned', 'AI Scanned & Extracted'),
            ('failed', 'OCR Extraction Failed'),
        ],
        string='AI OCR Status',
        default='not_scanned',
        copy=False,
        readonly=True,
        tracking=True
    )
    ocr_confidence_score = fields.Float(
        string='AI Confidence Score',
        readonly=True,
        copy=False
    )
    ocr_raw_data = fields.Text(
        string='Raw Extracted JSON',
        readonly=True,
        copy=False
    )
    ocr_queue_id = fields.Many2one(
        'ai.ocr.queue',
        string='Source OCR Queue',
        readonly=True,
        copy=False
    )

    def action_scan_ai_ocr(self):
        """Scans the primary PDF or image attachment of this vendor bill using AI Vision."""
        self.ensure_one()
        if self.move_type not in ('in_invoice', 'in_refund', 'in_receipt'):
            raise UserError(_("AI OCR scanning is designed for vendor bills and purchase receipts."))

        # Look for attachments
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('mimetype', 'in', ['application/pdf', 'image/jpeg', 'image/png', 'image/webp'])
        ], order='id desc', limit=1)

        if not attachment:
            raise UserError(_("No valid PDF or image file found attached to this bill. Please attach an invoice file first."))

        provider = self.env['ai.ocr.provider'].search([
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'connected'),
            ('is_default', '=', True)
        ], limit=1)

        if not provider:
            provider = self.env['ai.ocr.provider'].search([
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'connected')
            ], limit=1)

        if not provider:
            raise UserError(_("No connected AI OCR Provider configured. Please configure an OpenAI or Claude API key in Settings > AI OCR Providers."))

        ocr_service = self.env['ai.ocr.service']
        try:
            ocr_data = ocr_service.extract_document_data(
                provider=provider,
                file_bytes=attachment.raw,
                mime_type=attachment.mimetype,
                filename=attachment.name
            )

            auto_partner = self.env['ir.config_parameter'].sudo().get_param('ai_invoice_ocr.auto_create_partner', True)
            ocr_service.populate_vendor_bill(move=self, ocr_data=ocr_data, auto_create_partner=auto_partner)

            self.message_post(
                body=_("<b>AI Vision OCR Scan Succeeded:</b> Extracted line items and partner details using %s (%s). Confidence: %.1f%%") % (
                    provider.name, provider.model_name, (self.ocr_confidence_score * 100)
                )
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('AI Extraction Completed'),
                    'message': _('Vendor bill line items and details populated successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            self.write({'ocr_status': 'failed'})
            _logger.exception("AI OCR scanning failed on move %s: %s", self.name, str(e))
            raise UserError(_("AI Document OCR Failed:\n\n%s") % str(e))

    def action_open_ocr_wizard(self):
        """Opens wizard to upload and process a new bill document."""
        self.ensure_one()
        return {
            'name': _('Scan Invoice with AI'),
            'type': 'ir.actions.act_window',
            'res_model': 'ai.invoice.ocr.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
            }
        }
