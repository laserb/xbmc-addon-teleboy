import sys
import urllib
import xbmcgui
import xbmcplugin
from fetch_helpers import fetchApiJson, get_stationLogoURL, get_videoJson
from common import PARAMETER_KEY_MODE, PARAMETER_KEY_USERID
from common import pluginhandle, settings
from play import play_url, THUMBNAIL_URL


PARAMETER_KEY_STATION = "station"
MODE_PLAY = "play"


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


def play_live(user_id, params):
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
