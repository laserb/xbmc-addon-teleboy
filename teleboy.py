import sys
import urlparse
from common import PARAMETER_KEY_MODE, MODE_LIVE, MODE_RECORDINGS, settings
from recording_view import handle_recording_view
from main_view import handle_main_view
from live_view import handle_live_view

__author__ = "Raphael Freudiger"
__credits__ = ["Andreas Wetzel"]
__maintainer__ = "Raphael Freudiger"
__email__ = "laser_b@gmx.ch"


#
# xbmc entry point
############################################
params = urlparse.parse_qs(sys.argv[2][1:])
mode = params.get(PARAMETER_KEY_MODE, "[0]")[0]

# depending on the mode, call the appropriate function to build the UI.
if not sys.argv[2]:
    # new start
    if settings.getSetting('show_live') == 'true':
        handle_main_view(params)
    else:
        handle_recording_view(params)

elif mode == MODE_RECORDINGS:
    handle_recording_view(params)

elif mode == MODE_LIVE:
    handle_live_view(params)
