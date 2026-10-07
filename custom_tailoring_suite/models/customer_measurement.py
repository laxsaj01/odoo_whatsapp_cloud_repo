# -*- coding: utf-8 -*-
# Part of Custom Tailoring & Bespoke Apparel Suite.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class TailoringCustomerMeasurement(models.Model):
    _name = 'tailoring.customer.measurement'
    _description = 'Customer Bespoke Measurement Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_measured desc, id desc'

    name = fields.Char(string='Profile Reference', compute='_compute_name', store=True, readonly=False)
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer / Client',
        required=True,
        index=True,
        tracking=True
    )
    garment_type_id = fields.Many2one(
        'tailoring.garment.type',
        string='Garment Type',
        required=True,
        index=True,
        tracking=True
    )
    date_measured = fields.Date(
        string='Measurement Date',
        default=fields.Date.today,
        required=True,
        tracking=True
    )
    measured_by_id = fields.Many2one(
        'res.users',
        string='Master Cutter / Tailor',
        default=lambda self: self.env.user,
        tracking=True
    )
    measurement_unit = fields.Selection([
        ('inch', 'Inches (in)'),
        ('cm', 'Centimeters (cm)'),
    ], string='Measurement System', required=True, default='inch', tracking=True)

    # Anatomical & Posture Profile (Critical for Bespoke Pattern Cutters)
    posture_profile = fields.Selection([
        ('normal', 'Standard Balanced Posture'),
        ('erect', 'Erect Posture (Chest Out / Head Back)'),
        ('stooping', 'Stooping / Forward Leaning (Round Back)'),
    ], string='Spine & Posture Profile', default='normal', tracking=True)

    shoulder_slope = fields.Selection([
        ('regular', 'Standard Regular Slope (approx 20°)'),
        ('sloping', 'Sloping Shoulders (Low / Drooping)'),
        ('square', 'Square Shoulders (High / Horizontal)'),
        ('asymmetric', 'Asymmetric (Right or Left Low)'),
    ], string='Shoulder Slope Profile', default='regular', tracking=True)

    chest_shape = fields.Selection([
        ('regular', 'Regular Standard Proportions'),
        ('prominent', 'Prominent / Deep Athletic Chest'),
        ('flat', 'Flat / Sunken Chest'),
    ], string='Chest Anatomy', default='regular')

    stomach_profile = fields.Selection([
        ('flat', 'Flat / Athletic Abdomen'),
        ('regular', 'Standard Regular Abdomen'),
        ('prominent', 'Prominent / Corpulent / Portly'),
    ], string='Stomach Profile', default='regular')

    line_ids = fields.One2many(
        'tailoring.customer.measurement.line',
        'measurement_id',
        string='Body Measurement Lines',
        copy=True
    )
    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Cutter Notes & Specific Fit Preferences')

    @api.depends('partner_id.name', 'garment_type_id.name', 'date_measured')
    def _compute_name(self):
        for rec in self:
            client = rec.partner_id.name or _("Unknown Client")
            garment = rec.garment_type_id.name or _("Custom Garment")
            date_str = str(rec.date_measured or fields.Date.today())
            rec.name = f"[{client}] {garment} ({date_str})"

    @api.onchange('garment_type_id')
    def _onchange_garment_type_id(self):
        """Auto-populate standard parameters configured for this garment type."""
        if not self.garment_type_id:
            return
        existing_params = self.line_ids.mapped('parameter_id')
        new_lines = []
        for param in self.garment_type_id.parameter_ids:
            if param not in existing_params:
                new_lines.append((0, 0, {
                    'parameter_id': param.id,
                    'sequence': param.sequence,
                    'value': 0.0,
                    'alteration_adjustment': 0.0,
                }))
        if new_lines:
            self.line_ids = new_lines


class TailoringCustomerMeasurementLine(models.Model):
    _name = 'tailoring.customer.measurement.line'
    _description = 'Bespoke Measurement Parameter Line'
    _order = 'sequence, id'

    measurement_id = fields.Many2one(
        'tailoring.customer.measurement',
        string='Measurement Profile',
        required=True,
        ondelete='cascade',
        index=True
    )
    parameter_id = fields.Many2one(
        'tailoring.measurement.parameter',
        string='Body Parameter',
        required=True
    )
    sequence = fields.Integer(string='Sequence', default=10)
    body_part = fields.Selection(
        related='parameter_id.body_part',
        string='Body Region',
        store=True,
        readonly=True
    )
    value = fields.Float(
        string='Raw Value',
        required=True,
        digits=(6, 2),
        default=0.0
    )
    alteration_adjustment = fields.Float(
        string='Fitting Adjustment (±)',
        default=0.0,
        digits=(6, 2),
        help='Alteration offset applied after fitting trial (e.g. +0.50 inch or -0.25 inch)'
    )
    final_value = fields.Float(
        string='Finished Value',
        compute='_compute_final_value',
        store=True,
        digits=(6, 2),
        help='Net cutting measurement (Raw Value + Fitting Adjustment)'
    )
    unit = fields.Selection(
        related='measurement_id.measurement_unit',
        string='Unit',
        readonly=True
    )
    notes = fields.Char(string='Special Cutter Note / Fitting Mark')

    @api.depends('value', 'alteration_adjustment')
    def _compute_final_value(self):
        for line in self:
            line.final_value = round(line.value + line.alteration_adjustment, 2)
