import xbmc
import cookielib
import simplejson
import os
import urllib2
import urllib
import xbmcplugin
import base64
import requests
from common import RESOURCES_PATH
from common import settings, pluginhandle


API_URL = "https://tv.api.teleboy.ch"
API_KEY = base64.b64decode(
        "ZjBlN2JkZmI4MjJmYTg4YzBjN2ExM2Y3NTJhN2U4ZDVjMzc1N2ExM2Y3NTdhMTNmOWMwYzdhMTNmN2RmYjgyMg==")  # noqa: E501

COOKIE_FILE = RESOURCES_PATH + "cookie.dat"
USERID_FILE = RESOURCES_PATH + "userid.dat"

TB_URL = "https://www.teleboy.ch"


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

    with open(USERID_FILE, "w") as f:
        f.write(user_id)

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
    if not os.path.exists(COOKIE_FILE):
        return login()
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


def fetchApiJson(url, args={}, method="GET"):
    user_id = None
    if os.path.exists(USERID_FILE):
        with open(USERID_FILE, "r") as f:
            user_id = f.read().strip()
    if not user_id:
        user_id = get_user_id()
    url = API_URL + "/users/%s/" % user_id + url
    ans = fetchHttpWithCookies(url, args, method=method)
    return simplejson.loads(ans)
