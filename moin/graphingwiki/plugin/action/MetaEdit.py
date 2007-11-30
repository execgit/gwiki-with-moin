# -*- coding: utf-8 -*-"
"""
    MetaEdit action to MoinMoin
     - Editing pages with certain metadata keys or values

    @copyright: 2007 by Erno Kuusela and Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

action_name = 'MetaEdit'

import cgi
import urllib

from MoinMoin import wikiutil
from MoinMoin import config

from graphingwiki.editing import process_edit, getvalues
from graphingwiki.editing import metatable_parseargs

def urlquote(s):
    if isinstance(s, unicode):
        s = s.encode(config.charset)
    return urllib.quote(s)

def url_unquote(s):
    s = urllib.unquote(s)
    if not isinstance(s, unicode):
        s = unicode(s, config.charset)
    return s

def htmlquote(s):
    return cgi.escape(s, 1)

def show_queryform(request, pagename):
    _ = request.getText

    def wr(fmt, *args):
        args = tuple(map(htmlquote, args))
        request.write(fmt % args)

    wr(u'<form method="GET" action="%s">\n', urlquote(pagename))
    wr(u'<input type="hidden" name="action" value="%s">\n', action_name)
    wr(u'<input type="text" name="args">\n')

    wr(u'</table>\n')
    wr(u'<input type="submit" name="show" value="%s">\n', _("Edit table"))
    wr(u'</form>\n')

def show_editform(request, pagename, args):
    _ = request.getText
    formatter = request.formatter

    def wr(fmt, *args):
        args = tuple(map(htmlquote, args))
        request.write(fmt % args)

    formpage = '../' * pagename.count('/') + urlquote(pagename)

    wr(u'<form method="POST" action="%s">\n', formpage)
    wr(u'<input type="hidden" name="action" value="%s">\n', action_name)
    wr(formatter.table(1))
    wr(formatter.table_row(1, {'rowclass': 'meta_header'}))
    wr(formatter.table_cell(1, {'class': 'meta_page'}))

    # Note that metatable_parseargs handles permission issues
    globaldata, pagelist, metakeys = metatable_parseargs(request, args,
                                                         globaldata=None,
                                                         all_keys=True)

    for key in metakeys + ['']:
        wr(formatter.table_cell(1, {'class': 'meta_header'}))
        wr(u'<input type="text" name="%s" value="%s">',
            url_unquote(':: %s' % key), url_unquote(key))
    wr(formatter.table_row(0))

    values = dict()
    valnos = dict()
    
    for frompage in pagelist:
        values[frompage] = dict()

        for key in metakeys + ['']:
            values[frompage][key] = list()
            # If the page has no values for this key, it'll
            # have one in the table to add a value
            if not valnos.has_key(frompage):
                valnos[frompage] = 1

            for i, (val, typ) in enumerate(getvalues(request, globaldata,
                                                     frompage, key,
                                                     display=False)):
                values[frompage][key].append(val)
                # Enumerate starts from 0: #values++ 
                # One to add a value: #values++ 
                if valnos[frompage] < i + 2:
                    valnos[frompage] = i + 2

            values[frompage][key].append('')

    for frompage in pagelist:
        wr(formatter.table_row(1))
        wr(formatter.table_cell(1, {'class': 'meta_page',
                                    'rowspan': str(valnos[frompage])}))
        wr(u'%s', url_unquote(frompage))

        for i in range(valnos[frompage]):
            for key in metakeys + ['']:
                
                inputname = url_unquote(frompage) + u'!' + url_unquote(key)

                if len(values[frompage][key]) >= (i + 1):
                    val = values[frompage][key][i]
                else:
                    val = ''

                # Skip default labels
                if key == 'label' and val == url_unquote(frompage):
                    val = ''
                
                wr(formatter.table_cell(1, {'class': 'meta_cell'}))
                wr(u'<input type="text" name="%s" value="%s">',
                   url_unquote(inputname), val)

                #print frompage, key, inputname, values, '<br>'
            wr(formatter.table_row(0))

# Proto JS code to warn on leaving an empty key name
# <script language="JavaScript" type="text/javascript">
#    function myvalid(me) {
#      if (me.form.subject.value == "") {
#        if (confirm("Empty subject, send anyway?"))
#          return true;
#        else
#          return false;
#      }
#      return true;
#    }
# </script>
# <input type="submit" name="send" value="Send" class="button1"tabindex="7" onClick="return myvalid(this);" />

    wr(formatter.table(0))
    wr(u'<input type="submit" name="save" value="%s">\n', _('Save'))
    wr(u'</form>\n')

    globaldata.closedb()

def _enter_page(request, pagename):
    _ = request.getText
    
    title = _('Metatable editor')
    wikiutil.send_title(request, title,
                        pagename=pagename)
    # Start content - IMPORTANT - without content div, there is no
    # direction support!
    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    request.page.formatter = formatter

    request.write(request.page.formatter.startContent("content"))

def _exit_page(request, pagename):
    # End content
    request.write(request.page.formatter.endContent()) # end content div
    # Footer
    wikiutil.send_footer(request, pagename)

def execute(pagename, request):
    request.http_headers()
    _ = request.getText
    
    # This action generates data using the user language
    request.setContentLanguage(request.lang)

    if request.form.has_key('save'):
        msgs = process_edit(request, request.form)
        msg = ''

        for line in msgs:
            msg += line + request.formatter.linebreak(0)

        request.reset()
        request.page.send_page(request, msg=msg)
    elif request.form.has_key('args'):
        _enter_page(request, pagename)
        formatter = request.page.formatter
        
        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit metatable")))
        request.write(formatter.heading(0, 2))
        args = ', '.join(request.form['args'])
        show_editform(request, pagename, args)

        _exit_page(request, pagename)
    else:
        _enter_page(request, pagename)
        formatter = request.page.formatter

        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit current page")))
        request.write(formatter.heading(0, 2))
        show_editform(request, pagename, pagename)

        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit metatable")))
        request.write(formatter.heading(0, 2))
        show_queryform(request, pagename)

        _exit_page(request, pagename)
