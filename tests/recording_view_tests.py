import unittest
from os import path
import sys
from mock import call

import mock_xbmc  # noqa: F401
import mock_fetch_helpers  # noqa: F401

import fetch_helpers
import xbmcgui
import xbmcplugin

sys.path.append(path.dirname(path.abspath(__file__)))
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import recording_view  # noqa: E402


PARAMETER_KEY_FOLDER = "folder"


user_id = 1
recid = 10


class TestRecordingView(unittest.TestCase):

    def setUp(self):
        mock_xbmc.reset()
        mock_fetch_helpers.reset()

    def test_show_recordings(self):
        recording_view.show_recordings(user_id)
        fetch_helpers.get_records.assert_called_once_with(user_id)

        call_add_refresh = call().addContextMenuItems([('Refresh',
                                                        'Container.Refresh')])
        calls = [call('Hot oder Schrott - Die Allestester'),
                 call_add_refresh,
                 call('Genial daneben'),
                 call_add_refresh,
                 call('A2 - Abenteuer Autobahn'),
                 call_add_refresh,
                 call('Wir sind Kaiser')]

        xbmcgui.ListItem.assert_has_calls(calls)
        xbmcplugin.addDirectoryItem.assert_called()
        xbmcplugin.endOfDirectory.assert_called_once()

    def test_show_recordings_folder(self):
        params = {PARAMETER_KEY_FOLDER: ['Genial daneben']}
        recording_view.show_recordings_folder(user_id, params)
        xbmcgui.ListItem.assert_called()
        xbmcplugin.endOfDirectory.assert_called_once()

    def test_delete(self):
        recording_view.delete(user_id, recid)
        fetch_helpers.delete_record.assert_called_once_with(user_id, recid)


if __name__ == '__main__':
    unittest.main()
