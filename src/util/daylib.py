from datetime import datetime as dt
from datetime import  timedelta, timezone

# D: Date
# None: datetime
class daylib():
    @classmethod
    def intD_to_dt(cls, int_date):
        return dt.strptime(str(int_date),'%Y%m%d')

    @classmethod
    def dt_to_intD(cls, dt_obj):
        return int(dt_obj.strftime('%Y%m%d'))

    @classmethod
    def str_utc_to_dt_offset(cls, str_utc, offset=0):
        dt_utc = dt.strptime(str_utc + "+0000", '%Y-%m-%dT%H:%M:%S.%fZ%z')
        dt_offset = dt_utc.astimezone(timezone(timedelta(hours=offset)))
        return dt_offset