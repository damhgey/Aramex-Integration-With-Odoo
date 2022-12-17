from odoo import api, fields, models


class AramexCity(models.Model):
    _name = 'aramex.city'
    _rec_name = 'name'
    _description = 'Aramex City'

    name = fields.Char('Name')
    aramex_id = fields.Many2one(comodel_name="delivery.carrier", required=True, readonly=True)
