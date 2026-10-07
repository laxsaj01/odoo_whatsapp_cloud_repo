# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# License: OPL-1.

import json
import logging
import requests
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com"


class WhatsAppApiService(models.AbstractModel):
    _name = 'whatsapp.api.service'
    _description = 'Meta WhatsApp Graph API Service Client'

    def _get_headers(self, access_token, content_type='application/json'):
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        if content_type:
            headers['Content-Type'] = content_type
        return headers

    def _build_url(self, account, path):
        version = account.graph_api_version or 'v21.0'
        clean_path = path.lstrip('/')
        return f"{GRAPH_API_BASE}/{version}/{clean_path}"

    def _send_request(self, method, url, headers, json_data=None, data=None, files=None, timeout=30):
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                data=data,
                files=files,
                timeout=timeout
            )
            response_json = {}
            try:
                response_json = response.json()
            except ValueError:
                pass

            if not response.ok:
                error_msg = response_json.get('error', {}).get('message') or response.text
                error_code = response_json.get('error', {}).get('code', response.status_code)
                error_subcode = response_json.get('error', {}).get('error_subcode', '')
                error_detail = f"Meta Graph API Error [Code {error_code} | Subcode {error_subcode}]: {error_msg}"
                _logger.error("WhatsApp API Call failed: %s | Payload: %s", error_detail, json_data)
                raise UserError(_(error_detail))

            return response_json
        except requests.exceptions.Timeout:
            _logger.error("Timeout connecting to Meta Graph API (%s)", url)
            raise UserError(_("Connection to Meta Graph API timed out. Please check your internet connectivity."))
        except requests.exceptions.ConnectionError:
            _logger.error("Connection error reaching Meta Graph API (%s)", url)
            raise UserError(_("Could not connect to Meta Graph API. Please verify network access to graph.facebook.com."))

    def test_connection(self, account):
        """Verifies phone number ID and retrieves live quality rating and display phone."""
        url = self._build_url(account, f"{account.phone_number_id}?fields=display_phone_number,verified_name,quality_rating,code_verification_status")
        headers = self._get_headers(account.access_token)
        return self._send_request('GET', url, headers)

    def sync_meta_templates(self, account):
        """Fetches all templates from the WhatsApp Business Account and updates Odoo."""
        url = self._build_url(account, f"{account.waba_id}/message_templates?limit=100")
        headers = self._get_headers(account.access_token)
        result = self._send_request('GET', url, headers)
        templates_data = result.get('data', [])

        template_obj = self.env['whatsapp.template'].sudo()
        synced_count = 0

        for tmpl in templates_data:
            meta_id = tmpl.get('id')
            name = tmpl.get('name')
            language = tmpl.get('language')
            status = tmpl.get('status', 'PENDING')
            category = tmpl.get('category', 'UTILITY')
            components = tmpl.get('components', [])

            body_text = ''
            header_type = 'none'
            header_text = ''
            footer_text = ''
            buttons_payload = []

            for comp in components:
                c_type = comp.get('type')
                if c_type == 'BODY':
                    body_text = comp.get('text', '')
                elif c_type == 'HEADER':
                    header_format = comp.get('format', 'TEXT')
                    header_type = header_format.lower()
                    if header_type == 'text':
                        header_text = comp.get('text', '')
                elif c_type == 'FOOTER':
                    footer_text = comp.get('text', '')
                elif c_type == 'BUTTONS':
                    buttons_payload = comp.get('buttons', [])

            existing = template_obj.search([
                ('meta_template_id', '=', meta_id),
                ('account_id', '=', account.id)
            ], limit=1)

            vals = {
                'name': name,
                'meta_template_id': meta_id,
                'language_code': language,
                'category': category,
                'state': status.lower() if status.lower() in ['approved', 'rejected', 'paused', 'pending'] else 'pending',
                'body_text': body_text,
                'header_type': header_type,
                'header_text': header_text,
                'footer_text': footer_text,
                'account_id': account.id,
                'company_id': account.company_id.id,
            }

            if existing:
                existing.write(vals)
                record = existing
            else:
                record = template_obj.create(vals)

            # Sync buttons
            record.button_ids.unlink()
            for b_idx, btn in enumerate(buttons_payload):
                b_type = btn.get('type', 'QUICK_REPLY').lower()
                b_text = btn.get('text', '')
                b_url = btn.get('url', '')
                b_phone = btn.get('phone_number', '')
                self.env['whatsapp.template.button'].create({
                    'template_id': record.id,
                    'sequence': b_idx + 1,
                    'button_type': b_type,
                    'name': b_text,
                    'url': b_url,
                    'phone_number': b_phone,
                })

            synced_count += 1

        return synced_count

    def send_text_message(self, account, to_phone, message_text, preview_url=False):
        """Dispatches standard text message to recipient."""
        url = self._build_url(account, f"{account.phone_number_id}/messages")
        headers = self._get_headers(account.access_token)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": message_text
            }
        }
        return self._send_request('POST', url, headers, json_data=payload)

    def send_template_message(self, account, to_phone, template_name, language_code, components=None):
        """Sends an approved WhatsApp template with dynamic component parameters."""
        url = self._build_url(account, f"{account.phone_number_id}/messages")
        headers = self._get_headers(account.access_token)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        if components:
            payload["template"]["components"] = components
        return self._send_request('POST', url, headers, json_data=payload)

    def send_media_message(self, account, to_phone, media_type, media_id_or_url, caption=None, filename=None):
        """Sends document, image, video, or audio message."""
        url = self._build_url(account, f"{account.phone_number_id}/messages")
        headers = self._get_headers(account.access_token)
        media_payload = {}
        if media_id_or_url.startswith('http://') or media_id_or_url.startswith('https://'):
            media_payload["link"] = media_id_or_url
        else:
            media_payload["id"] = media_id_or_url

        if caption and media_type in ['image', 'video', 'document']:
            media_payload["caption"] = caption
        if filename and media_type == 'document':
            media_payload["filename"] = filename

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": media_type,
            media_type: media_payload
        }
        return self._send_request('POST', url, headers, json_data=payload)

    def upload_media(self, account, file_bytes, mime_type, filename):
        """Uploads a binary media file to Meta Cloud API and returns the media_id."""
        url = self._build_url(account, f"{account.phone_number_id}/media")
        headers = self._get_headers(account.access_token, content_type=None)
        files = {
            'file': (filename, file_bytes, mime_type),
        }
        data = {
            'messaging_product': 'whatsapp',
            'type': mime_type,
        }
        result = self._send_request('POST', url, headers, data=data, files=files)
        return result.get('id')

    def send_interactive_buttons(self, account, to_phone, body_text, buttons_list, header_text=None, footer_text=None):
        """
        Sends an interactive button message (up to 3 buttons).
        buttons_list: list of dicts [{'id': 'btn_1', 'title': 'Confirm'}, {'id': 'btn_2', 'title': 'Cancel'}]
        """
        url = self._build_url(account, f"{account.phone_number_id}/messages")
        headers = self._get_headers(account.access_token)
        formatted_buttons = []
        for btn in buttons_list[:3]:
            formatted_buttons.append({
                "type": "reply",
                "reply": {
                    "id": str(btn.get('id')),
                    "title": str(btn.get('title'))[:20]
                }
            })

        interactive = {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": formatted_buttons}
        }
        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": interactive
        }
        return self._send_request('POST', url, headers, json_data=payload)

    def send_interactive_list(self, account, to_phone, body_text, button_label, sections_list, header_text=None, footer_text=None):
        """
        Sends an interactive list message (menus/catalogs).
        sections_list: list of dicts [{'title': 'Section 1', 'rows': [{'id': 'row_1', 'title': 'Item', 'description': 'desc'}]}]
        """
        url = self._build_url(account, f"{account.phone_number_id}/messages")
        headers = self._get_headers(account.access_token)
        interactive = {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_label[:20],
                "sections": sections_list
            }
        }
        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": interactive
        }
        return self._send_request('POST', url, headers, json_data=payload)

    def mark_as_read(self, account, message_id):
        """Informs Meta that incoming message has been read by agent."""
        url = self._build_url(account, f"{account.phone_number_id}/messages")
        headers = self._get_headers(account.access_token)
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        try:
            return self._send_request('POST', url, headers, json_data=payload)
        except Exception as e:
            _logger.warning("Could not mark message %s as read: %s", message_id, str(e))
            return False
