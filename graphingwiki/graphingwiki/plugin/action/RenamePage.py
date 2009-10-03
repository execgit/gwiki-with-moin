# -*- coding: utf-8 -*-"
"""
    RenamePage action plugin to MoinMoin/Graphingwiki
     - Extends MoinMoin RenamePage action with link renaming

    @copyright: 2009 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""
import re

from MoinMoin import wikiutil
from MoinMoin.PageEditor import PageEditor
from MoinMoin.action.RenamePage import RenamePage as RenamePageBasic
from MoinMoin.parser.text_moin_wiki import Parser

class RenamePage(RenamePageBasic):

    def _inlink_rename(self, page, newpagename, oldpagename, comment):
        rel_newpagename = wikiutil.RelPageName(page, newpagename)

        # The following regexp match functions search for
        # occurrences of the target page name, determine
        # if they're absolute, relative or subpage
        # matches, and replace them accordingly
        def word_subfun(mo):
            match = mo.groups()
            if wikiutil.AbsPageName(page, match[1]) == oldpagename:
                # If the link was relative:
                if not oldpagename in match[1]:
                    # If the new page will be a subpage of the
                    # source, retain relative link. Else, make
                    # an absolute link.
                    if rel_newpagename.startswith('/'):
                        return match[1].replace(
                            wikiutil.RelPageName(page, oldpagename), 
                            rel_newpagename)
                    else:
                        return match[1].replace(
                            wikiutil.RelPageName(page, oldpagename), 
                            newpagename)

                # Else, change absolute link
                return match[1].replace(oldpagename, newpagename)
            # No match in this link -> move on
            else:
                return match[1]

        def link_subfun(mo):
            match = mo.groups()

            if wikiutil.AbsPageName(page, match[1]) == oldpagename:
                # If the link was relative:
                if not oldpagename in match[0]:
                    # If the new page will be a subpage of the
                    # source, retain relative link. Else, make
                    # an absolute link.
                    if rel_newpagename.startswith('/'):
                        return match[0].replace(
                            wikiutil.RelPageName(page, oldpagename), 
                            rel_newpagename)
                    else:
                        return match[0].replace(
                            wikiutil.RelPageName(page, oldpagename), 
                            newpagename)

                # Else, change absolute link
                return match[0].replace(oldpagename, newpagename)
            # No match in this link -> move on
            else:
                return match[0]

        self.page = PageEditor(self.request, page)
        savetext = self.page.get_raw_body()

        # Must replace both WikiWords and links, as
        # [[WikiWord]] is a link.
        word_re = re.compile(Parser.word_rule, re.VERBOSE)
        savetext = word_re.sub(word_subfun, savetext)
        link_re = re.compile(Parser.link_rule, re.VERBOSE)
        savetext = link_re.sub(link_subfun, savetext)

        msg = self.page.saveText(savetext, 0, comment=comment, 
                                 notify=False)
        return msg

    def do_action(self):
        _ = self.request.getText

        pdata = self.request.graphdata.getpage(self.pagename)
        oldpagename = self.pagename

        success, msgs = RenamePageBasic.do_action(self)

        rename_links = 0
        if 'rename_links' in self.form:
            try:
                rename_links = int(self.form['rename_links'][0])
            except:
                pass

        if rename_links and success:
            newpagename = self.form.get('newpagename', [u''])[0]
            newpagename = self.request.normalizePagename(newpagename)

            comment = self.form.get('comment', [u''])[0]
            comment = wikiutil.clean_input(comment)
            comment = "%s (%s)" % (comment, _("changed links:") + 
                                   " %s -> %s" % (self.pagename, newpagename))

            # List pages that link to the renamed page
            pages = set()
            for type in pdata.get('in', {}):
                pages.update(pdata['in'][type])

            # Update listed pages
            for page in pages:
                # User rights _ARE_ checked here!
                if not self.request.user.may.write(page):
                    continue

                msg = self._inlink_rename(page, newpagename, 
                                          oldpagename, comment)
                msgs = "%s %s" % (msgs, msg)

        return success, msgs

    # Modified from original Moin code to include inlink renaming
    def get_form_html(self, buttons_html):
        _ = self._
        if self.subpages:
            subpages = ' '.join(self.subpages)

            d = {
                'subpage': subpages,
                'subpages_checked': ('', 'checked')[self.request.form.get('subpages_checked', ['0'])[0] == '1'],
                'subpage_label': _('Rename all /subpages too?'),
                'links_label': _('Rename links to page too?'),
                'links_checked': ('checked', '')[self.request.form.get('subpages_checked', ['0'])[0] == '1'],
                'pagename': wikiutil.escape(self.pagename, True),
                'newname_label': _("New name"),
                'comment_label': _("Optional reason for the renaming"),
                'buttons_html': buttons_html,
                'querytext': _('Really rename this page?')
                }

            return '''
<strong>%(querytext)s</strong>
<br>
<br>
<table>
    <tr>
    <dd>
        %(subpage_label)s<input type="checkbox" name="rename_subpages" value="1" %(subpages_checked)s>
    </dd>
    <dd>
        <class="label"><subpage> %(subpage)s</subpage>
    </dd>
    </tr>
</table>
<table>
    <tr>
        <td class="label"><label>%(newname_label)s</label></td>
        <td class="content">
            <input type="text" name="newpagename" value="%(pagename)s" size="80">
        </td>
    </tr>
    <tr>
        <td class="label"><label>%(comment_label)s</label></td>
        <td class="content">
            <input type="text" name="comment" size="80" maxlength="200">
        </td>
    </tr>
    <tr>
    <td>
    <dd>
        %(links_label)s<input type="checkbox" name="rename_links" value="1" %(links_checked)s>
    </dd>
    </td>
    </tr>
    <tr>
        <td></td>
        <td class="buttons">
            %(buttons_html)s
        </td>
    </tr>
</table>
''' % d

        else:
            d = {
                'pagename': wikiutil.escape(self.pagename, True),
                'newname_label': _("New name"),
                'comment_label': _("Optional reason for the renaming"),
                'links_label': _('Rename links to page too?'),
                'links_checked': ('checked', '')[self.request.form.get('subpages_checked', ['0'])[0] == '1'],
                'buttons_html': buttons_html,
                }
            return '''
<table>
    <tr>
        <td class="label"><label>%(newname_label)s</label></td>
        <td class="content">
            <input type="text" name="newpagename" value="%(pagename)s" size="80">
        </td>
    </tr>
    <tr>
        <td class="label"><label>%(comment_label)s</label></td>
        <td class="content">
            <input type="text" name="comment" size="80" maxlength="200">
        </td>
    </tr>
    <tr>
    <td>
    <dd>
        %(links_label)s<input type="checkbox" name="rename_links" value="1" %(links_checked)s>
    </dd>
    </td>
    </tr>
    <tr>
        <td></td>
        <td class="buttons">
            %(buttons_html)s
        </td>
    </tr>
</table>
''' % d

def execute(pagename, request):
    """ Glue code for actions """
    RenamePage(pagename, request).render()
