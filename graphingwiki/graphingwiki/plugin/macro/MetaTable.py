# -*- coding: utf-8 -*-"
"""
    MetaTable macro plugin to MoinMoin/Graphingwiki
     - Shows in tabular form the Metadata of desired pages

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
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
import re
import StringIO

from urllib import unquote as url_unquote
from urllib import quote as url_quote

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.parser.wiki import Parser

from graphingwiki.editing import metatable_parseargs, getmetas
from graphingwiki.editing import formatting_rules
from graphingwiki.patterns import encode

Dependencies = ['metadata']

def t_cell(macro, vals, head=0, style={}):
    out = macro.request

    if not style.has_key('class'):
        if head:
            style['class'] = 'meta_page'
        else:
            style['class'] = 'meta_cell'

    out.write(macro.formatter.table_cell(1, attrs=style))
    cellstyle = style.get('gwikistyle', '').strip('"')

    if cellstyle == 'list':
        out.write(macro.formatter.bullet_list(1))

    first_val = True
    
    for data in sorted(vals):

        # cosmetic for having a "a, b, c" kind of lists
        if cellstyle not in ['list'] and not first_val:
            out.write(macro.formatter.text(',') + \
                      macro.formatter.linebreak())

        if not isinstance(data, unicode):
            data = unicode(data, config.charset)

        if head:
            kw = {}
            if '?' in data:
                data, query = data.split('?')
                kw['querystr'] = query
            out.write(macro.formatter.pagelink(1, data, **kw))
            out.write(macro.formatter.text(data))
            out.write(macro.formatter.pagelink(0))
        elif data.strip():
            if cellstyle == 'list':
                out.write(macro.formatter.listitem(1))

            out.page.formatter = out.formatter
            parser = Parser(data, out)
            # No line anchors of any type to table cells
            out.page.formatter.in_p = 1
            parser._line_anchordef = lambda: ''

            # Using StringIO in order to strip the output
            data = StringIO.StringIO()
            out.redirect(data)
            # Produces output on a single table cell
            out.page.format(parser)
            out.redirect()

            out.write(data.getvalue().strip())

            if cellstyle == 'list':
                out.write(macro.formatter.listitem(0))

        first_val = False

    if cellstyle == 'list':
        out.write(macro.formatter.bullet_list(1))

def construct_table(macro, globaldata, pagelist, metakeys, 
                    legend='', checkAccess=True, styles={}):
    request = macro.request
    request.page.formatter = request.formatter
    _ = request.getText

    row = 0

    # Start table
    request.write(macro.formatter.linebreak() +
                  u'<div class="metatable">' +
                  macro.formatter.table(1))

    if metakeys:
        # Give a class to headers to make it customisable
        request.write(macro.formatter.table_row(1, {'rowclass':
                                                    'meta_header'}))
        # Upper left cell is empty or has the desired legend
        t_cell(macro, [legend])

    for key in metakeys:
        key = unicode(url_unquote(key), config.charset)
        style = styles.get(key, {})
        
        # Styles can modify key naming
        name = style.get('gwikiname', '').strip('"')

        # We don't want stuff like bullet lists in out header
        headerstyle = dict()
        for st in style:
            if not st.startswith('gwiki'):
                headerstyle[st] = style[st]

        if name:
            t_cell(macro, [name], style=headerstyle)
        else:
            t_cell(macro, [key], style=headerstyle)

    request.write(macro.formatter.table_row(0))

    for page in pagelist:
        row = row + 1
        metas = getmetas(request, globaldata, page,
                         metakeys, display=False,
                         checkAccess=checkAccess)

        if row % 2:
            request.write(macro.formatter.table_row(1, {'rowclass':
                                                        'metatable-odd-row'}))
        else:
            request.write(macro.formatter.table_row(1, {'rowclass':
                                                        'metatable-even-row'}))
        t_cell(macro, [url_unquote(page)], head=1)

        for key in metakeys:
            values = [x for x,y in metas[key]]
            key = unicode(url_unquote(key), config.charset)
            style = styles.get(key, {})
            t_cell(macro, values, style=style)

        request.write(macro.formatter.table_row(0))
    request.write(macro.formatter.table(0))
    request.write(u'</div>')

def execute(macro, args):
    if args is None:
        args = ''

    editlink = True

    if args.strip().endswith('noeditlink'):
        editlink = False
        args = ','.join(args.split(',')[:-1])

    # Note, metatable_parseargs deals with permissions
    globaldata, pagelist, metakeys, styles = \
                metatable_parseargs(macro.request, args,
                                    get_all_keys=True)

    request = macro.request
    _ = request.getText

    # No data -> bail out quickly, Scotty
    if not pagelist:
        request.write(macro.formatter.linebreak() +
                      u'<div class="metatable">' +
                      macro.formatter.table(1))
        t_cell(macro, ["%s (%s)" % (_("Metatable has no contents"), args)])
        request.write(macro.formatter.table(0) + 
                      u'</div>')

        globaldata.closedb()
        return ""

    # We're sure the user has the access to the page, so don't check
    construct_table(macro, globaldata, pagelist, metakeys,
                    checkAccess=False, styles=styles)

    globaldata.closedb()

    def action_link(action, linktext, args):
        req_url = request.getScriptname() + \
                  '/' + request.page.page_name + \
                  '?action=' + action + '&args=' + args 
        return '<a href="%s" id="footer">[%s]</a>\n' % \
               (request.getQualifiedURL(req_url), _(linktext))

    args = url_quote(encode(args))
    # If the user has no write access to this page, omit editlink
    if editlink:
        request.write(action_link('MetaEdit', 'edit', args))

    request.write(action_link('metaCSV', 'csv', args))

    return ""