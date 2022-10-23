from ITUMobil.MobilAuth import ITUMobilAuth
from ITUMobil.MobilCalendar import ITUMobilCalendar
handle = ITUMobilAuth.ITUMobilAuthHandler()
handle.login_to_itu_mobil()
try:
    calhandler = ITUMobilCalendar.ITUMobilCalendarHandler()
    calhandler.export_to_ics()
except:
    print("Error occured.")
finally:
    handle.logout_from_itu_mobil()