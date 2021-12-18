import time
from item import Item

from util import daylib
from util import utils
dl = daylib.daylib()

class histData(Item):
    def __init__(self):
        super(histData, self).__init__(name="histData",item_type="histData",currency="BTC")
        self.file_hist = self.hist.HistDataHandler(self.logger, self.general_config_ini)
        self.init_mongodb()
        self.db_hist = self.hist.DbLoadHandler(self.logger, self.general_config_ini,self.mongo_db)
        self.db_hist.load_db_accessor()
        
    def load(self, sym, kind, since_int_date, until_int_date, mode=None):
        if kind in ['trade']:
            # file  hist
            mode = 'auto' if mode is None else mode
            data =  self.file_hist.bulk_load(sym, kind, since_int_date, until_int_date, is_save=True, mode=mode)
        elif kind  in ['orderbook']:
            # Db hist
            data =  self.db_hist.bulk_load(sym, kind, since_int_date, until_int_date)
        else:
            raise Exception(f"Invalid  data kind={kind}")
        return  data
        