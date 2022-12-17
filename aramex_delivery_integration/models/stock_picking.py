from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_shipment_registered = fields.Boolean()
    shipment_state = fields.Char(string="Shipment status", readonly=True)
    tracking_number = fields.Char(string="Tracking Number", readonly=True)
    shipment_awb_url = fields.Char(string="AWB", readonly=True)
    shipment_lable_url = fields.Char(string="Lable PDF", readonly=True)

