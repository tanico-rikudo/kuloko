import time
import pandas as pd
import copy

from item import Item

from util import daylib

dl = daylib.daylib()

from processed_data_handler import *


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
        self.hist_file_handler = self.hist_file_handler.HistFileHandler(
            self.logger, self.general_config_ini, self.general_config_mode
        )
        self.init_mongodb()
        self.init_postgres()
        self.db_handler = self.db_handler.DbHandler(
            self.logger, self.general_config_ini, mongodb=self.mongodb
        )
        # self.db_handler.load_db_accessor()

    def download_update_trade(self, symbol, until_date=None):
        """
        Download trade data in Advace
        :param symbol:
        :param until_date:
        :return:
        """
        until_date = (
            dl.dt_to_intD(dl.currentTime()) if until_date is None else until_date
        )
        since_date = dl.add_day(until_date, -3)
        df = self.hist_file_handler.bulk_load(symbol, "trade", since_date, until_date)
        if df.shape[0] == 0:
            self.logger.warning(
                f"[Failure] All Download trade. Sym={symbol}, Date={since_date}~{until_date}"
            )
            return
        fetch_dates = set(
            [int(_date) for _date in list(df.index.dt.strftime("%Y%m%d"))]
        )
        target_dates = set(dl.get_between_date(since_date, until_date))
        left_dates = target_dates - fetch_dates
        if len(left_dates) > 0:
            self.logger.warning(
                f"[Failure] Download trade. Sym={symbol}, Failure Date={left_dates}"
            )
        else:
            self.logger.info(
                f"[DONE] Download trade. Sym={symbol}, Date={since_date}~{until_date}"
            )

    #### Fetch and Send hist data ###
    def get_data(self, ch, sym, sd, ed):
        if ch == "trade":
            data = self.get_hist_trades(sym, sd, ed)
        elif ch == "orderbook":
            data = self.get_hist_orderbooks(sym, sd, ed)
        elif ch == "ticker":
            data = self.get_hist_tickers(sym, sd, ed)
        elif ch == "ohlcv":
            data = self.get_hist_ohlcv(sym, sd, ed)
        else:
            raise Exception(f"Not support channel={ch}")
        return data

    ### Create or Get data ###

    def get_hist_trades(self, sym, sd, ed):
        target_dates = set(dl.get_between_date(sd, ed))
        df_empty = self.create_dataframe(
            columns=["datetime", "symbol", "price", "side", "size"],
            index_col="datetime",
        )

        # File based data
        file_data = self.hist_file_handler.bulk_load(
            sym, "trade", sd, ed, is_save=True, mode="auto"
        )
        file_data = pd.concat([df_empty, file_data], axis=0)
        self.logger.warning(f"[DONE] file_data fetching. Size={file_data.shape}")

        # Fill by db (index is datetime)
        db_data = pd.concat(
            [
                self.db_handler.bulk_load(sym, "trade", target_date, target_date)
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
        df = self.db_handler.bulk_load(sym, "orderbook", sd, ed)
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
        df = self.db_handler.bulk_load(sym, "ticker", sd, ed)
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

    def get_hist_ohlcv(self, sym, sd, ed):

        df = self.hist_file_handler.bulk_load(sym, "trade", sd, ed)
        df_empty = self.create_dataframe(
            columns=[
                "symbol",
                "dateime",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ],
            index_col="datetime",
        )
        df = pd.concat([df_empty, df], axis=0)
        if (df is None) or (df.shape[0] == 0):
            self.logger.warning("[Failure] Orderbook fetching.")

        df_ohlcv = calc_ohlcv(df)
        datetime_col = "datetime"
        df_ohlcv.reset_index(inplace=True)
        df_ohlcv.loc[:, datetime_col] = df_ohlcv.loc[:, datetime_col].apply(
            lambda x: dl.dt_to_strYMDHMSFformat(x)
        )
        return df_ohlcv

    def create_dataframe(self, columns, index_col=None):
        """Create Empty DataFrame

        Args:
            columns (str list): _description_
            index_col (str, optional): _description_. Defaults to None.

        Returns:
            pandas.DataFrame: Empty DataFrame
        """
        assert (
            index_col in columns
        ), f"index_col:{index_col} must be in columns:{columns}"
        df_empty = pd.DataFrame(columns=columns)
        df_empty.set_index(index_col, inplace=True)
        return df_empty

    def create_volatility(self, trades, tickers):
        """
        Create volatility from trade and ticker
        :param symbol:
        :param until_date:
        :return:
        """
        # Fixed
        VOLATILITY_VAR_DAYS = 30
        VOLATILITY_DAYS = 1

        # Get data:

        daily_close_trade = (
            trades.price.resample("T", label="left", closed="left")
            .ohlc()
            .loc[:, "close"]
        )

        if "last" in tickers.columns():
            daily_close_ticker = tickers.loc[:, "last"]
        elif "close" in tickers.columns():
            daily_close_ticker = tickers.loc[:, "close"]
        else:
            daily_close_ticker = None

        # Fill each other
        daily_close = pd.concat([daily_close_trade, daily_close_ticker], axis=0)

        # calc volatility
        daily_close = calc_daily_volatility(
            daily_close, VOLATILITY_VAR_DAYS, VOLATILITY_DAYS, close_time="00:00"
        )
        daily_close["close_time"] = daily_close.index.strftime("%H%M")
        daily_close["date"] = daily_close.index.strftime("%Y%M%D")

        # # Insert
        # # todo: old delete old data
        # insert_json = []
        # for _idx, _row in daily_close.iteritems():
        #     record = {
        #         "date": _row["date"],
        #         "close_time": _row["close_time"],
        #         "volatility": _row["volatility"],
        #         "variance_days": _row["variance_days"],
        #         "volatility_days": _row["volatility_days"],
        #     }
        #     insert_json.append(record)
        # self.hd.mongodb.dao.insert_many(insert_json)
