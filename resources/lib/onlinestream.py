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


from kodi_six import xbmc, xbmcaddon, xbmcgui, py2_decode, py2_encode
import sys,re,os

from resources.lib import client
from resources.lib import directory
from resources.lib import favorite
from resources.lib import m3u8_parser

try:
    from urllib import quote_plus
except:
    from urllib.parse import quote_plus

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__addonicon__ = __addon__.getAddonInfo('icon')
__lang__ = __addon__.getLocalizedString
__dialog__ = xbmcgui.Dialog()
__addon__.setSetting('ver', __addon__.getAddonInfo('version'))

class indexer:
    def __init__(self, headless = False):
        self.headless = headless
        self.list = []
        self.base_link = 'https://onlinestream.live'


    def resolve(self, url, image, title, mediatype, multi_res, stream_name = None):
        #xbmc.log("Resolving '{}' ...".format(url), level=xbmc.LOGINFO)

        pattern = '(?:youtube\.com\/\S*(?:(?:\/e(?:mbed))?\/|watch\?(?:\S*?&?v\=))|youtu\.be\/)([a-zA-Z0-9_-]{6,11})'
        yt_link = re.search(pattern, url)
        if yt_link:
            url = 'plugin://plugin.video.youtube/play/?video_id=%s' % yt_link.group(1)

        result = dict()
        stream_description = []
        if stream_name is not None:
            stream_description.append(stream_name)

        if not yt_link and multi_res == True:
            r = client.request(url).text
            query = re.search("(https?.+?m3u8)", r)
            if query:
                query = query.group(1)
                try:
                    r = client.request(query).text
                    sources = m3u8_parser.parse(r)['playlists']
                    #sources = re.findall('RESOLUTION\s*=\s*(\d+x\d+).+\n\s*(.*\.m3u8)', r)
                    available_resoulutions = list([i['stream_info']['resolution'] for i in sources])
                    RE_RESOLUTION_STRING = re.compile(r'(\d+) ?x ?(\d+)')
                    if len(sources) > 1:
                        preferred_video_quality = __addon__.getSetting('preferred_video_quality')
                        q = None
                        if self.headless or preferred_video_quality == '1': # auto-pick best available
                            try:
                                sorted_resoultions = []
                                for i in range(len(available_resoulutions)):
                                    sorted_resoultions.append((int(RE_RESOLUTION_STRING.match(available_resoulutions[i]).group(1)), i))
                                sorted_resoultions.sort()
                                _, q = sorted_resoultions[-1]
                            except: pass
                        if q is None:
                            q = __dialog__.select(__lang__(32013), available_resoulutions) if not self.headless else -1
                        if q == -1: return
                    else: q = 0
                    try:
                        res_with, res_height, RE_RESOLUTION_STRING.match(available_resoulutions[i]).groups()
                        result['videoStreamInfo'] = {
                            'width': res_with,
                            'height': res_height
                        }
                    except: pass
                    url = query.rsplit('/', 1)[0] + '/' + sources[q]['uri']
                    stream_description.append(available_resoulutions[q])
                except:
                    url = query

        stream_description.append('[B]URL:[/B] {}'.format(url))

        result['url'] = url
        result['image'] = image
        result['mediatype'] = mediatype
        result['infoLabels'] = {'Title': title, 'Plot': '\n\n'.join(stream_description)}
    
        return result


    def favorites(self):
        try:
            fav_list = favorite.getFavorites()
            if fav_list == []: raise Exception()
            
            for id, title, type, image in fav_list:    
                cm = [{'title': __lang__(32009), 'query': {'action': '%s_track_list' % type, 'station_id': id}},
                    {'title': __lang__(32018), 'query': {'action': 'favorite_delete', 'station_id': id}}]
                if type == 'tv':
                    label = __lang__(32014)
                elif type =='webcam':
                    label = __lang__(32039)
                else:
                    label = __lang__(32015)
                self.list.append({'action': '%s_stream_list' % type, 'label': '%s  (%s)' % (title, label), 'image': image, 'station_id': id, 'cm': cm}) 
    
            directory.add(self.list, content='addons', isFolder=False)
        except:
            if not self.headless:
                __dialog__.notification(__addonname__, __lang__(32019), __addonicon__, 3000, sound=False)
            return


    def get_stations(self, action, station_id=None):
        stations = client.request(self.base_link + '/list.json', cache=True).json()
        if not stations:
            if not self.headless:
                __dialog__.notification(__addonname__, __lang__(32011), __addonicon__, 3000, sound=False)
            return []

        stations = stations['stations']

        if station_id:
            return [i['station'][0] for i in stations if i['station'][0]['station_id'] == station_id][0]

        if action == 'radio':
            stations = [i['station'][0] for i in stations if i['station'][0]['tv'] == i['station'][0]['webcam'] == '0']
        else:
            stations = [i['station'][0] for i in stations if i['station'][0][action] == '1']

        if action == 'tv':
            filter = []
            tv_seq = client.request(self.base_link + '/tv-seq.json', cache=True).json()
            if tv_seq:
                for i in tv_seq['stations']:
                    for x in stations:
                        if i['station_id'] == x['station_id']:
                            filter.append(x)

            filter += [i for i in stations if not i in filter]
            stations = [i for i in filter if not all('' == s['stream_url'].strip() for s in i['channel']) or not all('' == x['hls_url'].strip() for x in i['channel'])]

        return stations


    def station_list(self, action, search_text=None):
        stations = self.get_stations(action)
        fav_ids = favorite.getFavorites(id=True)

        for item in stations:
            try:
                title = item['title']

                station_id = item['station_id']

                logo = item['logo']
                if logo == None or logo.strip() == '':
                    l = action if action == 'radio' else 'tv'
                    logo = os.path.join(__addon__.getAddonInfo('path'), 'resources', 'media', '%s.png' % l)
                
                if action == 'radio':
                    description = item['description']
    
                    listeners = item['listeners']
                    listeners = listeners if listeners.isdigit() and int(listeners) >= 0 else ''
                    
                    listeners_peak = item['listeners_peak']
                    
                    broadcast = item['broadcast']
                    broadcast = 'DAB+/FM' if broadcast == '1' else ''
                    
                    station_title = '[COLOR white][B]%s[/B][/COLOR]' % title
                    if not broadcast == '': station_title += '  [COLOR FF008000]%s[/COLOR]' % broadcast
                    if not listeners == '': station_title += '  [%s/%s]' % (listeners, listeners_peak)
                else: 
                    station_title = title
                
                cm = []
                if action != 'webcam':
                    cm.append({'title': __lang__(32009), 'query': {'action': '%s_track_list' % action, 'station_id': station_id}})
                if not station_id in fav_ids:
                    cm.append({'title': __lang__(32017), 'query': {'action': 'favorite_add', 'station_id': station_id, 'title': title, 'type': action, 'image': logo}})

                self.list.append({'title': title, 'label': station_title, 'image': logo, 'station_id': station_id, 'cm': cm})

            except:
                pass
    
    
        if not search_text == None:
            self.list = [i for i in self.list if py2_decode(search_text).lower() in i['title'].lower()]
            if self.list == []:
                if not self.headless:
                    __dialog__.notification(__addonname__, __lang__(32012), __addonicon__, 3000, sound=False)
                return

        if self.list == []: return
        for i in self.list: i.update({'action': '%s_stream_list' % action})
        
        infotype = 'Music' if action == 'radio' else 'Video'
        directory.add(self.list, content='addons', infotype=infotype, isFolder=False)


    def stream_list(self, station_id, action, image='', track_list=False, exclude_indirect_streams=False):
        xbmc.log("Getting {} {} list for station_id='{}' ...".format(action, 'track' if track_list else 'stream', station_id), level=xbmc.LOGINFO)
        station = self.get_stations(action, station_id=station_id)
        result = self.stream_list_by_station(station, action, image, track_list)
        xbmc.log('RESULT: ' + str(result), level=xbmc.LOGINFO)
        if result is None:
            if not self.headless:
                __dialog__.ok(__addonname__, __lang__(32037))
            return

        if track_list == True:
            return result

        player_data = result['player_data']
        player_item = xbmcgui.ListItem()
        player_item.setPath(player_data['url'])
        if 'videoStreamInfo' in player_data:
            player_item.setStreamInfo('video', player_data['videoStreamInfo'])
        if 'image' in player_data:
            player_item.setArt({'icon': player_data['image'], 'thumb': player_data['image']})
        player_item.setInfo(type=player_data['mediatype'], infoLabels=player_data['infoLabels'])
        xbmc.Player().play(player_data['url'], player_item)
        return result

    def stream_list_by_station(self, station, action, image='', track_list=False, exclude_indirect_streams=False):
        station_title = station['title']

        for item in station['channel']:
            try:
                stream_url = item['stream_url']
                hls_url = item['hls_url']
                if stream_url.strip() == '' and hls_url.strip() == '': continue
                
                channel_id = item['channel_id']
                
                description = item['description']
                
                format = item['format']
                
                channel_title = item['title']
                
                listeners = item['listeners']
                listeners = listeners if listeners.isdigit() and int(listeners) >= 0 else '?'
                
                listeners_peak = item['listeners_peak']
                
                bitrate = item['bitrate']
                
                resolution = item['video_resolution']

                if action == 'radio':
                    mediatype = 'Music' if not format.strip().lower() in ['flv', 'hls'] else 'Video'
                    title = '%s: %s [%s/%s] [%s, %s kbps]' % (channel_id, channel_title, listeners, listeners_peak, format, bitrate)
                    title = re.sub('\[\?\/.*\]\s', '', title)
                    if re.search(',\s+\D', title):
                        title = re.sub('\s*kbps', '', title)
                    litle = title.replace('[?, ', '[').replace('[, ', '[')
                    title = re.sub(',\s*\?', '', title)
                    title = re.sub('\[\s*\??\s*\]', '', title)

                else:
                    mediatype = 'Video'
                    title = 'Stream %s - %s' % (channel_id, description) if not description == '' else 'Stream %s' % channel_id

                self.list.append({'station_title': station_title, 'title': title, 'stream_url': stream_url, 'hls_url': hls_url, 'video_resolution': resolution, 'mediatype': mediatype})
            except:
                pass

        if self.list == []: return

        if not track_list == False:
            return self.list

        def resolve(i):
            mediatype = i['mediatype']
            url = i['hls_url'] if mediatype == 'Video' and i['hls_url'].strip() != '' else i['stream_url']
            multi_res = True if u'T\xf6bbf\xe9le' in i['video_resolution'] else False
            title = i['station_title']
            i['player_data'] = self.resolve(url, image, title=title, mediatype=mediatype, multi_res=multi_res, stream_name=i['title'])
            return i

        def is_indirect_stream(s):
            return s['player_data']['url'].startswith('plugin://')

        def is_unresolved_stream(s):
            return "redirect.onlinestream.live/mkredir.m3u8" in s['player_data']['url']

        ch_list = [resolve(i) for i in self.list]
        ch_list = list([i for i in ch_list if not is_unresolved_stream(i)])
        if exclude_indirect_streams:
            ch_list = list([i for i in ch_list if not is_indirect_stream(i)])

        if len(ch_list) == 0:
            return

        if self.headless or len(self.list) == 1 or __addon__.getSetting('preferred_stream') == '1': # auto-select first available stream
            q = 0
        else:
            q = __dialog__.select(__lang__(32008), list([i['title'] for i in ch_list])) if not self.headless else -1
            if q == -1: return

        return ch_list[q]


    def track_list(self, station_id, action):
        self.list = self.stream_list(station_id, action, track_list=True)
    
        if self.list == None: return
        try:
            ch_list = [i['title'] for i in self.list]

            if len(self.list) == 1 or __addon__.getSetting('preferred_stream') == '1': # auto-select first available stream
                ch_id = 0
            else:
                ch_id = __dialog__.select(__lang__(32008), ch_list) if not self.headless else -1
                if ch_id == -1: return

            ch_title = ch_list[ch_id]

            data = client.request(self.base_link + '/tracklist-json.cgi?id={}&ch={}'.format(station_id, str(ch_id + 1))).json()

            title = data['station'][0]['title']

            tracklist = data['tracklist'][:100]
            tr = []
            for track in tracklist:
                try:
                    time = track['track']['time']
                    song = track['track']['song']
                    if (song == '' or song == '-' or song == '?'): raise Exception()
                    label = u'[B][COLOR white]%s[/COLOR][/B]  %s' % (time, song)
                    tr.append(label)
                except:
                    pass

            if tr == []:
                raise Exception()

            if not self.headless:
                __dialog__.select(title, tr)
            return
        except:
            if not self.headless:
                __dialog__.notification(ch_title, __lang__(32010), __addonicon__, 3000, sound=False)
            return


    def search(self, action):
        if self.headless: raise Exception('search is not supported in headless mode')
        xbmc.executebuiltin('Dialog.Close(busydialog)')

        t = __lang__(32004)
        k = xbmc.Keyboard('', t) ; k.doModal()
        q = k.getText() if k.isConfirmed() else None

        if (q == None or q == '' or len(q) < 2):
            return

        url = '%s?action=%s_list&search_text=%s' % (sys.argv[0], action, quote_plus(py2_encode(q)))
        xbmc.executebuiltin('Container.Update(%s)' % url)
