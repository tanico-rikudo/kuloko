from datetime import datetime as dt
from datetime import  timedelta, timezone
import os

# D: Date
# None: datetime
class daylib():

    @classmethod
    def valid_intD(cls, int_date):
        if (int_date < 20000101)or(int_date>21001231):
            raise Exception("int_date must be 8-digits and following realworld")
        return True

    @classmethod
    def intD_to_dt(cls, int_date):
        cls.valid_intD(int_date)
        return dt.strptime(str(int_date),'%Y%m%d')

    @classmethod
    def intD_to_strD(cls, int_date):
        cls.valid_intD(int_date)
        return str(int_date)

    @classmethod
    def dt_to_intD(cls, dt_obj):
        return int(dt_obj.strftime('%Y%m%d'))

    @classmethod
    def dt_to_intYMDHMSF(cls, dt_obj):
        return dt_obj.strftime('%Y%m%d%H%M%S%f')

    @classmethod
    def str_utc_to_dt_offset(cls, str_utc, offset=0,is_T=True,is_ms=True, is_Z=True):
        format = '%Y-%m-%d'

        T =  'T' if  is_T else ' '
        format = format + T
        if is_ms:
            format = format +'%H:%M:%S.%f'
        else:
            format = format +'%H:%M:%S'
        # format += '.%z'
        format +=  'Z' if  is_Z else ''

        # dt_utc = dt.strptime(str_utc + "+0000", format)
        dt_utc = dt.strptime(str_utc, format)
        dt_offset = dt_utc.astimezone(timezone(timedelta(hours=offset)))
        return dt_offset


    @classmethod
    def add_day(cls, int_date, offset):
        # No checl : OK
        dt_obj = cls.intD_to_dt(int_date)
        dt_obj = dt_obj+ timedelta(days=offset)
        return cls.dt_to_intD(dt_obj)



    @classmethod
    def get_between_date(cls, since_int_date, until_int_date) :
        _ = cls.valid_intD(since_int_date)    
        _ = cls.valid_intD(until_int_date)
        _int_date = since_int_date
        dates = []
        while True:
            if  _int_date > until_int_date:
                break
            dates.append(_int_date)
            _int_date = cls.add_day(_int_date,1)
        return dates

