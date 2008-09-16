# -*- coding: utf-8 -*-"
"""
    ClarifiedTopology macro plugin to MoinMoin/Graphingwiki
     - Shows the Topology information generated by Clarified
       Analyser as an image

    @copyright: 2008 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""
import os
import cgi
import StringIO

from math import pi
from tempfile import mkstemp
from MoinMoin.action import AttachFile

from graphingwiki.editing import metatable_parseargs, getmetas
from graphingwiki.patterns import encode_page

cairo_found = True
try:
    import cairo
except ImportError:
    cairo_found = False
    pass

Dependencies = ['metadata']

def execute(macro, args):
    formatter = macro.formatter
    macro.request.page.formatter = formatter
    request = macro.request
    _ = request.getText

    if not args:
        args = encode_page(request.page.page_name)

    topology = args

    # Get all containers
    args = 'CategoryContainer, %s=/.+/' % (args)

    #request.write(args)

    # Note, metatable_parseargs deals with permissions
    pagelist, metakeys, _ = metatable_parseargs(request, args,
                                                get_all_keys=True)
    
    coords = dict()
    images = dict()
    aliases = dict()

    for page in pagelist:
        crds = [x.split(',') for x in getmetas(request, page, [topology])]

        if not crds:
            continue
        crds = [x.strip() for x in crds[0]]
        if not len(crds) == 2:
            continue

        try:
            [int(x) for x in crds]
        except ValueError:
            continue

        coords[page] = crds

        img = getmetas(request, page, ['gwikishapefile'])
        if img:
            img = img[0].split('/')[-1]
            images[page] = AttachFile.getFilename(request, page, img)

        alias = getmetas(request, page, ['tia-name'])
        if alias:
            aliases[page] = alias[0]

    allcoords = coords.values()
    max_x = max([int(x[0]) for x in allcoords])
    min_x = min([int(x[0]) for x in allcoords])
    max_y = max([int(x[1]) for x in allcoords])
    min_y = min([int(x[1]) for x in allcoords])

    surface_y = max_y - min_y
    surface_x = max_x - min_x

    # Setup Cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 surface_x, surface_y)
    # request.write(repr([surface_x, surface_y]))
    ctx = cairo.Context(surface)
    ctx.select_font_face("Times-Roman", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12)

    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.rectangle(0, 0, surface_x, surface_y)
    ctx.fill()

    for page in pagelist:
        if not coords.has_key(page):
            continue

        x, y = [int(x) for x in coords[page]]
#         request.write('<br>' + repr(getmetas(request, page, ['tia-name'])) + '<br>')
#         request.write(repr(coords[page]) + '<br>')
#         request.write(str(x-min_x) + '<br>')
#         request.write(str(y-min_y) + '<br>')

        if page in aliases:
            ctx.set_source_rgb(0, 0, 0)
            ctx.move_to(x-min_x, y-min_y)
            ctx.show_text(aliases[page])

        if not images.has_key(page):
            ctx.set_source_rgb(0, 0, 0)
            ctx.rectangle(x-min_x, y-min_y, 10, 10)
        else:
            try:
                sf_temp = cairo.ImageSurface.create_from_png(images[page])
                w = sf_temp.get_height()
                h = sf_temp.get_width()
                ctx.set_source_surface(sf_temp, x-min_x, y-min_y)
                ctx.rectangle(x-min_x, y-min_y, w, h)
            except cairo.Error:
                continue

        ctx.fill()

    s2 = surface
# Proto for scaling and rotating code
#     scale = 1
#     rotate = 1

#     if scale:
#         # For scaling
#         new_surface_y = 1000.0
#         new_surface_x = surface_x / (surface_y/new_surface_y)
#     else:
#         new_surface_y = surface_y
#         new_surface_x = surface_x

#     if rotate:
#         temp = new_surface_x
#         new_surface_x = new_surface_y
#         new_surface_y = temp
#         temp = surface_x
#         surface_x = surface_y
#         surface_y = temp
#         transl = -surface_x

#     s2 = cairo.ImageSurface(cairo.FORMAT_ARGB32,
#                                  new_surface_x, new_surface_y)

#     ctx = cairo.Context(s2)

#     if rotate:
#         ctx.rotate(90.0*pi/180.0)

#     if scale:
#         ctx.scale(new_surface_x/surface_x, new_surface_y/surface_y)

#     if rotate:
#         ctx.translate(0, -surface_x)
        
#     ctx.set_source_surface(surface, 0, 0)
#     ctx.paint()

    # Output a PNG file
    tmp_fileno, tmp_name = mkstemp()
    s2.write_to_png(tmp_name)
    s2.finish()
    
    f = file(tmp_name)
    data = f.read()
    os.close(tmp_fileno)
    os.remove(tmp_name)

    return '<img src="data:image/png,%s">' % (cgi.escape(data))
