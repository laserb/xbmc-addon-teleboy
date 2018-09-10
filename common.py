import sys
import os
import xbmcaddon

#
# constants definition
############################################
PLUGINID = "plugin.video.teleboy"

MODE_RECORDINGS = "recordings"
MODE_LIVE = "live"
PARAMETER_KEY_MODE = "mode"
PARAMETER_KEY_ACTION = "action"
PARAMETER_KEY_USERID = "userid"

RESOURCES_PATH = "/tmp/" + PLUGINID + "/"

pluginhandle = int(sys.argv[1])
settings = xbmcaddon.Addon(id=PLUGINID)

if not os.path.exists(RESOURCES_PATH):
    os.mkdir(RESOURCES_PATH)
