import cookielib
import os
import requests, urllib
from datetime import datetime, timedelta
import xbmc, xbmcplugin, xbmcgui, xbmcaddon, xbmcvfs

PS_VUE_ADDON = xbmcaddon.Addon('plugin.video.psvue')
ADDON_PATH_PROFILE = xbmc.translatePath(PS_VUE_ADDON.getAddonInfo('profile'))
UA_ANDROID_TV = 'Mozilla/5.0 (Linux; Android 6.0.1; Hub Build/MHC19J; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/61.0.3163.98 Safari/537.36'
CHANNEL_URL = 'https://media-framework.totsuko.tv/media-framework/media/v2.1/stream/channel'
EPG_URL = 'https://epg-service.totsuko.tv/epg_service_sony/service/v2'
SHOW_URL = 'https://media-framework.totsuko.tv/media-framework/media/v2.1/stream/airing/'
VERIFY = False
# -----------------------------------------------------------------------------------------
# EPG Code
# Setup
#  - Build Playlist (PS Vue Addon (Settings/Build Playlist)
#  - Enable Web Server (Settings/Services/Control/Allow remote control via HTTP)
#  - Enabled PVR IPTV Simple Client (Addons/My add-ons/PVR Clients)
#  - Set M3U play Local Path (Home Folder/userdata/addon_data/plugin.video.psvue/playlist.m3u)
#  - Set IPTV Channel Logos - Channels Logos from XMLTV to prefer M3U
# ------------------------------------------------------------------------------------------


def build_playlist():
    """
    <webserverpassword>web_passwor</webserverpassword>
    <webserverport default="true">8080</webserverport>
    <webserverusername>web_username</webserverusername>
    """
    settings_file = xbmcvfs.File(os.path.join("special://userdata","guisettings.xml"),"r")
    gui_settings = settings_file.read()
    webserver_usr = find(gui_settings,'<webserverusername>','</webserverusername>')
    webserver_pwd = find(gui_settings,'<webserverpassword>','</webserverpassword>')
    webserver_port = find(gui_settings, '<webserverport default="true">', '</webserverport>')

    json_source = get_json(EPG_URL + '/browse/items/channels/filter/all/sort/channeltype/offset/0/size/500')
    m3u_file = open(os.path.join(ADDON_PATH_PROFILE, "playlist.m3u"),"w")
    m3u_file.write("#EXTM3U")
    m3u_file.write("\n")

    channel_ids = []
    channel_names_str = ''
    for channel in json_source['body']['items']:
        title = channel['title']
        if channel['channel_type'] == 'linear':
            title = title.encode('utf-8')
            channel_id = str(channel['id'])
            channel_ids.append(channel_id)
            logo = None
            for image in channel['urls']:
                if 'width' in image:
                    xbmc.log(str(image['width']))
                    if image['width'] == 600 or image['width'] == 440:
                        logo = image['src']
                        logo = logo.encode('utf-8')
                        break

            url = 'http://'
            if webserver_usr and webserver_pwd: url += webserver_usr + ':' + webserver_pwd + '@'
            url += 'localhost:' + webserver_port
            url += '/jsonrpc?request='
            url += urllib.quote('{"jsonrpc":"2.0","method":"Addons.ExecuteAddon","params":{"addonid":"script.psvue.epg","params":{"url":"' + CHANNEL_URL + '/' + channel_id + '"}},"id": 1}')

            #url = 'http://localhost:8080/jsonrpc?request='
            #url += urllib.quote('{"jsonrpc":"2.0","method":"Addons.ExecuteAddon","params":{"addonid":"script.psvue.epg","params":{"url":"' + CHANNEL_URL + '/' + channel_id + '"}},"id": 1}')

            m3u_file.write("\n")
            channel_info = '#EXTINF:-1 tvg-id="'+channel_id+'" tvg-name="' + title + '"'
            if logo is not None: channel_info += ' tvg-logo="'+logo+'"'
            channel_info += ' group_title="PS Vue",' + title
            m3u_file.write(channel_info+"\n")
            m3u_file.write(url+"\n")

            channel_names_str += '<channel id="' + channel_id + '">\n'
            channel_names_str += '    <display-name lang="en">' + title + '</display-name>\n'
            channel_names_str += '</channel>\n'

    m3u_file.close()

    channel_ids_str = ",".join(channel_ids)
    PS_VUE_ADDON.setSetting(id='channelIDs', value=channel_ids_str)
    PS_VUE_ADDON.setSetting(id='channelNamesXML', value=channel_names_str)

    dialog = xbmcgui.Dialog()
    dialog.notification('PS Vue Playlist', 'The playlist has finished building', xbmcgui.NOTIFICATION_INFO, 3000)


def build_epg():
    channel_ids = PS_VUE_ADDON.getSetting('channelIDs').split(',')
    channel_names_xml = PS_VUE_ADDON.getSetting('channelNamesXML')
    xmltv_file = open(os.path.join(ADDON_PATH_PROFILE, "epg.xml"), "w")
    xmltv_file.write('<?xml version="1.0" encoding="utf-8" ?>\n')
    xmltv_file.write("<tv>\n")
    xmltv_file.write(channel_names_xml)

    xbmc.log("-----------------------------------------------------------------------------------------------------")
    xbmc.log(str(channel_ids))
    xbmc.log(channel_names_xml)
    xbmc.log("-----------------------------------------------------------------------------------------------------")

    progress = xbmcgui.DialogProgress()
    progress.create('PS Vue EPG')
    progress.update(0, 'Retrieving Programming Information...')

    i = 1
    for channel in channel_ids:
        percent = int((float(i) / len(channel_ids)) * 100)
        message = "Loading channel " + str(i) + ' of ' + str(len(channel_ids))
        progress.update(percent, message)
        build_epg_channel(xmltv_file, channel)
        i += 1

    xmltv_file.write('</tv>\n')
    xmltv_file.close()
    progress.update(100, 'Done!')
    progress.close()


def build_epg_channel(xmltv_file, channel_id):
    json_source = get_json(EPG_URL + '/timeline/live/' + channel_id + '/watch_history_size/0/coming_up_size/20')
    for strand in json_source['body']['strands']:
        if strand['id'] == 'now_playing' or strand['id'] == 'coming_up':
            for program in strand['programs']:
                icon = ""
                for image in program['urls']:
                    if 'width' in image:
                        if image['width'] == 600 or image['width'] == 440:
                            icon = image['src']
                            break

                title = program['title']
                title = title.encode('utf-8')
                sub_title = ''
                if 'title_sub' in program:
                    sub_title = program['title_sub']
                    sub_title = sub_title.encode('utf-8')
                desc = ''
                if 'synopsis' in program:
                    desc = program['synopsis']
                    desc = desc.encode('utf-8')
                start_time = datetime.strptime(program['airing_date'], "%Y-%m-%dT%H:%M:%S.%fZ")
                start_time = start_time.strftime("%Y%m%d%H%M%S")
                stop_time = datetime.strptime(program['expiration_date'], "%Y-%m-%dT%H:%M:%S.%fZ")
                stop_time = stop_time.strftime("%Y%m%d%H%M%S")

                xmltv_file.write('<programme start="' + start_time + '" stop="' + stop_time + '" channel="' + channel_id + '">\n')
                xmltv_file.write('    <title lang="en">' + title + '</title>\n')
                xmltv_file.write('    <sub-title lang="en">' + sub_title + '</sub-title>\n')
                xmltv_file.write('    <desc lang="en">'+desc+'</desc>\n')
                for item in program['genres']:
                    genre = item['genre']
                    genre = genre.encode('utf-8')
                    xmltv_file.write('    <category lang="en">'+genre+'</category>\n')

                xmltv_file.write('    <icon src="'+icon+'"/>\n')
                xmltv_file.write('</programme>\n')


def get_json(url):
    headers = {
        'Accept': '*/*',
        'reqPayload': PS_VUE_ADDON.getSetting(id='EPGreqPayload'),
        'User-Agent': UA_ANDROID_TV,
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.5',
        'X-Requested-With': 'com.snei.vue.android',
        'Connection': 'keep-alive'
    }

    r = requests.get(url, headers=headers, cookies=load_cookies(), verify=VERIFY)

    if r.status_code != 200:
        dialog = xbmcgui.Dialog()
        msg = 'The request could not be completed.'
        try:
            json_source = r.json()
            msg = json_source['header']['error']['message']
        except:
            pass
        dialog.notification('Error '+str(r.status_code), msg, xbmcgui.NOTIFICATION_INFO, 9000)
        sys.exit()

    return r.json()


def load_cookies():
    cookie_file = os.path.join(ADDON_PATH_PROFILE, 'cookies.lwp')
    cj = cookielib.LWPCookieJar()
    try:
        cj.load(cookie_file, ignore_discard=True)
    except:
        pass

    return cj


def find(source, start_str, end_str):
    start = source.find(start_str)
    end = source.find(end_str, start + len(start_str))

    if start != -1:
        return source[start + len(start_str):end]
    else:
        return ''


def check_files():
    build_playlist()
    build_epg()

    # Reload pvr simple iptv
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":8,"params":{"addonid":"pvr.iptvsimple","enabled":false}}')
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":8,"params":{"addonid":"pvr.iptvsimple","enabled":true}}')


if __name__ == '__main__':
    monitor = xbmc.Monitor()
    last_update = datetime.now()
    check_files()
    while not monitor.abortRequested():
        # Sleep/wait for abort for 10 minutes
        if monitor.waitForAbort(600):
            if last_update < datetime.now() - timedelta(hours=3):
                check_files()
                last_update = datetime.now()

            # Abort was requested while waiting. We should exit
            break
        xbmc.log("hello addon!", level=xbmc.LOGNOTICE)

