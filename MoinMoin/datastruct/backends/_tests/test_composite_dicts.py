# -*- coding: iso-8859-1 -*-

"""
MoinMoin.datastruct.backends.composite_dicts test

@copyright: 2009 MoinMoin:DmitrijsMilajevs
            2008 MoinMoin: MelitaMihaljevic
@license: GPL, see COPYING for details
"""

from py.test import raises

from MoinMoin.datastruct.backends._tests import DictsBackendTest
from MoinMoin.datastruct import ConfigDicts, CompositeDicts, DictDoesNotExistError
from MoinMoin._tests import wikiconfig
from MoinMoin import security


class TestCompositeDict(DictsBackendTest):

    class Config(wikiconfig.Config):

        one_dict = {u'SomeTestDict': {u'First': u'first item',
                                      u'text with spaces': u'second item',
                                      u'Empty string': u'',
                                      u'Last': u'last item'}}

        other_dict = {u'SomeOtherTestDict': {u'One': '1',
                                             u'Two': '2'}}

        def dict_manager_init(self, request):
            return CompositeDicts(request,
                                  CompositeDicts(request, self.one_dict),
                                  CompositeDicts(request, self.other_dict))


coverage_modules = ['MoinMoin.datastruct.backends.composite_dicts']
