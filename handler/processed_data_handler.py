import pandas as pd
import numpy as np

from utils import daylib
dl = daylib.daylib()


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
