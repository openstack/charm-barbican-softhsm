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

import reactive.handlers as handlers

import charms_openstack.test_utils as test_utils


class TestRegisteredHooks(test_utils.TestRegisteredHooks):

    def test_hooks(self):
        defaults = [
            'config.changed',
            'update-status']
        hook_set = {
            'when': {
                'hsm_connected': ('hsm.connected', ),
            },
            'when_not': {
                'install_packages': ('charm.installed', ),
            }
        }
        # test that the hooks were registered via the
        # reactive.barbican_handlers
        self.registered_hooks_test_helper(handlers, hook_set, defaults)


class TestBarbicanHandlers(test_utils.PatchHelper):

    def test_install_packages(self):
        self.patch_object(handlers.softhsm, 'install')
        self.patch_object(handlers.reactive, 'set_state')
        handlers.install_packages()
        self.install.assert_called_once_with()
        self.set_state.assert_called_once_with('charm.installed')

    def test_hsm_connected(self):
        self.patch_object(handlers.softhsm, 'on_hsm_connected')
        self.patch_object(handlers.reactive, 'set_state')
        self.patch_object(handlers.softhsm, 'assess_status')
        handlers.hsm_connected('hsm-thing')
        self.on_hsm_connected.assert_called_once_with('hsm-thing')
        self.set_state.assert_called_once_with('hsm.available')
        self.assess_status.assert_called_once_with()
