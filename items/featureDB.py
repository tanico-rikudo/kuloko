import sys, os
import time
import pandas as pd
import numpy as np
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

from util import daylib

dl = daylib.daylib()


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
        df = self.hd.file_hist.bulk_load(symbol, "trade", since_date, until_date)
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

    """ Create features"""

    def create_volatility(self, symbol, until_date=None):
        """
        Create volatility from trade ad ticker
        :param symbol:
        :param until_date:
        :return:
        """
        # Fixed
        VOLATILITY_VAR_DAYS = 30
        VOLATILITY_DAYS = 1
        until_date = (
            dl.dt_to_intD(dl.currentTime()) if until_date is None else until_date
        )
        since_date = dl.add_day(until_date, VOLATILITY_VAR_DAYS + 1)

        # trade
        trades = self.hd.get_hist_trades(symbol, since_date, until_date)
        daily_close_trade = (
            trades.price.resample("T", label="left", closed="left")
            .ohlc()
            .loc[:, "close"]
        )

        # ticker
        tickers = self.hd.get_hist_tickers(symbol, since_date, until_date)
        if "last" in tickers.columns():
            daily_close_ticker = tickers.loc[:, "last"]
        elif "close" in tickers.columns():
            daily_close_ticker = tickers.loc[:, "close"]
        else:
            daily_close_ticker = None

        # Fill each other
        daily_close = pd.concat([daily_close_trade, daily_close_ticker], axis=0)

        # calc volatility
        daily_close = self.calc_daily_volatility(
            daily_close, VOLATILITY_VAR_DAYS, VOLATILITY_DAYS, close_time="00:00"
        )
        daily_close["close_time"] = daily_close.index.strftime("%H%M")
        daily_close["date"] = daily_close.index.strftime("%Y%M%D")

        # Insert
        # todo: old delete old data
        insert_json = []
        for _idx, _row in daily_close.iteritems():
            record = {
                "date": _row["date"],
                "close_time": _row["close_time"],
                "volatility": _row["volatility"],
                "variance_days": _row["variance_days"],
                "volatility_days": _row["volatility_days"],
            }
            insert_json.append(record)
        self.hd.mongodb.dao.insert_many(insert_json)

    @staticmethod
    def calc_daily_volatility(
        daily_close, variance_days, volatility_days, close_time="00:00"
    ):
        """
        Calc volatility
        :param daily_close:
        :param variance_days:
        :param volatility_days:
        :param close_time:
        :return: dataframe
        """

        # Create molt
        ls_date = [int(_date) for _date in daily_close.index.strftime("%Y%m%d")]
        min_date, max_date = min(ls_date), max(ls_date)
        ls_date = dl.get_between_date(min_date, max_date)
        df_date = pd.DataFrame(ls_date, index=[_i for _i in ls_date], columns=["date"])
        df_date["datetime"] = pd.to_datetime(
            df_date["date"] + close_time, format="%Y%m%d %H:%M"
        )
        del df_date["date"]

        df_close = pd.merge_asof(
            df_date, daily_close, on="datetime", direction="nearest"
        )
        df_close["volatility"] = df_close.pct_change().rolling(
            variance_days
        ).std() * np.sqrt(volatility_days)
        return df_close
