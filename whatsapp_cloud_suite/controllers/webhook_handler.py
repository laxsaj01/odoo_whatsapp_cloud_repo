# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# License: OPL-1.

import hmac
import hashlib
import json
import logging
import re
from odoo import http, fields, _
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class WhatsAppWebhookController(http.Controller):

    def _verify_meta_signature(self, account, payload_bytes, hub_signature_header):
        """Validates HMAC-SHA256 signature sent in X-Hub-Signature-256 header."""
        if not account.app_secret or not hub_signature_header:
            return True  # If no app secret is configured, bypass check

        if not hub_signature_header.startswith('sha256='):
            return False

        expected_sig = hub_signature_header.split('sha256=')[-1]
        calculated_sig = hmac.new(
            key=account.app_secret.encode('utf-8'),
            msg=payload_bytes,
            digestmod=hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_sig, calculated_sig)

    @http.route('/whatsapp/webhook/<int:account_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def webhook_challenge_verification(self, account_id, **kwargs):
        """
        Meta Webhook verification handshake:
        Meta sends GET with hub.mode, hub.challenge, and hub.verify_token.
        """
        hub_mode = kwargs.get('hub.mode')
        hub_challenge = kwargs.get('hub.challenge')
        hub_verify_token = kwargs.get('hub.verify_token')

        account = request.env['whatsapp.account'].sudo().browse(account_id)
        if not account.exists():
            _logger.warning("WhatsApp Webhook GET: Account ID %s not found.", account_id)
            return Response("Account not found", status=404)

        if hub_mode == 'subscribe' and hub_verify_token == account.webhook_verify_token:
            _logger.info("WhatsApp Webhook handshake verified successfully for Account %s", account.name)
            return Response(hub_challenge, status=200, content_type='text/plain')

        _logger.warning("WhatsApp Webhook handshake failed: token mismatch for Account %s", account.name)
        return Response("Forbidden: Invalid verify token", status=403)

    @http.route('/whatsapp/webhook/<int:account_id>', type='json', auth='public', methods=['POST'], csrf=False)
    def webhook_receive_event(self, account_id, **kwargs):
        """
        Meta Webhook event processor:
        Receives inbound messages and delivery status callbacks.
        """
        account = request.env['whatsapp.account'].sudo().browse(account_id)
        if not account.exists() or not account.active:
            return {'status': 'ignored', 'reason': 'Account not active or not found'}

        # Verify Signature if available
        hub_signature = request.httprequest.headers.get('X-Hub-Signature-256')
        raw_body = request.httprequest.get_data()
        if hub_signature and not self._verify_meta_signature(account, raw_body, hub_signature):
            _logger.warning("WhatsApp Webhook POST: Signature verification failed for Account %s", account.name)
            return {'status': 'error', 'reason': 'Invalid HMAC signature'}

        data = request.jsonrequest
        if not data or 'entry' not in data:
            return {'status': 'ignored', 'reason': 'No entry object'}

        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})

                # 1. Process Status Callbacks (sent, delivered, read, failed)
                statuses = value.get('statuses', [])
                if statuses:
                    self._handle_status_updates(account, statuses)

                # 2. Process Inbound Messages from Customers
                messages = value.get('messages', [])
                contacts = value.get('contacts', [])
                if messages:
                    self._handle_incoming_messages(account, messages, contacts)

        return {'status': 'success'}

    def _handle_status_updates(self, account, statuses):
        queue_obj = request.env['whatsapp.message.queue'].sudo()
        chat_obj = request.env['whatsapp.chat.history'].sudo()

        for st in statuses:
            wamid = st.get('id')
            new_status = st.get('status')  # sent, delivered, read, failed

            state_map = {
                'sent': 'sent',
                'delivered': 'delivered',
                'read': 'read',
                'failed': 'failed',
            }
            mapped_state = state_map.get(new_status)
            if not mapped_state:
                continue

            # Update Queue
            queue_records = queue_obj.search([('meta_message_id', '=', wamid)])
            for q in queue_records:
                vals = {'state': mapped_state}
                if mapped_state == 'failed':
                    errors = st.get('errors', [{}])[0]
                    vals['last_error'] = f"Meta Error Code {errors.get('code')}: {errors.get('title', '')} - {errors.get('message', '')}"
                q.write(vals)

            # Update Chat Log
            chat_records = chat_obj.search([('meta_message_id', '=', wamid)])
            if chat_records:
                chat_records.write({'state': mapped_state})

    def _handle_incoming_messages(self, account, messages, contacts):
        partner_obj = request.env['res.partner'].sudo()
        chat_obj = request.env['whatsapp.chat.history'].sudo()
        channel_obj = request.env['discuss.channel'].sudo()

        contact_name_map = {}
        for c in contacts:
            wa_id = c.get('wa_id')
            p_name = c.get('profile', {}).get('name')
            if wa_id and p_name:
                contact_name_map[wa_id] = p_name

        for msg in messages:
            from_phone = msg.get('from')
            msg_id = msg.get('id')
            msg_type = msg.get('type')
            sender_name = contact_name_map.get(from_phone, f"WhatsApp User ({from_phone})")

            # Find or create partner
            clean_phone = re.sub(r'[\s\-\(\)\+]', '', from_phone)
            partner = partner_obj.search([
                '|', ('phone', 'like', clean_phone), ('mobile', 'like', clean_phone)
            ], limit=1)

            if not partner:
                partner = partner_obj.create({
                    'name': sender_name,
                    'phone': f"+{clean_phone}",
                    'mobile': f"+{clean_phone}",
                    'company_id': account.company_id.id,
                })

            body_content = ''
            if msg_type == 'text':
                body_content = msg.get('text', {}).get('body', '')
            elif msg_type == 'interactive':
                interactive_data = msg.get('interactive', {})
                i_type = interactive_data.get('type')
                if i_type == 'button_reply':
                    body_content = interactive_data.get('button_reply', {}).get('title', '')
                elif i_type == 'list_reply':
                    body_content = interactive_data.get('list_reply', {}).get('title', '')
            elif msg_type in ['image', 'video', 'document', 'audio']:
                caption = msg.get(msg_type, {}).get('caption', '')
                body_content = f"[{msg_type.upper()} Attachment] {caption}"
            elif msg_type == 'location':
                loc = msg.get('location', {})
                body_content = f"[Location: Lat {loc.get('latitude')}, Long {loc.get('longitude')}]"

            # Create Chat History Record
            chat_record = chat_obj.create({
                'account_id': account.id,
                'partner_id': partner.id,
                'sender_phone': from_phone,
                'receiver_phone': account.display_phone_number or 'Business',
                'direction': 'inbound',
                'message_type': msg_type if msg_type in dict(chat_obj._fields['message_type'].selection) else 'text',
                'message_text': body_content,
                'meta_message_id': msg_id,
                'state': 'received',
            })

            # Sync with Discuss Channel
            channel_name = f"WA: {partner.name}"
            channel = channel_obj.search([
                ('name', '=', channel_name),
                ('channel_type', '=', 'chat')
            ], limit=1)

            if not channel:
                channel = channel_obj.create({
                    'name': channel_name,
                    'channel_type': 'chat',
                    'channel_partner_ids': [(4, partner.id)],
                })

            chat_record.write({'channel_id': channel.id})

            # Post message in discuss channel
            channel.message_post(
                body=f"<b>WhatsApp ({from_phone}):</b> {body_content}",
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                author_id=partner.id,
            )

            # Check for Bot Triggers
            enable_bot = request.env['ir.config_parameter'].sudo().get_param('whatsapp_cloud_suite.enable_bot', True)
            if enable_bot:
                self._handle_bot_automation(account, partner, from_phone, body_content)

    def _handle_bot_automation(self, account, partner, from_phone, text_content):
        """Automated interactive responses and order generation."""
        api_service = request.env['whatsapp.api.service'].sudo()
        cleaned_msg = text_content.strip().upper()

        if cleaned_msg in ['MENU', 'CATALOG', 'PRODUCTS']:
            # Send top 5 products as interactive list
            products = request.env['product.product'].sudo().search([
                ('sale_ok', '=', True),
                ('company_id', 'in', [False, account.company_id.id])
            ], limit=5)

            if products:
                rows = []
                for p in products:
                    rows.append({
                        'id': f"PROD_{p.id}",
                        'title': p.name[:24],
                        'description': f"{p.currency_id.symbol} {p.list_price:,.2f}"[:72]
                    })
                sections = [{'title': 'Featured Products', 'rows': rows}]
                api_service.send_interactive_list(
                    account=account,
                    to_phone=from_phone,
                    body_text=_("Welcome! Here are our featured products. Tap below to browse and order:"),
                    button_label=_("View Products"),
                    sections_list=sections,
                    header_text=_("Product Catalog"),
                    footer_text=_("Reply with item to place an order.")
                )
        elif cleaned_msg.startswith('PROD_') or 'ORDER' in cleaned_msg:
            # Auto-create draft quotation in Odoo
            product_id = None
            if cleaned_msg.startswith('PROD_'):
                try:
                    product_id = int(cleaned_msg.replace('PROD_', ''))
                except ValueError:
                    pass

            sale_order_vals = {
                'partner_id': partner.id,
                'company_id': account.company_id.id,
                'origin': _('WhatsApp Automated Order'),
            }
            order = request.env['sale.order'].sudo().create(sale_order_vals)

            if product_id:
                product = request.env['product.product'].sudo().browse(product_id)
                if product.exists():
                    request.env['sale.order.line'].sudo().create({
                        'order_id': order.id,
                        'product_id': product.id,
                        'product_uom_qty': 1.0,
                        'price_unit': product.list_price,
                    })

            # Send confirmation reply
            reply_msg = _("Thank you %(name)s! We have generated a draft quotation: %(ref)s for you. Our sales representative will finalize your order shortly.") % {
                'name': partner.name,
                'ref': order.name,
            }
            api_service.send_text_message(
                account=account,
                to_phone=from_phone,
                message_text=reply_msg
            )
