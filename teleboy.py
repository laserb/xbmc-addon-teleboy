
import os
import sys
import base64
import cookielib
import urllib
import urllib2
import urlparse
from dateutil.parser import parse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import simplejson

__author__ = "Andreas Wetzel"
__copyright__ = "Copyright 2011-2015, mindmade.org"
__credits__ = ["Roman Haefeli", "Francois Marbot"]
__maintainer__ = "Andreas Wetzel"
__email__ = "xbmc@mindmade.org"

#
# constants definition
############################################
PLUGINID = "plugin.video.teleboy"

MODE_RECORDINGS = "recordings"
MODE_LIVE = "live"
MODE_PLAY = "play"
MODE_PLAY_RECORDING = "playrec"
MODE_DELETE = "delete"
PARAMETER_KEY_MODE = "mode"
PARAMETER_KEY_STATION = "station"
PARAMETER_KEY_USERID = "userid"
PARAMETER_KEY_RECID = "recid"
PARAMETER_KEY_DURATION = "duration"

TB_URL = "https://www.teleboy.ch"
IMG_URL = "http://media.cinergy.ch"
THUMBNAIL_URL = "https://media.service.teleboy.ch/media/teleboyteaser8/{}.jpg"
API_URL = "http://tv.api.teleboy.ch"
API_KEY = base64.b64decode(
        "ZjBlN2JkZmI4MjJmYTg4YzBjN2ExM2Y3NTJhN2U4ZDVjMzc1N2ExM2Y3NTdhMTNmOWMwYzdhMTNmN2RmYjgyMg==")  # noqa: E501
COOKIE_FILE = xbmc.translatePath(
    "special://home/addons/" + PLUGINID + "/resources/cookie.dat")


pluginhandle = int(sys.argv[1])
settings = xbmcaddon.Addon(id=PLUGINID)
cookies = cookielib.LWPCookieJar(COOKIE_FILE)


def ensure_login():
    global cookies
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
    urllib2.install_opener(opener)
    try:
        cookies.revert(ignore_discard=True)
        found_cookie = False
        for c in cookies:
            if c.name == "cinergy_auth" and not c.is_expired():
                found_cookie = True
                break
        if found_cookie:
            for c in cookies:
                if c.name == "cinergy_s" and not c.is_expired():
                    return True
    except IOError:
        pass
    cookies.clear()
    fetchHttp(TB_URL + "/login")

    xbmc.log("logging in...", level=xbmc.LOGNOTICE)
    login = settings.getSetting(id="login")
    password = settings.getSetting(id="password")
    url = TB_URL + "/login_check"
    args = {"login": login,
            "password": password,
            "keep_login": "1"}
    hdrs = {"Referer": TB_URL}

    reply = fetchHttp(url, args, hdrs, post=True)

    if "Falsche Eingaben" in reply \
            or "Anmeldung war nicht erfolgreich" in reply:
        xbmc.log("login failure", level=xbmc.LOGNOTICE)
        xbmc.log(reply, level=xbmc.LOGNOTICE)
        xbmc.executebuiltin("XBMC.Notification({},{})".format(
                "Login Failure!",
                "Please set your login/password in the addon settings"))
        xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=False)
        return False
    cookies.save(ignore_discard=True)

    xbmc.log("login ok", level=xbmc.LOGNOTICE)
    return True


def fetchHttpWithCookies(url, args={}, hdrs={}, post=False):
    if ensure_login():
        html = fetchHttp(url, args, hdrs, post)
        if "Bitte melde dich neu an" in html:
            os.unlink(xbmc.translatePath(COOKIE_FILE))
            if not ensure_login():
                return ""
            html = fetchHttp(url, args, hdrs, post)
        return html
    return ""


def get_stationLogoURL(station):
    return IMG_URL + "/t_station/" + station + "/icon320_dark.png"


def fetchApiJson(user_id, url, args={}):
    # get session key from cookie
    global cookies
    cookies.revert(ignore_discard=True)
    session_cookie = ""
    for c in cookies:
        if c.name == "cinergy_s":
            session_cookie = c.value
            break

    if (session_cookie == ""):
        xbmc.executebuiltin("XBMC.Notification({},{})".format(
                "Session cookie not found!",
                "Please set your login/password in the addon settings"))
        return False

    hdrs = {"x-teleboy-apikey": API_KEY,
            "x-teleboy-session": session_cookie}
    url = API_URL + "/users/%s/" % user_id + url
    ans = fetchHttpWithCookies(url, args, hdrs)
    return simplejson.loads(ans)


def get_videoJson(user_id, sid):
    url = "stream/live/%s" % sid
    return fetchApiJson(user_id, url, {"alternative": "false"})


def show_main():
    html = fetchHttpWithCookies(TB_URL + "/live")

    # extract user id
    user_id = ""
    lines = html.split('\n')
    for line in lines:
        if "setId" in line:
            dummy, uid = line.split("(")
            user_id = uid[:-1]
            xbmc.log("user id: " + user_id, level=xbmc.LOGNOTICE)
            break

    # add recordings directory
    params = {PARAMETER_KEY_MODE: MODE_RECORDINGS,
              PARAMETER_KEY_USERID: user_id}
    url = "{}?{}".format(sys.argv[0], urllib.urlencode(params))
    li = xbmcgui.ListItem("Aufnahmen")
    xbmcplugin.addDirectoryItem(handle=pluginhandle,
                                url=url,
                                listitem=li,
                                isFolder=True)

    # add live directory
    params = {PARAMETER_KEY_MODE: MODE_LIVE,
              PARAMETER_KEY_USERID: user_id}
    url = "{}?{}".format(sys.argv[0], urllib.urlencode(params))
    li = xbmcgui.ListItem("Live")
    xbmcplugin.addDirectoryItem(handle=pluginhandle,
                                url=url,
                                listitem=li,
                                isFolder=True)

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_live(user_id):
    content = fetchApiJson(user_id, "broadcasts/now",
                           {"expand": "flags,station,previewImage",
                            "stream": True})
    for item in content["data"]["items"]:
        channel = item["station"]["name"].encode('utf8')
        station_id = str(item["station"]["id"])
        title = item["title"].encode('utf8')
        tstart = item["begin"][11:16]
        tend = item["end"][11:16]
        if settings.getSetting('epg') == 'true':
            label = "[B]{}[/B][CR]{} [COLOR darkgray]({} - {})[/COLOR]" \
                    .format(channel, title, tstart, tend)
        else:
            label = channel
        img = get_stationLogoURL(station_id)
        preview = THUMBNAIL_URL.format(item['preview_image']['hash'])
        li = xbmcgui.ListItem(label, iconImage=preview, thumbnailImage=preview)
        li.setArt({'thumb': preview, 'poster': img, 'fanart': img})
        li.setProperty("Video", "true")
        params = {PARAMETER_KEY_STATION: station_id,
                  PARAMETER_KEY_MODE: MODE_PLAY,
                  PARAMETER_KEY_USERID: user_id}
        url = "{}?{}".format(sys.argv[0], urllib.urlencode(params))
        xbmcplugin.addDirectoryItem(handle=pluginhandle,
                                    url=url,
                                    listitem=li)
    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_recordings(user_id):
    content = fetchApiJson(user_id, "records/ready",
                           {"expand": "station",
                            "limit": 500,
                            "skip": 0})

    for item in content["data"]["items"]:
        station = item['station']

        # set label
        starttime = parse(item["begin"])
        endtime = parse(item['end'])
        titlestring = '[B]{}[/B]'.format(item["title"].encode('utf8'))
        if item['subtitle']:
            titlestring += ' - {}'.format(item["subtitle"].encode('utf8'))

        datestring = starttime.strftime("%d.%m.%y %H:%M")
        label = "{}[CR][COLOR darkgray]{} {}[/COLOR]".format(titlestring,
                                                             datestring,
                                                             station['name'])
        recid = str(item["id"])

        # set image
        broadcast = fetchApiJson(user_id,
                                 "broadcasts/{}".format(item["broadcast_id"]),
                                 {"expand": "previewImage"})
        broadcast = broadcast["data"]

        images = broadcast.get("teleboy_images", [])
        img = ""
        if not images:
            images = broadcast.get("images", [])
        if images:
            img = THUMBNAIL_URL.format(images[0]["hash"])

        preview = ""
        if "preview_image" in broadcast:
            preview = THUMBNAIL_URL.format(broadcast["preview_image"]["hash"])

        primary_image = ""
        if "primary_image" in broadcast:
            primary_image = THUMBNAIL_URL \
                    .format(broadcast["primary_image"]["hash"])

        if not img and not preview and not primary_image:
            img = "DefaultVideo.png"
            preview = img
        elif not img and not preview and primary_image:
            img = primary_image
            preview = primary_image
        elif not img and preview:
            img = preview
        elif img and not preview:
            preview = img

        li = xbmcgui.ListItem(label, iconImage=preview, thumbnailImage=preview)
        li.setArt({'thumb': preview, 'poster': img, 'fanart': img})
        li.setProperty("Video", "true")

        # show video information
        duration = endtime - starttime
        info = {
            'title': item['title'],
            'plot': item['info_5'],
            'plotoutline': item['info'],
            'duration': duration.total_seconds(),
            'studio': station['name'],
            'genre': item['genre'],
            'director': item.get('director'),
        }
        episode = item.get('episode', '')
        if episode:
            info['episode'] = episode
        cast = item.get('cast', '')
        anchor = item.get('anchor', '')
        if anchor:
            if cast:
                cast += ',%s' % anchor
            else:
                cast = anchor
        if cast:
            info['cast'] = cast.split(',')
        li.setInfo('video', info)

        # add refresh option
        context_menu = [('Refresh', 'Container.Refresh')]

        # add delete option
        script_path = xbmc.translatePath("special://home/addons/{}/teleboy.py"
                                         .format(PLUGINID))
        params = {PARAMETER_KEY_MODE: MODE_DELETE,
                  PARAMETER_KEY_USERID: user_id,
                  PARAMETER_KEY_RECID: recid}
        context_menu.append(('Delete', 'RunScript({}, {}, ?{})'
                             .format(script_path,
                                     pluginhandle,
                                     urllib.urlencode(params))))

        li.addContextMenuItems(context_menu)

        params = {PARAMETER_KEY_MODE: MODE_PLAY_RECORDING,
                  PARAMETER_KEY_USERID: user_id,
                  PARAMETER_KEY_RECID: recid,
                  PARAMETER_KEY_DURATION: duration.total_seconds()}
        url = "{}?{}".format(sys.argv[0], urllib.urlencode(params))
        xbmcplugin.addDirectoryItem(handle=pluginhandle,
                                    url=url,
                                    listitem=li)

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def play_url(url, title, img="", start_percent=0):
    li = xbmcgui.ListItem(title, iconImage=img, thumbnailImage=img)
    li.setProperty("IsPlayable", "true")
    li.setProperty("Video", "true")

    li.setProperty("startPercent", str(start_percent))

    xbmc.Player().play(url, li)


def fetchHttp(url, args={}, hdrs={}, post=False):
    xbmc.log("fetchHttp(%s): %s" % ("POST" if post else "GET", url),
             level=xbmc.LOGNOTICE)
    if args:
        xbmc.log("args-keys: %s" % args.keys(), level=xbmc.LOGNOTICE)
    hdrs["User-Agent"] = "Mozilla/5.0 (X11; Linux i686; rv:5.0) Gecko/20100101 Firefox/5.0"  # noqa: E501
    if post:
        req = urllib2.Request(url, urllib.urlencode(args), hdrs)
    else:
        url = url + "?" + urllib.urlencode(args)
        req = urllib2.Request(url, None, hdrs)
    response = urllib2.urlopen(req)
    text = response.read()
    responsetext = text.decode('utf8')
    response.close()

    return responsetext


def delete_record(user_id, recid):
    # get session key from cookie
    global cookies
    cookies.revert(ignore_discard=True)
    session_cookie = ""
    for c in cookies:
        if c.name == "cinergy_s":
            session_cookie = c.value
            break

    if (session_cookie == ""):
        xbmc.executebuiltin("XBMC.Notification({},{})".format(
                "Session cookie not found!",
                "Please set your login/password in the addon settings"))
        return False

    hdrs = {"x-teleboy-apikey": API_KEY,
            "x-teleboy-session": session_cookie}
    url = API_URL + "/users/%s/records/%s" % (user_id, recid)
    hdrs["User-Agent"] = "Mozilla/5.0 (X11; Linux i686; rv:5.0) Gecko/20100101 Firefox/5.0"  # noqa: E501
    req = urllib2.Request(url, None, hdrs)
    req.get_method = lambda: 'DELETE'
    urllib2.urlopen(req)


#
# xbmc entry point
############################################
params = urlparse.parse_qs(sys.argv[2][1:])
mode = params.get(PARAMETER_KEY_MODE, "[0]")[0]
user_id = params.get(PARAMETER_KEY_USERID, "[0]")[0]
recid = params.get(PARAMETER_KEY_RECID, "[0]")[0]

# depending on the mode, call the appropriate function to build the UI.
if not sys.argv[2]:
    # new start
    ok = show_main()

elif mode == MODE_DELETE:
    xbmc.log("[delete {} {}]".format(user_id, recid), level=xbmc.LOGNOTICE)
    delete_record(user_id, recid)
    xbmc.executebuiltin("Container.Refresh")

elif mode == MODE_RECORDINGS:
    show_recordings(user_id)

elif mode == MODE_LIVE:
    show_live(user_id)

elif mode == MODE_PLAY:
    station = params[PARAMETER_KEY_STATION][0]
    json = get_videoJson(user_id, station)
    if not json:
        exit(1)

    title = json["data"]["epg"]["current"]["title"]
    url = json["data"]["stream"]["url"]

    if not url:
        exit(1)
    img = get_stationLogoURL(station)

    play_url(url, title, img)

elif mode == MODE_PLAY_RECORDING:
    duration = float(params[PARAMETER_KEY_DURATION][0])
    url = "stream/record/%s" % recid
    json = fetchApiJson(user_id, url)

    title = json["data"]["record"]["title"]
    url = json["data"]["stream"]["url"]

    # set stream start to where the actual record starts
    start_offset = float(json["data"]["stream"]["offset_before"])
    end_offset = float(json["data"]["stream"]["offset_after"])
    stream_duration = start_offset + duration + end_offset
    start_percent = 100.0*start_offset/stream_duration

    play_url(url, title, start_percent=start_percent)
