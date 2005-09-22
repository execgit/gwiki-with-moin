# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - User Accounts

    @copyright: 2000-2004 by J�rgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import os, string, time, Cookie, sha, codecs

try:
    import cPickle as pickle
except ImportError:
    import pickle

# Set pickle protocol, see http://docs.python.org/lib/node64.html
PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL

from MoinMoin import config, caching, wikiutil
from MoinMoin.util import datetime, filesys

def getUserList(request):
    """ Get a list of all (numerical) user IDs.

    @param request: current request
    @rtype: list
    @return: all user IDs
    """
    import re, dircache
    user_re = re.compile(r'^\d+\.\d+(\.\d+)?$')
    files = dircache.listdir(request.cfg.user_dir)
    userlist = filter(user_re.match, files)
    return userlist

def getUserId(request, searchName):
    """
    Get the user ID for a specific user NAME.

    @param searchName: the user name to look up
    @rtype: string
    @return: the corresponding user ID or None
    """
    if not searchName:
        return None
    cfg = request.cfg
    try:
        _name2id = cfg._name2id
    except AttributeError:
        arena = 'user'
        key = 'name2id'
        cache = caching.CacheEntry(request, arena, key)
        try:
            _name2id = pickle.loads(cache.content())
        except (pickle.UnpicklingError, IOError, EOFError, ValueError):
            _name2id = {}
        cfg._name2id = _name2id
    id = _name2id.get(searchName, None)
    if id is None:
        for userid in getUserList(request):
            name = User(request, id=userid).name
            _name2id[name] = userid
        cfg._name2id = _name2id
        arena = 'user'
        key = 'name2id'
        cache = caching.CacheEntry(request, arena, key)
        cache.update(pickle.dumps(_name2id, PICKLE_PROTOCOL))
        id = _name2id.get(searchName, None)
    return id

def getUserIdentification(request, username=None):
    """ 
    Return user name or IP or '<unknown>' indicator.
    
    @param request: the request object
    @param username: (optional) user name
    @rtype: string
    @return: user name or IP or unknown indicator
    """
    _ = request.getText

    if username is None:
        username = request.user.name

    return username or (request.cfg.show_hosts and request.remote_addr) or _("<unknown>")

def encodePassword(pwd, charset='utf-8'):
    """ Encode a cleartext password

    Compatible to Apache htpasswd SHA encoding.

    When using different encoding than 'utf-8', the encoding might fail
    and raise UnicodeError.

    @param pwd: the cleartext password, (unicode)
    @param charset: charset used to encode password, used only for
        compatibility with old passwords generated on moin-1.2.
    @rtype: string
    @return: the password in apache htpasswd compatible SHA-encoding,
        or None
    """
    import base64

    # Might raise UnicodeError, but we can't do anything about it here,
    # so let the caller handle it.
    pwd = pwd.encode(charset)

    pwd = sha.new(pwd).digest()
    pwd = '{SHA}' + base64.encodestring(pwd).rstrip()
    return pwd
    
def normalizeName(name):
    """ Make normalized user name

    Prevent impersonating another user with names containing leading,
    trailing or multiple whitespace, or using invisible unicode
    characters.

    Prevent creating user page as sub page, because '/' is not allowed
    in user names.

    Prevent using ':' and ',' which are reserved by acl.
    
    @param name: user name, unicode
    @rtype: unicode
    @return: user name that can be used in acl lines
    """
    name = name.replace('_', ' ') # we treat _ as a blank
    username_allowedchars = "'" # O'Brian :)
    # Strip non alpha numeric characters (except username_allowedchars), keep white space
    name = ''.join([c for c in name if c.isalnum() or c.isspace() or c in username_allowedchars])

    # Normalize white space. Each name can contain multiple 
    # words separated with only one space.
    name = ' '.join(name.split())

    return name
    
def isValidName(request, name):
    """ Validate user name

    @param name: user name, unicode
    """
    normalized = normalizeName(name)
    name = name.replace('_', ' ') # we treat _ as a blank
    return (name == normalized) and not wikiutil.isGroupPage(request, name)

def encodeList(items):
    """ Encode list of items in user data file

    Items are separated by '\t' characters.
    
    @param items: list unicode strings
    @rtype: unicode
    @return: list encoded as unicode
    """
    line = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        line.append(item)
        
    line = '\t'.join(line)
    return line

def decodeList(line):
    """ Decode list of items from user data file
    
    @param line: line containing list of items, encoded with encodeList
    @rtype: list of unicode strings
    @return: list of items in encoded in line
    """
    items = []
    for item in line.split('\t'):
        item = item.strip()
        if not item:
            continue
        items.append(item)
    return items
    
class User:
    """A MoinMoin User"""

    def __init__(self, request, id=None, name="", password=None, auth_username=""):
        """
        Initialize user object
        
        @param request: the request object
        @param id: (optional) user ID
        @param name: (optional) user name
        @param password: (optional) user password
        @param auth_username: (optional) already authenticated user name (e.g. apache basic auth)
        """
        self._cfg = request.cfg
        self.valid = 0
        self.trusted = 0
        self.id = id
        self.auth_username = auth_username

        # create some vars automatically
        for tuple in self._cfg.user_form_fields:
            key = tuple[0]
            default = self._cfg.user_form_defaults.get(key, '')
            setattr(self, key, default)
       
        if name:
            self.name = name
        
        # create checkbox fields (with default 0)
        for key, label in self._cfg.user_checkbox_fields:
            setattr(self, key, self._cfg.user_checkbox_defaults.get(key, 0))

        self.enc_password = ""
        if password:
            if password.startswith('{SHA}'):
                self.enc_password = password
            else:
                try:
                    self.enc_password = encodePassword(password)
                except UnicodeError:
                    pass # Should never happen

        #self.edit_cols = 80
        self.tz_offset = int(float(self._cfg.tz_offset) * 3600) # XXX 'tz_offset': (???, True)
        self.language = "" # XXX 'language': ('', True)
        self.date_fmt = "" # XXX 'date_fmt': ('', True)
        self.datetime_fmt = "" # XXX 'datetime_fmt': ('', True)
        self.quicklinks = [] # XXX 'quicklinks': ([], True)
        self.subscribed_pages = [] # XXX 'subscribed_pages': ([], True)
        self.theme_name = self._cfg.theme_default # XXX 'theme_name': ("modern", True)
        self.editor_default = self._cfg.editor_default # XXX 'editor_default': ('text', True)
        self.editor_ui = self._cfg.editor_ui # XXX 'editor_ui': ('both', True)
        self.last_saved = str(time.time())
        
        # attrs not saved to profile
        self._request = request
        self._trail = []

        # we got an already authenticated username:
        check_pass = 0
        if not self.id and self.auth_username:
            self.id = getUserId(request, self.auth_username)
            if not password is None:
                check_pass = 1
        if self.id:
            self.load_from_id(check_pass)
            if self.name == self.auth_username:
                self.trusted = 1
        elif self.name:
            self.id = getUserId(self._request, self.name)
            if self.id:
                self.load_from_id(1)
            else:
                self.id = self.make_id()
        else:
            self.id = self.make_id()

        # "may" so we can say "if user.may.read(pagename):"
        if self._cfg.SecurityPolicy:
            self.may = self._cfg.SecurityPolicy(self)
        else:
            from security import Default
            self.may = Default(self)
        
        from MoinMoin.i18n.meta import languages
        if self.language and not languages.has_key(self.language):
            self.language = 'en'

    def make_id(self):
        """ make a new unique user id """
        #!!! this should probably be a hash of REMOTE_ADDR, HTTP_USER_AGENT
        # and some other things identifying remote users, then we could also
        # use it reliably in edit locking
        from random import randint
        return "%s.%d" % (str(time.time()), randint(0,65535))
            
    def __filename(self):
        """
        get filename of the user's file on disk
        @rtype: string
        @return: full path and filename of user account file
        """
        return os.path.join(self._cfg.user_dir, self.id or "...NONE...")

    def __bookmark_filename(self):
        if self._cfg.interwikiname:
            return (self.__filename() + "." + self._cfg.interwikiname +
                    ".bookmark")
        else:
            return self.__filename() + ".bookmark"


    def exists(self):
        """
        Do we have a user account for this user?
        
        @rtype: bool
        @return: true, if we have a user account
        """
        return os.path.exists(self.__filename())

    def load_from_id(self, check_pass=0):
        """
        Load user account data from disk.

        Can only load user data if the id number is already known.

        This loads all member variables, except "id" and "valid" and
        those starting with an underscore.
        
        @param check_pass: If 1, then self.enc_password must match the
                           password in the user account file.
        """
        if not self.exists(): return

        data = codecs.open(self.__filename(), "r", config.charset).readlines()
        user_data = {'enc_password': ''}
        for line in data:
            if line[0] == '#':
                continue

            try:
                key, val = line.strip().split('=', 1)
                if key not in self._cfg.user_transient_fields and key[0] != '_':
                    # Decode list values
                    if key in ['quicklinks', 'subscribed_pages']:
                        val = decodeList(val)
                    user_data[key] = val
            except ValueError:
                pass

        # Validate data from user file. In case we need to change some
        # values, we set 'changed' flag, and later save the user data.
        changed = 0

        if check_pass:
            # If we have no password set, we don't accept login with username
            if not user_data['enc_password']:
                return
            # Check for a valid password, possibly changing encoding
            valid, changed = self._validatePassword(user_data)
            if not valid: 
                return
            else:
                self.trusted = 1

        # Remove ignored checkbox values from user data
        for key, label in self._cfg.user_checkbox_fields:
            if user_data.has_key(key) and key in self._cfg.user_checkbox_disable:
                del user_data[key]

        # Copy user data into user object
        for key, val in user_data.items():
            vars(self)[key] = val

        self.tz_offset = int(self.tz_offset)

        # Remove old unsupported attributes from user data file.
        remove_attributes = ['passwd', 'show_emoticons']
        for attr in remove_attributes:
            if hasattr(self, attr):
                delattr(self, attr)
                changed = 1
        
        # make sure checkboxes are boolean
        for key, label in self._cfg.user_checkbox_fields:
            try:
                setattr(self, key, int(getattr(self, key)))
            except ValueError:
                setattr(self, key, 0)

        # convert (old) hourly format to seconds
        if -24 <= self.tz_offset and self.tz_offset <= 24:
            self.tz_offset = self.tz_offset * 3600

        # clear trail
        self._trail = []

        if not self.disabled:
            self.valid = 1

        # If user data has been changed, save fixed user data.
        if changed:
            self.save()

    def _validatePassword(self, data):
        """ Try to validate user password

        This is a private method and should not be used by clients.

        In pre 1.3, the wiki used some 8 bit charset. The user password
        was entered in this 8 bit password and passed to
        encodePassword. So old passwords can use any of the charset
        used.

        In 1.3, we use unicode internally, so we encode the password in
        encodePassword using utf-8.

        When we compare passwords we must compare with same encoding, or
        the passwords will not match. We don't know what encoding the
        password on the user file uses. We may ask the wiki admin to put
        this into the config, but he may be wrong.

        The way chosen is to try to encode and compare passwords using
        all the encoding that were available on 1.2, until we get a
        match, which means that the user is valid.

        If we get a match, we replace the user password hash with the
        utf-8 encoded version, and next time it will match on first try
        as before. The user password did not change, this change is
        completely transparent for the user. Only the sha digest will
        change.

        @param data: dict with user data
        @rtype: 2 tuple (bool, bool)
        @return: password is valid, password did change
        """
        # First try with default encoded password. Match only non empty
        # passwords. (require non empty enc_password)
        if self.enc_password and self.enc_password == data['enc_password']:
            return True, False

        # Try to match using one of pre 1.3 8 bit charsets

        # Get the clear text password from the form (require non empty
        # password)
        password = self._request.form.get('password',[None])[0]
        if not password:
            return False, False 
                
        # First get all available pre13 charsets on this system
        import codecs
        pre13 = ['iso-8859-1', 'iso-8859-2', 'euc-jp', 'gb2312', 'big5',]
        available = []
        for charset in pre13:
            try:
                encoder = codecs.getencoder(charset)
                available.append(charset)
            except LookupError:
                pass # missing on this system
                
        # Now try to match the password
        for charset in available:
            # Try to encode, failure is expected
            try:
                enc_password = encodePassword(password, charset=charset)
            except UnicodeError:
                continue

            # And match (require non empty enc_password)
            if enc_password and enc_password == data['enc_password']:
                # User password match - replace the user password in the
                # file with self.password
                data['enc_password'] = self.enc_password
                return True, True

        # No encoded password match, this must be wrong password
        return False, False

    def save(self):
        """
        Save user account data to user account file on disk.

        This saves all member variables, except "id" and "valid" and
        those starting with an underscore.
        """
        if not self.id:
            return

        user_dir = self._cfg.user_dir
        filesys.makeDirs(user_dir)

        self.last_saved = str(time.time())

        # !!! should write to a temp file here to avoid race conditions,
        # or even better, use locking
        
        data = codecs.open(self.__filename(), "w", config.charset)
        data.write("# Data saved '%s' for id '%s'\n" % (
            time.strftime(self._cfg.datetime_fmt, time.localtime(time.time())),
            self.id))
        attrs = vars(self).items()
        attrs.sort()
        for key, value in attrs:
            if key not in self._cfg.user_transient_fields and key[0] != '_':
                # Encode list values
                if key in ['quicklinks', 'subscribed_pages']:
                    value = encodeList(value)
                line = u"%s=%s\n" % (key, unicode(value))
                data.write(line)
        data.close()

        try:
            os.chmod(self.__filename(), 0666 & config.umask)
        except OSError:
            pass

        if not self.disabled:
            self.valid = 1

    def getTime(self, tm):
        """
        Get time in user's timezone.
        
        @param tm: time (UTC UNIX timestamp)
        @rtype: int
        @return: tm tuple adjusted for user's timezone
        """
        return datetime.tmtuple(tm + self.tz_offset)


    def getFormattedDate(self, tm):
        """
        Get formatted date adjusted for user's timezone.

        @param tm: time (UTC UNIX timestamp)
        @rtype: string
        @return: formatted date, see cfg.date_fmt
        """
        date_fmt = self.date_fmt or self._cfg.date_fmt
        return time.strftime(date_fmt, self.getTime(tm))


    def getFormattedDateTime(self, tm):
        """
        Get formatted date and time adjusted for user's timezone.

        @param tm: time (UTC UNIX timestamp)
        @rtype: string
        @return: formatted date and time, see cfg.datetime_fmt
        """
        datetime_fmt = self.datetime_fmt or self._cfg.datetime_fmt
        return time.strftime(datetime_fmt, self.getTime(tm))


    def setBookmark(self, tm):
        """
        Set bookmark timestamp.
        
        @param tm: timestamp
        """
        if self.valid:
            bm_fn = self.__bookmark_filename()
            bmfile = open(bm_fn, "w")
            bmfile.write(str(tm)+"\n")
            bmfile.close()
            try:
                os.chmod(bm_fn, 0666 & config.umask)
            except OSError:
                pass

    def getBookmark(self):
        """
        Get bookmark timestamp.
        
        @rtype: int
        @return: bookmark timestamp or None
        """
        bm = None
        bm_fn = self.__bookmark_filename()

        if self.valid and os.path.exists(bm_fn):
            try:
                bm = long(open(bm_fn, 'r').readline()) # must be long for py 2.2
            except (OSError, ValueError):
                pass
        return bm

    def delBookmark(self):
        """
        Removes bookmark timestamp.

        @rtype: int
        @return: 0 on success, 1 on failure
        """
        bm_fn = self.__bookmark_filename()
        if self.valid:
            if os.path.exists(bm_fn):
                try:
                    os.unlink(bm_fn)
                except OSError:
                    return 1
            return 0
        return 1

    def getQuickLinks(self):
        """ Get list of pages this user wants in the navibar

        @rtype: list
        @return: quicklinks from user account
        """
        return self.quicklinks

    def getSubscriptionList(self):
        """ Get list of pages this user has subscribed to
        
        @rtype: list
        @return: pages this user has subscribed to
        """
        return self.subscribed_pages

    def isQuickLinkedTo(self, pagelist):
        """
        Check if user quicklink matches any page in pagelist.
        
        @param pagelist: list of pages to check for quicklinks
        @rtype: int
        @return: 1, if user has quicklinked any page in pagelist
                 0, if not
        """
        quicklinked = 0
        if self.valid:
            interwikiname = self._cfg.interwikiname
            for page in pagelist:
                if page in self.quicklinks:
                    quicklinked = 1
                    break
                # do also try our own interwiki name
                if interwikiname:
                    iwpage = "%s:%s" % (interwikiname, page)
                    if iwpage in self.quicklinks:
                        quicklinked = 1
                        break
        return quicklinked

    def isSubscribedTo(self, pagelist):
        """
        Check if user subscription matches any page in pagelist.
        
        @param pagelist: list of pages to check for subscription
        @rtype: int
        @return: 1, if user has subscribed any page in pagelist
                 0, if not
        """
        import re

        matched = 0
        if self.valid:
            pagelist_lines = '\n'.join(pagelist)
            # do also try our own interwiki name
            if self._cfg.interwikiname:
                pagelist_lines = "%s\n%s" % (pagelist_lines,
                                  '\n'.join(
                    ["%s:%s" % (self._cfg.interwikiname, page)
                     for page in pagelist]))
            for pattern in self.getSubscriptionList():
                # check if pattern matches one of the pages in pagelist
                matched = pattern in pagelist
                if matched: break
                try:
                    rexp = re.compile("^"+pattern+"$", re.M)
                except re.error:
                    # skip bad regex
                    continue
                matched = rexp.search(pagelist_lines)
                if matched: break
        if matched:
            return 1
        else:
            return 0

    def quicklinkPage(self, pagename, remove=False):
        """ Add or remove a quicklink to a wiki page.

        Note that you need to save the user data to make this stick!

        @param pagename: name of the page to quicklink
        @param remove: unsubscribe pagename if set
        @type remove: bool
        @rtype: bool
        @return: true, if page was NEWLY quicklinked.
        """
        if remove:
            if pagename in self.quicklinks:
                self.quicklinks.remove(pagename)
                return 1
            
        # check for our own interwiki name
        if self._cfg.interwikiname:
            pagename = "%s:%s" % (self._cfg.interwikiname, pagename)

        if remove and (pagename in self.quicklinks):
            self.quicklinks.remove(pagename)
            return 1
    
        else:
            # add the interwiki name!
            if pagename not in self.quicklinks:
                self.quicklinks.append(pagename)
                return 1
        return 0

    def subscribePage(self, pagename, remove=False):
        """ Subscribe or unsubscribe to a wiki page.

        Note that you need to save the user data to make this stick!

        @param pagename: name of the page to subscribe
        @param remove: unsubscribe pagename if set
        @type remove: bool
        @rtype: bool
        @return: true, if page was NEWLY subscribed.
        """
        if remove:
            if pagename in self.subscribed_pages:
                self.subscribed_pages.remove(pagename)
                return 1
            
        # check for our own interwiki name
        if self._cfg.interwikiname:
            pagename = "%s:%s" % (self._cfg.interwikiname, pagename)

        if remove and (pagename in self.subscribed_pages):
            self.subscribed_pages.remove(pagename)
            return 1
    
        else:
            # add the interwiki name!
            if pagename not in self.subscribed_pages:
                self.subscribed_pages.append(pagename)
                return 1
        return 0


    def addTrail(self, pagename):
        """
        Add page to trail.
        
        @param pagename: the page name to add to the trail
        """
        # TODO: acquire lock here, so multiple processes don't clober
        # each one trail.

        if self.valid and (self.show_page_trail or self.remember_last_visit):
            # load trail if not known
            self.getTrail()      

            # Add only existing pages that the user may read
            if self._request:
                from MoinMoin.Page import Page
                page = Page(self._request, pagename)
                if not (page.exists() and
                        self._request.user.may.read(page.page_name)):
                    return

            # save interwiki links internally
            if self._cfg.interwikiname:
                pagename = "%s:%s" % (self._cfg.interwikiname,
                                      pagename)

            # don't append tail to trail ;)
            if self._trail and self._trail[-1] == pagename: return

            # append new page, limiting the length
            self._trail = filter(lambda p, pn=pagename: p != pn, self._trail)
            self._trail = self._trail[-(self._cfg.trail_size-1):]
            self._trail.append(pagename)
            self.saveTrail()

            ## TODO: release lock here
            
    def saveTrail(self):
        """ Save trail file

        Save using one write call, which should be fine in most cases,
        but will fail in rare cases without real file locking.
        """
        data = '\n'.join(self._trail) + '\n'
        path = self.__filename() + ".trail"
        try:
            file = codecs.open(path, "w", config.charset)
            try:
                file.write(data)
            finally:
                file.close()

            # TODO: do we realy need to set perimssion for each save, which
            # is on each request?
            try:
                os.chmod(path, 0666 & config.umask)
            except OSError, err:
                self._request.log("Can't change mode of trail file: %s" %
                                  str(err))
        except (IOError, OSError), err:
            self._request.log("Can't save trail file: %s" % str(err))

    def getTrail(self):
        """
        Return list of recently visited pages.
        
        @rtype: list
        @return: pages in trail
        """
        if self.valid and (self.show_page_trail or self.remember_last_visit) \
                and not self._trail \
                and os.path.exists(self.__filename() + ".trail"):
            try:
                self._trail = codecs.open(self.__filename() + ".trail", 'r', config.charset).readlines()
            except (OSError, ValueError):
                self._trail = []
            else:
                self._trail = filter(None, map(string.strip, self._trail))
                self._trail = self._trail[-self._cfg.trail_size:]

        return self._trail

    def isCurrentUser(self):
        return self._request.user.name == self.name

    def host(self):
        """ Return user host """
        _ = self._request.getText
        host = self.isCurrentUser() and self._cfg.show_hosts and self._request.remote_addr
        return host or _("<unknown>")

    def signature(self):
        """ Return user signature using markup
        
        Users sign with a link to their homepage, or with text if they
        don't have one. The text may be parsed as a link if it's using
        CamelCase. Visitors return their host address.
        """
        if not self.name:
            return self.host()
        
        interwiki = wikiutil.getInterwikiHomePage(self._request, self.name)
        wikiname, pagename = interwiki
        if wikiname == 'Self':
            if not wikiutil.isStrictWikiname(self.name):
                markup = '["%s"]' % pagename
            else:
                markup = pagename
        else:
            markup = '%s:%s' % (wikiname, pagename.replace(" ","_")) # XXX moin only. better ideas?
        return markup

