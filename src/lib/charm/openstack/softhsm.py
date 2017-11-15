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

import json
import os
import os.path
import shutil
import subprocess

import charmhelpers.core.hookenv as hookenv
import charmhelpers.core.host as ch_core_host

import charms_openstack.adapters
import charms_openstack.charm


SOFTHSM2_UTIL_CMD = "/usr/bin/softhsm2-util"
TOKEN_STORE = "/var/lib/softhsm/tokens/"
SOFTHSM2_CONF = "/etc/softhsm/softhsm2.conf"
SOFTHSM2_LIB_PATH = "/usr/lib/x86_64-linux-gnu/softhsm/libsofthsm2.so"
PIN_LENGTH = 32
BARBICAN_TOKEN_LABEL = "barbican_token"
STORED_PINS_FILE = "/var/lib/softhsm/stored_pins.txt"


def install():
    """Use the singleton from the BarbicanSoftHSMCharm to install the packages
    on the unit
    """
    BarbicanSoftHSMCharm.singleton.install()


def on_hsm_connected(hsm):
    """When SoftHSM connects to Barbican, configure Barbican with the
    information necessary to configure the plugin.

    :param hsm: the hsm relation object
    """
    BarbicanSoftHSMCharm.singleton.on_hsm_connected(hsm)


def assess_status():
    """Call the charm assess_status function"""
    BarbicanSoftHSMCharm.singleton.assess_status()


class BarbicanSoftHSMCharm(charms_openstack.charm.OpenStackCharm):

    service_name = 'barbican-softhsm'
    name = 'softhsm'
    release = 'mitaka'

    # Packages that the service needs installed
    packages = ['softhsm2']

    # Standard interface adapters class to use.
    adapters_class = charms_openstack.adapters.OpenStackRelationAdapters

    def install(self):
        """Perform the normal charm install, and then kick off setting up the
        barbican_token in the softhsm2 token store.
        """
        super(BarbicanSoftHSMCharm, self).install()
        # now add the barbican user to the softhsm group so that the
        # barbican-worker can access the softhsm2.conf file.
        ch_core_host.add_user_to_group('barbican', 'softhsm')
        self.setup_token_store()
        hookenv.status_set(
            'waiting', 'Charm installed and token store configured')

    def setup_token_store(self):
        """Set up the token store for barbican to use, create a pin and
        user_pin and store those details locally so that they can be used when
        Barbican connects.

        Performs as needed:

        softhsm2-util --init-token --free --label "barbican_token" --pin <pin>
                      --so-pin <so-pin>

        The <pin> and <so-pin> are generated randomly and saved to a
        configuration file.

        If the <pin> and <so-pin> configuration file don't exist, then the
        token directory is deleted and re-initialised.

        Thus if we are upgrading a charm, the charm checks to see if it has
        already been run on this host, and if so, doesn't re-initialise the
        token store, otherwise the token store is re-initialised.

        The configuration file for the softhsm2 library is also written.
        """
        # see if the <pin> and <so_pin> exist?
        pin, so_pin = read_pins_from_store()
        if pin is not None:
            # return as the token store is already set up
            return
        # see if the token directory exists - if so, delete it.
        if os.path.exists(TOKEN_STORE):
            if os.path.isdir(TOKEN_STORE):
                shutil.rmtree(TOKEN_STORE)
            else:
                os.remove(TOKEN_STORE)
        os.makedirs(TOKEN_STORE)
        # We need the token store to be 1777 so that whoever creates a token
        # can also gain access to it - the token will be created by the
        # barbican user.
        os.chmod(TOKEN_STORE, 0o1777)
        # now create the token store
        pin = ch_core_host.pwgen(PIN_LENGTH)
        so_pin = ch_core_host.pwgen(PIN_LENGTH)
        write_pins_to_store(pin, so_pin)
        cmd = [
            'sudo', '-u', 'barbican',
            SOFTHSM2_UTIL_CMD,
            '--init-token', '--free',
            '--label', BARBICAN_TOKEN_LABEL,
            '--pin', pin,
            '--so-pin', so_pin]
        subprocess.check_call(cmd)
        hookenv.log("Initialised token store.")

    def on_hsm_connected(self, hsm):
        """Called when the hsm interface becomes connected.  This means the
        plugin has connected to the principal Barbican charm.

        In order for the Barbican charm to use this plugin (softhsm2) the
        plugin needs to provide a PKCS#11 libary for barbican to access, a
        password to access the token and a slot_id for the token.

        This sets the plugin_data on the hsm relation for the Barbican charm to
        pick up.

        :param hsm: a BarbicanProvides instance for the relation.
        :raises RuntimeError: if the token_store can't be setup - which is
        FATAL.
        """
        hookenv.log("Setting plugin name to softhsm2", level=hookenv.DEBUG)
        hsm.set_name('softhsm2')
        pin, so_pin = read_pins_from_store()
        if pin is None:
            self.setup_token_store()
            pin, so_pin = read_pins_from_store()
            if pin is None:
                hookenv.status_set('error', "Couldn't set up the token store?")
                raise RuntimeError(
                    "BarbicanSoftHSMCharm.setup_token_store() failed?")
        slot_id = read_slot_id(BARBICAN_TOKEN_LABEL)
        if slot_id is None:
            raise RuntimeError("No {} slot in token store?"
                               .format(BARBICAN_TOKEN_LABEL))
        plugin_data = {
            "library_path": SOFTHSM2_LIB_PATH,
            "login": pin,
            "slot_id": slot_id
        }
        hsm.set_plugin_data(plugin_data)


def read_pins_from_store():
    """Read the pin and so_pin from the STORED_PINS_FILE file so that they can
    be retrieved later.

    The pins are stored in the file with 600 permissions, with the following
    JSON format:

    {
      'pin': <pin string>,
      'so_pin': <so_pin string>
    }

    :returns (pin, so_pin): the pins from the store or None, None
    """
    try:
        with open(STORED_PINS_FILE, 'r') as f:
            o = json.load(f)
        pin = o['pin']
        so_pin = o['so_pin']
        return pin, so_pin
    except Exception:
        return None, None


def write_pins_to_store(pin, so_pin):
    """Write the pin and so_pin to the STORED_PINS_FILE file so that they can
    be retrieved later.

    The pins are stored in the file with 600 permissions, with the following
    JSON format:

    {
      'pin': <pin string>,
      'so_pin': <so_pin string>
    }

    :param pin: string to store
    :param so_pin: string to store
    :raises OSError: If the file couldn't be written.
    :returns None:
    """
    try:
        with os.fdopen(os.open(STORED_PINS_FILE,
                               os.O_WRONLY | os.O_CREAT,
                               0o600), 'w') as f:
            json.dump({'pin': pin, 'so_pin': so_pin}, f)
    except OSError as e:
        hookenv.log("Couldn't write pins file: {}".format(str(e)))


def read_slot_id(label):
    """Read the slot id for the `label` slot.

    The format of the slot from 'softhsm2-util --show-slots' is:

    Available slots:
    Slot 0
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

    The function reads the text and then looks for the 'Label:' field, to
    recover the Slot number.

    :param label: string representing the slot to look for
    :returns: slot number as String.
    """
    cmd = [SOFTHSM2_UTIL_CMD, '--show-slots']
    results = subprocess.check_output(cmd)
    lines = results.decode().split("\n")
    slot = None
    for line in lines:
        if line.startswith("Slot "):
            slot = line[5:]
        if (line.find('Label:') >= 0 and
                line.find(label) >= 0 and
                slot is not None):
            return slot
    return None
