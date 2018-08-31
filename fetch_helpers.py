import xbmc
import simplejson
import os
import urllib2
import urllib
import xbmcplugin
from common import API_KEY, API_URL, COOKIE_FILE
from common import settings, pluginhandle, cookies  # noqa: F401


IMG_URL = "http://media.cinergy.ch"
TB_URL = "https://www.teleboy.ch"


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


def get_stationLogoURL(station):
    return IMG_URL + "/t_station/" + station + "/icon320_dark.png"


def get_videoJson(user_id, sid):
    url = "stream/live/%s" % sid
    return fetchApiJson(user_id, url, {"alternative": "false"})
