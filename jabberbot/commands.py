# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - inter-thread communication commands

    This file defines command objects used by notification
    bot's threads to communicate among each other.

    @copyright: 2007 by Karol Nowak <grywacz@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# First, XML RPC -> XMPP commands
class NotificationCommand:
    """Class representing a notification request"""
    def __init__(self, jids, notification, msg_type="message", async=True):
        """A constructor

        @param jids: a list of jids to sent this message to
        @type jids: list
        @param async: async notifications get queued if contact is DnD

        """
        if type(jids) != list:
            raise Exception("jids argument must be a list!")

        self.notification = notification
        self.jids = jids
        self.async = async
        self.msg_type = msg_type

class NotificationCommandI18n(NotificationCommand):
    """Notification request that should be translated by the XMPP bot"""
    def __init__(self, jids, notification, msg_type="message", async=True):
        """A constructor

        Params as in NotificationCommand.

        """
        NotificationCommand.__init__(self, jids, notification, msg_type, async)

    def translate(self, gettext_func):
        """Translate the message using a provided gettext function

        @param gettext_func: a unary gettext function
        @return: translated message
        """
        if self.notification.has_key('data'):
            return gettext_func(self.notification['text']) % self.notification['data']
        else:
            return gettext_func(self.notification['text'])

class AddJIDToRosterCommand:
    """Class representing a request to add a new jid to roster"""
    def __init__(self, jid):
        self.jid = jid

class RemoveJIDFromRosterCommand:
    """Class representing a request to remove a jid from roster"""
    def __init__(self, jid):
        self.jid = jid

# XMPP <-> XML RPC commands
# These commands are passed in both directions, with added data
# payload when they return to the XMPP code. Naming convention
# follows method names defined by the Wiki RPC Interface v2.

class BaseDataCommand(object):
    """Base class for all commands used by the XMPP component.

    It has to support an optional data payload and store JID the
    request has come from and provide a help string for its parameters.
    """

    # Description of what the command does
    description = u""

    # Parameter list in a human-readable format
    parameter_list = u""

    def __init__(self, jid):
        """A constructor

        @param jid: Jabber ID to send the reply to
        @type jid: unicode
        """
        self.jid = jid
        self.data = None

class GetPage(BaseDataCommand):

    description = u"retrieve raw content of a named page"
    parameter_list = u"pagename"

    def __init__(self, jid, pagename):
        BaseDataCommand.__init__(self, jid)
        self.pagename = pagename

class GetPageHTML(BaseDataCommand):

    description = u"retrieve HTML-formatted content of a named page"
    parameter_list = u"pagename"

    def __init__(self, jid, pagename):
        BaseDataCommand.__init__(self, jid)
        self.pagename = pagename

class GetPageList(BaseDataCommand):

    description = u"get a list of accesible pages"
    parameter_list = u""

    def __init__(self, jid):
        BaseDataCommand.__init__(self, jid)

class GetPageInfo(BaseDataCommand):

    description = u"show detailed information about a page"
    parameter_list = u"pagename"

    def __init__(self, jid, pagename):
        BaseDataCommand.__init__(self, jid)
        self.pagename = pagename

class Search(BaseDataCommand):

    description = u"perform a wiki search"
    parameter_list = u"{title|text} term"

    def __init__(self, jid, term, search_type):
        BaseDataCommand.__init__(self, jid)
        self.term = term
        self.search_type = search_type

class GetUserLanguage:
    """Request user's language information from wiki"""

    def __init__(self, jid):
        """
        @param jid: user's (bare) Jabber ID
        """
        self.jid = jid
        self.language = None
