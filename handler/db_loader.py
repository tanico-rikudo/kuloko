# coding: utf-8

import urllib.parse
import configparser

import pandas as pd
import numpy as np

import requests
import json
import os
import copy

import time
from datetime import datetime as dt
from datetime import timedelta, timezone
from joblib import Parallel, delayed

import hmac
import hashlib

from util.exceptions import *
from util import daylib
from util import utils
from util.config import ConfigManager

from mongodb.src.mongo_handler import *

cm = ConfigManager(os.environ["KULOKO_INI"])
dl = daylib.daylib()


class DbLoadHandler:
    def __init__(
            self,
            logger,
            general_config_ini=None,
            general_config_mode="DEFAULT",
            mongo_db=None,
    ):
        self._logger = logger
        if general_config_ini is None:
            general_config_ini = cm.load_ini_config(
                path=None, config_name="general", mode=general_config_mode
            )
            self._logger.info("[DONE]Load General Config.")

        self.load_config(general_config_ini, general_config_mode)
        self.set_config()
        self.mongo_db = mongo_db
        self.load_db_accessor()
        self._logger.info("[DONE]DB loader Initialized")

    def load_config(self, general_config_ini, general_config_mode):
        if general_config_ini is None:
            self.general_config = cm.load_ini_config(
                path=None, config_name="general", mode=general_config_mode
            )
        else:
            self.general_config = general_config_ini[general_config_mode]
        self._logger.info(f"[DONE]Load General Config. Mode={general_config_mode}")

    def set_config(self):
        self.n_usable_core = self.general_config.getint("N_USABLE_CORE")
        self._logger.info("[DONE]Set Config from loaded config")

    def load_db_accessor(self):
        self.db_accesser = MongoUtil(self.mongo_db, self._logger)

    def bulk_load(self, sym, kind, since_int_date, until_int_date):
        target_dates = dl.get_between_date(since_int_date, until_int_date)
        table_name = kind
        # Note:  Thread object inhibit multiproicesss...
        dfs = []
        for _target_date in target_dates:
            df = self.get_db_hist(sym, table_name, _target_date, _target_date)
            if df is not None:
                dfs.append(df)
        # dfs = [ df for  df in dfs if df is not None]
        if len(dfs) == 0:
            self._logger.warning("ALL object is failure.")
            return None
        return pd.concat(dfs, axis=0)

    def get_db_hist(self, sym, table_name, start_date, end_date):
        """
        Get realtime feed data from DB
        """
        datas = []
        date_list = dl.get_between_date(start_date, end_date)
        for _date in date_list:
            raw_data = pd.DataFrame(
                self.db_accesser.find_at_date(table_name, date=str(_date), symbol=sym)
            )
            for _key in ["_id", "channel"]:
                if _key in raw_data.keys():
                    del raw_data[_key]
            # raw_data["date"] = _date
            datas.append(raw_data)

        datas = pd.concat(datas, ignore_index=True)

        if datas.shape[0] > 0 and table_name in ["trade", "orderbook", 'ticker']:
            datas["datetime"] = datas["time"].apply(lambda x: dl.strYMDHMSF_to_dt(x))
            del datas["time"]
            datas.set_index("datetime", inplace=True)

        return datas
