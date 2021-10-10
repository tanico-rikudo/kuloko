import os
import sys
import logging
import logging.config
class Item:
    def __init__(self,name,item_type,currency):
        import configparser
        import logging
        import logging.config
        
        # Metas
        self.name = name
        self.item_type = item_type
        self.currency = currency
        
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
        self.base_api = skt_api

        # Init Logger 
        logging.config.fileConfig(os.path.join(KULOKO_DIR,'ini/logconfig.ini'),defaults={'logfilename': os.path.join(LOGDIR,'logging.log')})
        self.logger = logging.getLogger("KULOKO")

        # Init mongo
        self.mongo_ini = configparser.ConfigParser()
        self.mongo_ini.read(os.path.join(MONGO_DIR,'ini/mongo_config.ini'), encoding='utf-8')

        # Init API
        self.private_api_ini = configparser.ConfigParser()
        self.private_api_ini.read(os.path.join(KULOKO_DIR,'ini/private_api.ini'), encoding='utf-8')

        self.general_config_ini = configparser.ConfigParser()
        self.general_config_ini.read(os.path.join(KULOKO_DIR,'ini/config.ini'), encoding='utf-8')
        
    def init_mongodb():
        self.mongo_db = MongoHandler(self.mongo_ini['LOCAL'],item_type)
        self.logger.info("[DONE] Init mongo DB")
        
    def init_api():
        self.public_socket_url = self.base_api.get_public_socket_url()
        self.private_socket_url = self.base_api.get_private_socket_url()
        
    
    