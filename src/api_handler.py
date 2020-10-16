import requests
import json
import urllib.parse
import logging
import logging.config

import pandas as pd
import numpy as np

from datetime import datetime as dt


ALLOW_SYM=['BTC']
logging.config.fileConfig('./ini/logconfig.ini')
logger = logging.getLogger("KULOKO")

class RequestError(Exception):
    pass

class InvalidArgumentError(Exception):
    pass



class API:

    def __init__(self):
        self.load_urls()
        pass

    def load_urls(self):
        # todo: move onto config

        ENDPOINT = 'https://api.coin.z.com'
        TICK     = '/public/v1/ticker'
        TRADE     = '/public/v1/trades'
        ORDERBOOKS     = '/public/v1/orderbooks'
        self.url_parts = {
            'endpoint':ENDPOINT,
            'tick':TICK,
            'orderbooks':ORDERBOOKS,
            'trade':TRADE,
        }
        logger.info('[DONE]Set url parts')

    def get_url(self, url_type, sym):
        if url_type not in self.url_parts.keys():
            raise Exception("Url_type={0} is not allowed".format(url_type))

        base_url = urllib.parse.urljoin(self.url_parts["endpoint"], self.url_parts[url_type])
        target_url = urllib.parse.urljoin(base_url, '?symbol={0}'.format(sym))
        logger.info("[DONE] Get URL string={0}".format(target_url))
        return target_url
    
    def fetch_data(self, url_type, sym):
        data = None
        try:
            target_url = self.get_url(url_type,sym)
            response = requests.get(target_url)
            data = response.json()
            if data['status'] !=0:
                raise RequestError(data['messages'])
            logger.info("[DONE] Fetch Data. URL={0}".format(target_url))
        except RequestError as e:
            logger.error(e,exc_info=True)           
        except Exception as e:
            raise Exception(e)

        return data

# todo: API is as parent 
class Orderbook():
    def __init__(self):
        self.__sym = None
        self.__rest_api = None 
        self.__depth=-1 # default: no limit

    def fetch(self, depth=None, return_type='dataframe', *args, **kwargs):

        orderbook = self.__rest_api.fetch_data("orderbooks",self.__sym)

        if depth is None:
            depth = self.__depth
        if depth is -1:
            logger.warn("Try to fetch FUll Depth orderbook")

        data = self.convert_shape(orderbook, depth, return_type)
        logger.info("[DONE] Fetch orderbook. Depth={0}, Return_type={1}".format(depth, return_type))
        return data


    def convert_shape(self, raw_data, depth, return_type):

        #Depth
        for _side in ['asks','bids']:
                raw_data['data'][_side]= raw_data['data'][_side][:depth]
        
        responsetime_dt = dt.strptime(raw_data['responsetime'],'%Y-%m-%dT%H:%M:%S.%fZ')

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
            for _size in ["bids","asks"]:
                depth = len(raw_data['data'][_side])
                for _depth in range(depth):
                    values.append(float(raw_data['data'][_side][_depth]['price']))
                    values.append(float(raw_data['data'][_side][_depth]['size']))
                    keys.append(_size+str(_depth))
                    keys.append(_size+str(_depth)+'_size')
            
            if return_type is 'json':
                data = {_key :_value for _key, _value in zip(keys, values)}
            elif return_type is 'seq':
                data = values         

            return data

        else:
            raise InvalidArgumentError('Cannot accept return_type={0}'.format(return_type))

        
    @property
    def sym(self):
        pass

    @sym.setter
    def sym(self, sym):
        if sym is None:
            raise TypeError('Cannot accept None type')
        if sym not in ALLOW_SYM:
            raise Exception("sym={0} is not allowed".format(sym))
        self.__sym = sym

    @property
    def depth(self):
        pass

    @depth.setter
    def depth(self, depth):
        if depth is None:
            raise TypeError('Cannot accept None type')
        if type(depth) is not int:
            raise TypeError('Cannot accept {0} type'.format(type(sym)))
        self.__depth = depth

    @property
    def rest_api(self):
        pass

    @rest_api.setter
    def rest_api(self, api):
        if api is None:
            raise TypeError('invalid api obj')
        self.__rest_api = api


class Ticks():
    def __init__(self):
        self.__sym = None
        self.__rest_api = None 

    def fetch(self, depth=None, return_type='json', *args, **kwargs):
        tick = self.__rest_api.fetch_data("tick",self.__sym)
        data = self.convert_shape(tick,return_type)
        logger.info("[DONE] Fetch ticks. Depth={0}, Return_type={1}".format(depth, return_type))
        return data

    def convert_shape(self, raw_data,return_type):
        if return_type is 'raw':
            return raw_data
        elif return_type is 'json':
            data = {}
            for _item in ['ask','bid','high','last','low','volume']:
                data[_item] =float(raw_data['data'][0][_item])
            data["timestamp"] = dt.strptime(raw_data['data'][0]["timestamp"],'%Y-%m-%dT%H:%M:%S.%fZ')
            return data
        else:
            raise InvalidArgumentError('Cannot accept return_type={0}'.format(return_type))
        
    @property
    def sym(self):
        pass

    @sym.setter
    def sym(self, sym):
        if sym is None:
            raise TypeError('Cannot accept None type')
        if sym not in ALLOW_SYM:
            raise Exception("sym={0} is not allowed".format(sym))
        self.__sym = sym

    @property
    def rest_api(self):
        pass

    @rest_api.setter
    def rest_api(self, api):
        if api is None:
            raise TypeError('invalid api obj')
        self.__rest_api = api
    def __init__(self):
        self.__sym = None
        self.__rest_api = None 

    def fetch(self, depth=None, return_type='json', *args, **kwargs):
        tick = self.__rest_api.fetch_data("tick",self.__sym)
        data = self.convert_shape(tick,return_type)
        logger.info("[DONE] Fetch ticks. Depth={0}, Return_type={1}".format(depth, return_type))
        return data

    def convert_shape(self, raw_data,return_type):
        if return_type is 'raw':
            return raw_data
        elif return_type is 'json':
            data = {}
            for _item in ['ask','bid','high','last','low','volume']:
                data[_item] =float(raw_data['data'][0][_item])
            data["timestamp"] = dt.strptime(raw_data['data'][0]["timestamp"],'%Y-%m-%dT%H:%M:%S.%fZ')
            return data
        else:
            raise InvalidArgumentError('Cannot accept return_type={0}'.format(return_type))
        
    @property
    def sym(self):
        pass

    @sym.setter
    def sym(self, sym):
        if sym is None:
            raise TypeError('Cannot accept None type')
        if sym not in ALLOW_SYM:
            raise Exception("sym={0} is not allowed".format(sym))
        self.__sym = sym

    @property
    def rest_api(self):
        pass

    @rest_api.setter
    def rest_api(self, api):
        if api is None:
            raise TypeError('invalid api obj')
        self.__rest_api = api

class Trade():
    def __init__(self):
        self.__sym = None
        self.__rest_api = None 

    def fetch(self, return_type='json', since_time=None, *args, **kwargs):
        tick = self.__rest_api.fetch_data("trade",self.__sym)
        latest_time = dt.strptime(tick['data']['list'][0]["timestamp"],'%Y-%m-%dT%H:%M:%S.%fZ')
        since_time = dt.strptime(tick['data']['list'][-1]["timestamp"],'%Y-%m-%dT%H:%M:%S.%fZ') if since_time is None else since_time
        data = self.convert_shape(tick, return_type, since_time)
        logger.info("[DONE] Fetch trade.  Return_type={0}".format(return_type))
        return data, latest_time

    def convert_shape(self, raw_data, return_type, since_time):

        if return_type is 'raw':
            logger.info("since_time is ignored due to return raw data")
            return raw_data
        elif return_type in ['json','dataframe']:
            data = []
            for _trade in raw_data['data']['list']:
                _trade["timestamp"] = dt.strptime(_trade["timestamp"],'%Y-%m-%dT%H:%M:%S.%fZ')
                if _trade["timestamp"] > since_time:
                    _trade['price'] = float(_trade['price'])   
                    _trade['size'] = float(_trade['size'])
                    data.append(_trade)
            if return_type in 'json':
                return data
            if return_type in 'dataframe':
                return pd.DataFrame(data)
        else:
            raise InvalidArgumentError('Cannot accept return_type={0}'.format(return_type))
        
    @property
    def sym(self):
        pass

    @sym.setter
    def sym(self, sym):
        if sym is None:
            raise TypeError('Cannot accept None type')
        if sym not in ALLOW_SYM:
            raise InvalidArgumentError("sym={0} is not allowed".format(sym))
        self.__sym = sym

    @property
    def rest_api(self):
        pass

    @rest_api.setter
    def rest_api(self, api):
        if api is None:
            raise TypeError('invalid api obj')
        self.__rest_api = api