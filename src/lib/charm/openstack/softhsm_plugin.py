import charms_openstack.charm
import charms_openstack.adapters


def install():
    """Use the singleton from the BarbicanSoftHSMCharm to install the packages
    on the unit
    """
    BarbicanSoftHSMCharm.singleton.install()


class BarbicanSoftHSMCharm(charms_openstack.charm.OpenStackCharm):

    service_name = 'barbican-softhsm'
    name = 'softhsm'
    release = 'mitaka'

    # Packages that the service needs installed
    packages = []

    # Init services the charm manages
    services = []

    # Standard interface adapters class to use.
    adapters_class = charms_openstack.adapters.OpenStackRelationAdapters

    # Ports that need exposing
    default_service = ''
    api_ports = {}

    # Database sync command (if needed)
    sync_cmd = []

    # The restart map defines which services should be restarted when a given
    # file changes
    restart_map = {
    }
