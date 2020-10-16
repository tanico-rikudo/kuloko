# coding: utf-8

import urllib.parse
import logging
import logging.config
import configparser

import pandas as pd
import numpy as np

import requests
import json
import os

from datetime import datetime as dt
from datetime import  timedelta, timezone
from .util import daylib
from .util.utils import *


config_ini = configparser.ConfigParser()
config_ini.read('./ini/config.ini', encoding='utf-8')

env_ini = configparser.ConfigParser()
env_ini.read('./ini/env.ini', encoding='utf-8')

logging.config.fileConfig('./ini/logconfig.ini')
logger = logging.getLogger("KULOKO")

dl = daylib.daylib()


class HistDataHandler:

    def __init__(self):
        self.endpoint = config_ini.get('DEFAULT','ENDPOINT_URL')
        self.load_config()
        self.set_config()

    def load_config(self):
        env_info= get_env()
        if env_info is None:
            raise Exception("Cannot load env name")
        self.env = env_ini[env_info['env_name']]

        logger.info('[DONE]Load Config. Env={0}'.format(env_info['env_name'] ))

    def set_config(self):
        self.download_folderpath = self.env.get('DOWNLOAD_PATH')
        logger.info('[DONE]Set Config from loaded config')

    def get_url(self, sym, int_date):
        _ = dl.intD_to_dt(int_date)
        str_date = str(int_date)
        dl_url = self.endpoint+ "/data/trades/"+ sym+ "/"+ str_date[:4]+ "/"+str_date[4:6]+ "/"+ str_date+ "_"+ sym+ ".csv.gz"
        logger.info("[DONE] Get URL string={0}".format(dl_url))
        return dl_url

    def get_hist(self,sym, int_date, save_path=None):
        str_date = str(int_date)

        # Fetch
        try:
            dl_url = self.get_url(sym, int_date)
            response = requests.get(dl_url)
            if response.headers['Content-Type'] != 'text/csv':
                raise Exception("Response content type is invalid. Type={0}".format(response.headers['Content-Type']))
            logger.info("[DONE] Get historical data. Sym={0}, Date={1}".format(sym, int_date))

        except Exception as e:
            logger.error("Fail to get historical data. Sym={0}, Date={1}: {2}".format(sym, int_date, e))
            return 

        # Save or Return
        if save_path is None:
            return response.content

        file_path = os.path.join(self.download_folderpath, "trades", sym, str_date+".csv.gz" )
        try:
            if os.path.isfile(file_path):
                logger.warn("Filepath={0} is already exist. However, download and overwirte forcefully".format(file_path))           
            with open(file_path, 'wb') as f:
                f.write(content)
            logger.info("[DONE] Save historical data. Sym={0}, Date={1}".format(sym, int_date))

        except Exception as e:
            logger.error("Fail to save historical data. Sym={0}, Date={1}: {2}".format(sym, int_date, e))
            return False


    def read_hist(self, sym, int_date):
        str_date = str(int_date)
        pass
        
    def send_dynamo(self):
        pass

