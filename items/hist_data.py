import time
from item import Item

from util import daylib
from util import utils
dl = daylib.daylib()

class histData(Item):
    def __init__(self):
        super(histData, self).__init__(name="histData",item_type="histData",currency="BTC")
        self.hist = self.hist.HistDataHandler(self.logger, self.general_config_ini)
        
    def load(self, sym, kind, since_int_date, until_int_date, mode=None):
        mode = 'auto' if mode is None else mode
        return self.hist.bulk_load(sym, kind, since_int_date, until_int_date, is_save=True, mode=mode)