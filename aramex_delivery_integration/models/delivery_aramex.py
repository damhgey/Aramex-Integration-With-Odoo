from odoo import api, fields, models
import requests
import json


class ProviderAramex(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('aramex', "Aramex")], ondelete={'aramex': 'cascade'})

    aramex_username = fields.Char(string="Aramex User Name", )
    aramex_password = fields.Char(string="Aramex Password", )
    aramex_account_number = fields.Char(string="Aramex Account Number", )
    aramex_account_pin = fields.Char(string="Aramex Account PIN", )
    aramex_account_entity = fields.Char(string="Aramex Account Entity", )
    aramex_account_city = fields.Char(string="Aramex Account City", )
    aramex_country_code = fields.Selection([('EG', 'EG')], default='EG', string='Country Code')
    aramex_environment = fields.Selection(string="Environment",
                                          selection=[('test', 'Test'), ('production', 'Production')], default='test')
    aramex_cities = fields.One2many(comodel_name="aramex.city", inverse_name="aramex_id", string="Aramex Cities")

    def action_update_aramex_cities(self):
        aramex_city_object = self.env['aramex.city']
        current_aramex_cities = aramex_city_object.search([]).mapped('name')
        url = "https://ws.aramex.net/ShippingAPI.V2/Location/Service_1_0.svc/json/FetchCities"
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        payload = {"ClientInfo": {"UserName": "a.hussein@enarat.com",
                                  "Password": "01551447367Ma@",
                                  "Version": "v1",
                                  "AccountNumber": "60529141",
                                  "AccountPin": "553654",
                                  "AccountEntity": "CAI",
                                  "AccountCountryCode": "EG",
                                  "Source": 24},
                   "CountryCode": "EG", }

        response = requests.request("POST", url=url, headers=headers, data=json.dumps(payload))

        cities = response.json()['Cities']
        for city in cities:
            if city not in current_aramex_cities:
                aramex_city_object.create({'name': city, 'aramex_id': self.id})
