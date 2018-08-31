import sys
import urlparse
from common import PARAMETER_KEY_MODE, PARAMETER_KEY_USERID, \
        MODE_LIVE, MODE_RECORDINGS
from recording_view import show_recordings, delete_record, play_recording, \
        MODE_PLAY_RECORDING, MODE_DELETE
from main_view import show_main
from live_view import show_live, play_live, MODE_PLAY

__author__ = "Raphael Freudiger"
__credits__ = ["Andreas Wetzel"]
__maintainer__ = "Raphael Freudiger"
__email__ = "laser_b@gmx.ch"


#
# xbmc entry point
############################################
params = urlparse.parse_qs(sys.argv[2][1:])
mode = params.get(PARAMETER_KEY_MODE, "[0]")[0]
user_id = params.get(PARAMETER_KEY_USERID, "[0]")[0]

# depending on the mode, call the appropriate function to build the UI.
if not sys.argv[2]:
    # new start
    ok = show_main()

elif mode == MODE_DELETE:
    delete_record(user_id, params)

elif mode == MODE_RECORDINGS:
    show_recordings(user_id)

elif mode == MODE_LIVE:
    show_live(user_id)

elif mode == MODE_PLAY:
    play_live(user_id, params)

elif mode == MODE_PLAY_RECORDING:
    play_recording(user_id, params)
