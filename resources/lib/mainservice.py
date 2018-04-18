from globals import *
from database import Database
from guideservice import BuildGuide
from webservice import PSVueWebService


if not xbmc.getCondVisibility('System.HasAddon(pvr.iptvsimple)'):
    dialog = xbmcgui.Dialog()
    dialog.notification('PS Vue EPG', 'Please enable PVR IPTV Simple Client', xbmcgui.NOTIFICATION_INFO, 5000, False)
    sys.exit()

IPTV_SIMPLE_ADDON = xbmcaddon.Addon('pvr.iptvsimple')


class MainService:
    monitor = None
    last_update = None

    def __init__(self):
        self.monitor = xbmc.Monitor()

        xbmc.log('Calling PSVueWebService to start....')
        self.psvuewebservice = PSVueWebService()
        self.psvuewebservice.start()

        xbmc.log('Calling BuildGuide to start....')
        self.guideservice = BuildGuide()
        self.guideservice.start()

        self.last_update = datetime.now()
        #check_files()
        self.db = Database()
        self.db.set_db_channels(get_channel_list())
        build_playlist(self.db.get_db_channels())

        xbmc.log("PS Vue EPG Update Check. Last Update: " + self.last_update.strftime('%m/%d/%Y %H:%M:%S'),
                 level=xbmc.LOGNOTICE)
        self.main_loop()

    def main_loop(self):
        while not self.monitor.abortRequested():
            # Sleep/wait for abort for 10 minutes
            if self.monitor.waitForAbort(600):
                # Abort was requested while waiting. We should exit
                break
            if self.last_update < datetime.now() - timedelta(days=1):
                self.db.set_db_channels(get_channel_list())
                build_playlist(self.db.get_db_channels())
                self.last_update = datetime.now()

            xbmc.log("PS Vue EPG Update Check. Last Update: " + self.last_update.strftime('%m/%d/%Y %H:%M:%S'),
                     level=xbmc.LOGNOTICE)

        self.close()

    def close(self):
        self.psvuewebservice.stop()
        self.guideservice.stop()
        del self.monitor