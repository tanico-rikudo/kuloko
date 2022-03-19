import os
import sys
import logging
import logging.config

from datetime import datetime as dt

# Path
KULOKO_DIR = os.environ["KULOKO_DIR"]
MONGO_DIR = os.environ["MONGO_DIR"]
LOGDIR = os.environ["KULOKO_LOGDIR"]

# DB libs
from pymongo import MongoClient

sys.path.append(os.environ["COMMON_DIR"])
from mongodb.src.mongo_handler import MongoHandler
from postgres.src.postgres_handler import PostgresHandler

# Handlers
sys.path.append(os.path.join(os.environ["KULOKO_DIR"], "handler"))
import socket_handler as skt_api
import api_handler as web_api
import hist_file_handler as hist_file_handler
import db_handler as db_handler

# util
from util.config import ConfigManager
from util.daylib import daylib

cm = ConfigManager(os.environ["KULOKO_INI"])


class Item(object):
    def __init__(
        self,
        name,
        item_type,
        symbol,
        general_config_mode="DEFAULT",
        private_api_mode="DEFAULT",
        logger=None,
    ):
        import configparser
        import logging
        import logging.config

        # Metas
        self.name = name
        self.item_type = item_type
        self.symbol = symbol

        # Handlers
        self.skt_api = skt_api
        self.web_api = web_api
        self.hist_file_handler = hist_file_handler
        self.db_handler = db_handler

        # Init Logger
        if logger is None:
            self.logger = cm.load_log_config(
                os.path.join(KULOKO_DIR, "logging.log"), log_name="KULOKO"
            )
        else:
            self.logger = logger

        # Init mongo
        self.mongo_ini = cm.load_ini_config(path=None, config_name="mongo", mode=None)
        self.postgres_ini = cm.load_ini_config(path=None, config_name="postgres", mode=None)

        # Init API
        self.general_config_mode = general_config_mode
        self.general_config_ini = cm.load_ini_config(
            path=None, config_name="general", mode=None
        )
        self.general_config = (
            None
            if general_config_mode is None
            else self.general_config_ini[self.general_config_mode]
        )

        self.private_api_mode = private_api_mode
        self.private_api_ini = cm.load_ini_config(
            path=None, config_name="private_api", mode=None
        )
        self.private_api = (
            None
            if private_api_mode is None
            else self.private_api_ini[self.private_api_mode]
        )

        # util
        self.dl = daylib()

    def init_mongodb(self, mongo_config_mode=None):
        if mongo_config_mode is None:
            self.logger.info(
                f"[DONE] mongo_config_mode is filled with general_config_mode:{self.general_config_mode}"
            )
            mongo_config_mode = self.general_config_mode
        self.mongodb = MongoHandler(self.mongo_ini[mongo_config_mode], self.item_type)
        # todo: hide here
        self.logger.info(
            f"[DONE] Init mongo DB. Mode={mongo_config_mode}. Url={self.mongodb.connect_url}"
        )

    def init_postgres(self, postgres_config_mode=None):
        if postgres_config_mode is None:
            self.logger.info(
                f"[DONE] postgres_config_mode is filled with general_config_mode:{self.general_config_mode}"
            )
            postgres_config_mode = self.general_config_mode
        self.postgres = PostgresHandler(
            self.postgres_ini[postgres_config_mode]        )
        # todo: hide here
        self.logger.info(
            f"[DONE] Init Postgress. Mode={postgres_config_mode}. Url={self.postgres.host+':'+self.postgres.port}"
        )
