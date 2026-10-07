# -*- coding: utf-8 -*-
# Part of Smart AI Vendor Bill & Invoice OCR Automation.
# License: OPL-1.

import base64
import mimetypes
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AiInvoiceOcrWizard(models.TransientModel):
    _name = 'ai.invoice.ocr.wizard'
    _description = 'Interactive AI Invoice OCR Upload Wizard'

    file_data = fields.Binary(
        string='Invoice Document (PDF / Image)',
        required=True,
        help='Upload invoice PDF, scanned receipt, JPG, or PNG document.'
    )
    file_name = fields.Char(string='Filename', required=True)
    provider_id = fields.Many2one(
        'ai.ocr.provider',
        string='AI Engine',
        required=True,
        domain="[('state', '=', 'connected')]",
        default=lambda self: self._default_provider_id()
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Purchase Journal',
        domain="[('type', '=', 'purchase')]",
        default=lambda self: self._default_journal_id()
    )
    move_id = fields.Many2one(
        'account.move',
        string='Target Bill'
    )
    execution_mode = fields.Selection(
        [
            ('immediate', 'Scan & Open Immediately'),
            ('queue', 'Add to Background Queue'),
        ],
        string='Processing Mode',
        default='immediate',
        required=True
    )

    def _default_provider_id(self):
        prov = self.env['ai.ocr.provider'].search([
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'connected'),
            ('is_default', '=', True)
        ], limit=1)
        if not prov:
            prov = self.env['ai.ocr.provider'].search([
                ('company_id', '=', self.env.company.id),
                ('state', '=', 'connected')
            ], limit=1)
        return prov.id if prov else False

    def _default_journal_id(self):
        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return journal.id if journal else False

    def action_process(self):
        """Processes the uploaded invoice file either synchronously or via queue."""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("Please upload an invoice document."))

        raw_bytes = base64.b64decode(self.file_data)
        mime_type, _ = mimetypes.guess_type(self.file_name or '')
        if not mime_type:
            mime_type = 'application/pdf' if (self.file_name or '').lower().endswith('.pdf') else 'image/jpeg'

        # Create persistent attachment
        attachment = self.env['ir.attachment'].create({
            'name': self.file_name,
            'type': 'binary',
            'raw': raw_bytes,
            'mimetype': mime_type,
        })

        if self.execution_mode == 'queue':
            queue_item = self.env['ai.ocr.queue'].create({
                'attachment_id': attachment.id,
                'provider_id': self.provider_id.id,
                'company_id': self.env.company.id,
                'move_id': self.move_id.id if self.move_id else False,
                'state': 'queued',
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Document Enqueued'),
                    'message': _('Invoice %s added to background AI extraction queue.') % self.file_name,
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Immediate Processing
        ocr_service = self.env['ai.ocr.service']
        try:
            ocr_data = ocr_service.extract_document_data(
                provider=self.provider_id,
                file_bytes=raw_bytes,
                mime_type=mime_type,
                filename=self.file_name
            )

            move = self.move_id
            if not move:
                move = self.env['account.move'].create({
                    'move_type': 'in_invoice',
                    'journal_id': self.journal_id.id if self.journal_id else False,
                    'company_id': self.env.company.id,
                })

            # Link attachment to the move
            attachment.write({
                'res_model': 'account.move',
                'res_id': move.id,
            })

            auto_partner = self.env['ir.config_parameter'].sudo().get_param('ai_invoice_ocr.auto_create_partner', True)
            ocr_service.populate_vendor_bill(move=move, ocr_data=ocr_data, auto_create_partner=auto_partner)

            return {
                'name': _('Extracted Vendor Bill'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': move.id,
                'view_mode': 'form',
                'target': 'current',
            }

        except Exception as e:
            _logger.exception("AI OCR extraction failed in wizard: %s", str(e))
            raise UserError(_("AI Document OCR Failed:\n\n%s") % str(e))
