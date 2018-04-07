import threading
import cherrypy
import xbmc, xbmcgui, xbmcaddon
import requests
import cookielib
import os
import sys
import m3u8

ADDON = xbmcaddon.Addon()
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
    stream_url = r.json()['body']['video']

    r = requests.get(stream_url, headers=headers)
    variant_m3u8 = m3u8.loads(r.text)
    bandwidth = 0
    best_stream = ''
    for playlist in variant_m3u8.playlists:
        xbmc.log(str(playlist.stream_info.bandwidth))
        xbmc.log(playlist.uri)
        if playlist.stream_info.bandwidth > bandwidth:
            bandwidth = playlist.stream_info.bandwidth
            best_stream = playlist.uri

    if 'http' not in best_stream and best_stream != '':
        stream_url = stream_url.replace(stream_url.rsplit('/', 1)[-1], best_stream)

    return stream_url


class Root(object):
    exposed = True

    @cherrypy.expose
    def GET(self, params):
        cherrypy.response.cookie['reqPayload'] = PS_VUE_ADDON.getSetting(id='EPGreqPayload')
        cherrypy.response.cookie['reqPayload']['Domain'] = 'totsuko.tv'
        cherrypy.response.cookie['reqPayload']['Path'] = '/'
        stream_url = epg_play_stream(params)
        raise cherrypy.HTTPRedirect(stream_url)


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

            'tools.sessions.on': False,

            'tools.response_headers.on': True

            }

        })
        cherrypy.engine.start()

    def stop(self):
        cherrypy.engine.exit()
        self.join(0)
        del self.__root