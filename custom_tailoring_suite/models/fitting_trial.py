# -*- coding: utf-8 -*-
# Part of Custom Tailoring & Bespoke Apparel Suite.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TailoringFittingTrial(models.Model):
    _name = 'tailoring.fitting.trial'
    _description = 'Bespoke Fitting & Trial Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc, id desc'

    name = fields.Char(string='Trial Reference', required=True, copy=False, default='Draft Trial')
    order_id = fields.Many2one(
        'tailoring.order',
        string='Bespoke Order',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        related='order_id.partner_id',
        string='Client',
        store=True,
        readonly=True
    )
    garment_type_id = fields.Many2one(
        'tailoring.garment.type',
        related='order_id.garment_type_id',
        string='Garment',
        store=True,
        readonly=True
    )
    trial_type = fields.Selection([
        ('1st_basted', '1st Fitting: Basted Skeleton Trial (White Stitching)'),
        ('2nd_forward', '2nd Fitting: Forward Trial (Pockets & Canvas Mounted)'),
        ('final_check', 'Final Fitting: Finished Garment Inspection'),
    ], string='Trial Stage', default='1st_basted', required=True, tracking=True)

    scheduled_date = fields.Datetime(
        string='Scheduled Appointment',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    tailor_id = fields.Many2one(
        'res.users',
        string='Fitting Artisan / Master Tailor',
        default=lambda self: self.env.user,
        tracking=True
    )
    fit_result = fields.Selection([
        ('perfect', 'Perfect Fit (No Alterations Required)'),
        ('minor_adjustment', 'Minor Alterations (Waist / Sleeves / Length)'),
        ('major_alteration', 'Major Alteration (Shoulder slope / Chest recut)'),
    ], string='Fitting Assessment', tracking=True)

    alteration_notes = fields.Text(
        string='Alteration Instructions & Chalk Marks',
        help='Detailed tailor notes for the workshop sewing artisan'
    )
    state = fields.Selection([
        ('scheduled', 'Appointment Scheduled'),
        ('in_progress', 'Trial In Progress'),
        ('completed', 'Trial Completed'),
        ('cancelled', 'Appointment Cancelled'),
    ], string='Status', default='scheduled', tracking=True)

    def action_start_trial(self):
        for rec in self:
            rec.state = 'in_progress'

    def action_complete_trial(self):
        for rec in self:
            if not rec.fit_result:
                raise UserError(_("Please record the Fitting Assessment result before completing the trial."))
            rec.state = 'completed'
            # Update order state accordingly
            if rec.trial_type == '1st_basted':
                if rec.fit_result == 'perfect':
                    rec.order_id.state = 'tailoring'
                else:
                    rec.order_id.state = 'alteration'
            elif rec.trial_type == '2nd_forward':
                if rec.fit_result == 'perfect':
                    rec.order_id.state = 'ready'
                else:
                    rec.order_id.state = 'alteration'
            elif rec.trial_type == 'final_check':
                rec.order_id.state = 'ready'

    def action_cancel_trial(self):
        for rec in self:
            rec.state = 'cancelled'
