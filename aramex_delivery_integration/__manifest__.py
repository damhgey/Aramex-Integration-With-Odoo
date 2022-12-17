# -*- coding: utf-8 -*-
{
    'name': "Aramex Delivery Integration",

    'summary': """ Send your shippings to Aramex and track them from Odoo""",

    'description': """
        Send multi Aramex shipments form picking in odoo
         with auto fill information of the shipments with 
         pickings info and get AWB number, tracking link 
         and Label PDF link after send shipments and store 
         them in fields in pickings.
        """,

    'author': "Ahmed Elsayed Aldamhogy",

    'category': 'Warehouse',

    'version': '14.0.1',

    'depends': ['stock', 'delivery', 'mail'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/send_aramex_shipment_information_wizard.xml',
        'data/data.xml',
        'views/delivery_aramex_view.xml',
        'views/stock_picking_view.xml',
    ],
}
