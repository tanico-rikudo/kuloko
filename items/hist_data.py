import time
import pandas as pd
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

    #### Fetch hist data ###
    def get_data(self, ch, sym, sd, ed):
        if ch == "trade":
            data = self.get_hist_trades(sym, sd, ed)
        elif ch == "orderbook":
            data = self.get_hist_orderbooks(sym, sd, ed)
        elif ch == "ticker":
            data = self.get_hist_tickers(sym, sd, ed)
        else:
            raise Exception(f"Not support channel={ch}")
        return data

    def get_hist_trades(self, sym, sd, ed):
        target_dates = set(dl.get_between_date(sd, ed))
        trades = self.load(sym, "trade", sd, ed)

        file_data = self.file_hist.bulk_load(
            sym, sym, "trade", sd, ed, is_save=True, mode="auto"
        )
        file_fetched_date = set(file_data.timestamp.apply(lambda x: dl.strYMDHMSF_to_dt(x)))
        left_dates = target_dates - file_fetched_date

        # Fill by db (index is datetime)
        db_data = pd.concat(
            [self.db_hist.bulk_load(sym, "trade", target_date, target_date) for target_date in target_dates],
            axis=0)
        db_fetched_date = set(db_data.timestamp.apply(lambda x: dl.strYMDHMSF_to_dt(x)))
        left_dates = left_dates - db_fetched_date

        df = pd.concat([file_data, db_data], axis=0)
        df_empty = self.create_dataframe(
            columns=['datetime', 'symbol', "price", "side", "size"],
            index_col="datetime")
        df = pd.concat([df_empty, df], axis=0)

        if (df is None) or (df.shape[0] == 0):
            self.logger.warning("[Failure] trades fetching.")
            return None
        return trades

    def get_hist_orderbooks(self, sym, sd, ed):
        # only local
        df = self.db_hist.bulk_load(sym, "orderbook", sd, ed)
        df_empty = self.create_dataframe(
            columns=['datetime', 'symbol', 'bids0', 'bids0_size', 'bids1', 'bids1_size', 'bids2',
                     'bids2_size', 'bids3', 'bids3_size', 'bids4', 'bids4_size', 'asks0',
                     'asks0_size', 'asks1', 'asks1_size', 'asks2', 'asks2_size', 'asks3',
                     'asks3_size', 'asks4', 'asks4_size'],
            index_col="datetime")
        df = pd.concat([df_empty, df], axis=0)
        if (df is None) or (df.shape[0] == 0):
            self.logger.warning("[Failure] Orderbook fetching.")
        return df

    def get_hist_tickers(self, sym, sd, ed):
        # only local
        df = self.db_hist.bulk_load(sym, "ticker", sd, ed)
        df_empty = self.create_dataframe(
            columns=["symbol", "ask", "bid", "open", "high", "low", "last", "volume", "datetime"],
            index_col="datetime")
        df = pd.concat([df_empty, df], axis=0)
        if (df is None) or (df.shape[0] == 0):
            self.logger.warning("[Failure] Orderbook fetching.")
        return df

    def create_dataframe(self, columns, index_col=None):
        assert index_col in columns, f"index_col:{index_col} must be in columns:{columns}"
        df_empty = pd.DataFrame(columns=columns)
        df_empty.set_index(index_col)
        return df_empty
