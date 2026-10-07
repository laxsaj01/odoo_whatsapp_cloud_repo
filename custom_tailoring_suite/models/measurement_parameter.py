# -*- coding: utf-8 -*-
# Part of Custom Tailoring & Bespoke Apparel Suite.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class TailoringMeasurementParameter(models.Model):
    _name = 'tailoring.measurement.parameter'
    _description = 'Bespoke Measurement Body Parameter'
    _order = 'sequence, name'

    name = fields.Char(string='Parameter Name', required=True, translate=True)
    code = fields.Char(string='Parameter Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    body_part = fields.Selection([
        ('upper_body', 'Upper Body (Chest, Neck, Shoulders)'),
        ('arm', 'Arms & Sleeves (Bicep, Wrist, Sleeve Length)'),
        ('torso', 'Torso & Waist (Stomach, Natural Waist)'),
        ('lower_body', 'Lower Body & Hips (Seat, Trouser Waist)'),
        ('leg', 'Legs (Inseam, Outseam, Thigh, Knee, Bottom Hem)'),
        ('posture', 'Posture & Structural Metrics'),
    ], string='Anatomical Region', required=True, default='upper_body')
    default_unit = fields.Selection([
        ('inch', 'Inches (in)'),
        ('cm', 'Centimeters (cm)'),
    ], string='Default Measurement Unit', required=True, default='inch')
    min_allowed_value = fields.Float(
        string='Minimum Permissible Value',
        default=5.0,
        digits=(6, 2),
        help='Sanity check to prevent typo or measurement errors'
    )
    max_allowed_value = fields.Float(
        string='Maximum Permissible Value',
        default=150.0,
        digits=(6, 2),
        help='Sanity check to prevent typo or measurement errors'
    )
    help_instruction = fields.Text(
        string='Master Tailor Instructions',
        help='Visual or practical instructions for the cutter on how to take this measurement'
    )
    garment_type_ids = fields.Many2many(
        'tailoring.garment.type',
        'tailoring_garment_param_rel',
        'param_id',
        'garment_id',
        string='Applicable Garments'
    )
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The parameter code must be unique!')
    ]

    @api.constrains('min_allowed_value', 'max_allowed_value')
    def _check_value_range(self):
        for record in self:
            if record.min_allowed_value < 0:
                raise ValidationError(_("Minimum allowed value cannot be negative."))
            if record.max_allowed_value <= record.min_allowed_value:
                raise ValidationError(_("Maximum allowed value must be strictly greater than minimum value."))
