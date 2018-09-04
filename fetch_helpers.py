import xbmc
import cookielib
import simplejson
import os
import urllib2
import urllib
import xbmcplugin
import base64
import requests
from common import PLUGINID
from common import settings, pluginhandle


API_URL = "http://tv.api.teleboy.ch"
API_KEY = base64.b64decode(
        "ZjBlN2JkZmI4MjJmYTg4YzBjN2ExM2Y3NTJhN2U4ZDVjMzc1N2ExM2Y3NTdhMTNmOWMwYzdhMTNmN2RmYjgyMg==")  # noqa: E501

COOKIE_FILE = xbmc.translatePath(
    "special://home/addons/" + PLUGINID + "/resources/cookie.dat")

IMG_URL = "http://media.cinergy.ch"
TB_URL = "https://www.teleboy.ch"

RECORDINGS_FILE = xbmc.translatePath(
    "special://home/addons/" + PLUGINID + "/resources/recordings.dat")
RECORDINGS_BROADCASTS_FILE = xbmc.translatePath(
        "special://home/addons/" + PLUGINID + "/resources/recordings_broadcasts.dat")  # noqa: E501


cookies = cookielib.LWPCookieJar(COOKIE_FILE)
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
urllib2.install_opener(opener)


def get_user_id():
    html = fetchHttpWithCookies(TB_URL + "/live")

    # extract user id
    user_id = ""
    lines = html.split('\n')
    for line in lines:
        if "setId" in line:
            dummy, uid = line.split("(")
            user_id = uid[:-1]
            break
    xbmc.log("user id: " + user_id, level=xbmc.LOGNOTICE)
    return user_id


def login():
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

    reply = fetchHttp(url, args, hdrs, method="POST")

    if "Falsche Eingaben" in reply \
            or "Anmeldung war nicht erfolgreich" in reply \
            or "Bitte melde dich neu an" in reply:
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


def ensure_login():
    global cookies
    cookies.revert(ignore_discard=True)
    cookies_dict = requests.utils.dict_from_cookiejar(cookies)
    if "cinergy_auth" in cookies_dict and "cinergy_s" in cookies_dict:
        xbmc.log("Already logged in", level=xbmc.LOGNOTICE)
        return True
    else:
        return login()


def get_session_cookie():
    global cookies
    ensure_login()
    cookies_dict = requests.utils.dict_from_cookiejar(cookies)
    return cookies_dict["cinergy_s"]


def fetchHttp(url, args={}, hdrs={}, method="GET"):
    xbmc.log("fetchHttp(%s): %s" % (method, url),
             level=xbmc.LOGNOTICE)
    if args:
        xbmc.log("args-keys: %s" % args.keys(), level=xbmc.LOGNOTICE)
    hdrs["User-Agent"] = "Mozilla/5.0 (X11; Linux i686; rv:5.0) Gecko/20100101 Firefox/5.0"  # noqa: E501
    if method == "POST":
        req = urllib2.Request(url, urllib.urlencode(args), hdrs)
    elif method == "DELETE":
        req = urllib2.Request(url, None, hdrs)
        req.get_method = lambda: 'DELETE'
    else:
        url = url + "?" + urllib.urlencode(args)
        req = urllib2.Request(url, None, hdrs)
    response = urllib2.urlopen(req)
    text = response.read()
    responsetext = text.decode('utf8')
    response.close()

    return responsetext


def fetchHttpWithCookies(url, args={}, hdrs={}, method="GET"):
    session_cookie = get_session_cookie()

    hdrs["x-teleboy-apikey"] = API_KEY
    hdrs["x-teleboy-session"] = session_cookie
    return fetchHttp(url, args, hdrs, method)


def fetchApiJson(user_id, url, args={}, method="GET"):
    url = API_URL + "/users/%s/" % user_id + url
    ans = fetchHttpWithCookies(url, args, method)
    return simplejson.loads(ans)


def get_stationLogoURL(station):
    return IMG_URL + "/t_station/" + station + "/icon320_dark.png"


def get_videoJson(user_id, sid):
    url = "stream/live/%s" % sid
    return fetchApiJson(user_id, url, {"alternative": "false"})


def get_play_data(user_id, recid):
    url = "stream/record/%s" % recid
    return fetchApiJson(user_id, url)


def get_records(user_id):
    updated, content = check_records_updated(user_id)

    if updated:
        broadcasts = fetch_records(user_id, content)
    else:
        broadcasts = read_broadcasts()

    return broadcasts, content


def read_broadcasts():
    broadcasts = {}
    if os.path.exists(RECORDINGS_BROADCASTS_FILE):
        with open(RECORDINGS_BROADCASTS_FILE, 'r') as f:
            s = f.read()
            if s:
                broadcasts = simplejson.loads(s)
    return broadcasts


def check_records_updated(user_id):
    recordings = None
    if os.path.exists(RECORDINGS_FILE):
        with open(RECORDINGS_FILE, 'r') as f:
            s = f.read()
            if s:
                recordings = simplejson.loads(s)

    content = fetchApiJson(user_id, "records/ready",
                           {"expand": "station",
                            "limit": 500,
                            "skip": 0})

    if content != recordings:
        xbmc.log("updated", level=xbmc.LOGDEBUG)
        with open(RECORDINGS_FILE, 'w') as f:
            simplejson.dump(content, f)
        return True, content
    return False, content


def fetch_records(user_id, content):
    old_broadcasts = read_broadcasts()
    broadcasts = {}
    for item in content["data"]["items"]:
        broadcast_id = str(item["broadcast_id"])
        if broadcast_id in old_broadcasts:
            broadcast = old_broadcasts[broadcast_id]
        else:
            broadcast = fetchApiJson(user_id,
                                     "broadcasts/{}".format(broadcast_id),
                                     {"expand": "previewImage"})
        broadcasts[broadcast_id] = broadcast
    with open(RECORDINGS_BROADCASTS_FILE, 'w') as f:
        simplejson.dump(broadcasts, f)
    return broadcasts


def delete_record(user_id, recid):
    url = "records/%s" % recid
    fetchApiJson(user_id, url, method="DELETE")
