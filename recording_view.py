import os
import sys
import urllib
import xbmcplugin
import xbmc
import xbmcgui
import simplejson
from dateutil.parser import parse
from common import PARAMETER_KEY_MODE, PARAMETER_KEY_ACTION, \
        MODE_RECORDINGS, \
        PLUGINID, \
        pluginhandle
from fetch_helpers import fetchApiJson
from play import play_url, THUMBNAIL_URL


PARAMETER_KEY_DURATION = "duration"
PARAMETER_KEY_RECID = "recid"
PARAMETER_KEY_FOLDER = "folder"
ACTION_PLAY_RECORDING = "playrec"
ACTION_DELETE = "delete"
ACTION_RECORDINGS_FOLDER = "recfolder"

RECORDINGS_FILE = xbmc.translatePath(
    "special://home/addons/" + PLUGINID + "/resources/recordings.dat")
RECORDINGS_BROADCASTS_FILE = xbmc.translatePath(
        "special://home/addons/" + PLUGINID + "/resources/recordings_broadcasts.dat")  # noqa: E501


def handle_recording_view(params):
    action = params.get(PARAMETER_KEY_ACTION, "[0]")[0]
    recid = params.get(PARAMETER_KEY_RECID, "[0]")[0]
    if action == ACTION_DELETE:
        delete(recid)
    elif action == ACTION_PLAY_RECORDING:
        play_recording(recid, params)
    elif action == ACTION_RECORDINGS_FOLDER:
        show_recordings_folder(params)
    else:
        show_recordings()


def add_refresh_option(context_menu):
    # add refresh option
    context_menu.append(('Refresh', 'Container.Refresh'))
    return context_menu


def add_delete_option(recid, context_menu):
    # add delete option
    script_path = xbmc.translatePath("special://home/addons/{}/teleboy.py"
                                     .format(PLUGINID))
    params = {PARAMETER_KEY_MODE: MODE_RECORDINGS,
              PARAMETER_KEY_ACTION: ACTION_DELETE,
              PARAMETER_KEY_RECID: recid}
    context_menu.append(('Delete', 'RunScript({}, {}, ?{})'
                         .format(script_path,
                                 pluginhandle,
                                 urllib.urlencode(params))))
    return context_menu


def show_recordings():
    broadcasts, content = get_records()

    titles = [item["title"] for item in content["data"]["items"]]
    # create unique list of titles
    titles = sorted(list(set(titles)))
    titles = [title.encode("utf8") for title in titles]

    for title in titles:
        params = {PARAMETER_KEY_MODE: MODE_RECORDINGS,
                  PARAMETER_KEY_ACTION: ACTION_RECORDINGS_FOLDER,
                  PARAMETER_KEY_FOLDER: title}
        url = "{}?{}".format(sys.argv[0], urllib.urlencode(params))
        li = xbmcgui.ListItem(title)

        context_menu = add_refresh_option([])
        li.addContextMenuItems(context_menu)

        xbmcplugin.addDirectoryItem(handle=pluginhandle,
                                    url=url,
                                    listitem=li,
                                    isFolder=True)

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def get_image(broadcasts, broadcast_id):
    def get_image_url(image):
        if not image:
            return ""
        return THUMBNAIL_URL.format(image)

    broadcast = broadcasts[broadcast_id]["data"]

    teleboy_images = broadcast.get("teleboy_images", [])
    images = teleboy_images or broadcast.get("images", []) or [{}]

    image = get_image_url(images[0].get("hash"))

    preview = get_image_url(broadcast.get("preview_image", {}).get("hash"))
    primary_image = broadcast.get("primary_image", {}).get("hash")
    primary_image = get_image_url(primary_image)

    preview = preview or image or primary_image or "DefaultVideo.png"
    image = image or preview or primary_image or "DefaultVideo.png"
    return preview, image


def show_recordings_folder(params):
    folder = params.get(PARAMETER_KEY_FOLDER, "[0]")[0]

    broadcasts, content = get_records()
    items = content["data"]["items"]

    # filter items for current folder
    items = [item for item in items if item["title"].encode("utf8") == folder]

    for item in items:
        # get ids
        recid = str(item["id"])
        broadcast_id = str(item["broadcast_id"])

        # get title
        title = item["title"].encode("utf8")
        subtitle = item.get("subtitle", "").encode("utf8")

        station = item["station"]["name"]

        # get times
        starttime = parse(item["begin"])
        endtime = parse(item['end'])
        duration = (endtime - starttime).total_seconds()

        # get cast
        cast = item.get('cast', '').split(',')
        cast += item.get('anchor', '').split(',')

        # set label
        titlestring = '[B]{}[/B]'.format(title)
        if subtitle:
            titlestring += ' - {}'.format(subtitle)

        datestring = starttime.strftime("%d.%m.%y %H:%M")
        label = "{}[CR][COLOR darkgray]{} {}[/COLOR]".format(titlestring,
                                                             datestring,
                                                             station)

        # set image
        preview, image = get_image(broadcasts, broadcast_id)

        # video info
        info = {
            'title': title,
            'plot': item['info_5'],
            'plotoutline': item['info'],
            'duration': duration,
            'studio': station,
            'genre': item['genre'],
            'director': item.get('director', ''),
            'episode': item.get('episode', ''),
            'cast': cast
        }

        li = xbmcgui.ListItem(label, iconImage=preview, thumbnailImage=preview)
        li.setArt({'thumb': preview, 'poster': image, 'fanart': image})
        li.setProperty("Video", "true")

        # show video information
        li.setInfo('video', info)

        # add refresh option
        context_menu = add_refresh_option([])
        context_menu = add_delete_option(recid, context_menu)
        li.addContextMenuItems(context_menu)

        params = {PARAMETER_KEY_MODE: MODE_RECORDINGS,
                  PARAMETER_KEY_ACTION: ACTION_PLAY_RECORDING,
                  PARAMETER_KEY_RECID: recid,
                  PARAMETER_KEY_DURATION: duration}
        url = "{}?{}".format(sys.argv[0], urllib.urlencode(params))
        xbmcplugin.addDirectoryItem(handle=pluginhandle,
                                    url=url,
                                    listitem=li)

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def get_play_data(recid):
    url = "stream/record/%s" % recid
    return fetchApiJson(url)


def play_recording(recid, params):
    duration = float(params[PARAMETER_KEY_DURATION][0])

    json = get_play_data(recid)

    title = json["data"]["record"]["title"]
    url = json["data"]["stream"]["url"]

    start_offset = float(json["data"]["stream"]["offset_before"])
    end_offset = float(json["data"]["stream"]["offset_after"])

    # set stream start to where the actual record starts
    stream_duration = start_offset + duration + end_offset
    start_percent = 100.0*start_offset/stream_duration

    play_url(url, title, start_percent=start_percent)


def get_records():
    updated, content = check_records_updated()

    if updated:
        broadcasts = fetch_records(content)
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


def check_records_updated():
    recordings = None
    if os.path.exists(RECORDINGS_FILE):
        with open(RECORDINGS_FILE, 'r') as f:
            s = f.read()
            if s:
                recordings = simplejson.loads(s)

    content = fetchApiJson("records/ready",
                           {"expand": "station",
                            "limit": 500,
                            "skip": 0})

    if content != recordings:
        xbmc.log("updated", level=xbmc.LOGDEBUG)
        with open(RECORDINGS_FILE, 'w') as f:
            simplejson.dump(content, f)
        return True, content
    return False, content


def fetch_records(content):
    old_broadcasts = read_broadcasts()
    broadcasts = {}
    for item in content["data"]["items"]:
        broadcast_id = str(item["broadcast_id"])
        if broadcast_id in old_broadcasts:
            broadcast = old_broadcasts[broadcast_id]
        else:
            broadcast = fetchApiJson("broadcasts/{}".format(broadcast_id),
                                     {"expand": "previewImage"})
        broadcasts[broadcast_id] = broadcast
    with open(RECORDINGS_BROADCASTS_FILE, 'w') as f:
        simplejson.dump(broadcasts, f)
    return broadcasts


def delete(recid):
    delete_record(recid)
    xbmc.executebuiltin("Container.Refresh")


def delete_record(recid):
    url = "records/%s" % recid
    fetchApiJson(url, method="DELETE")
