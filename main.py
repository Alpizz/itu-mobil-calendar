from ITUMobil.MobilAuth import ITUMobilAuth
from ITUMobil.MobilCalendar import ITUMobilCalendar

auth_handle = ITUMobilAuth.ITUMobilAuthHandler()
auth_handle.login_to_itu_mobil()
try:
    calendar_handle = ITUMobilCalendar.ITUMobilCalendarHandler()
    calendar_handle.export_to_ics()
except Exception as e:
    print("Error occured.", e)
finally:
    auth_handle.logout_from_itu_mobil()
