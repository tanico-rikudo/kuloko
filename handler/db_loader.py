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

from util.exceptions import *
from util import daylib
from util import utils
from util.config import ConfigManager

from mongodb.src.mongo_handler import *

cm = ConfigManager(os.environ['KULOKO_INI'])
dl = daylib.daylib()

class DbLoadHandler:

    def __init__(self,logger, general_config_ini=None,general_config_mode="DEFAULT",mongo_db=None):
        self._logger = logger

        if general_config_ini is None:
            general_config_ini=cm.load_ini_config(path=None,config_name="general", mode=general_config_mode)
            self._logger.info('[DONE]Load General Config.')
        if private_api_ini is None:            
            private_api_ini=cm.load_ini_config(path=None,config_name="private_api", mode=private_api_mode)
            self._logger.info('[DONE]Load Private API Config.')

        self.load_config( general_config_ini,private_api_ini,general_config_mode,private_api_mode)
        self.set_config()
        self.mongo_db = mongo_db
        self._logger.info('[DONE]DB loader Initialized')
        
    def load_db_accessor(self, mongo_db):
        self.db_accesser =  MongoUtil(self.mongo_db, self.logger)
        
    def bulk_load(self, sym, kind, since_int_date, until_int_date):
        target_dates = dl.get_between_date(since_int_date, until_int_date)
        table_name =  kind
        dfs = Parallel(n_jobs=self.n_usable_core)(delayed(self.get_db_hist)(sym, table_name, _target_date) for _target_date in target_dates)
        dfs = [ df for  df in dfs if df is not None]
        if len(dfs) ==  0:
            self._logger.warning("ALL object is failure.")
            return None
        return pd.concat(dfs, axis=0)
        
    def get_db_hist(self, sym, table_name, start_date, end_date, tables):
        """
        Get realtime feed data from DB
        """
        if  tables is None:
            tables  = self.tables
        datas = {}
        date_list  = self.dl.get_between_date(start_date, end_date)
        for _date in  date_list:
            datas[_date] = {}
            for table_name in tables:
                datas[_date][table_name] = self.db_accesser.find_at_date(table_name, str(_date))
        
        return datas

