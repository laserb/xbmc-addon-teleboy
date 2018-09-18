import sys
import urllib
import xbmcgui
import xbmcplugin
from fetch_helpers import fetchApiJson
from common import PARAMETER_KEY_MODE, PARAMETER_KEY_ACTION, MODE_LIVE
from common import pluginhandle, settings
from play import play_url, THUMBNAIL_URL


PARAMETER_KEY_STATION = "station"
ACTION_PLAY = "play"

IMG_URL = "http://media.cinergy.ch"


def handle_live_view(params):
    action = params.get(PARAMETER_KEY_ACTION, "[0]")[0]
    if action == ACTION_PLAY:
        play_live(params)
    else:
        show_live()


def show_live():
    content = fetchApiJson("broadcasts/now",
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
                  PARAMETER_KEY_MODE: MODE_LIVE,
                  PARAMETER_KEY_ACTION: ACTION_PLAY}
        url = "{}?{}".format(sys.argv[0], urllib.urlencode(params))
        xbmcplugin.addDirectoryItem(handle=pluginhandle,
                                    url=url,
                                    listitem=li)
    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def get_stationLogoURL(station):
    return IMG_URL + "/t_station/" + station + "/icon320_dark.png"


def get_videoJson(sid):
    url = "stream/live/%s" % sid
    return fetchApiJson(url, {"alternative": "false"})


def play_live(params):
    station = params[PARAMETER_KEY_STATION][0]
    json = get_videoJson(station)
    if not json:
        exit(1)

    title = json["data"]["epg"]["current"]["title"]
    url = json["data"]["stream"]["url"]

    if not url:
        exit(1)

    play_url(url, title)
