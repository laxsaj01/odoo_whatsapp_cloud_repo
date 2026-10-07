# -*- coding: utf-8 -*-
# Part of Custom Tailoring & Bespoke Apparel Suite.
# Developed for Odoo 17.0 & 18.0.
# License: OPL-1 (Odoo Proprietary License v1.0).

{
    'name': 'Custom Tailoring & Bespoke Apparel Suite',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Sales/Point of Sale',
    'summary': 'All-in-One Bespoke Tailoring ERP: 30+ Body Measurements, Style Customizer, Cutting Tickets, Fitting Trials & Workshop Workflow',
    'description': """
Custom Tailoring & Bespoke Apparel Suite
========================================
Enterprise Sartorial ERP designed specifically for bespoke tailors, couture ateliers, 
made-to-measure (MTM) brands, bridal houses, and garment workshops.

Standard ERPs only manage mass-production fixed sizes (S, M, L). This suite provides a 
complete end-to-end operational engine for custom-fitted garment craftsmanship.

Key Features & Enterprise Capabilities:
---------------------------------------
* **30+ Body Anatomical Measurements:** Master parameter library (Chest, Neck, Shoulders, Sleeve Length, Bicep, Wrist, Trouser Waist, Inseam, Outseam, Thigh, Crotch Rise).
* **Anatomical Posture & Slope Profiling:** Record posture (Erect, Stooping, Balanced), shoulder slope (Square, Regular, Sloping), chest prominence, and stomach profile for pattern drafting.
* **Bespoke Style Configurator:** Lapel styles (Notch, Peak, Shawl), button closures (Single 1/2-button, Double Breasted 6x2), pocket configurations, jacket vents, lining styles, trouser pleats, and cuffs.
* **Premium Surcharges Engine:** Dynamic price markups for luxury linings, custom pick stitching, and double-breasted cuts.
* **Workshop Cutting Ticket (Job Sheet PDF):** Printable high-resolution cutting ticket with customer anatomy, measurement tables, raw vs. finished cut adjustments, fabric swatches, and artisan sign-offs.
* **Custom Monogramming & Embroidery:** Specify initials, typography (Cursive, Serif, Modern), thread color, and placement positions.
* **Multi-Stage Workshop Workflow:**
  `Draft Consultation -> Order Confirmed -> Cutting Room -> Assembly & Basting -> 1st Basted Trial -> Alterations -> 2nd Forward Trial -> Quality Passed -> Delivered`.
* **Dedicated Fitting Trial Scheduler:** Calendar appointments for skeleton basted fittings, chalk alteration note recording, and fit assessment tracking.
* **Sales Order & Customer Integration:** Direct 1-click launch from Quotations/Sales Orders and permanent measurement history under Customer profiles.
    """,
    'author': 'Enterprise Odoo Solutions',
    'website': 'https://apps.odoo.com',
    'license': 'OPL-1',
    'price': 500.00,
    'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'stock',
    ],
    'data': [
        'security/tailoring_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/tailoring_default_data.xml',
        'report/cutting_ticket_report.xml',
        'report/cutting_ticket_template.xml',
        'wizard/measurement_wizard_views.xml',
        'views/garment_type_views.xml',
        'views/measurement_parameter_views.xml',
        'views/style_option_views.xml',
        'views/customer_measurement_views.xml',
        'views/fitting_trial_views.xml',
        'views/tailoring_order_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
