import xbmcgui
import xbmcplugin
import sys
import urllib
from fetch_helpers import get_user_id
from common import PARAMETER_KEY_MODE, PARAMETER_KEY_USERID, \
        MODE_LIVE, MODE_RECORDINGS
from common import pluginhandle


def handle_main_view(params):
    show_main()


def show_main():
    user_id = get_user_id()

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
