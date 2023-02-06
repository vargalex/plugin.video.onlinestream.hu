# -*- coding: utf-8 -*-

'''
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


from kodi_six import xbmc, xbmcaddon, xbmcvfs
import os
import requests
import requests_cache

try:
    transPath = xbmcvfs.translatePath
except:
    transPath = xbmc.translatePath

addon = xbmcaddon.Addon()
addonVersion = addon.getAddonInfo('version')
addonUserDataFolder = transPath(addon.getAddonInfo('profile'))
CACHE_FILE = os.path.join(addonUserDataFolder, 'requests_cache')

customHeaders = {'User-Agent': 'Online Stream for Kodi/%s' % addonVersion}

def request(url, cache=False):

    requests_cache.install_cache(CACHE_FILE, backend='sqlite', expire_after=3600)

    if url == 'clear_cache':
        requests_cache.clear()
        return

    if cache == False:
        with requests_cache.disabled():
            return requests.get(url, headers=customHeaders)
    else:
        return requests.get(url, headers=customHeaders)
