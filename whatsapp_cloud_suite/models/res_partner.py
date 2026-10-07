# -*- coding: utf-8 -*-
# Part of WhatsApp Business Cloud API Enterprise Suite.
# License: OPL-1.

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    whatsapp_chat_count = fields.Integer(
        string='WhatsApp Messages',
        compute='_compute_whatsapp_chat_count'
    )

    def _compute_whatsapp_chat_count(self):
        chat_obj = self.env['whatsapp.chat.history']
        for partner in self:
            partner.whatsapp_chat_count = chat_obj.search_count([('partner_id', '=', partner.id)])

    def action_open_whatsapp_composer(self):
        """1-Click composer opener from partner profile."""
        self.ensure_one()
        phone = self.mobile or self.phone
        account = self.env['whatsapp.account'].search([
            ('company_id', '=', self.company_id.id if self.company_id else self.env.company.id),
            ('state', '=', 'connected')
        ], limit=1)

        return {
            'name': _('Chat via WhatsApp'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.send.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_recipient_phone': phone,
                'default_model_name': 'res.partner',
                'default_res_id': self.id,
                'default_account_id': account.id if account else False,
            }
        }

    def action_view_whatsapp_chats(self):
        self.ensure_one()
        return {
            'name': _('WhatsApp Conversations'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.chat.history',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
