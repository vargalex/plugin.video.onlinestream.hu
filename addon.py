# -*- coding: utf-8 -*-

'''
    Online Stream Addon for Kodi
    Copyright (C) 2017 aky01
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import sys,json
from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcplugin, PY2
from resources.lib import onlinestream
from resources.lib import directory
from resources.lib import iptv

try:
    from urlparse import parse_qsl
except:
    from urllib.parse import parse_qsl

xbmc.log(json.dumps(sys.argv), level=xbmc.LOGINFO)

__lang__ = xbmcaddon.Addon().getLocalizedString
__addonname__ = xbmcaddon.Addon().getAddonInfo('name')

params = dict(parse_qsl(sys.argv[2].replace('?','')))
if sys.argv[0].endswith('/iptv/channels'):
    iptv.channels(int(params.get('port')))
    sys.exit(0)

elif sys.argv[0].endswith('/iptv/epg'):
    iptv.epg(int(params.get('port')))
    sys.exit(0)

indexer = onlinestream.indexer()

action = params.get('action')

try: n_action = action.split('_')[0]
except: n_action = ''

channels = params.get('channels')

title = params.get('title')

image = params.get('image')

station_id = params.get('station_id')

search_text = params.get('search_text')

type = params.get('type')


def root():        
    root_list = [ 
    {
    'title': 32001,
    'action': 'tv_list',
    'icon': 'tv.png'
    },
    {
    'title': 32002,
    'action': 'radio_list',
    'icon': 'radio.png'
    },
    {
    'title': 32038,
    'action': 'webcam_list',
    'icon': 'tv.png'
    },
    {
    'title': 32016,
    'action': 'get_favorites',
    'icon': 'fav.png'
    },        
    {
    'title': 32004,
    'action': 'search',
    'icon': 'search.png'
    }
    ]

    directory.add(root_list, content='addons')


if action == None:
    root()

elif action in ['tv_list', 'radio_list', 'webcam_list']:
    indexer.station_list(n_action, search_text=search_text)

elif action in ['tv_stream_list', 'radio_stream_list', 'webcam_stream_list']:
    indexer.stream_list(station_id, n_action, image=image)

elif action == 'tv_track_list' or action == 'radio_track_list':
    indexer.track_list(station_id, n_action)

elif action == 'favorite_add':
    from resources.lib import favorite
    favorite.addFavorite(station_id, title, type, image)

elif action == 'favorite_delete':
    from resources.lib import favorite
    favorite.deleteFavorite(station_id)

elif action == 'get_favorites':
    indexer.favorites()

elif action == 'tv_search' or action == 'radio_search':
    indexer.search(n_action)

elif action == 'search':
    lst = [
    {
    'title': 32014,
    'action': 'tv_search',
    'icon': 'search.png'
    },
    {
    'title': 32015,
    'action': 'radio_search',
    'icon': 'search.png'
    }
    ]

    directory.add(lst, isFolder=False)
    
elif action == 'clearCache':
    yes = xbmcgui.Dialog().yesno(__lang__(32023), '', '')
    if yes:
        from resources.lib import client
        client.request('clear_cache')
        xbmcgui.Dialog().notification(__addonname__, __lang__(32024), xbmcgui.NOTIFICATION_INFO, sound=False)

elif action == 'clearFav':
    yes = xbmcgui.Dialog().yesno(__lang__(32023), '', '')
    if yes:
        from resources.lib import favorite
        favorite.clear()
        xbmcgui.Dialog().notification(__addonname__, __lang__(32024), xbmcgui.NOTIFICATION_INFO, sound=False)
