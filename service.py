import os
import requests
import xbmc, xbmcplugin, xbmcgui, xbmcaddon

ADDON = xbmcaddon.Addon('plugin.video.psvue')
ADDON_PATH_PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile'))
# -----------------------------------------------------------------------------------------
# EPG Code
# Setup
#  - Build Playlist (PS Vue Addon (Settings/Build Playlist)
#  - Enable Web Server (Settings/Services/Control/Allow remote control via HTTP)
#  - Enabled PVR IPTV Simple Client (Addons/My add-ons/PVR Clients)
#  - Set M3U play Local Path (Home Folder/userdata/addon_data/plugin.video.psvue/playlist.m3u)
#  - Set IPTV Channel Logos - Channels Logos from XMLTV prefer M3U
# ------------------------------------------------------------------------------------------
def build_playlist():
    json_source = get_json(EPG_URL + '/browse/items/channels/filter/all/sort/channeltype/offset/0/size/500')

    m3u_file = open(os.path.join(ADDON_PATH_PROFILE, "playlist.m3u"),"w")
    m3u_file.write("#EXTM3U")
    m3u_file.write("\n")

    xmltv_file = open(os.path.join(ADDON_PATH_PROFILE, "epg.xml"),"w")
    xmltv_file.write('<?xml version="1.0" encoding="utf-8" ?>\n')
    xmltv_file.write("<tv>\n")
    channel_list = []
    for channel in json_source['body']['items']:
        title = channel['title']
        if channel['channel_type'] == 'linear':
            title = title.encode('utf-8')
            channel_id = str(channel['id'])
            channel_list.append(channel_id)
            logo = None
            for image in channel['urls']:
                if 'width' in image:
                    xbmc.log(str(image['width']))
                    if image['width'] == 600 or image['width'] == 440:
                        logo = image['src']
                        logo = logo.encode('utf-8')
                        break

            url = 'http://localhost:8080/jsonrpc?request='
            url += urllib.quote('{"jsonrpc":"2.0","method":"Addons.ExecuteAddon","params":{"addonid":"plugin.video.psvue","params":{"mode":"902","url":"' + CHANNEL_URL + '/' + channel_id + '"}},"id": 1}')

            m3u_file.write("\n")
            channel_info = '#EXTINF:-1 tvg-id="'+channel_id+'" tvg-name="' + title + '"'
            if logo is not None: channel_info += ' tvg-logo="'+logo+'"'
            channel_info += ' group_title="PS Vue",' + title
            m3u_file.write(channel_info+"\n")
            m3u_file.write(url+"\n")

            xmltv_file.write('<channel id="'+channel_id+'">\n')
            xmltv_file.write('    <display-name lang="en">'+title+'</display-name>\n')
            xmltv_file.write('</channel>\n')

    for channel_id in channel_list:
        build_epg(channel_id, xmltv_file)

    xmltv_file.write('</tv>\n')
    m3u_file.close()
    xmltv_file.close()

    dialog = xbmcgui.Dialog()
    msg = 'EPG Done Building'
    dialog.notification('EPG Finished', msg, xbmcgui.NOTIFICATION_INFO, 3000)


def build_epg(channel_id, xmltv_file):
    """
    <?xml version="1.0" encoding="utf-8" ?>
    <tv>
      <channel id="id1">
          <display-name lang="en">Channel 1</display-name>
      </channel>
      <channel id="id2">
          <display-name lang="en">Channel 2</display-name>
      </channel>
    ...
      <programme start="20130215080000 +0100" stop="20130215081500 +0100" channel="id1">
          <title lang="en">News</title>
      </programme>
      <programme start="20130215080500 +0100" stop="20130215083500 +0100" channel="id2">
          <title lang="en">Movie</title>
      </programme>

       <programme start="20080715023000 -0600" stop="20080715040000 -0600" channel="I10436.labs.zap2it.com">
            <title lang="en">Mystery!</title>
            <sub-title lang="en">Foyle's War, Series IV: Casualties of War</sub-title>
            <desc lang="en">The murder of a prominent scientist may have been due to a gambling debt.</desc>
            <date>20070708</date>
            <category lang="en">Anthology</category>
            <category lang="en">Mystery</category>
            <category lang="en">Series</category>
            <episode-num system="dd_progid">EP00003026.0666</episode-num>
            <episode-num system="onscreen">2706</episode-num>
            <audio>
              <stereo>stereo</stereo>
            </audio>
            <previously-shown start="20070708000000" />
            <subtitles type="teletext" />
        </programme>
    ...
    </tv>
    title = "test " + channel_id
    xmltv_file.write('<programme start="20170315160000 -0500" stop="20190315170000 -0500" channel="' + channel_id + '">\n')
    xmltv_file.write('    <title lang="en">' + title + '</title>\n')
    xmltv_file.write('</programme>\n')
    """
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
                start_time = string_to_date(program['airing_date'], "%Y-%m-%dT%H:%M:%S.%fZ")
                start_time = start_time.strftime("%Y%m%d%H%M%S")
                stop_time = string_to_date(program['expiration_date'], "%Y-%m-%dT%H:%M:%S.%fZ")
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
        'reqPayload': ADDON.getSetting(id='EPGreqPayload'),
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

def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]


try:
    params=get_params()
except:
    pass

url=None
try: url=urllib.unquote_plus(params["url"])
except: pass

if url is not None:
    epg_play_stream(url)
