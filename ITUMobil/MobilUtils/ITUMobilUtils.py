from datetime import datetime as dt

import pytz
from ITUMobil.configuration import ITU_MOBIL_LOCAL_TIMEZONE


class ITUMobilUtils:
    def get_timestamp_between_brackets(self, tarih="()"):
        return int(tarih[tarih.find("(") + 1 : tarih.find(")")])

    def convert_timestamp_to_datetime(self, timestamp: int):
        local_tz = pytz.timezone(zone=ITU_MOBIL_LOCAL_TIMEZONE)
        dt_obj = dt.fromtimestamp(timestamp / 1000, tz=local_tz)
        return dt_obj
