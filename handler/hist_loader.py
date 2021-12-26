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
import sys
from joblib import Parallel, delayed

from datetime import datetime as dt
from datetime import  timedelta, timezone
sys.path.append(os.environ['COMMON_DIR'] )
from util.exceptions import *
from util import daylib
from util import utils
from util.config import ConfigManager

cm = ConfigManager(os.environ['KULOKO_INI'])
dl = daylib.daylib()

class HistDataHandler:

    def __init__(self,logger, general_config_ini=None,general_config_mode="DEFAULT"):
        self._logger = logger
        if general_config_ini is None:
            general_config_ini = cm.load_ini_config(path=None,config_name="general", mode=general_config_mode)
            self._logger.info('[DONE]Load General Config.')

        self.load_config(general_config_ini, general_config_mode)
        self.set_config()
        self._logger.info('[DONE]API Initialized')
        
    def load_config(self,general_config_ini,general_config_mode):
        self.general_config = general_config_ini[general_config_mode]
        self._logger.info('[DONE]Load Config. Hist File loader:[{0}] General:[{1}]'
            .format(general_config_ini,general_config_mode))

    def set_config(self):
        self.remote_end_point = os.path.join(self.general_config.get('ENDPOINT_URL'),self.general_config.get('HISTDATA_URL'))
        self.local_end_point= self.general_config.get('LOCAL_HISTDATA_PATH')
        self.n_usable_core= self.general_config.getint('N_USABLE_CORE')
        self._logger.info("[DONE] Get end points={0}".format(self.remote_end_point))
        self._logger.info('[DONE]Set Config from loaded config')
        
    def get_remote_target_url(self,sym, kind, int_date=None):
        int_date = dl.dt_to_intD(dl.currentTime(0)) if int_date is None  else int_date
        str_date = dl.intD_to_strD(int_date)
        target_url = os.path.join(self.remote_end_point,
                                  kind,
                                  sym,
                                  str_date[:4],
                                  str_date[4:6],
                                  str_date+ "_"+ sym+ ".csv.gz")
        # self._logger.info("[DONE]Get remote  taget url:{0}".format(target_url))
        return target_url
    
    def get_local_target_url(self,sym, kind, int_date=None):
        # differ from remote  path
        int_date = dl.dt_to_intD(dl.currentTime(0)) if int_date is None  else int_date
        str_date = dl.intD_to_strD(int_date)
        target_url = os.path.join(self.local_end_point,
                                  kind,
                                  sym,
                                  str_date[:4],
                                  str_date[4:6],
                                  str_date+ "_"+ sym+ ".csv.gz")
        # self._logger.info("[DONE]Get local  taget url:{0}".format(target_url))
        return target_url

    def get_file_hist(self,sym, kind, int_date, is_save=False, mode="auto"):
        str_date = dl.intD_to_strD(int_date)
        local_path = self.get_local_target_url(sym, kind, int_date)
        remote_path = self.get_remote_target_url(sym, kind, int_date)
        save_path = local_path if is_save else None
        self.item_validation(kind, mode)
        if mode == 'local':
            if not os.path.isfile(local_path):
                self._logger.error("Fail to get hist data. path{0}".format(local_path))
            df = self.read_local_hist(local_path)
            self._logger.info("[DONE] Get local hist data. Path={0}".format(local_path))
            
        elif mode == 'remote':
            df = self.download_remote_hist( remote_path, save_path=save_path)
            self._logger.info("[DONE] Get remote hist data. Path={0}".format(remote_path))
        elif mode == 'auto':
            if not os.path.isfile(local_path):
                self._logger.info("No local hist data. Try: remote.  path{0}".format(local_path))
                df = self.download_remote_hist(remote_path, save_path=save_path)
                self._logger.info("[DONE] Get remote hist data. Path={0}".format(remote_path))
            else:
                df = self.read_local_hist(local_path)
                self._logger.info("[DONE] Get local hist data. Path={0}".format(local_path))
        
        if  df is not None:
            # time stamp format     
            df['timestamp'] = df['timestamp'].apply(lambda x: dl.dt_to_strYMDHMSF(dl.str_utc_to_dt_offset(x,is_Z=False, is_T=False)))
        
        return df

        
    def download_remote_hist(self,url, save_path=None):
        # Fetch
        try:
            response = requests.get(url)
            if response.headers['Content-Type'] != 'text/csv':
                raise Exception("Response content type is invalid. Type={0}".format(response.headers['Content-Type']))
            self._logger.info("[DONE] Get historical data. url={0}".format(url))

        except Exception as e:
            self._logger.error("Fail to get historical data. url={0}:{1}".format(url, e))
            return None
        
        binary_data = response.content
        data = self.convert_gzip_binary_to_plain(binary_data)
        
        # save or return 
        if save_path is None:
            return data
        
        else:
            # save
            try:
                self.save_hist(binary_data, save_path)
            except Exception as e:
                self._logger.error("Fail to save historical data. Url={0}:{1}".format(save_path, e))
            finally:
                return data
            
    def save_hist(self, data, save_path):
        if os.path.isfile(save_path):
            self._logger.warn("Filepath={0} is already exist. "
                        "However, download and overwirte forcefully".format(save_path))
        save_dir = os.path.dirname(save_path)
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir)    
            self._logger.info("[DONE] Make dir:{0}".format(save_dir))   
        with open(save_path, 'wb') as f:
            f.write(data)
        self._logger.info("[DONE] Save historical data. path:{0}".format(save_path))
        
    def read_local_hist(self, read_local_path):
        df=None
        try:
            df = pd.read_csv(read_local_path, compression='gzip')
            self._logger.info("[DONE] Readed data. Path={0}".format(read_local_path))
        except Exception as e:
            self._logger.warning("[Fialure] Reading hist data. Path={0}:{1} ".format(read_local_path,e))
        return df
    
    def convert_gzip_binary_to_plain(self,  data):
        import io
        import gzip
        import csv
        f = io.BytesIO(data)
        fh_r = pd.read_csv(f, compression='gzip', encoding='utf-8')
        return fh_r
        # with gzip.GzipFile(fileobj=f,mode='rb' ) as fh:
        #     # Passing a binary file to csv.reader works in PY2
        #     return f.read().decode()
        #     # reader = csv.reader(fh)
        #     # for row in reader:
        #     #     print(row)

    def bulk_load(self,sym, kind, since_int_date, until_int_date, is_save=True, mode='auto'):
        target_dates = dl.get_between_date(since_int_date, until_int_date)
        dfs = Parallel(n_jobs=self.n_usable_core)(delayed(self.get_file_hist)(sym, kind, _target_date,  is_save, mode) for _target_date in target_dates)
        dfs = [ df for  df in dfs if df is not None]
        if len(dfs) ==  0:
            self._logger.warning("ALL object is failure.")
            return None
        return pd.concat(dfs, axis=0)
    
    def item_validation(self,kind, mode):
        assert kind in ['trades','orderbooks'] ,"No such option. Mode={kind}"
        assert mode in ['local','remote','auto'] ,"{kind} has no such option. Mode={mode}"
        if kind == 'trades':
            pass
        elif kind == 'orderbooks':
            if mode == 'auto':
                mode == 'local'
                self._logger(f"{kind} fetch mode is changed to local mode.")
            else:
                pass
        else:
            pass
            
    def send_dynamo(self):
        pass

