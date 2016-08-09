# Overview

This charm provides the SoftHSM2 HSM plugin to Barbican. **Note that this plugin DOES NOT WORK at present due to
[bug#1611393](https://bugs.launchpad.net/barbican/+bug/1611393).  It does, however, demonstrate how an HSM
plugin will work with Barbican.**

# Usage

barbican-softhsm is a subordinate charm and lives in the same unit as a barbican charm.

    juju deploy barbican
    juju deploy ... other services for barbican -- see barbican charm
    juju deploy barbican-softhsm
    juju add-relation barbican barbican-softhsm

# Bugs

Please report bugs on [Launchpad](https://bugs.launchpad.net/charm-barbican-softhsm/+filebug).

For general questions please refer to the OpenStack [Charm Guide](https://github.com/openstack/charm-guide).
