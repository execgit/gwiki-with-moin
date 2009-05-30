# -*- coding: iso-8859-1 -*-

"""
MoinMoin.groups.GroupManager test

@copyright: 2009 MoinMoin:DmitrijsMilajevs
            2008 MoinMoin: MelitaMihaljevic
@license: GPL, see COPYING for details
"""

from py.test import raises

from MoinMoin.groups import BackendManager, GroupManager

class TestGroupManagerAPI(object):
    """
    Performs test of the API of GroupManager.
    """

    from MoinMoin._tests import wikiconfig
    class Config(wikiconfig.Config):
        pass

    def setup_class(self):
        self.admin_group = frozenset([u'Admin', u'JohnDoe'])
        self.editor_group = frozenset([u'MainEditor', u'JohnDoe'])
        self.fruit_group = frozenset([u'Apple', u'Banana', u'Cherry'])

        first_backend_groups = {u'AdminGroup': self.admin_group,
                                u'EditorGroup': self.editor_group,
                                u'FruitGroup': self.fruit_group}

        self.user_group = frozenset([u'JohnDoe', u'Bob', u'Joe'])
        self.city_group = frozenset([u'Bolzano', u'Riga', u'London'])
        # Suppose, someone hacked second backend
        # and added himself to AdminGroup
        self.second_admin_group = frozenset([u'TheHacker'])

        second_backend_groups = {u'UserGroup': self.user_group,
                                 u'CityGroup': self.city_group,
                                 # Here group name clash occurs.
                                 # AdminGroup is defined in both
                                 # first_backend and second_backend.
                                 u'AdminGroup': self.second_admin_group}

        self.Config.group_manager = lambda self, request: GroupManager(backends=[BackendManager(request, first_backend_groups),
                                                                                 BackendManager(request, second_backend_groups)])

    def setup_method(self, method):
        self.group_manager = self.request.cfg.group_manager(self.request)

    def test_getitem(self):
        """
        Tests __getitem__ API method. It should return a group by its name.
        """
        assert self.fruit_group == self.group_manager[u'FruitGroup']
        raises(KeyError, lambda: self.group_manager[u'not existing group'])

    def test_clashed_getitem(self):
        """
        This test check situation when groups with a same name are
        defined in several backends. In this case, the only one
        backend must be taken in consideration, that backend which is
        defined first in the backends list.
        """
        admin_group = self.group_manager[u'AdminGroup']

        assert self.admin_group == admin_group

        # Nevertheless, TheHacker added himself to the second backend,
        # it must not be taken into consideration, because AdminGroup is defined
        # in first backend
        assert u'TheHacker' not in admin_group

    def test_iter(self):
        """
        Tests __iter__ API method. It should iterate over all groups
        available via backends. It should avoid group name clashes.
        """
        all_group_names = [group_name for group_name in self.group_manager]

        assert 5 == len(all_group_names)
        # There are no duplicates
        assert len(set(all_group_names)) == len(all_group_names)

    def test_contains(self):
        """
        Tests __contains__ API method. It should check if a group
        called group_name is available via some backend.
        """
        assert u'UserGroup' in self.group_manager
        assert u'not existing group' not in self.group_manager

    def test_membergroups(self):
        """
        Tests membergroups API method. It should lists all groups
        where member is a member of. It should return a list of group
        names.
        """
        apple_groups = self.group_manager.membergroups(u'Apple')
        assert 1 == len(apple_groups)
        assert u'FruitGroup' in apple_groups
        assert u'AdminGroup' not in apple_groups

        john_doe_groups = self.group_manager.membergroups(u'JohnDoe')
        assert 3 == len(john_doe_groups)
        assert u'EditorGroup' in john_doe_groups
        assert u'AdminGroup' in john_doe_groups
        assert u'UserGroup' in john_doe_groups
        assert u'FruitGroup' not in john_doe_groups

coverage_modules = ['MoinMoin.groups']
