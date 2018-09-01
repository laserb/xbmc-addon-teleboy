import base64
import sys
import cookielib
import xbmcaddon
import xbmc

#
# constants definition
############################################
PLUGINID = "plugin.video.teleboy"

MODE_RECORDINGS = "recordings"
MODE_LIVE = "live"
PARAMETER_KEY_MODE = "mode"
PARAMETER_KEY_ACTION = "action"
PARAMETER_KEY_USERID = "userid"

API_URL = "http://tv.api.teleboy.ch"
API_KEY = base64.b64decode(
        "ZjBlN2JkZmI4MjJmYTg4YzBjN2ExM2Y3NTJhN2U4ZDVjMzc1N2ExM2Y3NTdhMTNmOWMwYzdhMTNmN2RmYjgyMg==")  # noqa: E501

COOKIE_FILE = xbmc.translatePath(
    "special://home/addons/" + PLUGINID + "/resources/cookie.dat")

pluginhandle = int(sys.argv[1])
settings = xbmcaddon.Addon(id=PLUGINID)
cookies = cookielib.LWPCookieJar(COOKIE_FILE)
