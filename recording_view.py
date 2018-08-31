import sys
import os
import urllib
import urllib2
import xbmcplugin
import xbmc
import xbmcgui
import simplejson
from dateutil.parser import parse
from common import PARAMETER_KEY_MODE, \
        PARAMETER_KEY_USERID, \
        PLUGINID, API_KEY, API_URL, \
        pluginhandle
from common import cookies  # noqa: F401
from fetch_helpers import fetchApiJson
from play import play_url, THUMBNAIL_URL


RECORDINGS_FILE = xbmc.translatePath(
    "special://home/addons/" + PLUGINID + "/resources/recordings.dat")
RECORDINGS_BROADCASTS_FILE = xbmc.translatePath(
        "special://home/addons/" + PLUGINID + "/resources/recordings_broadcasts.dat")  # noqa: E501
PARAMETER_KEY_DURATION = "duration"
PARAMETER_KEY_RECID = "recid"
MODE_PLAY_RECORDING = "playrec"
MODE_DELETE = "delete"


def read_broadcasts():
    broadcasts = {}
    if os.path.exists(RECORDINGS_BROADCASTS_FILE):
        with open(RECORDINGS_BROADCASTS_FILE, 'r') as f:
            s = f.read()
            if s:
                broadcasts = simplejson.loads(s)
    return broadcasts


def show_recordings(user_id):
    updated, content = check_records_updated(user_id)

    with open(RECORDINGS_FILE, 'w') as f:
        simplejson.dump(content, f)

    if updated:
        fetch_records(user_id, content)

    broadcasts = read_broadcasts()

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
        broadcast = broadcasts[str(item["broadcast_id"])]
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
        return True, content
    return False, content


def play_recording(user_id, params):
    recid = params.get(PARAMETER_KEY_RECID, "[0]")[0]
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


def delete_record(user_id, params):
    recid = params.get(PARAMETER_KEY_RECID, "[0]")[0]
    # get session key from cookie
    global cookies
    xbmc.log("[delete {} {}]".format(user_id, recid), level=xbmc.LOGNOTICE)
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
    xbmc.executebuiltin("Container.Refresh")
