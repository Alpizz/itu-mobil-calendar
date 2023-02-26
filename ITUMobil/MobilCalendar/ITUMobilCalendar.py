import json
import pytz
import uuid
import os
import requests
from urllib import parse
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
    NINOVA_HOMEWORK_BASE_URL,
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
        self.person_odev_list = []

        self.local_tz = None
        self.main_dtstart = None
        self.main_dtend = None
        self.donem = {}
        self.lesson_calendar = Calendar()
        
        self.itu_mobil_utils = ITUMobilUtils.ITUMobilUtils()
        self.itu_mobil_token = os.environ.get("ITU_MOBIL_TOKEN")
        
        self.include_homeworks = self.itu_mobil_utils.query_yes_no("Do you want to export homeworks?", default="no")
        self.homework_calendar = Calendar()

    def get_query_from_ituportal(self, method):
        if not self.itu_mobil_token:
            raise ValueError("ITU Portal token is not set.")
        params = {
            "method": method,
            "securityId": ITU_MOBIL_SECURITY_ID,
            "Token": self.itu_mobil_token,
            "Locale": ITU_MOBIL_LOCALE,
        }
        response = requests.get(ITU_MOBIL_API_BASE_URL, params=params)
        response = response.json()
        return response

    def set_attributes_for_lessons(self, response=None):
        """Parse the response from the server.

        Args:
            response: A string containing the response from the server.

        Returns:
            A dictionary containing the parsed response.
        """
        
        method = "GetPersonSISSchedule"
        response = self.get_query_from_ituportal(method)
        self.status_code = response["StatusCode"]
        if self.status_code != 0:
            raise ValueError("Status code is not 0.")
        self.result_code = response["ResultCode"]
        self.result_message = response["ResultMessage"]
        self.ders_baslangic_tarihi = response["DersBaslangicTarihi"]
        self.ders_bitis_tarihi = response["DersBitisTarihi"]
        self.akademik_donem_kodu = response["AkadamikDonemKodu"]
        self.akademik_takvim_tipi_id = response["AkademikTakvimTipiId"]
        self.person_ders_list = response["PersonDersList"]
        # Return the response.
        return response
    
    def set_attributes_for_homeworks(self):
        method = "GetNinovaSinif"
        response = self.get_query_from_ituportal(method)
        self.person_odev_list = response["NinovaOdevListesi"]
        return response

    def prepare_lessons_for_calendar(self):
        """Prepare the response for the calendar.

        Returns:
            A dictionary containing the prepared response.
        """
        self.set_attributes_for_lessons()
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
    
    def prepare_homeworks_for_calendar(self):
        """_summary_.

        Returns:
            _description_.
        """
        self.set_attributes_for_homeworks()
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

    def create_lesson_calendar(self):
        """Create the calendar.

        Returns:
            An iCalendar calendar object.
        """
        self.prepare_lessons_for_calendar()
        # Create the calendar.
        self.lesson_calendar.add("prodid", "-//Alpiz//ITU Mobil Calendar//EN")
        self.lesson_calendar.add("version", "2.0")
        self.lesson_calendar.add(
            "x-wr-calname",
            f"İTÜ {self.donem['donem_adi']} {self.donem['donem_yil']-1}-{self.donem['donem_yil']} Ders Programı",
        )
        self.lesson_calendar.add("x-wr-caldesc", "ITU Mobil Calendar")
        self.lesson_calendar.add("x-wr-timezone", ITU_MOBIL_LOCAL_TIMEZONE)
        # Return the calendar.
        return self.lesson_calendar
    
    def create_homework_calendar(self):
        """Create the calendar.

        Returns:
            An iCalendar calendar object.
        """
        self.prepare_homeworks_for_calendar()
        # Create the calendar.
        self.homework_calendar.add("prodid", "-//Alpiz//ITU Mobil Calendar//EN")
        self.homework_calendar.add("version", "2.0")
        self.homework_calendar.add(
            "x-wr-calname",
            f"İTÜ {self.donem['donem_adi']} {self.donem['donem_yil']-1}-{self.donem['donem_yil']} Ödev Programı",
        )
        self.homework_calendar.add("x-wr-caldesc", "ITU Mobil Calendar")
        self.homework_calendar.add("x-wr-timezone", ITU_MOBIL_LOCAL_TIMEZONE)
        # Return the calendar.
        return self.homework_calendar

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
    
    def create_event_from_homework(self, homework):
        event = Event()
        event.add("title", homework["DersKodu"])
        event.add(
            "summary",
            homework["OdevBaslik"]
            + " - "
            + homework["DersKodu"],
        )
        event.add("description", homework["OdevAciklama"])
        event.add("dtstart", self.correct_homework_dt(homework)["HomeworkDTStart"])
        event.add("dtend", self.correct_homework_dt(homework)["HomeworkDTEnd"])
        event.add("dtstamp", dt.now())
        event.add("location", f'{homework["CRN"]} - {homework["DersAdi"]}')
        event.add("uid", str(uuid.uuid4()))
        event.add("url", self.get_homework_url(homework)["OdevURL"])
        return event
    
    def get_homework_url(self, homework):
        homework_detail_query = "?" + homework["DetailQuery"]
        params = dict(parse.parse_qsl(parse.urlsplit(homework_detail_query).query))
        homework["OdevURL"] = NINOVA_HOMEWORK_BASE_URL.format(**params)
        return homework

    def add_event_to_calendar(self, event, event_type="lesson"):
        """Add an event to the calendar.

        Args:
            event: An iCalendar event object.
        """
        if event_type == "lesson":
            self.lesson_calendar.add_component(event)
        elif event_type == "homework":
            self.homework_calendar.add_component(event)
        else:
            print("Event type is not valid.")

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

    def correct_homework_dt(self, homework):
        homework_deadline = homework["OdevTeslimBitis"]
        hw_timestamp = self.itu_mobil_utils.get_timestamp_between_brackets(homework_deadline)
        hw_date = self.itu_mobil_utils.convert_timestamp_to_datetime(hw_timestamp)
        homework["HomeworkDTStart"] = hw_date - timedelta(hours=1)    
        homework["HomeworkDTEnd"] = hw_date
        return homework
    
    def create_calendar_and_add_lessons(self):
        self.create_lesson_calendar()
        for lesson in self.person_ders_list:
            lesson_event = self.create_event_from_lesson(lesson)
            self.add_event_to_calendar(lesson_event, event_type="lesson")
            
    def create_calendar_and_add_homeworks(self):
        self.create_homework_calendar()
        for homework in self.person_odev_list:
            homework_event = self.create_event_from_homework(homework)
            self.add_event_to_calendar(homework_event, event_type="homework")
    
    def export_to_ics(self):
        self.create_calendar_and_add_lessons()
        if not os.path.isdir(CALENDAR_OUTPUT_PATHNAME):
            os.mkdir(path=CALENDAR_OUTPUT_PATHNAME)
        with open(f"{CALENDAR_OUTPUT_PATHNAME}/itu-calendar-lessons.ics", "wb") as f:
            f.write(self.lesson_calendar.to_ical())
        print(f"Lesson calendar exported to {CALENDAR_OUTPUT_PATHNAME}/itu-calendar-lessons.ics")
        
        if self.include_homeworks:
            self.create_calendar_and_add_homeworks()
            with open(f"{CALENDAR_OUTPUT_PATHNAME}/itu-calendar-homeworks.ics", "wb") as f:
                f.write(self.homework_calendar.to_ical())
            print(f"Homework calendar exported to {CALENDAR_OUTPUT_PATHNAME}/itu-calendar-homeworks.ics")
