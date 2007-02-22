# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - "pollsistersites" action

    This action fetches lists of page urls and page names from sister sites,
    so we can implement SisterWiki functionality.
    See: http://usemod.com/cgi-bin/mb.pl?SisterSitesImplementationGuide
    
    @copyright: 2007 by MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import time, urllib

from MoinMoin import caching
from MoinMoin.util import timefuncs

def execute(pagename, request):
    status = []
    for sistername, sisterurl in request.cfg.sistersites.items():
        arena = 'sisters'
        key = sistername
        cache = caching.CacheEntry(request, arena, key, scope='farm', use_pickle=True)
        if cache.exists():
            data = cache.content()
        else:
            data = {'lastmod': ''}
        uo = urllib.URLopener()
        uo.version = 'MoinMoin SisterPage list fetcher 1.0'
        lastmod = data['lastmod']
        if lastmod:
            uo.addheader('If-Modified-Since', lastmod)
        try:
            sisterpages = {}
            f = uo.open(sisterurl)
            for line in f:
                line = line.strip()
                try:
                    page_url, page_name = line.split(' ', 1)
                    sisterpages[page_name.decode('utf-8')] = page_url
                except:
                    pass # ignore invalid lines
            try:
                lastmod = f.info()["Last-Modified"]
            except:
                lastmod = timefuncs.formathttpdate(time.time())
            f.close()
            data['lastmod'] = lastmod
            data['sisterpages'] = sisterpages
            cache.update(data)
            status.append(u"Site: %s Status: Updated. Pages: %d" % (sistername, len(sisterpages)))
        except IOError, (title, code, msg, headers):
            status.append(u"Site: %s Status: Not updated." % sistername)

    request.emit_http_headers(["Content-Type: text/plain; charset=UTF-8"])
    request.write("\r\n".join(status).encode("utf-8"))
