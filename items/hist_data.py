import time
import pandas as pd
import copy

from item import Item

from util import daylib
from util import utils

dl = daylib.daylib()


class histData(Item):
    def __init__(self, symbol, general_config_mode, private_api_mode, logger=None):
        super(histData, self).__init__(
            name="histData",
            item_type="histData",
            symbol=symbol,
            general_config_mode=general_config_mode,
            private_api_mode=private_api_mode,
            logger=logger,
        )
        self.file_hist = self.file_hist.HistDataHandler(
            self.logger, self.general_config_ini, self.general_config_mode
        )
        self.init_mongodb()
        self.db_hist = self.db_hist.DbLoadHandler(
            self.logger, self.general_config_ini, mongodb=self.mongodb
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
        df_empty = self.create_dataframe(
            columns=["datetime", "symbol", "price", "side", "size"],
            index_col="datetime",
        )

        # File based data
        file_data = self.file_hist.bulk_load(
            sym, "trade", sd, ed, is_save=True, mode="auto"
        )
        file_data = pd.concat([df_empty, file_data], axis=0)
        self.logger.warning(f"[DONE] file_data fetching. Size={file_data.shape}")

        # Fill by db (index is datetime)
        db_data = pd.concat(
            [
                self.db_hist.bulk_load(sym, "trade", target_date, target_date)
                for target_date in target_dates
            ],
            axis=0,
        )
        db_data = pd.concat([df_empty, db_data], axis=0)
        self.logger.warning(f"[DONE] db_data fetching. Size={db_data.shape}")

        # _columns = file_data.reset_index().columns
        # if file_data.shape[0] > 0 and db_data.shape[0] > 0:
        #     trade_data = pd.merge_asof(
        #         file_data.reset_index(),
        #         db_data.reset_index(),
        #         on="datetime",
        #         allow_exact_matches=False,
        #     )
        #     trade_data = trade_data.iloc[:, : len(_columns)]
        #     trade_data.columns = _columns
        # else:
        #     if file_data.shape[0] > 0:
        #         trade_data = file_data
        #     else:
        #         trade_data = db_data
        trade_data = copy.copy(file_data)

        if (trade_data is None) or (trade_data.shape[0] == 0):
            self.logger.warning("[Failure] trades fetching.")
            return None
        self.logger.warning(f"[DONE] trades fetching. Size={trade_data.shape}")
        return trade_data

    def get_hist_orderbooks(self, sym, sd, ed):
        # only local
        df = self.db_hist.bulk_load(sym, "orderbook", sd, ed)
        df_empty = self.create_dataframe(
            columns=[
                "datetime",
                "symbol",
                "bids0",
                "bids0_size",
                "bids1",
                "bids1_size",
                "bids2",
                "bids2_size",
                "bids3",
                "bids3_size",
                "bids4",
                "bids4_size",
                "asks0",
                "asks0_size",
                "asks1",
                "asks1_size",
                "asks2",
                "asks2_size",
                "asks3",
                "asks3_size",
                "asks4",
                "asks4_size",
            ],
            index_col="datetime",
        )
        df = pd.concat([df_empty, df], axis=0)
        self.logger.warning(f"[DONE] orderbook fetching. Size={df.shape}")
        if df.shape[0] == 0:
            self.logger.warning("Orderbook is None.")
        return df

    def get_hist_tickers(self, sym, sd, ed):
        # only local
        df = self.db_hist.bulk_load(sym, "ticker", sd, ed)
        df_empty = self.create_dataframe(
            columns=[
                "symbol",
                "ask",
                "bid",
                "open",
                "high",
                "low",
                "last",
                "volume",
                "datetime",
            ],
            index_col="datetime",
        )
        df = pd.concat([df_empty, df], axis=0)
        if (df is None) or (df.shape[0] == 0):
            self.logger.warning("[Failure] Orderbook fetching.")
        return df

    def create_dataframe(self, columns, index_col=None):
        assert (
            index_col in columns
        ), f"index_col:{index_col} must be in columns:{columns}"
        df_empty = pd.DataFrame(columns=columns)
        df_empty.set_index(index_col, inplace=True)
        return df_empty
