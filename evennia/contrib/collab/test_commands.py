from uuid import uuid4
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.test import override_settings
from evennia.contrib.collab.commands import CmdCreate, CmdBuildNick, CmdDig, CmdOpen, CmdDestroy, CmdChown, CmdLink
from evennia.contrib.collab.perms import quota_queryset, get_owner, set_owner
from evennia.contrib.collab.test_base import CollabTest


class CollabCommandTestMixin(object):
    """

    """
    def retrieve(self, caller):
        """
        Retrieve the last object created by the caller.
        """
        build_nick = str(uuid4())
        self.call(CmdBuildNick(), build_nick, caller=caller)
        return caller.search(build_nick)


class CollabCreateCommandTestMixin(CollabCommandTestMixin):
    """
    Test collaborative commands. Verify they have the expected effects.
    """
    command = CmdCreate
    type_key = 'object'

    def create(self, cmd_string='thing', caller=None):
        caller = caller or self.char1
        self.call(self.command(), cmd_string, caller=caller)
        return self.retrieve(caller)

    def get_typeclass(self):
        return settings.COLLAB_TYPES[self.type_key]['typeclass']

    def test_create_typeclass(self):
        """
        Test creating an object.
        """
        thing = self.create()
        self.assertEqual(thing.typename, self.get_typeclass().split('.')[-1])

    def test_set_destination(self):
        """
        Test that setting a destination for an object works.
        """
        thing = self.create('thing=here')
        self.assertTrue(thing.destination)
        self.assertEqual(thing.destination, self.char1.location)

    def test_set_aliases(self):
        """
        Test that aliases can be set for created objects.
        """
        thing = self.create('thing;thingus;thingectomy')
        self.assertEqual(set(thing.aliases.all()), {'thingus', 'thingectomy'})

    def test_affects_quota(self):
        """
        Make sure creating objects of a specific type affects the quota for that type.
        """
        old_count = quota_queryset(self.player, self.get_typeclass()).count()
        self.create()
        new_count = quota_queryset(self.player, self.get_typeclass()).count()
        self.assertEquals(new_count, old_count + 1)

    def test_sets_display_owner(self):
        """
        Ensure the 'display owner' of an object is set upon creation.
        """
        thing = self.create()
        owner = get_owner(thing)
        self.assertEqual(owner, self.char1)

    def test_sets_owner(self):
        """
        Ensure the 'true owner' of an object is set upon creation.
        """
        thing = self.create()
        owner = get_owner(thing, player_check=True)
        self.assertEqual(owner, self.player)

    def test_perm_check(self):
        """
        Verify a character without build permissions can't create.
        """
        self.player2.permissions.clear()
        self.player2.permissions.add("Player")
        thing = self.create(caller=self.char2)
        self.assertIs(thing, None)

    def test_respect_quota(self):
        """
        Verify that an object is not created by the command if the user's quota is already hit.
        """
        settings.COLLAB_TYPES[self.type_key]['quota'] = 1
        thing = self.create(caller=self.char2)
        self.assertTrue(thing)
        thing2 = self.create('dingus', caller=self.char2)
        self.assertFalse(thing2)
        self.assertEqual(quota_queryset(self.player2, self.get_typeclass()).count(), 1)


class CreateCmdTest(CollabCreateCommandTestMixin, CollabTest):
    pass


class CmdDigTest(CollabCreateCommandTestMixin, CollabTest):
    command = CmdDig
    type_key = 'room'


class OpenCmdTest(CollabCreateCommandTestMixin, CollabTest):
    command = CmdOpen
    type_key = 'exit'


class CmdDestroyTest(CollabTest):
    """
    Tests the destroy command.
    """
    def test_destroy_object(self):
        """
        Verify destroy's base functionality.
        """
        set_owner(self.player, self.obj1)
        self.call(CmdDestroy(), self.obj1.name)
        self.assertRaises(ObjectDoesNotExist, getattr, self.obj1, 'name')

    def test_perms_failure(self):
        """
        Make sure destroy does not work on objects the user does not own.
        """
        set_owner(self.player, self.obj1)
        self.call(CmdDestroy(), self.obj1.name, caller=self.player2)
        # Should not raise an exception, because it still exists.
        self.obj1.name
        # Force should not help here.
        self.call(CmdDestroy(), '/force %s' % self.obj1.name, caller=self.player)
        self.obj1.name

    def test_destroy_override(self):
        """
        Verify an object that a user does not own is not destroyed unless the user really means it.
        """
        set_owner(self.player2, self.obj1)
        self.call(CmdDestroy(), self.obj1.name, caller=self.char1)
        self.obj1.name
        self.call(CmdDestroy(), '/force %s' % self.obj1.name, caller=self.char1)
        self.assertRaises(ObjectDoesNotExist, getattr, self.obj1, 'name')


class TestCmdChown(CollabTest):
    """
    Tests that CmdChown works.
    """
    def test_good_chown(self):
        """
        Verify that a user who should be able to chown an object can.
        """
        self.assertNotEqual(get_owner(self.obj2), self.char1)
        self.assertNotEqual(get_owner(self.obj2, player_check=True), self.player)
        # Player is an immortal, so should always be able to chown.
        self.call(CmdChown(), self.obj2.name, caller=self.char1)
        self.assertEqual(get_owner(self.obj2), self.char1)
        self.assertEqual(get_owner(self.obj2, player_check=True), self.player)

    def test_bad_chown(self):
        """
        Verify that a user who should not be able to chown cannot.
        """
        self.assertNotEqual(get_owner(self.obj1), self.char2)
        self.assertNotEqual(get_owner(self.obj1, player_check=True), self.player2)
        self.call(CmdChown(), self.obj1.name, caller=self.char2)
        self.assertNotEqual(get_owner(self.obj1), self.char2)
        self.assertNotEqual(get_owner(self.obj1, player_check=True), self.player2)


class TestCmdLink(CollabTest, CollabCommandTestMixin):
    """
    Verify linking works sanely.
    """

    def test_can_link(self):
        """
        Make sure that a user can link an exit they own to a room they own.
        """
        set_owner(self.char2, self.room1)
        set_owner(self.char2, self.room2)
        set_owner(self.char2, self.exit)
        self.exit.destination = None
        self.call(CmdLink(), '%s=#%s' % (self.exit.name, self.room2.id), caller=self.char2)
        self.assertEqual(self.exit.destination, self.room2)

    def test_no_link_to_unowned(self):
        """
        Make sure that a user cannot link to a place they do not own.
        """
        set_owner(self.char2, self.room1)
        set_owner(self.char2, self.exit)
        self.exit.destination = None
        self.call(CmdLink(), '%s=#%s' % (self.exit.name, self.room2.id), caller=self.char2)
        self.assertFalse(self.exit.destination)

    def test_no_link_unowned_exit(self):
        """
        Make sure that a user cannot link up an exit they do not own.
        """
        set_owner(self.char2, self.room1)
        set_owner(self.char2, self.room2)
        self.exit.destination = None
        self.call(CmdLink(), '%s=#%s' % (self.exit.name, self.room2.id), caller=self.char2)
        self.assertFalse(self.exit.destination)
