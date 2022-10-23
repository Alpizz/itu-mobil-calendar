from datetime import datetime as dt

import sys
import pytz
from ITUMobil.configuration import ITU_MOBIL_LOCAL_TIMEZONE


class ITUMobilUtils:
    def get_timestamp_between_brackets(self, tarih="()"):
        return int(tarih[tarih.find("(") + 1 : tarih.find(")")])

    def convert_timestamp_to_datetime(self, timestamp: int):
        local_tz = pytz.timezone(zone=ITU_MOBIL_LOCAL_TIMEZONE)
        dt_obj = dt.fromtimestamp(timestamp / 1000, tz=local_tz)
        return dt_obj
    
    def query_yes_no(self, question, default="no"):
        """Ask a yes/no question via raw_input() and return their answer.

        "question" is a string that is presented to the user.
        "default" is the presumed answer if the user just hits <Enter>.
                It must be "yes" (the default), "no" or None (meaning
                an answer is required of the user).

        The "answer" return value is True for "yes" or False for "no".
        """
        valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
        if default is None:
            prompt = " [y/n] "
        elif default == "yes":
            prompt = " [Y/n] "
        elif default == "no":
            prompt = " [y/N] "
        else:
            raise ValueError(f"invalid default answer: {default}")

        while True:
            print(question + prompt)
            choice = input().lower()
            if default is not None and choice == "":
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                print("Please respond with 'yes' or 'no' " "(or 'y' or 'n').")
