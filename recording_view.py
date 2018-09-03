import sys
import urllib
import xbmcplugin
import xbmc
import xbmcgui
from dateutil.parser import parse
from common import PARAMETER_KEY_MODE, PARAMETER_KEY_ACTION, \
        PARAMETER_KEY_USERID, \
        MODE_RECORDINGS, \
        PLUGINID, \
        pluginhandle
from fetch_helpers import get_records, delete_record, get_play_data
from play import play_url, THUMBNAIL_URL


PARAMETER_KEY_DURATION = "duration"
PARAMETER_KEY_RECID = "recid"
PARAMETER_KEY_FOLDER = "folder"
ACTION_PLAY_RECORDING = "playrec"
ACTION_DELETE = "delete"
ACTION_RECORDINGS_FOLDER = "recfolder"


def handle_recording_view(params):
    user_id = params.get(PARAMETER_KEY_USERID, "[0]")[0]
    action = params.get(PARAMETER_KEY_ACTION, "[0]")[0]
    recid = params.get(PARAMETER_KEY_RECID, "[0]")[0]
    if action == ACTION_DELETE:
        delete(user_id, recid)
    elif action == ACTION_PLAY_RECORDING:
        play_recording(user_id, recid, params)
    elif action == ACTION_RECORDINGS_FOLDER:
        show_recordings_folder(user_id, params)
    else:
        show_recordings(user_id)


def show_recordings(user_id):
    broadcasts, content = get_records(user_id)

    folders = []

    for item in content["data"]["items"]:
        title = item["title"].encode('utf8')
        if title in folders:
            continue

        folders.append(title)

        params = {PARAMETER_KEY_MODE: MODE_RECORDINGS,
                  PARAMETER_KEY_ACTION: ACTION_RECORDINGS_FOLDER,
                  PARAMETER_KEY_FOLDER: title,
                  PARAMETER_KEY_USERID: user_id}
        url = "{}?{}".format(sys.argv[0], urllib.urlencode(params))
        li = xbmcgui.ListItem(title)

        # add refresh option
        context_menu = [('Refresh', 'Container.Refresh')]
        li.addContextMenuItems(context_menu)

        xbmcplugin.addDirectoryItem(handle=pluginhandle,
                                    url=url,
                                    listitem=li,
                                    isFolder=True)

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def show_recordings_folder(user_id, params):
    folder = params.get(PARAMETER_KEY_FOLDER, "[0]")[0]

    broadcasts, content = get_records(user_id)

    for item in content["data"]["items"]:
        title = item["title"].encode('utf8')
        if title != folder:
            continue
        station = item['station']

        # set label
        starttime = parse(item["begin"])
        endtime = parse(item['end'])
        titlestring = '[B]{}[/B]'.format(title)
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
        params = {PARAMETER_KEY_MODE: MODE_RECORDINGS,
                  PARAMETER_KEY_ACTION: ACTION_DELETE,
                  PARAMETER_KEY_USERID: user_id,
                  PARAMETER_KEY_RECID: recid}
        context_menu.append(('Delete', 'RunScript({}, {}, ?{})'
                             .format(script_path,
                                     pluginhandle,
                                     urllib.urlencode(params))))

        li.addContextMenuItems(context_menu)

        params = {PARAMETER_KEY_MODE: MODE_RECORDINGS,
                  PARAMETER_KEY_ACTION: ACTION_PLAY_RECORDING,
                  PARAMETER_KEY_USERID: user_id,
                  PARAMETER_KEY_RECID: recid,
                  PARAMETER_KEY_DURATION: duration.total_seconds()}
        url = "{}?{}".format(sys.argv[0], urllib.urlencode(params))
        xbmcplugin.addDirectoryItem(handle=pluginhandle,
                                    url=url,
                                    listitem=li)

    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def play_recording(user_id, recid, params):
    duration = float(params[PARAMETER_KEY_DURATION][0])

    json = get_play_data(user_id, recid)

    title = json["data"]["record"]["title"]
    url = json["data"]["stream"]["url"]

    start_offset = float(json["data"]["stream"]["offset_before"])
    end_offset = float(json["data"]["stream"]["offset_after"])

    # set stream start to where the actual record starts
    stream_duration = start_offset + duration + end_offset
    start_percent = 100.0*start_offset/stream_duration

    play_url(url, title, start_percent=start_percent)


def delete(user_id, recid):
    delete_record(user_id, recid)
    xbmc.executebuiltin("Container.Refresh")
