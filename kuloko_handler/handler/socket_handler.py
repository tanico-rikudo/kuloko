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

from ..util import daylib
dl = daylib.daylib()

import websocket
from collections import deque
import threading
websocket.enableTrace(True) #trace ON


class RequestError(Exception):
    pass

class InvalidArgumentError(Exception):
    pass

class Socket(object):
    def __init__(self,channel,logger, general_config_ini,private_api_ini,general_config_mode="DEFAULT",private_api_mode="DEFAULT"):
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

        self.channel = channel
        self.load_urls()

    def load_config(self,general_config_ini,private_api_ini,general_config_mode,private_api_mode):
        self.private_api_config = private_api_ini[private_api_mode]
        self.general_config = general_config_ini[general_config_mode]
        self._logger.info('[DONE]Load Config. Private API:[{0}] General:[{1}]'
            .format(private_api_mode,general_config_mode))

    def set_config(self):
        self.allow_sym = eval(self.general_config.get('ALLOW_SYM'))
        self.tz_offset = self.general_config.getint('TIMEZONE_OFFSET_HOUR')
        self._logger.info('[DONE]Set Config from loaded config')

    def load_urls(self):
        self.url_parts = {
            'endpoint':self.general_config.get('ENDPOINT_URL'),
            'socket_endpoint':self.general_config.get('SOCKET_ENDPOINT_URL'),
            'public':self.general_config.get('SOCKET_PUBLIC_URL'),
            'private':self.general_config.get('SOCKET_PRIVATE_URL'),
            'socket_access_token':self.general_config.get('SOCKET_ACCESS_TOKEN'),
        }
        self._logger.info('[DONE]Set URL parts')

    def get_url(self):
        path = os.path.join(self.url_parts['socket_endpoint'],self.url_parts['public'])
        return path


    def connect(self,url,sym,maxlen=100):
        self.url = url
        self.maxlen =maxlen
        self.sym = sym
        self.queue = deque([],self.maxlen)
        self.ws = websocket.WebSocketApp(
            url,
            on_message = self.on_message,on_open=self.on_open,
            on_error = self.on_error, on_close = self.on_close)
        self._logger.info("Socket Connected")
    
    def subscribe(self):
        self.ws.keep_running = True 
        self.thread = threading.Thread(target=lambda: self.ws.run_forever())
        self.thread.daemon = True
        self.thread.start()
        self._logger.info("Start to subscribe")

    def is_connected(self):
        flag =  self.ws.sock and self.ws.sock.connected
        self._logger.info("Is connected:{0}".format(flag))

    def disconnect(self):
        self.ws.keep_running = False
        self.ws.close()
        self._logger.info("Socket closed")

    def get(self):
        queue_len = len(self.queue)
        return [ self.queue.popleft() for _ in range(queue_len)]

    def clean_data(self, return_data):
        for _i in range(return_data):
            return_data[_i]['timestamp'] =return_data[_i]['timestamp']
            return_data[_i]['price'] =return_data[_i]['price']
            return_data[_i]['size'] =return_data[_i]['size']
        return return_data

    def on_message(self, message):
        self._logger.info('Received:{0}'.format(message))
        self.queue.append(json.loads(message))
        if len(self.queue) > self.maxlen:
            self._logger.warn("Message queue is full. Old item are discarded")

    def on_error(self, error):
        self._logger.error('Try reconnect {0}'.format(error),exc_info=True)
        self.disconnect()
        time.sleep(0.5)
        self.connect(self.url , self.sym)

    def on_close(self):
        message = {
            "command": "unsubscribe",
            "channel": self.channel,
            "symbol": self.sym 
        }
        self.ws.send(json.dumps(message))
        self._logger.info('Websocket disconnected')

    def on_open(self):
        message = {
            "command": "subscribe",
            "channel": self.channel,
            "symbol": self.sym 
        }
        self.ws.send(json.dumps(message))
        self._logger.info('Socket opened')


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

    def get_access_token(self):
        reqBody = {}
        path = self.url_parts["socket_access_token"]
        endPoint = self.url_parts["endpoint"]
        headers= self.make_header(path.split('/private')[1],'POST',json.dumps(reqBody))
        target_url=endPoint+path
        try:
            response = requests.post(target_url, headers=headers, data=json.dumps(reqBody))
            data = response.json()
            if data['status'] !=0:
                raise RequestError(data['messages'])
            self.token=data['data']
            self._logger.info("[DONE] GET Socket Access token. URL={0}".format(target_url))

        except RequestError as e:
            self._logger.error(e,exc_info=True)
  
        except Exception as e:
            raise Exception(e)

        return 

    def extend_access_token(self):
        reqBody = {'token':self.token}
        path = self.url_parts["socket_access_token"]
        endPoint = self.url_parts["endpoint"]
        headers= self.make_header(path.split('/private')[1],'PUT')
        target_url=endPoint+path
        try:
            response = requests.put(target_url, headers=headers, data=json.dumps(reqBody))
            data = response.json()
            if data['status'] !=0:
                raise RequestError(data['messages'])
            self._logger.info("[DONE] Extend Socket Access token. URL={0}".format(target_url))
        except RequestError as e:
            self._logger.error(e,exc_info=True)
            # data = None        
        except Exception as e:
            raise Exception(e)

        return 

class Trade(Socket):
    def __init__(self,logger, general_config_ini,private_api_ini):
        super().__init__("trades",logger, general_config_ini,private_api_ini)

    def convert_shape(self, raw_data, return_type):
        if return_type is 'raw':
            return raw_data
        elif return_type in ['json','dataframe']:
            data = []
            for _trade in raw_data:
                _trade["timestamp"] = dl.str_utc_to_dt_offset(_trade["timestamp"],self.tz_offset)
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
    

class Orderbooks(Socket):
    def __init__(self,logger, general_config_ini,private_api_ini):
        super().__init__("orderbooks",logger, general_config_ini,private_api_ini)
    


class Ticker(Socket):
    def __init__(self,logger, general_config_ini,private_api_ini):
        super().__init__("ticker",logger, general_config_ini,private_api_ini)
