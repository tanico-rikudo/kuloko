import os
import sys
import logging
import logging.config

from datetime import datetime as dt

# Path
KULOKO_DIR=os.environ['KULOKO_DIR'] 
MONGO_DIR=os.environ['MONGO_DIR'] 
LOGDIR=os.environ['LOGDIR'] 

# DB libs 
from pymongo import MongoClient
sys.path.append(os.environ['COMMON_DIR'] )
from mongodb.src.mongo_handler import MongoHandler

# Handlers
sys.path.append(os.path.join(os.environ['KULOKO_DIR'],"handler" ))
import  socket_handler as skt_api 
import  api_handler as web_api 
import hist_loader as hist

#util
from util.config import ConfigManager
from util.daylib import daylib

cm = ConfigManager(os.environ['KULOKO_INI'])

class Item:
    def __init__(self,name,item_type,currency):
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
        self.hist = hist

        # Init Logger 
        self.logger = cm.load_log_config(os.path.join(LOGDIR,'logging.log'),log_name="KULOKO")

        # Init mongo
        self.mongo_ini=cm.load_ini_config(path=None,config_name="mongo", mode=None)

        # Init API
        general_config_mode = None
        self.general_config_ini=cm.load_ini_config(path=None,config_name="general", mode=general_config_mode)

        private_api_mode = None
        self.private_api_ini=cm.load_ini_config(path=None,config_name="private_api", mode=private_api_mode)
        
        #util 
        self.dl = daylib()
        
    def init_mongodb(self):
        self.mongo_db = MongoHandler(self.mongo_ini['LOCAL'],self.item_type)
        self.logger.info("[DONE] Init mongo DB")