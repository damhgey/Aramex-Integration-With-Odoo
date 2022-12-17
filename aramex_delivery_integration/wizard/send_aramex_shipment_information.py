# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import xmltodict
import requests
import json
import datetime


class AramexShipmentToSend(models.TransientModel):
    _name = 'aramex.shipments.to.send'

    shipment_ids = fields.One2many(comodel_name="aramex.shipments.to.send.line", inverse_name='to_send_wiz_id',)

    @api.model
    def default_get(self, fields):
        res = super(AramexShipmentToSend, self).default_get(fields)
        aramex_shipment_line_obj = self.env['aramex.shipments.to.send.line']
        picking_ids = self.env['stock.picking'].browse(self.env.context.get('active_ids'))
        shipment_lines = []
        for picking in picking_ids:
            if not picking.is_shipment_registered:
                line_vals = {}

                shipment_ref = picking.origin or picking.name
                if picking.sale_id.shopify_payment_gateway_id.code != 'Cash on Delivery (COD)':
                    shipment_cod_value = 0
                else:
                    shipment_cod_value = picking.pick_amount
                shipper_party_address_country_code = 'EG'
                client_name = picking.partner_id.name
                client_phone1 = picking.partner_id.phone
                client_phone2 = picking.partner_id.mobile
                client_email = picking.partner_id.email
                client_address = picking.partner_id.street
                client_city = self.env['aramex.city'].search([('name', 'ilike', picking.partner_id.state_id.name)], limit=1).id

                # line_vals['to_send_wiz_id'] = self.id
                line_vals['shipment_ref'] = shipment_ref
                line_vals['pack_id'] = picking.id
                line_vals['shipment_cod_value'] = shipment_cod_value
                line_vals['shipper_party_address_country_code'] = shipper_party_address_country_code
                line_vals['client_name'] = client_name
                line_vals['client_phone1'] = client_phone1
                line_vals['client_phone2'] = client_phone2
                line_vals['client_email'] = client_email
                line_vals['client_address'] = client_address
                line_vals['client_city'] = client_city

                shipment_lines.append((0, 0, line_vals))

        res.update({'shipment_ids': shipment_lines})
        return res

    def send_shipment_to_aramex(self):
        for ship in self.shipment_ids:
            if not ship.pack_id.is_shipment_registered:
                picking = ship.pack_id
                shipment_request_data = ship.prepare_shipment_request()
                url = shipment_request_data['url']
                shipment_data = shipment_request_data['shipment_data']
                client_info = shipment_request_data['client_info']
                headers = {'Content-Type': 'application/json'}
                payload = json.dumps(shipment_data)
                response = requests.request("POST", url, headers=headers, data=payload)

                if response.status_code == 200:
                    response_content = response.content
                    response_content_dict = xmltodict.parse(response_content)
                    has_errors = response_content_dict['ShipmentCreationResponse']['HasErrors']
                    if has_errors == 'false':
                        shipment_response_info = response_content_dict['ShipmentCreationResponse']['Shipments']['ProcessedShipment']
                        shipment_state = 'Aramex receive shipment'
                        shipment_number = shipment_response_info['ID']
                        shipment_tracking_url = 'https://www.aramex.com/ar/en/track/results?ShipmentNumber=' + shipment_number
                        lable_print_url = shipment_response_info['ShipmentLabel']['LabelURL']

                        picking.write({'shipment_state': shipment_state, 'tracking_number': shipment_number, 'shipment_awb_url': shipment_tracking_url, 'shipment_lable_url': lable_print_url, 'is_shipment_registered': True})

                        logmessage = (_("Shipment Created Into Aramex With <br/> <b>Tracking Number : </b>%s <br/> <b>Print Lable:</b> %s") % (shipment_number, lable_print_url))
                        picking.message_post(body=logmessage)
                        self.env.cr.commit()
                    else:
                        try:
                            error_messages = response_content_dict['ShipmentCreationResponse']['Shipments']['ProcessedShipment']['Notifications']['Notification']
                        except:
                            error_messages = response_content_dict['ShipmentCreationResponse']['Notifications']['Notification']
                        raise ValidationError(_("Errors when Shipment Data: " + str(error_messages)))
                else:
                    raise ValidationError('Bad Request!. could not send shipment to Aramex.')


class AramexShipmentToSendLine(models.TransientModel):
    _name = 'aramex.shipments.to.send.line'

    to_send_wiz_id = fields.Many2one(comodel_name="aramex.shipments.to.send")
    pack_id = fields.Many2one(comodel_name="stock.picking", string="Pack")
    # Shipment information
    shipment_ref = fields.Char(string="Shipment Ref", required=True)
    shipment_datetime = fields.Datetime(string="Shipment Date", required=True, default=fields.Datetime.now)
    shipment_number_of_pieces = fields.Integer(string="Number Of Pieces", required=True, default=1)
    shipment_dimension_length = fields.Integer(string="Shipment Length", required=True, default=1)
    shipment_dimension_width = fields.Integer(string="Shipment Width", required=True, default=1)
    shipment_dimension_height = fields.Integer(string="Shipment Height", required=True, default=1)
    shipment_actual_weight_value = fields.Integer(string="Weight Value", required=True, default=1)
    shipment_actual_weight_unit = fields.Char(string="Weight Unit", required=True, default='KG')
    shipment_product_group = fields.Selection(string="Product Group", selection=[('exp', 'EXP'), ('DOM', 'DOM'), ],
                                              required=True, default='DOM')
    shipment_product_type = fields.Selection(string="Product Type", selection=[('OND', 'OND'), ('SMD', 'SMD')], required=True, default='SMD')
    shipment_payment_type = fields.Selection(string="Payment Type", required=True,
                                             selection=[('P', 'P')], default="P")
    shipment_description_of_goods = fields.Char(string="Description Of Goods", required=True, default='/')
    shipment_goods_origin_country = fields.Char(string="Goods Origin Country", required=True, default='EG')
    shipment_cod_value = fields.Float(string="COD Value", required=True)
    shipment_cod_currency_code = fields.Char(string="COD Currency", required=True,
                                                         default=lambda self: self.env.company.currency_id.name)
    shipment_comments = fields.Char(string="Shipment Comments", required=False, )
    shipment_operation_instruction = fields.Char(string="Shipment Instruction", required=False)
    # Shipper Information
    shipper_account_number = fields.Char(string="Shipper Account Number", required=True,
                                         default=lambda self: self.env['delivery.carrier'].search(
                                             [('delivery_type', '=', 'aramex')], limit=1).aramex_account_number, )
    shipper_party_address_country_code = fields.Char(string="Shipper Country Code", required=True)
    shipper_party_address_ine1 = fields.Char(string="Shipper Address", required=True,
                                             default=lambda self: self.env.company.street)
    shipper_party_address_city = fields.Char(string="Shipper City", required=True, default=lambda self: self.env['delivery.carrier'].search(
                                             [('delivery_type', '=', 'aramex')], limit=1).aramex_account_city,)
    shipper_contact_person_name = fields.Char(string="Shipper Name", required=True,
                                              default=lambda self: self.env.company.partner_id.name)
    shipper_contact_phone_number1 = fields.Char(string="Shipper Phone 1", required=True,
                                                default=lambda self: self.env.company.partner_id.phone or '0')
    shipper_contact_phone_number2 = fields.Char(string="Shipper Phone 2", required=True,
                                                default=lambda self: self.env.company.partner_id.mobile or '0')
    shipper_contact_cell_phone = fields.Char(string="Shipper Cell Phone", required=True,
                                             default=lambda self: self.env.company.partner_id.mobile or '0')
    shipper_contact_email_address = fields.Char(string="Shipper Email", required=True,
                                                default=lambda self: self.env.company.partner_id.email)
    # Client information
    client_name = fields.Char(string="Client Name", required=True)
    client_phone1 = fields.Char(string="Client Phone 1", required=True)
    client_phone2 = fields.Char(string="Client Phone 2", required=False)
    client_email = fields.Char(string="Client Email", required=False)
    client_address = fields.Char(string="Client Address", required=True)
    client_city = fields.Many2one(comodel_name="aramex.city", string="Client City", required=True)
    client_note = fields.Char(string="Client Note", required=False)

    def prepare_shipment_request(self):
        aramex_object = self.env['delivery.carrier'].search([('delivery_type', '=', 'aramex')], limit=1)
        # Get api URL
        if aramex_object.aramex_environment == 'production':
            url = 'https://ws.aramex.net/ShippingAPI.V2/Shipping/Service_1_0.svc/json/CreateShipments'
        else:
            url = 'https://ws.dev.aramex.net/ShippingAPI.V2/Shipping/Service_1_0.svc/json/CreateShipments'

        # Client Account Info
        client_account_info = self._get_client_account_info(aramex_object)

        # Shipment Info
        shipment_data = self._prepare_shipment_data(aramex_object)

        request_data = {'url': url, 'shipment_data': shipment_data, 'client_info': client_account_info}
        return request_data

    def _get_client_account_info(self, aramex_obj):
        if aramex_obj.aramex_environment == 'production':
            client_info = {"UserName": aramex_obj.aramex_username,
                           "Password": aramex_obj.aramex_password,
                           "Version": "1.0",
                           "AccountNumber": aramex_obj.aramex_account_number,
                           "AccountPin": aramex_obj.aramex_account_pin,
                           "AccountEntity": aramex_obj.aramex_account_entity,
                           "AccountCountryCode": aramex_obj.aramex_country_code,
                           "Source": 24}
        else:
            client_info = {"UserName": "testingapi@aramex.com",
                           "Password": "R123456789$r",
                           "Version": "1.0",
                           "AccountNumber": "20016",
                           "AccountPin": "331421",
                           "AccountEntity": "AMM",
                           "AccountCountryCode": "JO",
                           "Source": 24}
        return client_info

    def _prepare_shipper_data(self, aramex_obj):
        shipper_client_info = self._get_client_account_info(aramex_obj)
        if aramex_obj.aramex_environment == 'production':
            shipper_party_address_city = self.shipper_party_address_city
        else:
            shipper_party_address_city = "Amman"
        shipper_data = {
            "Reference1": self.shipment_ref,
            "Reference2": None,
            "AccountNumber": shipper_client_info['AccountNumber'],
            "PartyAddress": {
                "Line1": self.shipper_party_address_ine1,
                "Line2": None,
                "Line3": None,
                "City": shipper_party_address_city,
                "StateOrProvinceCode": "",
                "PostCode": "",
                "CountryCode": shipper_client_info['AccountCountryCode'],
            },
            "Contact": {
                "Department": None,
                "PersonName": self.shipper_contact_person_name,
                "Title": None,
                "CompanyName": self.shipper_contact_person_name,
                "PhoneNumber1": self.shipper_contact_phone_number1,
                "PhoneNumber1Ext": None,
                "PhoneNumber2": self.shipper_contact_phone_number2,
                "PhoneNumber2Ext": None,
                "FaxNumber": None,
                "CellPhone": self.shipper_contact_cell_phone,
                "EmailAddress": self.shipper_contact_email_address,
                "Type": None
            }
        }
        return shipper_data

    def _prepare_consignee_data(self):
        consignee_data = {
            "Reference1": self.shipment_ref,
            "Reference2": None,
            "AccountNumber": '',
            "PartyAddress": {
                "Line1": self.client_address,
                "Line2": None,
                "Line3": None,
                "City": self.client_city.name,
                "StateOrProvinceCode": None,
                "PostCode": "",
                "CountryCode": "EG"
            },
            "Contact": {
                "Department": None,
                "PersonName": self.client_name,
                "Title": None,
                "CompanyName": self.client_name,
                "PhoneNumber1": self.client_phone1,
                "PhoneNumber1Ext": None,
                "PhoneNumber2": self.client_phone2 or "",
                "PhoneNumber2Ext": None,
                "FaxNumber": None,
                "CellPhone": self.client_phone1,
                "EmailAddress": self.client_email or "",
                "Type": None
            }
        }
        return consignee_data

    # This method convert python datetime to aramex format datetime (which in C# JavascriptSerializer obj)
    # Which it's in this format "\/Date(1656950437000)\/" which means date in ticks (milli seconds)
    # For more info go to: shorturl.at/gKQZ7
    def aramex_shipping_datetime_format(self, date):
        ticks = (date - datetime.datetime(1970, 1, 1)).total_seconds() * 1000
        int_ticks = int(ticks)
        date_ticks = f"/Date({int_ticks})/"
        return date_ticks

    def _prepare_shipment_data(self, aramex_obj):
        picking = self.pack_id
        # Number of Piece validation
        if self.shipment_number_of_pieces <= 0:
            raise ValidationError('Number of pieces must be higher than 0')

        shipment_cod = {'Value': self.shipment_cod_value, 'CurrencyCode': 'EGP'}
        if self.shipment_cod_value:
            services = "CODS"
        else:
            services = None

        shipment_data = {
            "ClientInfo": self._get_client_account_info(aramex_obj),
            "LabelInfo": {"ReportID": 9729, "ReportType": "URL"},
            "Shipments": [
                {
                    "Reference1": "137798",
                    "Reference2": None,
                    "Reference3": None,
                    "Shipper": self._prepare_shipper_data(aramex_obj),
                    "Consignee": self._prepare_consignee_data(),
                    "ThirdParty": None,
                    "ShippingDateTime": self.aramex_shipping_datetime_format(self.shipment_datetime),
                    "DueDate": self.aramex_shipping_datetime_format(datetime.datetime.now() + datetime.timedelta(7)),
                    "Comments": self.shipment_comments or "",
                    "PickupLocation": "",
                    "OperationsInstructions": self.shipment_operation_instruction or "",
                    "AccountingInstrcutions": "",
                    "Details": {
                        "Dimensions": {
                            "Length": self.shipment_dimension_length,
                            "Width": self.shipment_dimension_width,
                            "Height": self.shipment_dimension_height,
                            "Unit": "CM"
                        },
                        "ActualWeight": {
                            "Value": self.shipment_actual_weight_value,
                            "Unit": "KG"
                        },
                        "ChargeableWeight": None,
                        "DescriptionOfGoods": self.shipment_description_of_goods,
                        "GoodsOriginCountry": "EG",
                        "NumberOfPieces": self.shipment_number_of_pieces,
                        "ProductGroup": self.shipment_product_group,
                        "ProductType": self.shipment_product_type,
                        "PaymentType": self.shipment_payment_type,
                        "PaymentOptions": None,
                        "CustomsValueAmount": None,
                        "CashOnDeliveryAmount": shipment_cod,
                        "InsuranceAmount": None,
                        "CashAdditionalAmount": None,
                        "CashAdditionalAmountDescription": None,
                        "CollectAmount": None,
                        "Services": services,
                        "Items": None
                    },
                    "Attachments": None,
                    "ForeignHAWB": "",
                    "TransportType_x0020_": None,
                    "PickupGUID": None
                }
            ]
        }
        return shipment_data

    @api.model
    def create(self, vals):
        shipment_ref = vals.get('shipment_ref')
        if not vals.get('client_city'):
            raise ValidationError(_('Could not set client city automatic for shipment: [%s] you should set it manually before send' % shipment_ref))
        res = super(AramexShipmentToSendLine, self).create(vals)
        return res

