import charms.reactive as reactive
import charmhelpers.core.hookenv as hookenv

# This charm's library contains all of the handler code associated with
# congress
import charm.openstack.softhsm_plugin as softhsm_plugin


# use a synthetic state to ensure that it get it to be installed independent of
# the install hook.
@reactive.when_not('charm.installed')
def install_packages():
    softhsm_plugin.install()
    reactive.set_state('charm.installed')

@reactive.when('hsm.connected')
def hsm_connected(hsm):
    hookenv.log("Setting my name to softhsm")
    hsm.set_name('softhsm')
