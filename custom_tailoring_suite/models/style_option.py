# -*- coding: utf-8 -*-
# Part of Custom Tailoring & Bespoke Apparel Suite.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

from odoo import api, fields, models, _

class TailoringStyleOption(models.Model):
    _name = 'tailoring.style.option'
    _description = 'Bespoke Garment Styling Attribute'
    _order = 'sequence, name'

    name = fields.Char(string='Style Attribute', required=True, translate=True)
    code = fields.Char(string='Attribute Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    category = fields.Selection([
        ('lapel', 'Lapel Construction'),
        ('buttons', 'Buttons & Closure Stance'),
        ('pockets', 'Pockets & Flaps'),
        ('vents', 'Jacket Vents'),
        ('lining', 'Interior Lining & Canvas'),
        ('trouser_waist', 'Trouser Waistband & Adjusters'),
        ('trouser_pleats', 'Trouser Pleats & Hem'),
        ('collar_cuff', 'Shirt Collar & Cuffs'),
        ('other', 'Other Styling Attributes'),
    ], string='Styling Category', required=True, default='other')
    value_ids = fields.One2many(
        'tailoring.style.option.value',
        'option_id',
        string='Available Options / Variations'
    )
    garment_type_ids = fields.Many2many(
        'tailoring.garment.type',
        'tailoring_garment_style_rel',
        'style_id',
        'garment_id',
        string='Applicable Garments'
    )
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The style attribute code must be unique!')
    ]


class TailoringStyleOptionValue(models.Model):
    _name = 'tailoring.style.option.value'
    _description = 'Bespoke Style Option Value'
    _order = 'sequence, name'

    option_id = fields.Many2one(
        'tailoring.style.option',
        string='Style Attribute',
        required=True,
        ondelete='cascade',
        index=True
    )
    name = fields.Char(string='Option Choice', required=True, translate=True)
    code = fields.Char(string='Choice Code', index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    price_extra = fields.Float(
        string='Premium Surcharge ($)',
        default=0.0,
        digits=(12, 2),
        help='Additional price markup applied when client selects this bespoke option'
    )
    description = fields.Char(string='Visual Description / Notes')
    active = fields.Boolean(string='Active', default=True)
