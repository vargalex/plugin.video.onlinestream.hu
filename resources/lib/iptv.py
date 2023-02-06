# -*- coding: utf-8 -*-

'''
    IPTV manager integration for Online Stream Addon

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

from kodi_six import xbmc, xbmcaddon
import json
import socket
import unicodedata
import os
import io
import xml.sax
import functools
import sys

from resources.lib import client
from resources.lib import onlinestream

if sys.version_info[0] >= 3:
    unicode = str

__addon__ = xbmcaddon.Addon()
__lang__ = __addon__.getLocalizedString
__addonid__ = __addon__.getAddonInfo('id')
__addonpath__ = __addon__.getAddonInfo('path')


def channels(response_port):
    xbmc.log("Assembling channels list...", level=xbmc.LOGINFO)
    IPTVManager(response_port).send_channels()
    xbmc.log("Done with channels list.", level=xbmc.LOGINFO)


def epg(response_port):
    xbmc.log("Assembling EPG...", level=xbmc.LOGINFO)
    IPTVManager(response_port).send_epg()
    xbmc.log("Done with EPG.", level=xbmc.LOGINFO)


def remove_accents(input_str):
    nkfd_form = unicodedata.normalize('NFKD', unicode(input_str))
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])


def get_unique_station_id(station):
    id = station['station_id']
    name = station['title']
    return remove_accents(u'{}-{}'.format(id, name)).lower().replace(' ', '')


class IPTVManager:
    """Interface to IPTV Manager"""

    def __init__(self, port):
        """Initialize IPTV Manager object"""
        self.port = port

    def via_socket(func):
        """Send the output of the wrapped function to socket"""

        def send(self):
            """Decorator to send over a socket"""
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', self.port))
            try:
                sock.sendall(json.dumps(func(self)).encode('utf-8'))
            finally:
                sock.close()

        return send

    @via_socket
    def send_channels(self):
        """Return JSON-STREAMS formatted information to IPTV Manager"""
        def resolve(item):
            if xbmcaddon.Addon().getSetting('iptv.autoselect_stream') == 'true':
                result = onlinestream.indexer(headless=True).stream_list_by_station(item, 'tv', exclude_indirect_streams=True)
                return result['player_data']['url'] if result is not None else None

            return 'plugin://{addon_id}?action=tv_stream_list&station_id={station_id}&title={title}&image={logo}'.format(
                addon_id=__addonid__,
                station_id=item['station_id'],
                title=item['title'],
                logo=item.get('logo', u'').strip() if item['logo'] not in [None, u'', ''] else os.path.join(__addonpath__, 'resources', 'media', 'tv.png')
            )

        streams = list([
            {
                'name': item['title'],
                'stream': resolve(item),
                'radio': False,
                'id': get_unique_station_id(item),
                'logo': item.get('logo', u'').strip() if item['logo'] not in [None, u'', ''] else os.path.join(__addonpath__, 'resources', 'media', 'tv.png')
            } for item in onlinestream.indexer(headless=True).get_stations('tv')
        ])
        streams = list([ s for s in streams if s['stream'] is not None ])
        return dict(version=1, streams=streams)

    @via_socket
    def send_epg(self):
        """Return JSON-EPG formatted information to IPTV Manager"""

        class EpgContentParser(xml.sax.ContentHandler):
            def __init__(self):
                self.stack = list()
                self.channels = dict()
                self.current_channel_id = None

            def startElement(self, tag, attributes):
                self.stack.append(tag.lower())
                if self.stack == [ 'tv', 'channel' ]:
                    self.current_channel_id = attributes['id']
                    self.channels[self.current_channel_id] = { 'names': [self.current_channel_id], 'programmes': list() }
                elif self.stack == [ 'tv', 'programme' ]:
                    self.current_channel_id = attributes['channel']
                    self.channels[self.current_channel_id] = self.channels.get(self.current_channel_id, { 'names': [self.current_channel_id], 'programmes': list() })
                    self.channels[self.current_channel_id]['programmes'].append(dict(attributes)) # copy

            def endElement(self, tag):
                assert self.stack[-1] == tag.lower()
                if self.stack == [ 'tv', 'channel' ] or self.stack == [ 'tv', 'programme' ]:
                    self.current_channel_id = None
                self.stack = self.stack[:-1]

            def characters(self, content):
                def save_attribute(attribute):
                    self.channels[self.current_channel_id]['programmes'][-1][attribute] = self.channels[self.current_channel_id]['programmes'][-1].get(attribute, content)

                if self.stack == [ 'tv', 'channel', 'display-name' ]:
                    self.channels[self.current_channel_id]['names'].append(content)
                elif self.stack == [ 'tv', 'programme', 'title' ]:
                    save_attribute('title')
                elif self.stack == [ 'tv', 'programme', 'desc' ]:
                    save_attribute('description')
                elif self.stack == [ 'tv', 'programme', 'sub-title' ]:
                    save_attribute('subtitle')
                elif self.stack == [ 'tv', 'programme', 'date' ]:
                    save_attribute('date')
                elif self.stack == [ 'tv', 'programme', 'category' ]:
                    save_attribute('genre')

            def generate_result(self, stations):
                result = dict()
                xmltv_id_blacklist = set()
                flat_channels = functools.reduce(lambda acc, xmltv_id: acc + [(xmltv_id, x_chname) for x_chname in self.channels[xmltv_id]['names']], self.channels, list())
                sorted_flat_channels = sorted(flat_channels, key=lambda x: len(x[1]))
                xbmc.log(json.dumps(sorted_flat_channels, indent=2), level=xbmc.LOGINFO)
                for item in sorted(stations, key=lambda x: len(x['title'])):
                    id = get_unique_station_id(item)
                    name = item['title']
                    xmltv_id = self.find_channel_by_name(name, sorted_flat_channels, xmltv_id_blacklist)
                    if xmltv_id is not None:
                        #xbmc.log("Station '{}' is mapped to xmltv_id '{}'".format(name, xmltv_id), level=xbmc.LOGINFO)
                        result[id] = self.channels[xmltv_id]['programmes']
                        xmltv_id_blacklist.update([xmltv_id])
                    #else:
                        #xbmc.log("Station '{}' has no mapping xmltv_id".format(name, xmltv_id), level=xbmc.LOGINFO)
                return result

            def find_channel_by_name(self, name, sorted_flat_channels, xmltv_id_blacklist):
                def clean(input_str):
                    return remove_accents(input_str).lower().replace(' HD', '')
                lname = clean(name)
                for xmltv_id, epgname in sorted_flat_channels:
                    if xmltv_id in xmltv_id_blacklist: continue
                    lepgname = clean(epgname)
                    if lname.replace(' ', '') == lepgname.replace(' ', ''): return xmltv_id
                    if lname.startswith(lepgname + ' '): return xmltv_id
                    if lname.endswith(' ' + lepgname): return xmltv_id
                    if lepgname.startswith(lname + ' '): return xmltv_id
                    if lepgname.endswith(' ' + lname): return xmltv_id

                return None

        epgurl = xbmcaddon.Addon().getSetting('iptv.epg_source')

        if epgurl in ['', u'', None, False]:
            xbmc.log("EPG URL is not specified. Returning empty EPG...", level=xbmc.LOGINFO)
            return dict(version=1, epg=dict())

        xbmc.log("Fetching stations from '{}' ...".format(epgurl), level=xbmc.LOGINFO)
        stations = onlinestream.indexer(headless=True).get_stations('tv')

        xbmc.log("Fetching XMLTV-EPG...", level=xbmc.LOGINFO)
        epg = client.request(epgurl).text
        if epg is None:
            xbmc.log("Failed to fetch XMLTV-EPG.", level=xbmc.LOGINFO)
            return dict(version=1, epg=dict())
        guide = io.BytesIO(epg.encode('utf-8'))

        xbmc.log("Parsing XMLTV-EPG...", level=xbmc.LOGINFO)
        parser = xml.sax.make_parser()
        epgContentParser = EpgContentParser()
        parser.setContentHandler(epgContentParser)
        parser.parse(guide)

        xbmc.log("Serializing JSON-EPG...", level=xbmc.LOGINFO)
        return dict(version=1, epg=epgContentParser.generate_result(stations))
