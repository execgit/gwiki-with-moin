# -*- coding: utf-8 -*-"
"""
    IOCList macro plugin to MoinMoin/Graphingwiki
     - Make a wiki page with metas on indicators of compromise
     - Currently supports IPv4 and IPv6 addresses, domains, 
       urls and email addresses

    @copyright: 2013 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

def execute(macro, args):
    f = macro.formatter
    macro.request.page.formatter = f
    request = macro.request
    _ = request.getText

    allow_overlap = 'no'
    template = 'IOCListTemplate'

    if args:
        args = [x.strip() for x in args.split(',')]
        if len(args) == 2:
            template, overlap = args
            if overlap in ['no', 'yes']:
                allow_overlap = overlap 
        elif len(args) == 1:
            template = args[0]

    html = [
        u'<form class="macro" method="POST" action="%s">' % \
            (request.href(f.page.page_name)),
        u'<div class="ioclist">',
        u'<input type="hidden" name="action" value="ioclist">',
        u'<input type="hidden" name="allow_overlap" value="%s">' % \
            (allow_overlap), 
        u'<input type="hidden" name="template" value="%s">' % (template),
        u'<p class="ioctext">Enter IOC:s in the text box below</p>',
        u'<textarea rows=10 cols=80 name="data"></textarea>',
        u'<p class="ioctext">List name',
        u'<input type="text" name="name">',
        u'<input type="submit" value="%s"></p>' % _("Create IOCList"),
        u'</div></form>',
        ]

    return macro.formatter.rawHTML('\n'.join(html))
