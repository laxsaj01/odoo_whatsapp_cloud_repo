# -*- coding: utf-8 -*-
# Part of Custom Tailoring & Bespoke Apparel Suite.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

from odoo import api, fields, models, _

class TailoringGarmentType(models.Model):
    _name = 'tailoring.garment.type'
    _description = 'Bespoke Garment Category / Type'
    _order = 'sequence, name'

    name = fields.Char(string='Garment Name', required=True, translate=True)
    code = fields.Char(string='Reference Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    category = fields.Selection([
        ('suit', 'Suits & Tuxedos'),
        ('jacket', 'Blazers & Sport Coats'),
        ('trouser', 'Trousers & Chinos'),
        ('shirt', 'Dress Shirts & Casual Shirts'),
        ('vest', 'Waistcoats & Vests'),
        ('traditional', 'Sherwani / Kurta / Traditional'),
        ('dress', 'Couture Dresses & Abayas'),
        ('outerwear', 'Overcoats & Trench Coats'),
        ('other', 'Other Custom Apparel'),
    ], string='Garment Classification', required=True, default='suit')
    default_lead_time_days = fields.Integer(
        string='Standard Lead Time (Days)',
        default=14,
        help='Estimated turnaround time from measurement confirmation to final delivery'
    )
    estimated_labor_hours = fields.Float(
        string='Estimated Artisan Labor (Hours)',
        default=16.0,
        help='Estimated workshop hours required for cutting, assembly, and hand-finishing'
    )
    standard_fabric_meters = fields.Float(
        string='Standard Fabric Consumption (Meters)',
        default=3.5,
        digits=(6, 2),
        help='Approximate fabric requirement for a standard adult size (140cm width)'
    )
    parameter_ids = fields.Many2many(
        'tailoring.measurement.parameter',
        'tailoring_garment_param_rel',
        'garment_id',
        'param_id',
        string='Required Measurement Parameters'
    )
    style_option_ids = fields.Many2many(
        'tailoring.style.option',
        'tailoring_garment_style_rel',
        'garment_id',
        'style_id',
        string='Customizable Style Options'
    )
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Workshop Specifications & Guide')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The garment reference code must be unique!')
    ]
