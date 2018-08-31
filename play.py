import xbmcgui
import xbmc


THUMBNAIL_URL = "https://media.service.teleboy.ch/media/teleboyteaser8/{}.jpg"


def play_url(url, title, img="", start_percent=0):
    li = xbmcgui.ListItem(title, iconImage=img, thumbnailImage=img)
    li.setProperty("IsPlayable", "true")
    li.setProperty("Video", "true")

    li.setProperty("startPercent", str(start_percent))

    xbmc.Player().play(url, li)
