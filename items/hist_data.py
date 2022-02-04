import time
from item import Item

from util import daylib
from util import utils

dl = daylib.daylib()


class histData(Item):
    def __init__(self, symbol, general_config_mode, private_api_mode):
        super(histData, self).__init__(
            name="histData",
            item_type="histData",
            symbol=symbol,
            general_config_mode=general_config_mode,
            private_api_mode=private_api_mode,
        )
        self.file_hist = self.file_hist.HistDataHandler(
            self.logger, self.general_config_ini, self.general_config_mode
        )
        self.init_mongodb()
        self.db_hist = self.db_hist.DbLoadHandler(
            self.logger, self.general_config_ini, mongo_db=self.mongo_db
        )
        # self.db_hist.load_db_accessor()

    def load(self, sym, kind, since_int_date, until_int_date, mode=None):
        if kind in ["trades"]:
            # file  hist
            mode = "auto" if mode is None else mode
            data = self.file_hist.bulk_load(
                sym, kind, since_int_date, until_int_date, is_save=True, mode=mode
            )
        elif kind in ["orderbooks"]:
            # Db hist
            data = self.db_hist.bulk_load(sym, kind, since_int_date, until_int_date)
        else:
            raise Exception(f"Invalid  data kind={kind}")
        return data

    #### Fetch hist data ###
    def get_data(self, ch, sym, sd, ed):
        if ch == "trades":
            data = self.get_hist_trades(sym, sd, ed)
        elif ch == "orderbooks":
            data = self.get_hist_trades(sym, sd, ed)
        else:
            raise Exception(f"Not support channel={ch}")
        return data

    def get_hist_trades(self, sym, sd, ed):
        trades = self.hd.load(sym, "trades", sd, ed)
        # print(trades.timestamp)
        trades.timestamp = pd.to_datetime(trades.timestamp, format="%Y%m%d%H%M%S%f")
        if (trades is None) or (trades.shape[0] == 0):
            self.logger.warning("[Failure] trades fethcing.")
            return None
        trades.set_index("timestamp", inplace=True)
        return trades

    def get_hist_orderbooks(self, sym, sd, ed):
        # only local
        orderbooks = self.hd.load(sym, "orderbooks", sd, ed, "local")
        if (orderbooks is None) or (orderbooks.shape[0] == 0):
            self.logger.warning("[Failure] Orderbook fethcing.")
            return None
        orderbooks.timestamp = pd.to_datetime(
            orderbooks.timestamp, format="%Y%m%d%H%M%S%f"
        )
        orderbooks.set_index("timestamp", inplace=True)
        return orderbooks
