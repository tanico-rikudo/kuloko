# coding: utf-8

import urllib.parse
import configparser

import pandas as pd
import numpy as np

import requests
import json
import os

import time
from datetime import datetime as dt
from datetime import  timedelta, timezone

import hmac
import hashlib

from util import daylib
dl = daylib.daylib()

class RequestError(Exception):
    pass

class InvalidArgumentError(Exception):
    pass

class API:

    def __init__(self,sym,logger, general_config_ini=None,private_api_ini=None,
                general_config_mode="DEFAULT",private_api_mode='DEFAULT'):
        self.sym=sym
        self._logger = logger

        if general_config_ini is None:
            general_config_ini = configparser.ConfigParser()
            general_config_ini.read('../ini/config.ini', encoding='utf-8')
            self._logger.info('[DONE]Load General Config.')
        if private_api_ini is None:            
            private_api_ini = configparser.ConfigParser()
            private_api_ini.read('../private_api.ini', encoding='utf-8')
            self._logger.info('[DONE]Load Private API Config.')

        self.load_config( general_config_ini,private_api_ini,general_config_mode,private_api_mode)
        self.set_config()
        self.load_urls()

        self._logger.info('[DONE]API Initialized')


    def load_urls(self):
        self.url_parts = {
            'endpoint':self.general_config.get('ENDPOINT_URL'),
            'tick':self.general_config.get('TICK_URL'),
            'orderbooks':self.general_config.get('ORDERBOOKS_URL'),
            'trade':self.general_config.get('TRADE_URL'),
            'margin':self.general_config.get('MARGIN_URL'),
            'assets':self.general_config.get('ASSERTS_URL'),
            'activeOrders':self.general_config.get('ACTIVEORDERS_URL'),
            'orders':self.general_config.get('ORDERS_URL'),
            'executions':self.general_config.get('EXECUTIONS_URL'),
            'latestExecutions':self.general_config.get('LATESTEXECUTIONS_URL'),
            'order':self.general_config.get('ORDER_URL'),
            'changeOrder':self.general_config.get('CHANGEORDER_URL'),
            'cancelOrder':self.general_config.get('CANCELORDER_URL'),
            
        }
        self._logger.info('[DONE]Set URL parts')

    def load_config(self,general_config_ini,private_api_ini,general_config_mode,private_api_mode):
        self.private_api_config = private_api_ini[private_api_mode]
        self.general_config = general_config_ini[general_config_mode]
        self._logger.info('[DONE]Load Config. Private API:[{0}] General:[{1}]'
            .format(private_api_mode,general_config_mode))


    def set_config(self):
        self.allow_sym = eval(self.general_config.get('ALLOW_SYM'))
        self.tz_offset = self.general_config.getint('TIMEZONE_OFFSET_HOUR')
        self._logger.info('[DONE]Set Config from loaded config')

    def make_header(self,access_path, access_method,request_body=""):
        timestamp = '{0}000'.format(
            int(time.mktime(dt.now().timetuple())))
        send_text = timestamp + access_method + access_path + request_body

        sign = hmac.new(
            bytes(self.private_api_config.get('API_SEC').encode('ascii')), 
            bytes(send_text.encode('ascii')), 
            hashlib.sha256).hexdigest()

        headers = {
            "API-KEY": self.private_api_config.get('API_KEY'),
            "API-TIMESTAMP": timestamp,
            "API-SIGN": sign
        }
        return headers

    def get_url(self, url_type, sym=None):
        if url_type not in self.url_parts.keys():
            raise Exception("Url_type={0} is not allowed".format(url_type))

        target_url = urllib.parse.urljoin(
            self.url_parts["endpoint"], self.url_parts[url_type])
        if sym is not None:
            target_url = urllib.parse.urljoin(target_url, '?symbol={0}'.format(sym))
        else:
            pass
        self._logger.info("[DONE] Get URL string={0}".format(target_url))
        return target_url
    
    def fetch_data(self, target_url, headers=None, params=None):
        data = None
        try:
            response = requests.get(target_url,headers=headers, params=params)
            data = response.json()
            if data['status'] !=0:
                raise RequestError(data['messages'])
            self._logger.info("[DONE] Fetch Data. URL={0}".format(target_url))
        except RequestError as e:
            self._logger.error(e,exc_info=True)
            data = None        
        except Exception as e:
            raise Exception(e)

        return data

    def post_data(self, target_url, headers=None, data=None):
        try:
            response = requests.post(target_url,headers=headers, data=data)
            data = response.json()
            if data['status'] !=0:
                raise RequestError(data['messages'])
            self._logger.info("[DONE] Post Data. URL={0}".format(target_url))
        except RequestError as e:
            self._logger.error(e,exc_info=True)    
        except Exception as e:
            raise Exception(e)

        return data

class Orderbook(API):
    def __init__(self,sym,logger, general_config_ini,private_api_ini,general_config_mode="DEFAULT",private_api_mode="DEFAULT"):
        super().__init__(sym,logger, general_config_ini,private_api_ini,general_config_mode,private_api_mode)
        self.__depth=-1 # default: no limit

    def fetch(self, depth=None, return_type='dataframe', *args, **kwargs):
        target_url = self.get_url("orderbooks",self.sym)
        orderbook = self.fetch_data(target_url)

        if depth is None:
            depth = self.__depth
        if depth is -1:
            self._logger.warn("Try to fetch FUll Depth orderbook")

        data = self.convert_shape(orderbook, depth, return_type)
        self._logger.info("[DONE] Fetch orderbook. Depth={0}, Return_type={1}".format(depth, return_type))
        return data


    def convert_shape(self, raw_data, depth, return_type):

        #Depth
        for _side in ['asks','bids']:
                raw_data['data'][_side]= raw_data['data'][_side][:depth]
        # self._logger.info(raw_data['responsetime'])
        responsetime_dt = dl.str_utc_to_dt_offset(raw_data['responsetime'],self.tz_offset)

        if return_type is 'raw':
            return raw_data

        elif return_type is "dataframe":
            data = {}
            for _side in ['asks','bids']:
                data[_side]= pd.DataFrame(raw_data['data'][_side])
                data[_side] = data[_side].astype(float)
            return {"time":responsetime_dt ,'data':data}

        elif return_type in ['seq','json']:
            values=[responsetime_dt]
            keys = ['time']
            for _side in ["bids","asks"]:
                depth = len(raw_data['data'][_side])
                for _depth in range(depth):
                    values.append(float(raw_data['data'][_side][_depth]['price']))
                    values.append(float(raw_data['data'][_side][_depth]['size']))
                    keys.append(_side+str(_depth))
                    keys.append(_side+str(_depth)+'_size')
            
            if return_type is 'json':
                data = {_key :_value for _key, _value in zip(keys, values)}
                data['time'] = dl.dt_to_intYMDHMSF(data['time'])
            elif return_type is 'seq':
                data = values         

            return data

        else:
            raise InvalidArgumentError('Cannot accept return_type={0}'.format(return_type))

    @property
    def depth(self):
        pass

    @depth.setter
    def depth(self, depth):
        if depth is None:
            raise TypeError('Cannot accept None type')
        if type(depth) is not int:
            raise TypeError('Cannot accept {0} type'.format(type(depth)))
        self.__depth = depth


class Ticks(API):
    def __init__(self,sym,logger, general_config_ini,private_api_ini,general_config_mode="DEFAULT",private_api_mode="DEFAULT"):
        super().__init__(sym,logger, general_config_ini,private_api_ini,general_config_mode,private_api_mode)

    def fetch(self, depth=None, return_type='json', *args, **kwargs):
        target_url = self.get_url("tick",self.sym)
        tick = self.fetch_data(target_url)
        data = self.convert_shape(tick,return_type)
        self._logger.info("[DONE] Fetch ticks. Depth={0}, Return_type={1}".format(depth, return_type))
        return data

    def convert_shape(self, raw_data,return_type):
        if return_type is 'raw':
            return raw_data
        elif return_type is 'json':
            data = {}
            for _item in ['ask','bid','high','last','low','volume']:
                data[_item] =float(raw_data['data'][0][_item])
            data["timestamp"] = dl.dt_to_intYMDHMSF(
                dl.str_utc_to_dt_offset(raw_data['data'][0]["timestamp"],self.tz_offset))
            return data
        else:
            raise InvalidArgumentError('Cannot accept return_type={0}'.format(return_type))

class Trade(API):
    def __init__(self,sym,logger, general_config_ini,private_api_ini,general_config_mode="DEFAULT",private_api_mode="DEFAULT"):
        super().__init__(sym,logger, general_config_ini,private_api_ini,general_config_mode,private_api_mode)

    def fetch(self, return_type='json', since_time=None, *args, **kwargs):
        target_url = self.get_url("trade",self.sym)
        trade = self.fetch_data(target_url)

        latest_time = dl.str_utc_to_dt_offset(trade['data']['list'][0]["timestamp"],self.tz_offset)
        since_time = dl.str_utc_to_dt_offset(trade['data']['list'][-1]["timestamp"],self.tz_offset) if since_time is None else since_time
        data = self.convert_shape(trade, return_type, since_time)
        self._logger.info("[DONE] Fetch trade.  Return_type={0}".format(return_type))
        return data, latest_time

    def convert_shape(self, raw_data, return_type, since_time):

        if return_type is 'raw':
            self._logger.info("since_time is ignored due to return raw data")
            return raw_data
        elif return_type in ['json','dataframe']:
            data = []
            for _trade in raw_data['data']['list']:
                _trade["timestamp"] = dl.str_utc_to_dt_offset(_trade["timestamp"],self.tz_offset)
                if _trade["timestamp"] > since_time:
                    _trade['price'] = float(_trade['price'])   
                    _trade['size'] = float(_trade['size'])
                    data.append(_trade)
            if return_type in 'json':
                for i in range(len(data)):
                    data[i]["timestamp"] = dl.dt_to_intYMDHMSF(data[i]["timestamp"])
                return data
            if return_type in 'dataframe':
                return pd.DataFrame(data)
        else:
            raise InvalidArgumentError('Cannot accept return_type={0}'.format(return_type))


class Margin(API):
    def __init__(self,sym,logger, general_config_ini,private_api_ini,general_config_mode="DEFAULT",private_api_mode="DEFAULT"):
        super().__init__(sym,logger, general_config_ini,private_api_ini,general_config_mode,private_api_mode)

    def fetch(self, return_type='json', since_time=None, *args, **kwargs):
        target_url = self.get_url("margin")
        headers= self.make_header(self.url_parts['margin'].split('/private')[1], 'GET')
        margin = self.fetch_data(target_url,headers=headers)
        margin = self.convert_shape(margin, return_type)

        self._logger.info("[DONE] Fetch margin.  Return_type={0}".format(return_type))
        return margin

    def convert_shape(self, raw_data, return_type):
        responsetime_dt = dl.str_utc_to_dt_offset(raw_data['responsetime'],
            self.tz_offset,is_Z=True,is_ms=True)

        if return_type is 'raw':
            return raw_data
        elif return_type in ['json','dataframe']:
            for _key in raw_data['data'].keys():
                v = raw_data['data'][_key]
                if _key == 'marginCallStatus':
                    raw_data['data'][_key]=  v
                else:
                    raw_data['data'][_key]= float(v) 

            if return_type in 'json':
                self._logger.info(raw_data['data'])
                raw_data['responsetime']= dl.dt_to_intYMDHMSF(responsetime_dt)
                return raw_data['data']
            if return_type in 'dataframe':
                return pd.Series(raw_data['data'])
        else:
            raise InvalidArgumentError('Cannot accept return_type={0}'.format(return_type))

class Assets(API):
    def __init__(self,sym,logger, general_config_ini,private_api_ini,general_config_mode="DEFAULT",private_api_mode="DEFAULT"):
        super().__init__(sym,logger, general_config_ini,private_api_ini,general_config_mode,private_api_mode)

    def fetch(self, return_type='json', *args, **kwargs):
        target_url = self.get_url("assets")
        headers= self.make_header(self.url_parts['assets'].split('/private')[1], 'GET')
        assets = self.fetch_data(target_url,headers=headers)
        assets = self.convert_shape(assets, return_type)

        self._logger.info("[DONE] Fetch assets.  Return_type={0}".format(return_type))
        return assets

    def convert_shape(self, raw_data, return_type):
        # responsetime_dt = dl.str_utc_to_dt_offset(raw_data['responsetime'],self.tz_offset)

        if return_type is 'raw':
            return raw_data
        elif return_type in ['json','dataframe']:
            data = []
            for _symbol_data in raw_data['data']:
                _symbol_data['amount']= float(_symbol_data['amount'])   
                _symbol_data['available']= float(_symbol_data['available'])   
                _symbol_data['conversionRate']= float(_symbol_data['conversionRate'])   
                data.append(_symbol_data)
            if return_type in 'json':
                # for i in range(len(data)):
                #     data[i]["timestamp"] = dl.dt_to_intYMDHMSF(data[i]["timestamp"])
                json_obj = { _data['symbol']: _data for _data in data}
                return json_obj
            if return_type in 'dataframe':
                return pd.DataFrame(data)
        else:
            raise InvalidArgumentError('Cannot accept return_type={0}'.format(return_type))

class Orders(API):
    def __init__(self,sym,logger, general_config_ini,private_api_ini,general_config_mode="DEFAULT",private_api_mode="DEFAULT"):
        super().__init__(sym,logger, general_config_ini,private_api_ini,general_config_mode,private_api_mode)
        
    def fetch_by_orderId(self, orderId, return_type='json', *args, **kwargs):
        parameters = { "orderId": str(orderId) }
        target_url = self.get_url("orders")
        headers= self.make_header(self.url_parts['orders'].split('/private')[1], 'GET')
        orders = self.fetch_data(target_url,headers=headers,params=parameters)
        orders = self.convert_shape(orders, return_type)

        self._logger.info("[DONE] Fetch orders. orderId={0}, Return_type={1}".format(orderId, return_type))
        return orders

    def fetch_active(self, sym, return_type='json', *args, **kwargs):
        parameters = {
            "symbol": sym,
            "page": 1,
            "count": 10
        }
        target_url = self.get_url("activeOrders")
        headers= self.make_header(self.url_parts['activeOrders'].split('/private')[1], 'GET')
        activeOrders = self.fetch_data(target_url,headers=headers,params=parameters)
        activeOrders = self.convert_shape(activeOrders, return_type)

        self._logger.info("[DONE] Fetch activeOrders. Sym={0}, Return_type={1}".format(self.sym, return_type))
        return activeOrders

    def convert_shape(self, raw_data, return_type):
        # responsetime_dt = dl.str_utc_to_dt_offset(raw_data['responsetime'],self.tz_offset)

        if return_type is 'raw':
            return raw_data
        elif return_type in ['json','dataframe']:
            data = []
            if len(raw_data['data']) > 0:
                for _order in raw_data['data']['list']:
                    _order['executedSize']= float(_order['executedSize'])   
                    _order['losscutPrice']= float(_order['losscutPrice'])   
                    _order['orderId']= int(_order['orderId'])
                    _order['price']= float(_order['price'])   
                    _order['rootOrderId']= int(_order['rootOrderId'])
                    _order['size']= float(_order['size'])   
                    _order['timestamp']= dl.str_utc_to_dt_offset(_order["timestamp"],self.tz_offset)
                    data.append(_order)
            if return_type in 'json':
                for i in range(len(data)):
                    data[i]["timestamp"] = dl.dt_to_intYMDHMSF(data[i]["timestamp"])
                return data
            if return_type in 'dataframe':
                return pd.DataFrame(data)
        else:
            raise InvalidArgumentError('Cannot accept return_type={0}'.format(return_type))
        

class Executions(API):
    def __init__(self,sym,logger, general_config_ini,private_api_ini,general_config_mode="DEFAULT",private_api_mode="DEFAULT"):
        super().__init__(sym,logger, general_config_ini,private_api_ini,general_config_mode,private_api_mode)

    def fetch_by_id(self, orderId=None,executionId=None, return_type='json', *args, **kwargs):

        parameters={}
        if orderId is not None:
            parameters["orderId"] =orderId 
        if executionId is not None:
            parameters["executionId"] =executionId 
        if len(parameters.keys()) >1:
            raise Exception("Cannot set both orderId and executionId. Needs to set either key.")
        if len(parameters.keys()) ==0:
            raise Exception("Needs to set either orderId or executionId ")
        target_url = self.get_url("executions")
        headers= self.make_header(self.url_parts['executions'].split('/private')[1], 'GET')
        executions = self.fetch_data(target_url,headers=headers,params=parameters)
        executions = self.convert_shape(executions, return_type)

        self._logger.info("[DONE] Fetch executions. orderId={0},  executionId={1},  Return_type={2}".format(orderId, executionId, return_type))
        return executions

    def fetch_latestExecutions(self,sym, count=100, return_type='json', *args, **kwargs):
        parameters = {
            "symbol": sym,
            "page": 1,
            "count": 100
        }
        target_url = self.get_url("latestExecutions")
        headers= self.make_header(self.url_parts['latestExecutions'].split('/private')[1], 'GET')
        latestExecutions = self.fetch_data(target_url,headers=headers,params=parameters)
        latestExecutions = self.convert_shape(latestExecutions, return_type)

        self._logger.info("[DONE] Fetch latestExecutions.  Sym={0}, Return_type={1}".format(sym, return_type))
        return latestExecutions

    def convert_shape(self, raw_data, return_type):
        # responsetime_dt = dl.str_utc_to_dt_offset(raw_data['responsetime'],self.tz_offset)

        if return_type is 'raw':
            return raw_data
        elif return_type in ['json','dataframe']:
            data = []
            if not len(raw_data['data']) == 0:
                for _execution in raw_data['data']['list']:
                    _execution['executionId']= int(_execution['executionId'])
                    _execution['orderId']= int(_execution['orderId'])
                    _execution['price']= float(_execution['price'])   
                    _execution['size']= float(_execution['size'])   
                    _execution['lossGain']= float(_execution['lossGain'])   
                    _execution['fee']= float(_execution['fee'])   
                    _execution['timestamp']= dl.str_utc_to_dt_offset(_execution["timestamp"],self.tz_offset)
                    data.append(_execution)
            if return_type in 'json':
                for i in range(len(data)):
                    data[i]["timestamp"] = dl.dt_to_intYMDHMSF(data[i]["timestamp"])
                return data
            if return_type in 'dataframe':
                return pd.DataFrame(data)
        else:
            raise InvalidArgumentError('Cannot accept return_type={0}'.format(return_type))
      

class Order(API):
    def __init__(self,sym,logger, general_config_ini,private_api_ini,general_config_mode="DEFAULT",private_api_mode="DEFAULT"):
        super().__init__(sym,logger, general_config_ini,private_api_ini,general_config_mode,private_api_mode)

    def validate_order_params(self, reqBody):
        # Sym
        if type(reqBody["symbol"]) is not str:
            raise Exception("symbol must be string. you set type={0}".format(type(reqBody["symbol"])))
        if reqBody["symbol"] is None:
            raise Exception("symbol must be set")
        if reqBody["symbol"] not in eval(self.general_config.get("ALLOW_SYM")):
            raise Exception("Order validation error. Invalid Sym={0}".format(reqBody["symbol"]))

        # side
        if type(reqBody["side"]) is not str:
            raise Exception("symbol must be string. you set type={0}".format(type(reqBody["symbol"])))
        if reqBody["side"] is None:
            raise Exception("side must be set")
        if reqBody["side"] not in eval(self.general_config.get("EXEC_SIDE")):
            raise Exception("Order validation error. Invalid Side={0}".format(reqBody["side"]))

        # executionType
        if type(reqBody["executionType"]) is not str:
            raise Exception("symbol must be string. you set type={0}".format(type(reqBody["symbol"])))
        if reqBody["executionType"] is None:
            raise Exception("executionType must be set")
        if reqBody["executionType"] not in eval(self.general_config.get("EXEC_TYPE")):
            raise Exception("Order validation error. Invalid executionType={0}".format(reqBody["executionType"]))
        
        # timeInForce
        if reqBody["timeInForce"] is None:
            if reqBody["executionType"] in ['MARKET','STOP']:
                reqBody["timeInForce"] = 'FAK'
                self._logger.info("timeInForce is set automatically=FAK")
            if reqBody["executionType"] in ['LIMIT']:
                reqBody["timeInForce"] = 'FAS'
                self._logger.info("timeInForce is set automatically=FAS") 
        if type(reqBody["timeInForce"]) is not str:
            raise Exception("symbol must be string. you set type={0}".format(type(reqBody["symbol"])))
        if reqBody["timeInForce"] not in eval(self.general_config.get("TIME_IN_FORCE")):
            raise Exception("Order validation error. Invalid timeInForce={0}".format(reqBody["timeInForce"]))
        if reqBody["timeInForce"] == 'FAK':
            if reqBody["executionType"] not in ["MARKET","STOP"]:
                raise Exception("Order validation error. executionType must be in MARKET or STOP when TimeInForce=FAK, but you set executionType={0}".format(reqBody["executionType"]))
        if reqBody["timeInForce"] in ["FOK",'FAS','SOK']:
            if reqBody["executionType"] not in ["LIMIT"]:
                raise Exception("Order validation error. executionType must be in LIMIT when TimeInForce={0}, but you set executionType={1}".format(reqBody["timeInForce"], reqBody["executionType"]))
            if reqBody["timeInForce"] == "SOK":
                if reqBody["symbol"] not in eval(self.general_config.get("LISTED_SYM")):
                    if reqBody["symbol"] != "BTC_JPY":
                        raise Exception("Order validation error. timeInForce can be set SOK when symbol is in spot symbols or BTC_JPY, you set={0}".format(reqBody["symbol"]))
        
        # price
        if reqBody["executionType"] in ["LIMIT",'STOP']:
            if reqBody["price"] is None:
                raise Exception("Price must be set.")
            if reqBody["price"] < 0.0:
                raise Exception("Price must be >0. you set = {0}".format(reqBody["price"]))
            reqBody["price"] = str(reqBody["price"])
        else:
            reqBody["price"] = None

        # losscutPrice
        if reqBody["losscutPrice"] is not None:
            if reqBody["symbol"] not in eval(self.general_config.get("LISTED_REV_SYM")):
                raise Exception("losscutPrice must be set when symbol is in LISTED_REV_SYM")
            if reqBody["executionType"] not in ["LIMIT",'STOP']:
                raise Exception("losscutPrice must be set when executionType is in LIMIT or STOP")
            if reqBody["executionType"] < 0.0:
                raise Exception("executionType must be >0. you set = {0}".format(reqBody["executionType"]))
            
            reqBody["losscutPrice"] = str(reqBody["losscutPrice"])
        else:
            reqBody["losscutPrice"] = None

        # size
        if reqBody["size"] is None:
            raise Exception("size must be set")
        if reqBody["size"] < 0.0:
            raise Exception("size must be >0. you set = {0}".format(reqBody["size"]))
        reqBody["size"] = str(reqBody["size"])

        # excl none
        reqBody = {_key :_val for _key, _val in reqBody.items() if _val is not None}
        self._logger.info("[DONE] Order parameter validation: OK")
        return reqBody

    def validate_change_params(self, reqBody):
        if reqBody["price"] is None:
            raise Exception("Price must be set.")
        if reqBody["price"] < 0.0:
            raise Exception("Price must be >0. you set = {0}".format(reqBody["price"]))
        reqBody["price"] = str(reqBody["price"])

        if reqBody["losscutPrice"] is not None:
            if reqBody["losscutPrice"] < 0.0:
                raise Exception("losscutPrice must be >0. you set = {0}".format(reqBody["losscutPrice"]))
            reqBody["losscutPrice"] = str(reqBody["losscutPrice"])
        else:
            reqBody["losscutPrice"] = None


        if reqBody["orderId"] is None:
            raise Exception("orderId must be set.")

         # excl none
        reqBody = {_key :_val for _key, _val in reqBody.items() if _val is not None}
        self._logger.info("[DONE] Change order parameter validation: OK")
        return reqBody     

    def validate_cancel_params(self, reqBody):
        if reqBody["orderId"] is None:
            raise Exception("orderId must be set.")

         # excl none
        reqBody = {_key :_val for _key, _val in reqBody.items() if _val is not None}
        self._logger.info("[DONE] Cancel order parameter validation: OK")
        return reqBody       

    def do_order(self,return_type='json', *args, **order_kwargs):
        try:
            reqBody = {
                "symbol": order_kwargs["symbol"],
                "side": order_kwargs["side"],
                "executionType": order_kwargs["executionType"],
                "timeInForce": order_kwargs["timeInForce"],
                "price": order_kwargs["price"],
                "losscutPrice": order_kwargs["losscutPrice"],
                "size": order_kwargs["size"]
            }
            reqBody = self.validate_order_params(reqBody)
            target_url = self.get_url("order")
            dumped_req_body = json.dumps(reqBody)
            headers= self.make_header(self.url_parts['order'].split('/private')[1], 'POST', request_body=dumped_req_body)
            order = self.post_data(target_url,headers=headers,data=dumped_req_body)
            if order['status'] == 0 :
                self._logger.info("[DONE] Post order. OrderId={0}, reqBody={1}".format(order['data'], json.dumps(reqBody)))
            else :
                self._logger.error("Reject to post order. reqBody={0}".format(json.dumps(reqBody)))
            return order

        except Exception as e:
            self._logger.error("Fail to post order: {0}".format(e),exc_info=True)
        

    def do_change(self,return_type='json', *args, **order_kwargs):
        try:
            reqBody = {
                "orderId": order_kwargs["orderId"],
                "price": order_kwargs["price"],
                "losscutPrice": order_kwargs["losscutPrice"],
            }
            reqBody = self.validate_change_params(reqBody)
            target_url = self.get_url("changeOrder")
            dumped_req_body = json.dumps(reqBody)
            headers= self.make_header(self.url_parts['changeOrder'].split('/private')[1], 'POST', request_body=dumped_req_body)
            order = self.post_data(target_url,headers=headers,data=dumped_req_body)
            if order['status'] == 0 :
                self._logger.info("[DONE] Change order. OrderId={0}, reqBody={1}".format(order_kwargs["orderId"], json.dumps(reqBody)))
            else :
                self._logger.error("Rejject to Change order. OrderId={0}, reqBody={1}".format(order_kwargs["orderId"], json.dumps(reqBody)))
            return order

        except Exception as e:
            self._logger.error("Fail to change order: {0}".format(e),exc_info=True)

    def do_cancel(self,return_type='json', *args, **order_kwargs):
        try:
            reqBody = {
                "orderId": order_kwargs["orderId"],
            }
            reqBody = self.validate_cancel_params(reqBody)
            target_url = self.get_url("cancelOrder")
            dumped_req_body = json.dumps(reqBody)
            headers= self.make_header(self.url_parts['cancelOrder'].split('/private')[1], 'POST', request_body=dumped_req_body)
            order = self.post_data(target_url,headers=headers,data=dumped_req_body)
            if order['status'] == 0 :
                self._logger.info("[DONE] Cancel order. OrderId={0}, reqBody={1}".format(order_kwargs["orderId"], json.dumps(reqBody)))
            else :
                self._logger.error("Reject to cancel order. OrderId={0}, reqBody={1}".format(order_kwargs["orderId"], json.dumps(reqBody)))
            return order

        except Exception as e:
            self._logger.error("Fail to cancel order: {0}".format(e),exc_info=True)

