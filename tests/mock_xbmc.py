import sys
from mock import Mock


xbmc_mock = Mock()
xbmcgui_mock = Mock()
xbmcaddon_mock = Mock()
xbmcplugin_mock = Mock()


sys.modules['xbmc'] = xbmc_mock
sys.modules['xbmcgui'] = xbmcgui_mock
sys.modules['xbmcaddon'] = xbmcaddon_mock
sys.modules['xbmcplugin'] = xbmcplugin_mock
sys.argv[1] = "123"


def reset():
    xbmc_mock.reset_mock()
    xbmcgui_mock.reset_mock()
    xbmcaddon_mock.reset_mock()
    xbmcplugin_mock.reset_mock()
