# -*- coding: utf-8 -*-
# Part of Custom Tailoring & Bespoke Apparel Suite.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TailoringMeasurementWizard(models.TransientModel):
    _name = 'tailoring.measurement.wizard'
    _description = 'Rapid Customer Measurement Wizard'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer / Client',
        required=True
    )
    garment_type_id = fields.Many2one(
        'tailoring.garment.type',
        string='Garment Category',
        required=True
    )
    date_measured = fields.Date(
        string='Measurement Date',
        default=fields.Date.today,
        required=True
    )
    measurement_unit = fields.Selection([
        ('inch', 'Inches (in)'),
        ('cm', 'Centimeters (cm)'),
    ], string='Unit', required=True, default='inch')

    posture_profile = fields.Selection([
        ('normal', 'Standard Balanced Posture'),
        ('erect', 'Erect Posture (Chest Out / Head Back)'),
        ('stooping', 'Stooping / Forward Leaning (Round Back)'),
    ], string='Posture Profile', default='normal')

    shoulder_slope = fields.Selection([
        ('regular', 'Standard Regular Slope'),
        ('sloping', 'Sloping Shoulders'),
        ('square', 'Square Shoulders'),
        ('asymmetric', 'Asymmetric Shoulders'),
    ], string='Shoulder Slope', default='regular')

    notes = fields.Text(string='Cutter Notes')
    line_ids = fields.One2many(
        'tailoring.measurement.wizard.line',
        'wizard_id',
        string='Measurement Lines'
    )

    @api.onchange('garment_type_id')
    def _onchange_garment_type_id(self):
        if not self.garment_type_id:
            return
        lines = []
        for param in self.garment_type_id.parameter_ids:
            lines.append((0, 0, {
                'parameter_id': param.id,
                'sequence': param.sequence,
                'value': 0.0,
            }))
        self.line_ids = lines

    def action_save_measurement(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Please add at least one measurement parameter line."))

        # Create the permanent customer measurement record
        measurement_vals = {
            'partner_id': self.partner_id.id,
            'garment_type_id': self.garment_type_id.id,
            'date_measured': self.date_measured,
            'measurement_unit': self.measurement_unit,
            'posture_profile': self.posture_profile,
            'shoulder_slope': self.shoulder_slope,
            'notes': self.notes,
            'line_ids': [(0, 0, {
                'parameter_id': line.parameter_id.id,
                'sequence': line.sequence,
                'value': line.value,
            }) for line in self.line_ids]
        }
        measurement = self.env['tailoring.customer.measurement'].create(measurement_vals)
        return {
            'name': _('Customer Measurement Profile'),
            'type': 'ir.actions.act_window',
            'res_model': 'tailoring.customer.measurement',
            'res_id': measurement.id,
            'view_mode': 'form',
        }


class TailoringMeasurementWizardLine(models.TransientModel):
    _name = 'tailoring.measurement.wizard.line'
    _description = 'Rapid Measurement Wizard Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        'tailoring.measurement.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    parameter_id = fields.Many2one(
        'tailoring.measurement.parameter',
        string='Body Parameter',
        required=True
    )
    sequence = fields.Integer(string='Sequence', default=10)
    body_part = fields.Selection(
        related='parameter_id.body_part',
        string='Region',
        readonly=True
    )
    value = fields.Float(
        string='Measurement Value',
        required=True,
        digits=(6, 2),
        default=0.0
    )
