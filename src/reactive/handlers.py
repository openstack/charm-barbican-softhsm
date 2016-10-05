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

import charms.reactive as reactive

import charms_openstack.charm

import charm.openstack.softhsm as softhsm

# Use the charms.openstack defaults for common states and hooks
charms_openstack.charm.use_defaults(
    'config.changed',
    'update-status')


# use a synthetic state to ensure that it get it to be installed independent of
# the install hook.
@reactive.when_not('charm.installed')
def install_packages():
    softhsm.install()
    reactive.set_state('charm.installed')


@reactive.when('hsm.connected')
def hsm_connected(hsm):
    softhsm.on_hsm_connected(hsm)
    reactive.set_state('hsm.available')
    softhsm.assess_status()
