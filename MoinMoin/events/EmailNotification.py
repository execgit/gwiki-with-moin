# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - email notification plugin from event system

    This code sends email notifications about page changes.
    TODO: refactor it to handle separate events for page changes, creations, etc

    @copyright: 2007 by Karol Nowak <grywacz@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import user
from MoinMoin.Page import Page
from MoinMoin.mail import sendmail
from MoinMoin.events import *

def sendNotification(request, page, comment, emails, email_lang, revisions, trivial):
    """ Send notification email for a single language.

    @param comment: editor's comment given when saving the page
    @param emails: list of email addresses
    @param email_lang: language of emails
    @param revisions: revisions of this page (newest first!)
    @param trivial: the change is marked as trivial
    @rtype: int
    @return: sendmail result
    """
    _ = request.getText
    page._ = lambda s, formatted=True, r=request, l=email_lang: r.getText(s, formatted=formatted, lang=l)

    if len(revisions) >= 2:
        querystr = {'action': 'diff',
                    'rev2': str(revisions[0]),
                    'rev1': str(revisions[1])}
    else:
        querystr = {}
    pagelink = request.getQualifiedURL(page.url(request, querystr, relative=False))

    mailBody = _("Dear Wiki user,\n\n"
        'You have subscribed to a wiki page or wiki category on "%(sitename)s" for change notification.\n\n'
        "The following page has been changed by %(editor)s:\n"
        "%(pagelink)s\n\n", formatted=False) % {
            'editor': page.uid_override or user.getUserIdentification(request),
            'pagelink': pagelink,
            'sitename': page.cfg.sitename or request.getBaseURL(),
    }

    if comment:
        mailBody = mailBody + \
            _("The comment on the change is:\n%(comment)s\n\n", formatted=False) % {'comment': comment}

    # append a diff (or append full page text if there is no diff)
    if len(revisions) < 2:
        mailBody = mailBody + \
            _("New page:\n", formatted=False) + \
            page.get_raw_body()
    else:
        lines = wikiutil.pagediff(request, page.page_name, revisions[1],
                                  page.page_name, revisions[0])
        if lines:
            mailBody = mailBody + "%s\n%s\n" % (("-" * 78), '\n'.join(lines))
        else:
            mailBody = mailBody + _("No differences found!\n", formatted=False)

    return sendmail.sendmail(request, emails,
        _('[%(sitename)s] %(trivial)sUpdate of "%(pagename)s" by %(username)s', formatted=False) % {
            'trivial': (trivial and _("Trivial ", formatted=False)) or "",
            'sitename': page.cfg.sitename or "Wiki",
            'pagename': page.page_name,
            'username': page.uid_override or user.getUserIdentification(request),
        },
        mailBody, mail_from=page.cfg.mail_from)


def notifySubscribers(request, page, comment, trivial):
    """ Send email to all subscribers of given page.

    @param comment: editor's comment given when saving the page
    @param trivial: editor's suggestion that the change is trivial (Subscribers may ignore this)
    @rtype: string
    @return: message, indicating success or errors.
    """
    _ = request.getText
    subscribers = page.getSubscribers(request, return_users=1, trivial=trivial)
    if subscribers:
        # get a list of old revisions, and append a diff
        revisions = page.getRevList()

        # send email to all subscribers
        results = [_('Status of sending notification mails:')]
        for lang in subscribers:
            emails = [u.email for u in subscribers[lang]]
            names = [u.name for u in subscribers[lang]]
            mailok, status = sendNotification(request, page, comment, emails, lang, revisions, trivial)
            recipients = ", ".join(names)
            results.append(_('[%(lang)s] %(recipients)s: %(status)s') % {
                'lang': lang, 'recipients': recipients, 'status': status})

        # Return mail sent results. Ignore trivial - we don't have
        # to lie. If mail was sent, just tell about it.
        return '<p>\n%s\n</p> ' % '<br>'.join(results)

    # No mail sent, no message.
    return ''

def handle(event):
    if not isinstance(event, PageChangedEvent):
        return

    if not event.request.cfg.mail_enabled:
        return
    
    return notifySubscribers(event.request, event.page, event.comment, event.trivial)