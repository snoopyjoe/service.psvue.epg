import threading
import thread
import cherrypy
import xbmc, xbmcgui, xbmcaddon
import requests, urllib
import cookielib
import os
import sys

PS_VUE_ADDON = xbmcaddon.Addon('plugin.video.psvue')
ADDON_PATH_PROFILE = xbmc.translatePath(PS_VUE_ADDON.getAddonInfo('profile'))
UA_ANDROID_TV = 'Mozilla/5.0 (Linux; Android 6.0.1; Hub Build/MHC19J; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/61.0.3163.98 Safari/537.36'
VERIFY = True

def load_cookies():
    cookie_file = os.path.join(ADDON_PATH_PROFILE, 'cookies.lwp')
    cj = cookielib.LWPCookieJar()
    try:
        cj.load(cookie_file, ignore_discard=True)
    except:
        pass

    return cj


def epg_play_stream(url):
    headers = {
        'Accept': '*/*',
        'Content-type': 'application/x-www-form-urlencoded',
        'Origin': 'https://vue.playstation.com',
        'Accept-Language': 'en-US,en;q=0.8',
        'Referer': 'https://vue.playstation.com/watch/live',
        'Accept-Encoding': 'gzip, deflate, br',
        'User-Agent': UA_ANDROID_TV,
        'Connection': 'Keep-Alive',
        'Host': 'media-framework.totsuko.tv',
        'reqPayload': PS_VUE_ADDON.getSetting(id='EPGreqPayload'),
        'X-Requested-With': 'com.snei.vue.android'
    }

    r = requests.get(url, headers=headers, cookies=load_cookies(), verify=VERIFY)
    json_source = r.json()
    stream_url = json_source['body']['video']
    headers = '|User-Agent='
    headers += 'Adobe Primetime/1.4 Dalvik/2.1.0 (Linux; U; Android 6.0.1 Build/MOB31H)'
    headers += '&Cookie=reqPayload=' + urllib.quote('"' + PS_VUE_ADDON.getSetting(id='EPGreqPayload') + '"')
    listitem = xbmcgui.ListItem()
    listitem.setMimeType("application/x-mpegURL")
    # Checks to see if VideoPlayer info is already saved. If not then info is loaded from stream link

    """

    if xbmc.getCondVisibility('String.IsEmpty(ListItem.Title)'):

        # listitem = xbmcgui.ListItem(title, plot, thumbnailImage=icon)

        # listitem.setInfo(type="Video", infoLabels={'title': title, 'plot': plot})

        listitem.setMimeType("application/x-mpegURL")

    else:

        listitem = xbmcgui.ListItem()

        listitem.setMimeType("application/x-mpegURL")

    """

    if xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)'):
        listitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
        listitem.setProperty('inputstream.adaptive.manifest_type', 'hls')
        listitem.setProperty('inputstream.adaptive.stream_headers', headers)
        listitem.setProperty('inputstream.adaptive.license_key', headers)

    else:
        stream_url += headers

    listitem.setPath(stream_url)
    xbmc.Player().play(item=stream_url+headers, listitem=listitem)




class Root(object):

    exposed = True

    @cherrypy.expose
    def GET(self, params):
        cherrypy.response.status = 302
        cherrypy.response.headers['Connection'] = 'keep-alive'
        cherrypy.response.headers['Content-Type'] = 'text/html'
        # Play default mp4 to avoid playback failed dialog
        cherrypy.response.headers['Location'] = 'http://clips.vorwaerts-gmbh.de/big_buck_bunny.mp4'
        epg_play_stream(params)



class PSVueWebService(threading.Thread):
    __root = None


    def __init__(self):
        self.__root = Root()

        if ADDON.getSetting(id='port') == '':
            dialog = xbmcgui.Dialog()
            dialog.notification('PS Vue EPG', 'Please enter a port number in the PS Vue EPG Build Settings', xbmcgui.NOTIFICATION_INFO, 5000, False)
            sys.exit()
        else:
            port = ADDON.getSetting(id='port')




        cherrypy.config.update({
            'server.socket_host': '127.0.0.1',
            'server.socket_port': int(port),
            'engine.timeout_monitor.frequency': 5,
            'server.shutdown_timeout': 1
        })
        threading.Thread.__init__(self)



    def run(self):
        cherrypy.tree.mount(Root(), '/psvue', {
        '/': {

            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),

            'tools.sessions.on': True,

            'tools.response_headers.on': True

            }

        })
        cherrypy.engine.start()



    def stop(self):
        cherrypy.engine.exit()
        self.join(0)
        del self.__root