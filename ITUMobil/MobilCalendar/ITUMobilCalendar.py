import json
import pytz
import uuid
import os
import requests
from datetime import datetime as dt
from datetime import timedelta
from icalendar import Calendar, Event, vDatetime
from enum import Enum


from ITUMobil.MobilUtils import ITUMobilUtils

from ..configuration import (
    ITU_MOBIL_API_BASE_URL,
    ITU_MOBIL_SECURITY_ID,
    ITU_MOBIL_DEVICE_NAME,
    ITU_MOBIL_DEVICE_MODEL,
    ITU_MOBIL_OS_TYPE,
    ITU_MOBIL_LOCALE,
    ITU_MOBIL_LOCAL_TIMEZONE,
    CALENDAR_OUTPUT_PATHNAME,
)


# TODO: Error handling
# TODO: Check for empty values (location lat long)
class ITUMobilCalendarHandler:
    def __init__(self):
        self.status_code: int = 0
        self.result_code: int = None
        self.result_message: str = None
        self.ders_baslangic_tarihi: str = ""
        self.ders_bitis_tarihi: str = ""
        self.akademik_donem_kodu: str = ""
        self.akademik_takvim_tipi_id: int = 0
        self.person_ders_list = []

        self.local_tz = None
        self.main_dtstart = None
        self.main_dtend = None
        self.donem = {}
        self.calendar = Calendar()

        self.itu_mobil_token = os.environ.get("ITU_MOBIL_TOKEN")
        self.itu_mobil_utils = ITUMobilUtils.ITUMobilUtils()

    def get_person_sis_schedule_from_ituportal(self):
        if not self.itu_mobil_token:
            raise ValueError("ITU Portal token is not set.")
        params = {
            "method": "GetPersonSISSchedule",
            "securityId": ITU_MOBIL_SECURITY_ID,
            "Token": self.itu_mobil_token,
            "Locale": ITU_MOBIL_LOCALE,
        }
        response = requests.get(ITU_MOBIL_API_BASE_URL, params=params)
        response = response.json()
        return response

    def set_attributes(self, response=None):
        """Parse the response from the server.

        Args:
            response: A string containing the response from the server.

        Returns:
            A dictionary containing the parsed response.
        """

        response = self.get_person_sis_schedule_from_ituportal()
        self.status_code = response["StatusCode"]
        self.result_code = response["ResultCode"]
        self.result_message = response["ResultMessage"]
        self.ders_baslangic_tarihi = response["DersBaslangicTarihi"]
        self.ders_bitis_tarihi = response["DersBitisTarihi"]
        self.akademik_donem_kodu = response["AkadamikDonemKodu"]
        self.akademik_takvim_tipi_id = response["AkademikTakvimTipiId"]
        self.person_ders_list = response["PersonDersList"]
        # Return the response.
        return response

    def prepare_for_calendar(self):
        """Prepare the response for the calendar.

        Returns:
            A dictionary containing the prepared response.
        """
        self.set_attributes()
        baslangic_timestamp = self.itu_mobil_utils.get_timestamp_between_brackets(
            tarih=self.ders_baslangic_tarihi
        )
        bitis_timestamp = self.itu_mobil_utils.get_timestamp_between_brackets(
            tarih=self.ders_bitis_tarihi
        )

        self.main_dtstart = self.convert_timestamp_to_ical_and_dt(
            timestamp=baslangic_timestamp
        )
        self.main_dtend = self.convert_timestamp_to_ical_and_dt(
            timestamp=bitis_timestamp
        )
        self.get_donem_name_from_response()
        return True

    def convert_timestamp_to_ical_and_dt(self, timestamp: int):
        """Convert a timestamp to an iCalendar datetime.

        Args:
            timestamp: A timestamp in milliseconds.

        Returns:
            A datetime object.
        """
        # Convert the timestamp to a datetime object.
        dt_obj = self.itu_mobil_utils.convert_timestamp_to_datetime(timestamp)
        # Convert the datetime object to an iCalendar vDatetime.
        v_dt_obj = vDatetime(dt_obj)
        date_dict = {"dt": dt_obj, "ical": v_dt_obj.to_ical()}
        # Return the iCalendar datetime.
        return date_dict

    def create_calendar(self):
        """Create the calendar.

        Returns:
            An iCalendar calendar object.
        """
        self.prepare_for_calendar()
        # Create the calendar.
        self.calendar.add("prodid", "-//Alpiz//ITU Mobil Calendar//EN")
        self.calendar.add("version", "2.0")
        self.calendar.add(
            "x-wr-calname",
            f"İTÜ {self.donem['donem_adi']} {self.donem['donem_yil']-1}-{self.donem['donem_yil']} Ders Programı",
        )
        self.calendar.add("x-wr-caldesc", "ITU Mobil Calendar")
        self.calendar.add("x-wr-timezone", ITU_MOBIL_LOCAL_TIMEZONE)
        # Return the calendar.
        return self.calendar

    def get_donem_name_from_response(self):
        class Donem(Enum):
            GÜZ = 1
            BAHAR = 2
            YAZ = 3

        donem_yil = self.akademik_donem_kodu[:4]
        donem_kod = self.akademik_donem_kodu[-2]
        for donem in Donem:
            if donem.value == int(donem_kod):
                donem_name = donem.name
                break
        else:
            raise ValueError("Incorrect Donem Kodu")
        donem = {"donem_yil": int(donem_yil), "donem_adi": donem_name}
        self.donem = donem
        return self.donem

    def create_event_from_lesson(self, lesson):
        """Create an event from lesson.

        Returns:
            An iCalendar event object from lesson.
        """
        # Create the event.
        event = Event()
        event.add("title", lesson["DersKodu"] + lesson["DersNumarasi"])
        event.add(
            "description",
            lesson["DersKodu"]
            + " "
            + lesson["DersNumarasi"]
            + " (CRN: "
            + lesson["CRN"]
            + ")",
        )
        event.add("summary", lesson["DersAdi"])
        event.add("dtstart", self.correct_lesson_dt(lesson)["LessonDTStart"])
        event.add("dtend", self.correct_lesson_dt(lesson)["LessonDTEnd"])
        event.add(
            "rrule",
            {"freq": "weekly", "until": self.main_dtend["dt"] + lesson["EndTimeDelta"]},
        )
        event.add("dtstamp", dt.now())
        lesson_location = (
            lesson["BinaKodu"]
            + "-"
            + ("?" if lesson["DerslikKodu"] == "-" else lesson["DerslikKodu"])
        )
        event.add("location", lesson_location)
        event.add("uid", str(uuid.uuid4()))
        event.add(
            "X-APPLE-STRUCTURED-LOCATION",
            "geo:" + str(lesson["Latitude"])[:8] + "," + str(lesson["Longitude"]),
            parameters={
                "VALUE": "URI",
                "X-ADDRESS": lesson_location,
                "X-APPLE-RADIUS": "72",
                "X-TITLE": lesson_location,
            },
        )
        # Return the event.
        return event

    def add_event_to_calendar(self, event):
        """Add an event to the calendar.

        Args:
            event: An iCalendar event object.
        """
        self.calendar.add_component(event)

    def correct_lesson_dt(self, lesson):
        """Correct the lesson's datetime.

        Args:
            lesson: A dictionary containing the lesson's information.

        Returns:
            A dictionary containing the corrected lesson's information.
        """
        # Correct the lesson's datetime.
        minute_timedelta = int(lesson["BaslangicZamani"])
        day_timedelta = int(lesson["GunObjectId"]) - 1

        lesson["StartTimeDelta"] = timedelta(
            days=day_timedelta, minutes=minute_timedelta
        )
        lesson["LessonDTStart"] = self.main_dtstart["dt"] + lesson["StartTimeDelta"]

        minute_timedelta = int(lesson["BitisZamani"])
        lesson["EndTimeDelta"] = timedelta(days=day_timedelta, minutes=minute_timedelta)
        lesson["LessonDTEnd"] = self.main_dtstart["dt"] + lesson["EndTimeDelta"]
        # Return the corrected lesson.
        return lesson

    def create_calendar_and_add_lessons(self):
        self.create_calendar()
        for lesson in self.person_ders_list:
            self.add_event_to_calendar(self.create_event_from_lesson(lesson))

    def export_to_ics(self):
        self.create_calendar_and_add_lessons()
        if not os.path.isdir(CALENDAR_OUTPUT_PATHNAME):
            os.mkdir(path=CALENDAR_OUTPUT_PATHNAME)
        with open(f"{CALENDAR_OUTPUT_PATHNAME}/itu-calendar.ics", "wb") as f:
            f.write(self.calendar.to_ical())
        print(f"Calendar exported to {CALENDAR_OUTPUT_PATHNAME}/itu-calendar.ics")
