import xbmcgui
import xbmcplugin

from common import pluginhandle


THUMBNAIL_URL = "https://media.service.teleboy.ch/media/teleboyteaser8/{}.jpg"


def play_url(url, title, start_percent=0):
    li = xbmcgui.ListItem(title, path=url)
    li.setProperty("IsPlayable", "true")
    li.setProperty("Video", "true")
#    li.setProperty("startPercent", str(start_percent))

    xbmcplugin.setResolvedUrl(pluginhandle, True, li)
