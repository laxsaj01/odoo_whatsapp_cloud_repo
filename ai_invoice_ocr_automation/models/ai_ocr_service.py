# -*- coding: utf-8 -*-
# Part of Smart AI Vendor Bill & Invoice OCR Automation.
# License: OPL-1.

import base64
import json
import re
import logging
import requests
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an elite accounting and enterprise ERP document analysis engine.
Analyze this invoice or receipt image/document with 100% precision.
Extract every single field and tabular line item into the following strict JSON schema.

JSON Schema:
{
  "vendor": {
    "name": "Supplier or Vendor business name",
    "vat": "Tax ID, VAT number, GST, or NTN if present, else empty",
    "phone": "Phone number if present, else empty",
    "email": "Email address if present, else empty",
    "address": "Full billing or supplier street address if present, else empty"
  },
  "invoice": {
    "number": "Invoice reference, bill number, or receipt code",
    "date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD (or same as date if not specified)",
    "currency": "Standard 3-letter currency code (e.g. USD, EUR, SAR, AED, PKR, GBP)"
  },
  "lines": [
    {
      "description": "Item description or product name",
      "quantity": 1.0,
      "unit_price": 10.0,
      "tax_percentage": 0.0,
      "subtotal": 10.0
    }
  ],
  "totals": {
    "untaxed_amount": 0.0,
    "tax_amount": 0.0,
    "total_amount": 0.0
  },
  "confidence_score": 0.98
}

Instructions:
1. Ensure all numerical values are plain floats (no currency symbols or commas).
2. Date must strictly be in YYYY-MM-DD format.
3. If multiple line items exist in a table, extract EVERY line item individually without skipping.
4. Output STRICTLY valid JSON only. Do not include markdown wraps or conversational text.
"""


class AiOcrService(models.AbstractModel):
    _name = 'ai.ocr.service'
    _description = 'AI Vision Document Extraction Service'

    def extract_document_data(self, provider, file_bytes, mime_type='application/pdf', filename='invoice.pdf'):
        """Dispatches document to selected AI vision engine and parses structured JSON response."""
        b64_data = base64.b64encode(file_bytes).decode('utf-8')
        raw_text = ''

        if provider.provider == 'openai':
            raw_text = self._call_openai(provider, b64_data, mime_type)
        elif provider.provider == 'anthropic':
            raw_text = self._call_anthropic(provider, b64_data, mime_type)
        elif provider.provider == 'gemini':
            raw_text = self._call_gemini(provider, b64_data, mime_type)
        else:
            raise UserError(_("Unsupported AI Provider: %s") % provider.provider)

        return self._clean_and_parse_json(raw_text)

    def _call_openai(self, provider, b64_data, mime_type):
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {provider.api_key.strip()}',
            'Content-Type': 'application/json'
        }
        # For OpenAI, image format data URL
        image_url = f"data:{mime_type};base64,{b64_data}"
        payload = {
            "model": provider.model_name or "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": SYSTEM_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 4096
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if not resp.ok:
            raise UserError(_("OpenAI API Error [%d]: %s") % (resp.status_code, resp.text))
        res_json = resp.json()
        return res_json['choices'][0]['message']['content']

    def _call_anthropic(self, provider, b64_data, mime_type):
        url = 'https://api.anthropic.com/v1/messages'
        headers = {
            'x-api-key': provider.api_key.strip(),
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        # Anthropic vision media type mapping
        a_mime = mime_type if mime_type in ['image/jpeg', 'image/png', 'image/gif', 'image/webp'] else 'image/jpeg'
        payload = {
            "model": provider.model_name or "claude-3-5-sonnet-20241022",
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": a_mime,
                                "data": b64_data
                            }
                        },
                        {"type": "text", "text": SYSTEM_PROMPT}
                    ]
                }
            ]
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if not resp.ok:
            raise UserError(_("Anthropic API Error [%d]: %s") % (resp.status_code, resp.text))
        res_json = resp.json()
        return res_json['content'][0]['text']

    def _call_gemini(self, provider, b64_data, mime_type):
        model = provider.model_name or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={provider.api_key.strip()}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_data
                        }
                    }
                ]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if not resp.ok:
            raise UserError(_("Gemini API Error [%d]: %s") % (resp.status_code, resp.text))
        res_json = resp.json()
        return res_json['candidates'][0]['content']['parts'][0]['text']

    def _clean_and_parse_json(self, raw_str):
        """Sanitizes raw AI response text and extracts valid dictionary."""
        cleaned = raw_str.strip()
        if '```json' in cleaned:
            cleaned = cleaned.split('```json')[-1].split('```')[0].strip()
        elif '```' in cleaned:
            cleaned = cleaned.split('```')[1].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            _logger.error("Failed to decode AI OCR JSON: %s | Raw: %s", str(e), raw_str)
            raise UserError(_("AI vision model returned invalid JSON structure. Please re-try scanning."))

    def populate_vendor_bill(self, move, ocr_data, auto_create_partner=True):
        """Maps extracted JSON schema fields directly into Odoo account.move and lines."""
        move.ensure_one()
        partner_obj = self.env['res.partner']
        tax_obj = self.env['account.tax']
        currency_obj = self.env['res.currency']

        vendor_data = ocr_data.get('vendor', {})
        inv_data = ocr_data.get('invoice', {})
        lines_data = ocr_data.get('lines', [])

        # 1. Resolve Partner
        partner = False
        v_vat = (vendor_data.get('vat') or '').strip()
        v_name = (vendor_data.get('name') or '').strip()
        v_email = (vendor_data.get('email') or '').strip()
        v_phone = (vendor_data.get('phone') or '').strip()

        if v_vat:
            partner = partner_obj.search([('vat', '=', v_vat)], limit=1)
        if not partner and v_email:
            partner = partner_obj.search([('email', '=', v_email)], limit=1)
        if not partner and v_phone:
            clean_phone = re.sub(r'[\s\-\(\)\+]', '', v_phone)
            partner = partner_obj.search(['|', ('phone', 'like', clean_phone), ('mobile', 'like', clean_phone)], limit=1)
        if not partner and v_name:
            partner = partner_obj.search([('name', '=ilike', v_name)], limit=1)

        if not partner and auto_create_partner and v_name:
            partner = partner_obj.create({
                'name': v_name,
                'vat': v_vat or False,
                'email': v_email or False,
                'phone': v_phone or False,
                'street': vendor_data.get('address') or False,
                'supplier_rank': 1,
                'company_id': move.company_id.id,
            })

        # 2. Resolve Currency
        curr_code = (inv_data.get('currency') or '').strip().upper()
        currency = currency_obj.search([('name', '=', curr_code)], limit=1) if curr_code else move.currency_id

        # 3. Update Move Header
        header_vals = {
            'ref': inv_data.get('number') or move.ref,
            'ocr_status': 'scanned',
            'ocr_confidence_score': ocr_data.get('confidence_score', 0.95),
            'ocr_raw_data': json.dumps(ocr_data, indent=2),
        }
        if partner:
            header_vals['partner_id'] = partner.id
        if inv_data.get('date'):
            header_vals['invoice_date'] = inv_data.get('date')
        if inv_data.get('due_date'):
            header_vals['invoice_date_due'] = inv_data.get('due_date')
        if currency:
            header_vals['currency_id'] = currency.id

        move.write(header_vals)

        # 4. Resolve Default Expense Account
        expense_account = move.journal_id.default_account_id
        if not expense_account:
            expense_account = self.env['account.account'].search([
                ('company_id', '=', move.company_id.id),
                ('account_type', '=', 'expense')
            ], limit=1)

        # 5. Populate Invoice Lines
        # Unlink existing lines to prevent duplicates
        move.invoice_line_ids.unlink()

        line_commands = []
        for line in lines_data:
            desc = line.get('description') or _('Expense Item')
            qty = float(line.get('quantity') or 1.0)
            price = float(line.get('unit_price') or 0.0)
            tax_rate = float(line.get('tax_percentage') or 0.0)

            tax_ids = []
            if tax_rate > 0:
                matching_tax = tax_obj.search([
                    ('company_id', '=', move.company_id.id),
                    ('type_tax_use', '=', 'purchase'),
                    ('amount', '=', tax_rate)
                ], limit=1)
                if matching_tax:
                    tax_ids = [matching_tax.id]

            line_vals = {
                'name': desc,
                'quantity': qty,
                'price_unit': price,
                'account_id': expense_account.id if expense_account else False,
                'tax_ids': [(6, 0, tax_ids)] if tax_ids else False,
            }
            line_commands.append((0, 0, line_vals))

        if line_commands:
            move.write({'invoice_line_ids': line_commands})

        return True
