import os
import sys
import logging
import logging.config

from datetime import datetime as dt

# Path
KULOKO_DIR=os.environ['KULOKO_DIR'] 
MONGO_DIR=os.environ['MONGO_DIR'] 
LOGDIR=os.environ['KULOKO_LOGDIR'] 

# DB libs 
from pymongo import MongoClient
sys.path.append(os.environ['COMMON_DIR'] )
from mongodb.src.mongo_handler import MongoHandler

# Handlers
sys.path.append(os.path.join(os.environ['KULOKO_DIR'],"handler" ))
import  socket_handler as skt_api 
import  api_handler as web_api 
import hist_loader as file_hist
import db_loader as db_hist

#util
from util.config import ConfigManager
from util.daylib import daylib

cm = ConfigManager(os.environ['KULOKO_INI'])

class Item(object):
    def __init__(self,name,item_type,currency,
                 general_config_mode="DEFAULT",private_api_mode="DEFAULT"):
        import configparser
        import logging
        import logging.config
        
        # Metas
        self.name = name
        self.item_type = item_type
        self.currency = currency
        
        # Handlers
        self.skt_api = skt_api
        self.web_api = web_api
        self.file_hist = file_hist
        self.db_hist = db_hist

        # Init Logger 
        self.logger = cm.load_log_config(os.path.join(KULOKO_DIR,'logging.log'),log_name="KULOKO")

        # Init mongo
        self.mongo_ini=cm.load_ini_config(path=None,config_name="mongo", mode=None)

        # Init API
        self.general_config_mode = general_config_mode
        self.general_config_ini=cm.load_ini_config(path=None, config_name="general", mode=None)
        self.general_config = None if general_config_mode is None else self.general_config_ini[self.general_config_mode] 

        self.private_api_mode = private_api_mode
        self.private_api_ini=cm.load_ini_config(path=None, config_name="private_api", mode=None)
        self.private_api = None if private_api_mode is None else self.private_api_ini[self.private_api_mode] 
        
        
        #util 
        self.dl = daylib()
        
    def init_mongodb(self, mongo_config_mode=None):
        if mongo_config_mode is None:
            self.logger.info("[DONE] mongo_config_mode is filled with general_config_mode.")
            mongo_config_mode = self.general_config_mode 
        self.mongo_db = MongoHandler(self.mongo_ini[mongo_config_mode],self.item_type)
        self.logger.info(f"[DONE] Init mongo DB. Mode={mongo_config_mode}")