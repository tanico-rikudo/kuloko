import sys, os
import time
import pika
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from .item import Item
import public_api
import private_api

sys.path.append(os.environ["COMMON_DIR"])
from mongodb.src.mongo_handler import *
import json
from mq.mq_handler import *
import hist_data


#  stand alone from ITEM
class FeatureDB(Item):
    def __init__(self, symbol, general_config_mode, private_api_mode):
        # Note: No specific private spi
        super(FeatureDB, self).__init__(
            name="featureDB",
            item_type="featureDB",
            symbol=symbol,
            general_config_mode=general_config_mode,
            private_api_mode=private_api_mode,
        )
        # Init handler
        self.hd = hist_data.histData(symbol, general_config_mode, private_api_mode)

    """ Download trades daily """
    def download_trade(self):
        pass

    def

    """


    def fetch_hist_data(self, ch, sym, sd, ed):
        """
        Get hist data from DB or file
        Returns:
            result pandas
        """
        result = self.hd.get_data(ch, sym, sd, ed)
        return result
