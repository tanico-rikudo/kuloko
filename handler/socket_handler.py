# coding: utf-8
import urllib.parse
import configparser

import pandas as pd
import numpy as np

import requests
import json
import os
import sys

import time
from datetime import datetime as dt
from datetime import timedelta, timezone

import hmac
import hashlib

import websocket
from collections import deque
import threading

websocket.enableTrace(True)  # trace ON

sys.path.append(os.environ["COMMON_DIR"])
from util import daylib
from util.config import ConfigManager

cm = ConfigManager(os.environ["KULOKO_INI"])
dl = daylib.daylib()


class RequestError(Exception):
    pass


class InvalidArgumentError(Exception):
    pass


class Socket(object):
    def __init__(
        self,
        channel,
        logger,
        general_config_ini,
        private_api_ini,
        general_config_mode="DEFAULT",
        private_api_mode="DEFAULT",
    ):
        self._logger = logger
        self.load_config(
            general_config_ini, private_api_ini, general_config_mode, private_api_mode
        )
        self.set_config()

        self.private_api_ini = private_api_ini

        self.channel = channel
        self.load_urls()
        self.ws = None

    def __del__(self):
        self.disconnect()
        self._logger.info("[DONE] Socket Instance deleted.")

    def load_config(
        self, general_config_ini, private_api_ini, general_config_mode, private_api_mode
    ):
        if general_config_ini is None:
            self.general_config = cm.load_ini_config(
                path=None, config_name="general", mode=general_config_mode
            )
        else:
            self.general_config = general_config_ini[general_config_mode]
        self._logger.info(f"[DONE]Load General Config. Mode={general_config_mode}")

        if private_api_ini is None:
            private_api_ini = cm.load_ini_config(
                path=None, config_name="private_api", mode=private_api_mode
            )
        else:
            private_api_config = private_api_ini[private_api_mode]
        self._logger.info(f"[DONE]Load Private API Config. Mode={private_api_mode}")

    def set_config(self):
        self.allow_sym = eval(self.general_config.get("ALLOW_SYM"))
        self.tz = self.general_config.get("TIMEZONE")
        self._logger.info("[DONE]Set Config from loaded config")

    def load_urls(self):
        self.url_parts = {
            "endpoint": self.general_config.get("ENDPOINT_URL"),
            "socket_public_endpoint": self.general_config.get("SOCKET_PUBLIC_ENDPOINT"),
            "private": self.general_config.get("SOCKET_PRIVATE_URL"),
            "socket_access_token": self.general_config.get("SOCKET_ACCESS_TOKEN"),
        }
        self._logger.info("[DONE]Set URL parts")

    def get_public_socket_url(self):
        return self.url_parts["socket_public_endpoint"]

    def get_private_socket_url(self):
        return self.url_parts["private"]

    def connect(self, url, sym, maxlen=100, opt_open_message=None):
        self.url = url
        self.maxlen = maxlen
        self.sym = sym
        self.opt_open_message = opt_open_message if opt_open_message is not None else {}
        self.queue = deque([], self.maxlen)
        self.ws = websocket.WebSocketApp(
            url,
            on_message=self.on_message,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self._logger.info(f"Socket Connected. Channel={self.channel}")

    def subscribe(self):
        self.ws.keep_running = True
        self.thread = threading.Thread(target=lambda: self.ws.run_forever())
        self.thread.daemon = True
        self.thread.start()
        self._logger.info(f"Start to subscribe. Channel={self.channel}")

    def is_connected(self):
        flag = False
        if self.ws is not None:
            flag = self.ws.sock and self.ws.sock.connected
        self._logger.info(
            "Connection :{0}".format("Connected" if flag else "Disconnected")
        )
        return flag

    def disconnect(self):
        self.ws.keep_running = False
        self.ws.close()
        self._logger.info(f"Socket closed. Channel={self.channel}")

    def get(self):
        """DeQue data possesing at present

        Returns:
            obj list : data list
        """
        queue_len = len(self.queue)
        return [self.queue.popleft() for _ in range(queue_len)]

    def clean_data(self, return_data):
        for _i in range(return_data):
            return_data[_i]["timestamp"] = return_data[_i]["timestamp"]
            return_data[_i]["price"] = return_data[_i]["price"]
            return_data[_i]["size"] = return_data[_i]["size"]
        return return_data

    def reconnect(self):
        try:
            self.disconnect()
        except:
            pass

        try:
            self.connect(self.url, self.sym, self.opt_open_message)
        except:
            pass

        try:
            self.subscribe()
        except:
            pass

    def on_message(self, ws, message):
        # self._logger.info('Received:{0}'.format(message))
        self._logger.debug("Received: Channel={0}".format(self.channel))
        self.queue.append(json.loads(message))
        if len(self.queue) > self.maxlen:
            self._logger.warning(
                f"Message queue is full. Old item are discarded. Channel={self.channel}"
            )

    def on_error(self, ws, error):
        self._logger.error("Try reconnect... {0}".format(error), exc_info=True)
        self.disconnect()
        time.sleep(0.5)
        self.connect(self.url, self.sym, self.opt_open_message)

    def on_close(self, ws, close_status_code, close_msg):
        """
        Post process after close
        :param ws: web socket
        :param close_status_code:
        :param close_msg:
        :return:
        """
        # message = {
        #     "command": "disconnected",
        #     "channel": self.channel,
        #     "symbol": self.sym,
        # }
        # self.ws.send(json.dumps(message))
        self._logger.info(f"Websocket disconnected. Channel={self.channel}")

    def on_open(self, ws):
        message = {"command": "subscribe", "channel": self.channel, "symbol": self.sym}
        message.update(self.opt_open_message)
        self.ws.send(json.dumps(message))
        self._logger.info(f"Socket opened. Open messge={message}")

    def make_header(self, access_path, access_method, request_body=""):
        timestamp = "{0}000".format(int(time.mktime(dt.now().timetuple())))
        send_text = timestamp + access_method + access_path + request_body

        sign = hmac.new(
            bytes(self.private_api_ini.get("API_SEC").encode("ascii")),
            bytes(send_text.encode("ascii")),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "API-KEY": self.private_api_ini.get("API_KEY"),
            "API-TIMESTAMP": timestamp,
            "API-SIGN": sign,
        }

        return headers

    def get_access_token(self):
        reqBody = {}
        path = self.url_parts["private"]
        endPoint = self.url_parts["endpoint"]
        headers = self.make_header(
            path.split("/private")[1], "POST", json.dumps(reqBody)
        )
        target_url = endPoint + path
        try:
            response = requests.post(
                target_url, headers=headers, data=json.dumps(reqBody)
            )
            data = response.json()
            if data["status"] != 0:
                raise RequestError(data["messages"])
            self.token = data["data"]
            self._logger.info(
                "[DONE] GET Socket Access token. URL={0}".format(target_url)
            )

        except RequestError as e:
            self._logger.error(e, exc_info=True)

        except Exception as e:
            raise Exception(e)

        return

    def error_handle(self, raw_data):
        if "error" in raw_data.keys():
            self._logger.warning("{0}".format(raw_data["error"]))
            return None
        else:
            return raw_data

    def extend_access_token(self):
        reqBody = {"token": self.token}
        path = self.url_parts["private"]
        endPoint = self.url_parts["endpoint"]
        headers = self.make_header(path.split("/private")[1], "PUT")
        target_url = endPoint + path
        try:
            response = requests.put(
                target_url, headers=headers, data=json.dumps(reqBody)
            )
            data = response.json()
            if data["status"] != 0:
                raise RequestError(data["messages"])
            self._logger.info(
                "[DONE] Extend Socket Access token. URL={0}".format(target_url)
            )
        except RequestError as e:
            self._logger.error(e, exc_info=True)
            # data = None
        except Exception as e:
            raise Exception(e)

        return


class Trade(Socket):
    def __init__(
        self,
        logger,
        general_config_ini,
        private_api_ini,
        general_config_mode="DEFAULT",
        private_api_mode="DEFAULT",
    ):
        super().__init__(
            "trades",
            logger,
            general_config_ini,
            private_api_ini,
            general_config_mode="DEFAULT",
            private_api_mode="DEFAULT",
        )

    def convert_shape(self, raw_data, return_type):
        raw_data = self.error_handle(raw_data)
        if raw_data is None:
            return {}

        data = raw_data
        if return_type is "raw":
            return raw_data
        elif return_type in ["json", "dataframe"]:
            # print(raw_data)
            data["time"] = dl.str_utc_to_dt_offset(raw_data["timestamp"], self.tz)
            del data["timestamp"]
            data["price"] = float(raw_data["price"])
            data["size"] = float(raw_data["size"])
            if return_type in "json":
                data["time"] = dl.dt_to_strYMDHMSF(data["time"])
                return data
            if return_type in "dataframe":
                return pd.DataFrame(data)
        else:
            raise InvalidArgumentError(
                "Cannot accept return_type={0}".format(return_type)
            )


class Orderbooks(Socket):
    def __init__(
        self,
        logger,
        general_config_ini,
        private_api_ini,
        general_config_mode="DEFAULT",
        private_api_mode="DEFAULT",
    ):
        super().__init__(
            "orderbooks",
            logger,
            general_config_ini,
            private_api_ini,
            general_config_mode="DEFAULT",
            private_api_mode="DEFAULT",
        )

    def convert_shape(self, raw_data, depth, return_type):
        raw_data = self.error_handle(raw_data)
        if raw_data is None:
            return {}
        # Filter Depth
        for _side in ["asks", "bids"]:
            raw_data[_side] = raw_data[_side][:depth]
        time_dt = dl.str_utc_to_dt_offset(raw_data["timestamp"], self.tz)
        symbol = raw_data["symbol"]

        if return_type is "raw":
            return raw_data

        elif return_type is "dataframe":
            data = {}
            for _side in ["asks", "bids"]:
                data[_side] = pd.DataFrame(raw_data[_side])
                data[_side] = data[_side].astype(float)
            return {"time": time_dt, "data": data}

        elif return_type in ["seq", "json"]:
            values = [time_dt, symbol]
            keys = ["time", "symbol"]
            for _side in ["bids", "asks"]:
                depth = len(raw_data[_side])
                for _depth in range(depth):
                    values.append(float(raw_data[_side][_depth]["price"]))
                    values.append(float(raw_data[_side][_depth]["size"]))
                    keys.append(_side + str(_depth))
                    keys.append(_side + str(_depth) + "_size")

            if return_type is "json":
                data = {_key: _value for _key, _value in zip(keys, values)}
                data["time"] = dl.dt_to_strYMDHMSF(data["time"])
            elif return_type is "seq":
                data = values

            return data

        else:
            raise InvalidArgumentError(
                "Cannot accept return_type={0}".format(return_type)
            )


class Ticker(Socket):
    def __init__(
        self,
        logger,
        general_config_ini,
        private_api_ini,
        general_config_mode="DEFAULT",
        private_api_mode="DEFAULT",
    ):
        super().__init__(
            "ticker",
            logger,
            general_config_ini,
            private_api_ini,
            general_config_mode="DEFAULT",
            private_api_mode="DEFAULT",
        )

    def convert_shape(self, raw_data, return_type):
        raw_data = self.error_handle(raw_data)
        if raw_data is None:
            return {}
        symbol = raw_data["symbol"]

        if return_type is "raw":
            return raw_data
        elif return_type is "json":
            data = {}
            for _item in ["ask", "bid", "high", "last", "low", "volume"]:
                data[_item] = float(raw_data[_item])
            data["time"] = dl.dt_to_strYMDHMSF(
                dl.str_utc_to_dt_offset(raw_data["timestamp"], self.tz)
            )
            data["symbol"] = symbol
            return data
        else:
            raise InvalidArgumentError(
                "Cannot accept return_type={0}".format(return_type)
            )
