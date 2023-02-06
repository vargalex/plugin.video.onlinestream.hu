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


from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs, py2_decode
import os

try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

try:
    transPath = xbmcvfs.translatePath
except:
    transPath = xbmc.translatePath

addonInfo = xbmcaddon.Addon().getAddonInfo
dataPath = transPath(addonInfo('profile'))
favoritesFile = os.path.join(dataPath, 'fav.db')
dialog = xbmcgui.Dialog()
lang = xbmcaddon.Addon().getLocalizedString

def getFavorites(id=False):
    try:
        dbcon = database.connect(favoritesFile)
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM favorite")
        items = dbcur.fetchall()
        if not id == False:
            items = [i[0] for i in items]
    except:
        items = []

    return items


def addFavorite(id, name, type, image):   
    xbmcvfs.mkdir(dataPath)
    dbcon = database.connect(favoritesFile)
    dbcur = dbcon.cursor()
    dbcur.execute("CREATE TABLE IF NOT EXISTS favorite (""id TEXT, ""name TEXT, ""type TEXT, ""image TEXT, ""UNIQUE(id)"");")
    dbcur.execute("DELETE FROM favorite WHERE id = '%s'" %  id)
    dbcur.execute("INSERT INTO favorite Values (?, ?, ?, ?)", (id, py2_decode(name), type, image))
    dbcon.commit()

    dialog.notification(name, lang(32020), image, 3000, sound=False)


def deleteFavorite(id):
    try:
        try:
            dbcon = database.connect(favoritesFile)
            dbcur = dbcon.cursor()
            dbcur.execute("DELETE FROM favorite WHERE id = '%s'" % id)
            dbcon.commit()
        except:
            pass

        xbmc.executebuiltin('Container.Refresh')
    except:
        return


def clear():
    try:
        dbcon = database.connect(favoritesFile)
        dbcur = dbcon.cursor()
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        dbcur.execute("DROP TABLE IF EXISTS favorite")
        dbcur.execute("VACUUM")
        dbcon.commit()
    except:
        pass