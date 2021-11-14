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
        logging.config.fileConfig(os.path.join(KULOKO_DIR,'ini/logconfig.ini'),defaults={'logfilename': os.path.join(LOGDIR,'logging.log')})
        self.logger = logging.getLogger("KULOKO")

        # Init mongo
        self.mongo_ini = configparser.ConfigParser()
        self.mongo_ini.read(os.path.join(MONGO_DIR,'ini/mongo_config.ini'), encoding='utf-8')

        # Init API
        general_config_mode = "DEFAULT"
        if general_config_ini is None:
            general_config_ini=cm.load_ini_config(path=None,config_name="general", mode=general_config_mode)
            self._logger.info('[DONE]Load General Config.')
        
        private_api_mode = "DEFAULT"
        if private_api_ini is None:            
            private_api_ini=cm.load_ini_config(path=None,config_name="private_api", mode=private_api_mode)
            self._logger.info('[DONE]Load Private API Config.')
        
    def init_mongodb(self):
        self.mongo_db = MongoHandler(self.mongo_ini['LOCAL'],self.item_type)
        self.logger.info("[DONE] Init mongo DB")