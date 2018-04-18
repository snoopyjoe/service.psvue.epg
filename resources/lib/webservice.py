import socket
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urlparse import parse_qs
from globals import *


def epg_get_stream(url):
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

    return stream_url


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        xbmc.log("WebServer: Get request Received")

        ##########################################################################################
        # Stream preparation chunk
        ##########################################################################################

        # Extract channel url from request URI
        if str(self.path)[0:6] == '/psvue':
            parameters = parse_qs(self.path[7:])
            channel_url = urllib.unquote(str(parameters['params'][0]))
            xbmc.log("Received Channel URL: " + channel_url)

            self.pvr_request(channel_url)
        else:
            request = self.path
            self.stream_request(request)

    def pvr_request(self, channel_url):
        stream_url = epg_get_stream(channel_url)
        xbmc.log("Retrieved Stream URL: " + stream_url)

        location = stream_url
        if '18.' not in xbmc.getInfoLabel("System.BuildVersion"):
            location = 'http://clips.vorwaerts-gmbh.de/big_buck_bunny.mp4'

        self.send_response(303)

        headers = {
            'Content-type': 'text/html;charset=utf-8',
            'Connection': 'close',
            #'Host': 'media-framework.totsuko.tv',
            'Location': location,
            'Set-Cookie': 'reqPayload=' + '"' + PS_VUE_ADDON.getSetting(id='EPGreqPayload') + '"' +
                          '; Domain=totsuko.tv; Path=/'
        }

        # Loop through the Header Array sending each one individually
        for key in headers:
            try:
                value = headers[key]
                self.send_header(key, value)
            except Exception as e:
                xbmc.log(e)
                pass

        # Tells the server the headers are done and the body can be started
        self.end_headers()

        # Close the server response file
        self.wfile.close()

        if '18.' not in xbmc.getInfoLabel("System.BuildVersion"):
            self.play_as_listitem(stream_url)

    def play_as_listitem(self, stream_url):
        headers = '|User-Agent='
        headers += UA_ADOBE
        headers += '&Cookie=reqPayload=' + urllib.quote('"' + PS_VUE_ADDON.getSetting(id='EPGreqPayload') + '"')
        listitem = xbmcgui.ListItem()
        listitem.setMimeType("application/x-mpegURL")
        if xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)'):
            listitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
            listitem.setProperty('inputstream.adaptive.manifest_type', 'hls')
            listitem.setProperty('inputstream.adaptive.stream_headers', headers)
            listitem.setProperty('inputstream.adaptive.license_key', headers)
        else:
            stream_url += headers

        listitem.setPath(stream_url)
        xbmc.Player().play(item=stream_url + headers, listitem=listitem)

    def stream_request(self, request):
        self.send_response(404)

        self.end_headers()
        self.wfile.write(request.path + ' NOT FOUND!')

        self.wfile.close()


class Server(HTTPServer):
    def get_request(self):
        self.socket.settimeout(5.0)
        result = None
        while result is None:
            try:
                result = self.socket.accept()
            except socket.timeout:
                pass
        result[0].settimeout(1000)
        return result


class ThreadedHTTPServer(ThreadingMixIn, Server):
    """Handle requests in a separate thread."""


class PSVueWebService(threading.Thread):
    httpd = None
    hostname = '127.0.0.1'
    port = ''

    def __init__(self):

        if ADDON.getSetting(id='port') == '':
            dialog = xbmcgui.Dialog()
            dialog.notification('PS Vue EPG', 'Please enter a port number in the PS Vue EPG Build Settings',
                                xbmcgui.NOTIFICATION_INFO, 5000, False)
            sys.exit()
        else:
            self.port = ADDON.getSetting(id='port')

        if self.httpd is None:
            socket.setdefaulttimeout(10)
            server_class = ThreadedHTTPServer
            xbmc.log('Initialized WebServer Hostname | Port -> ' + self.hostname + ' | ' + str(self.port))
            self.httpd = server_class((self.hostname, int(self.port)), RequestHandler)

        threading.Thread.__init__(self)

    def run(self):
        try:
            self.httpd.serve_forever()
        except Exception as e:
            xbmc.log('Web Server unable to server: ' + str(e))

    def stop(self):
        try:
            self.httpd.server_close()
            xbmc.log("WebServer Stopped %s:%s" % (self.hostname, self.port))
        except Exception as e:
            xbmc.log(e)
            pass

        self.join(0)
