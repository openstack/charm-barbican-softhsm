# Copyright 2016 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import print_function

import textwrap
import unittest

import mock

import charm.openstack.softhsm as softhsm


class Helper(unittest.TestCase):

    def setUp(self):
        self._patches = {}
        self._patches_start = {}
        # patch out the select_release to always return 'mitaka'
        # self.patch(softhsm.unitdata, 'kv')
        # _getter = mock.MagicMock()
        # _getter.get.return_value = softhsm.BarbicanSoftHSMCharm.release
        # self.kv.return_value = _getter

    def tearDown(self):
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch(self, obj, attr, return_value=None, **kwargs):
        mocked = mock.patch.object(obj, attr, **kwargs)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)


class TestSoftHSM(Helper):

    def test_install(self):
        self.patch(softhsm.BarbicanSoftHSMCharm.singleton, 'install')
        softhsm.install()
        self.install.assert_called_once_with()

    def test_on_hsm_connected(self):
        self.patch(softhsm.BarbicanSoftHSMCharm.singleton,
                   'on_hsm_connected')
        softhsm.on_hsm_connected('hsm-thing')
        self.on_hsm_connected.assert_called_once_with('hsm-thing')

    def test_read_pins_from_store(self):
        # test with no file (patch open so that it raises an error)
        mock_open = mock.MagicMock(return_value=mock.sentinel.file_handle)
        with mock.patch('builtins.open', mock_open):
            def raise_exception():
                raise Exception("Supposed to break")
            mock_open.side_effect = raise_exception
            pin, so_pin = softhsm.read_pins_from_store()
            self.assertEqual(pin, None)
            self.assertEqual(so_pin, None)
        # now provide the pin and so pin as a json object
        d = '{"pin": "1234", "so_pin": "5678"}'
        with mock.patch('builtins.open',
                        mock.mock_open(read_data=d),
                        create=True):
            pin, so_pin = softhsm.read_pins_from_store()
            self.assertEqual(pin, '1234')
            self.assertEqual(so_pin, '5678')

    def test_write_pins_to_store(self):
        f = mock.MagicMock()
        self.patch(softhsm.os, 'fdopen', return_value=f)
        self.patch(softhsm.os, 'open', return_value='opener')
        self.patch(softhsm.json, 'dump')
        softhsm.write_pins_to_store('1234', '5678')
        self.open.assert_called_once_with(
            softhsm.STORED_PINS_FILE,
            softhsm.os.O_WRONLY | softhsm.os.O_CREAT,
            0o600)
        self.fdopen.assert_called_once_with('opener', 'w')
        self.dump.assert_called_once_with(
            {'pin': '1234', 'so_pin': '5678'}, f.__enter__())

    def test_read_slot_id(self):
        result = textwrap.dedent("""
            Slot 5
                Slot info:
                Description: SoftHSM slot 0
                Manufacturer ID:  SoftHSM project
                Hardware version: 2.0
                Firmware version: 2.0
                Token present:    yes
            Token info:
                Manufacturer ID:  SoftHSM project
                Model:            SoftHSM v2
                Hardware version: 2.0
                Firmware version: 2.0
                Serial number:    02ae3171143498e7
                Initialized:      yes
                User PIN init.:   yes
                Label:            barbican_token
        """)
        self.patch(softhsm.subprocess, 'check_output',
                   return_value=result.encode())
        self.assertEqual(softhsm.read_slot_id('barbican_token'), '5')
        self.check_output.assert_called_once_with(
            [softhsm.SOFTHSM2_UTIL_CMD, '--show-slots'])
        self.assertEqual(softhsm.read_slot_id('not_found'), None)


class TestBarbicanSoftHSMCharm(Helper):

    def test_install(self):
        self.patch(softhsm.charms_openstack.charm.OpenStackCharm,
                   'install')
        self.patch(softhsm.ch_core_host, 'add_user_to_group')
        c = softhsm.BarbicanSoftHSMCharm()
        self.patch(c, 'setup_token_store')
        self.patch(softhsm.hookenv, 'status_set')
        c.install()
        self.install.assert_called_once_with()
        self.add_user_to_group.assert_called_once_with('barbican', 'softhsm')
        self.setup_token_store.assert_called_once_with()
        self.status_set.assert_called_once_with(
            'waiting', 'Charm installed and token store configured')

    def test_setup_token_store(self):
        self.patch(softhsm, 'read_pins_from_store')
        self.patch(softhsm.os.path, 'exists')
        self.patch(softhsm.os.path, 'isdir')
        self.patch(softhsm.shutil, 'rmtree')
        self.patch(softhsm.os, 'remove')
        self.patch(softhsm.os, 'makedirs')
        self.patch(softhsm.os, 'chmod')
        self.patch(softhsm.ch_core_host, 'pwgen')
        self.patch(softhsm, 'write_pins_to_store')
        self.patch(softhsm.subprocess, 'check_call')
        self.patch(softhsm.hookenv, 'log')
        # first, pretend that the token store is already setup.
        self.read_pins_from_store.return_value = ('1234', '5678', )
        c = softhsm.BarbicanSoftHSMCharm()
        c.setup_token_store()
        self.assertEqual(self.log.call_count, 0)
        # now pretend the token store isn't set up
        self.read_pins_from_store.return_value = None, None
        # assume that the token store exists and is a dir first:
        self.exists.return_value = True
        self.isdir.return_value = True
        # return two values, for each of the two pwgen calls.
        self.pwgen.side_effect = ['abcd', 'efgh']
        c.setup_token_store()
        # now validate it did everything we expected.
        self.exists.assert_called_once_with(softhsm.TOKEN_STORE)
        self.isdir.assert_called_once_with(softhsm.TOKEN_STORE)
        self.rmtree.assert_called_once_with(softhsm.TOKEN_STORE)
        self.makedirs.assert_called_once_with(softhsm.TOKEN_STORE)
        self.chmod.assert_called_once_with(softhsm.TOKEN_STORE, 0o1777)
        self.assertEqual(self.pwgen.call_count, 2)
        self.write_pins_to_store.assert_called_once_with('abcd', 'efgh')
        self.check_call.called_once_with([
            'sudo', '-u', 'barbican',
            softhsm.SOFTHSM2_UTIL_CMD,
            '--init-token', '--free',
            '--label', softhsm.BARBICAN_TOKEN_LABEL,
            '--pin', 'abcd',
            '--so-pin', 'efgh'])
        self.log.assert_called_once_with("Initialised token store.")

    def test_on_hsm_connected(self):
        hsm = mock.MagicMock()
        self.patch(softhsm, 'read_pins_from_store')
        self.patch(softhsm, 'read_slot_id')
        self.patch(softhsm.hookenv, 'status_set')
        self.patch(softhsm.hookenv, 'log')
        c = softhsm.BarbicanSoftHSMCharm()
        self.patch(c, 'setup_token_store')
        # simulate not being able to set up the token store
        self.read_pins_from_store.return_value = None, None
        with self.assertRaises(RuntimeError):
            c.on_hsm_connected(hsm)
            self.status_set.assert_called_once_with(
                'error', "Couldn't set up the token store?")
            self.setup_token_store.assert_called_once_with()
            self.log.assert_called_once_with(
                "Setting plugin name to softhsm2",
                level=softhsm.hookenv.DEBUG)
        # now assume that the pins can be read, but no slot is set up.
        self.read_pins_from_store.return_value = '1234', '5678'
        self.read_slot_id.return_value = None
        with self.assertRaises(RuntimeError):
            c.on_hsm_connected(hsm)
        # now assume that the slot is also set up.
        self.read_slot_id.return_value = '10'
        c.on_hsm_connected(hsm)
        hsm.set_plugin_data.assert_called_once_with({
            "library_path": softhsm.SOFTHSM2_LIB_PATH,
            "login": '1234',
            "slot_id": '10'
        })
        # finally test corner case where token store isn't set up already
        self.read_pins_from_store.side_effect = [
            [None, None], ['abcd', 'efgh']]
        hsm.reset_mock()
        self.setup_token_store.reset_mock()
        c.on_hsm_connected(hsm)
        self.setup_token_store.assert_called_once_with()
        hsm.set_plugin_data.assert_called_once_with({
            "library_path": softhsm.SOFTHSM2_LIB_PATH,
            "login": 'abcd',
            "slot_id": '10'
        })

