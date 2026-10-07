# -*- coding: utf-8 -*-
# Part of Custom Tailoring & Bespoke Apparel Suite.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class TailoringOrder(models.Model):
    _name = 'tailoring.order'
    _description = 'Bespoke Tailoring & Apparel Job Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'delivery_date asc, id desc'

    name = fields.Char(
        string='Job Order #',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client / Customer',
        required=True,
        index=True,
        tracking=True
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Source Sales Order',
        tracking=True,
        help='Linked commercial sales order'
    )
    sale_line_id = fields.Many2one(
        'sale.order.line',
        string='Sales Order Line'
    )
    garment_type_id = fields.Many2one(
        'tailoring.garment.type',
        string='Garment Category',
        required=True,
        tracking=True
    )
    measurement_id = fields.Many2one(
        'tailoring.customer.measurement',
        string='Measurement Profile',
        required=True,
        tracking=True,
        domain="[('partner_id', '=', partner_id), ('garment_type_id', '=', garment_type_id)]"
    )
    measurement_unit = fields.Selection(
        related='measurement_id.measurement_unit',
        string='Unit',
        readonly=True
    )

    order_date = fields.Date(
        string='Order Date',
        default=fields.Date.today,
        required=True,
        tracking=True
    )
    fitting_date = fields.Date(
        string='Target Fitting Trial Date',
        tracking=True
    )
    delivery_date = fields.Date(
        string='Target Delivery Due Date',
        required=True,
        tracking=True
    )
    priority = fields.Selection([
        ('0', 'Standard Lead Time'),
        ('1', 'High Priority'),
        ('2', 'Urgent Event / Wedding'),
        ('3', 'VIP Express Atelier'),
    ], string='Priority', default='0', tracking=True)

    # Workshop Artisans
    cutter_id = fields.Many2one(
        'res.users',
        string='Master Pattern Cutter',
        tracking=True,
        help='Lead artisan responsible for drafting the paper pattern and cutting fabric'
    )
    tailor_id = fields.Many2one(
        'res.users',
        string='Coat / Trouser Maker',
        tracking=True,
        help='Artisan responsible for basting, stitching, canvas, and pocket construction'
    )

    # Fabric & Trims Allocation
    fabric_product_id = fields.Many2one(
        'product.product',
        string='Primary Fabric / Cloth',
        tracking=True
    )
    fabric_lot_number = fields.Char(
        string='Fabric Bolt / Lot / Mill Spec',
        help='Mill reference or bolt serial (e.g. Loro Piana Super 150s Wool - Bolt #442)'
    )
    fabric_meterage_required = fields.Float(
        string='Required Cloth (Meters)',
        digits=(6, 2),
        default=3.5
    )
    fabric_meterage_consumed = fields.Float(
        string='Actual Consumed (Meters)',
        digits=(6, 2),
        default=0.0,
        tracking=True
    )
    lining_product_id = fields.Many2one(
        'product.product',
        string='Lining Fabric / Silk Bemberg'
    )
    button_spec = fields.Char(
        string='Buttons Specification',
        default='Real Horn / Mother of Pearl (Matching)'
    )

    # Monogram & Bespoke Embroidery
    monogram_required = fields.Boolean(
        string='Custom Monogram / Embroidery',
        default=False,
        tracking=True
    )
    monogram_text = fields.Char(
        string='Monogram Characters (Initials)',
        help='e.g. M.L. or full name'
    )
    monogram_font = fields.Selection([
        ('classic_serif', 'Classic English Serif'),
        ('script_cursive', 'Royal Script Cursive'),
        ('modern_sans', 'Minimalist Modern Sans'),
        ('block_caps', 'Traditional Block Capitals'),
    ], string='Monogram Typography', default='script_cursive')
    monogram_color = fields.Char(
        string='Embroidery Thread Color',
        default='Champagne Gold'
    )
    monogram_placement = fields.Selection([
        ('inside_pocket', 'Interior Jacket Pocket Facing'),
        ('left_cuff', 'Left Shirt / Coat Cuff'),
        ('collar_felt', 'Undercollar Melton Felt'),
        ('trouser_waistband', 'Interior Trouser Waistband'),
    ], string='Monogram Position', default='inside_pocket')

    # Dynamic Styling Specifications
    style_line_ids = fields.One2many(
        'tailoring.order.style.line',
        'order_id',
        string='Selected Bespoke Styling',
        copy=True
    )

    # Fitting Trials
    fitting_ids = fields.One2many(
        'tailoring.fitting.trial',
        'order_id',
        string='Fitting Trial Appointments'
    )
    fitting_count = fields.Integer(
        string='Fittings Count',
        compute='_compute_fitting_count'
    )

    # State Machine
    state = fields.Selection([
        ('draft', 'Draft / Consultation'),
        ('confirmed', 'Order & Measurement Confirmed'),
        ('cutting', 'Pattern Drafting & Cloth Cutting'),
        ('tailoring', 'Assembly & Basting In Progress'),
        ('fitting_1', '1st Basted Skeleton Fitting'),
        ('alteration', 'Workshop Alterations'),
        ('fitting_2', '2nd Forward Trial Fitting'),
        ('ready', 'Final Quality Pass & Ready for Pickup'),
        ('delivered', 'Delivered to Client'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    workshop_instructions = fields.Text(
        string='Master Cutter Instructions & Canvas Specifications',
        help='Technical notes passed to the workshop cutters and coat makers'
    )
    customer_notes = fields.Text(string='Client Notes & Fit Requests')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('tailoring.order') or _('New')
        return super().create(vals_list)

    @api.depends('fitting_ids')
    def _compute_fitting_count(self):
        for order in self:
            order.fitting_count = len(order.fitting_ids)

    @api.onchange('garment_type_id')
    def _onchange_garment_type_id(self):
        """Auto-populate default styling lines from garment type options."""
        if not self.garment_type_id:
            return
        lines = []
        for opt in self.garment_type_id.style_option_ids:
            first_val = opt.value_ids[:1]
            lines.append((0, 0, {
                'option_id': opt.id,
                'value_id': first_val.id if first_val else False,
            }))
        self.style_line_ids = lines
        if self.garment_type_id.standard_fabric_meters:
            self.fabric_meterage_required = self.garment_type_id.standard_fabric_meters

    def action_confirm(self):
        for order in self:
            if not order.measurement_id:
                raise UserError(_("Please assign a valid Customer Measurement Profile before confirming."))
            order.state = 'confirmed'

    def action_start_cutting(self):
        for order in self:
            order.state = 'cutting'

    def action_start_tailoring(self):
        for order in self:
            order.state = 'tailoring'

    def action_fitting_1(self):
        for order in self:
            order.state = 'fitting_1'
            # Automatically create 1st trial appointment if not present
            if not order.fitting_ids.filtered(lambda f: f.trial_type == '1st_basted'):
                self.env['tailoring.fitting.trial'].create({
                    'name': f"{order.name} - 1st Basted Trial",
                    'order_id': order.id,
                    'trial_type': '1st_basted',
                    'scheduled_date': fields.Datetime.now(),
                    'tailor_id': order.tailor_id.id or self.env.user.id,
                })

    def action_start_alteration(self):
        for order in self:
            order.state = 'alteration'

    def action_fitting_2(self):
        for order in self:
            order.state = 'fitting_2'
            if not order.fitting_ids.filtered(lambda f: f.trial_type == '2nd_forward'):
                self.env['tailoring.fitting.trial'].create({
                    'name': f"{order.name} - 2nd Forward Trial",
                    'order_id': order.id,
                    'trial_type': '2nd_forward',
                    'scheduled_date': fields.Datetime.now(),
                    'tailor_id': order.tailor_id.id or self.env.user.id,
                })

    def action_mark_ready(self):
        for order in self:
            order.state = 'ready'

    def action_deliver(self):
        for order in self:
            order.state = 'delivered'

    def action_cancel(self):
        for order in self:
            order.state = 'cancel'

    def action_view_fittings(self):
        self.ensure_one()
        return {
            'name': _('Fitting Trials - %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'tailoring.fitting.trial',
            'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }

    def action_print_cutting_ticket(self):
        self.ensure_one()
        return self.env.ref('custom_tailoring_suite.action_report_cutting_ticket').report_action(self)


class TailoringOrderStyleLine(models.Model):
    _name = 'tailoring.order.style.line'
    _description = 'Bespoke Order Style Line'
    _order = 'sequence, id'

    order_id = fields.Many2one(
        'tailoring.order',
        string='Job Order',
        required=True,
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(string='Sequence', default=10)
    option_id = fields.Many2one(
        'tailoring.style.option',
        string='Style Attribute',
        required=True
    )
    value_id = fields.Many2one(
        'tailoring.style.option.value',
        string='Chosen Specification',
        domain="[('option_id', '=', option_id)]"
    )
    price_extra = fields.Float(
        related='value_id.price_extra',
        string='Surcharge ($)',
        readonly=True
    )
    notes = fields.Char(string='Custom Notes')
