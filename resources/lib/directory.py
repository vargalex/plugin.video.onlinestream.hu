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


from kodi_six import xbmcaddon, xbmcgui, xbmcplugin, py2_encode
import json,os,sys
try:
    from urllib import quote_plus, urlencode
except:
    from urllib.parse import quote_plus, urlencode

def add(items, content=None, mediatype=None, infotype='', isFolder=True):
    if items == None or len(items) == 0: return

    sysaddon = sys.argv[0]
    syshandle = int(sys.argv[1])
    addonInfo = xbmcaddon.Addon().getAddonInfo
    sysicon = os.path.join(addonInfo('path'), 'resources', 'media')
    sysimage = addonInfo('icon')
    sysfanart = addonInfo('fanart')
    lang = xbmcaddon.Addon().getLocalizedString

    for i in items:
        #try:
            try: label = lang(i['title'])
            except: label = i['label']

            if 'image' in i and not i['image'] == '0': image = i['image']
            elif 'icon' in i and not i['icon'] == '0': image = os.path.join(sysicon, i['icon'])
            else: image = sysimage

            fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else sysfanart

            url = '%s?action=%s' % (sysaddon, i['action'])

            try: url += '&url=%s' % quote_plus(i['url'])
            except: pass
            try: url += '&title=%s' % quote_plus(i['title'])
            except: pass
            try: url += '&image=%s' % quote_plus(i['image'])
            except: pass
            try: url += '&station_id=%s' % quote_plus(i['station_id'])
            except: pass
            try: url += '&search_text=%s' % quote_plus(i['search_text'])
            except: pass

            cm = []
            menus = i['cm'] if 'cm' in i else []

            for menu in menus:
                #try:
                    try: tmenu = lang(menu['title'])
                    except: tmenu = menu['title']
                    #qmenu = urlencode(menu['query'])
                    qmenu = urlencode(dict([k, py2_encode(v)] for k,v in menu['query'].items()))
                    cm.append((tmenu, 'RunPlugin(%s?%s)' % (sysaddon, qmenu)))
                #except:
                    #pass

            meta = dict((k,v) for k, v in i.items() if not k in ['cm', 'action', 'image', 'station_id', 'label', 'search_text', 'url']  and not v == '0')
            if not mediatype == None: meta['mediatype'] = mediatype

            #meta.pop('action', None)
            #meta.pop('image', None)
            #meta.pop('station_id', None)
            #meta.pop('label', None)
            #meta.pop('search_text', None)
            #meta.pop('url', None)

            item = xbmcgui.ListItem(label=label)
            item.setArt({'icon': image, 'thumb': image})
            item.setProperty('Fanart_Image', fanart)

            item.addContextMenuItems(cm)
            item.setInfo(type=infotype, infoLabels = meta)
            xbmcplugin.addDirectoryItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
        #except:
            #pass

    #if not content == None: xbmcplugin.setContent(syshandle, content)
    xbmcplugin.endOfDirectory(syshandle, cacheToDisc=False)
