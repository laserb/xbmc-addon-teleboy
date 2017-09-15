
import os
import sys
import base64
import cookielib
import urllib
import urllib2
import HTMLParser
import re
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import simplejson
import datetime

__author__ = "Andreas Wetzel"
__copyright__ = "Copyright 2011-2015, mindmade.org"
__credits__ = ["Roman Haefeli", "Francois Marbot"]
__maintainer__ = "Andreas Wetzel"
__email__ = "xbmc@mindmade.org"

#
# constants definition
############################################
PLUGINID = "plugin.video.teleboy"

addon = xbmcaddon.Addon()
LOGFILE = os.path.join(addon.getAddonInfo('path'), "resources", "log.txt")

MODE_RECORDINGS = "recordings"
MODE_PLAY = "play"
MODE_PLAY_RECORDING = "playrec"
PARAMETER_KEY_MODE = "mode"
PARAMETER_KEY_STATION = "station"
PARAMETER_KEY_USERID = "userid"
PARAMETER_KEY_RECID = "recid"

TB_URL = "https://www.teleboy.ch"
IMG_URL = "http://media.cinergy.ch"
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

    log("logging in...")
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
        log("login failure")
        log(reply)
        notify("Login Failure!",
               "Please set your login/password in the addon settings")
        xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=False)
        return False
    cookies.save(ignore_discard=True)

    log("login ok")
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
        notify("Session cookie not found!",
               "Please set your login/password in the addon settings")
        return False

    hdrs = {"x-teleboy-apikey": API_KEY,
            "x-teleboy-session": session_cookie}
    url = API_URL + "/users/%s/" % user_id + url
    ans = fetchHttpWithCookies(url, args, hdrs)
    return simplejson.loads(ans)


def get_videoJson(user_id, sid):
    url = "stream/live/%s" % sid
    return fetchApiJson(user_id, url, {"alternative": "false"})

############
# TEMP
############


def parameters_string_to_dict(parameters):
    ''' Convert parameters encoded in a URL to a dict. '''
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = urllib.unquote(paramSplits[1])
    return paramDict


def addDirectoryItem(name, params={}, image="", total=0, isFolder=False):
    '''Add a list item to the XBMC UI.'''
    img = "DefaultVideo.png"
    if image != "":
        img = image

    name = htmldecode(name)
    li = xbmcgui.ListItem(name, iconImage=img, thumbnailImage=image)

    if not isFolder:
        li.setProperty("Video", "true")

    params_encoded = dict()
    for k in params.keys():
        params_encoded[k] = params[k].encode("utf-8")
    url = sys.argv[0] + '?' + urllib.urlencode(params_encoded)
    # xbmc.log("%s=%s" % (name,url))
    return xbmcplugin.addDirectoryItem(handle=pluginhandle,
                                       url=url,
                                       listitem=li,
                                       isFolder=isFolder,
                                       totalItems=total)
###########
# END TEMP
###########


def show_main():
    html = fetchHttpWithCookies(TB_URL + "/live")

    # extract user id
    user_id = ""
    lines = html.split('\n')
    for line in lines:
        if "setId" in line:
            dummy, uid = line.split("(")
            user_id = uid[:-1]
            log("user id: " + user_id)
            break

    addDirectoryItem("[ Recordings ]", {PARAMETER_KEY_MODE: MODE_RECORDINGS,
                                        PARAMETER_KEY_USERID: user_id},
                     isFolder=True)

    content = fetchApiJson(user_id, "broadcasts/now",
                           {"expand": "flags,station,previewImage",
                            "stream": True})
    print(repr(content))
    for item in sorted(content["data"]["items"],
                       key=lambda x: x["station"]["name"]):
        channel = item["station"]["name"]
        station_id = str(item["station"]["id"])
        title = item["title"]
        tstart = item["begin"][11:16]
        tend = item["end"][11:16]
        if settings.getSetting('epg') == 'true':
            label = channel + ": " + title + " (" + tstart + "-" + tend + ")"
        else:
            label = channel
        img = get_stationLogoURL(station_id)
        addDirectoryItem(label, {PARAMETER_KEY_STATION: station_id,
                                 PARAMETER_KEY_MODE: MODE_PLAY,
                                 PARAMETER_KEY_USERID: user_id}, img)
    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_recordings(user_id):
    content = fetchApiJson(user_id, "records/ready", {"limit": 500, "skip": 0})

    for item in content["data"]["items"]:
        starttime = item["begin"].split("+")[0][:-3].replace("T", " ")
        label = starttime + " " + item["title"]
        if "label" in item.keys():
            label = starttime + " " + item["label"] + ": " + item["title"]
        recid = str(item["id"])
        addDirectoryItem(label, {PARAMETER_KEY_MODE: MODE_PLAY_RECORDING,
                                 PARAMETER_KEY_USERID: user_id,
                                 PARAMETER_KEY_RECID: recid})

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def play_url(url, title, img=""):
    li = xbmcgui.ListItem(title, iconImage=img, thumbnailImage=img)
    li.setProperty("IsPlayable", "true")
    li.setProperty("Video", "true")

    xbmc.Player().play(url, li)

# Tools


def log(msg):
    msg = msg.encode("latin-1")
    logf = open(LOGFILE, "a")
    logf.write("%s: " % datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S"))
    logf.write(msg)
    logf.write('\n')
    logf.close()
    xbmc.log("### %s" % msg, level=xbmc.LOGNOTICE)


def notify(title, message):
    xbmc.executebuiltin("XBMC.Notification(" + title + "," + message + ")")


entitydict = {"E4": u"\xE4", "F6": u"\xF6", "FC": u"\xFC",
              "C4": u"\xE4", "D6": u"\xF6", "DC": u"\xDC",
              "2013": u"\u2013"}


def htmldecode(s):
    try:
        h = HTMLParser.HTMLParser()
        s = h.unescape(s)
        for k in entitydict.keys():
            s = s.replace("&#x" + k + ";", entitydict[k])
    except UnicodeDecodeError:
        pass

    return s


def fetchHttp(url, args={}, hdrs={}, post=False):
    log("fetchHttp(%s): %s" % ("POST" if post else "GET", url))
    if args:
        log("args-keys: %s" % args.keys())
    hdrs["User-Agent"] = "Mozilla/5.0 (X11; Linux i686; rv:5.0) Gecko/20100101 Firefox/5.0"  # noqa: E501
    if post:
        req = urllib2.Request(url, urllib.urlencode(args), hdrs)
    else:
        url = url + "?" + urllib.urlencode(args)
        req = urllib2.Request(url, None, hdrs)
    response = urllib2.urlopen(req)
    encoding = re.findall(
        "charset=([a-zA-Z0-9\-]+)", response.headers['content-type'])
    text = response.read()
    if len(encoding):
        responsetext = unicode(text, encoding[0])  # noqa: F821
    else:
        responsetext = text
    response.close()

    return responsetext


#
# xbmc entry point
############################################
params = parameters_string_to_dict(sys.argv[2])
mode = params.get(PARAMETER_KEY_MODE, "0")

# depending on the mode, call the appropriate function to build the UI.
if not sys.argv[2]:
    # new start
    ok = show_main()

elif mode == MODE_RECORDINGS:
    user_id = params[PARAMETER_KEY_USERID]
    show_recordings(user_id)

elif mode == MODE_PLAY:
    user_id = params[PARAMETER_KEY_USERID]
    station = params[PARAMETER_KEY_STATION]
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
    user_id = params[PARAMETER_KEY_USERID]
    rec_id = params[PARAMETER_KEY_RECID]

    url = "stream/record/%s" % rec_id
    json = fetchApiJson(user_id, url)

    title = json["data"]["record"]["title"]
    url = json["data"]["stream"]["url"]

    play_url(url, title)
