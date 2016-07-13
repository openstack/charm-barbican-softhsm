# Barbican SoftHSM2 Plugin

Barbican is a REST API designed for the secure storage, provisioning and
management of secrets. It is aimed at being useful for all environments,
including large ephemeral Clouds. (see [Barbican
Charm](https://github.com/openstack/barbican) for details on Barbican)

The Barbican SoftHSM2 Plugin is EXPERIMENTAL and not for use in Production
Systems.  It is intended to provide a example on how to plug an HSM into
Barbican.

In particular, the SoftHSM2 plugin charm (as a subordinate) implements the
barbican-hsm interface which transfers the credentials to the Barbican
charm to be able to access the the HSM.

From [the GitHub page](https://github.com/opendnssec/SoftHSMv2):

OpenDNSSEC handles and stores its cryptographic keys via the PKCS#11 interface.
This interface specifies how to communicate with cryptographic devices such as
HSM:s (Hardware Security Modules) and smart cards. The purpose of these devices
is, among others, to generate cryptographic keys and sign information without
revealing private-key material to the outside world. They are often designed to
perform well on these specific tasks compared to ordinary processes in a normal
computer.

A potential problem with the use of the PKCS#11 interface is that it might
limit the wide spread use of OpenDNSSEC, since a potential user might not be
willing to invest in a new hardware device. To counter this effect, OpenDNSSEC
is providing a software implementation of a generic cryptographic device with a
PKCS#11 interface, the SoftHSM. SoftHSM is designed to meet the requirements of
OpenDNSSEC, but can also work together with other cryptographic products
because of the PKCS#11 interface.

If you have a technical question about this Charm, you can send an email to the
[OpenStack General mailing list](
http://lists.openstack.org/pipermail/openstack/) at
`openstack@lists.openstack.org` with the prefix `[barbican]` in the subject, or
ask in the `#openstack-charms` on Freenode..

To file a bug, use our bug tracker on [Launchpad](
http://bugs.launchpad.net/charms/+source/barbican/).


## How it works

Barbican communicates with HSM devices via a local (to Barbican) PKCS11
library.  Thus an HSM plugin needs to be local to the unit that a Barbican is
installed on, and so a plugin charm is subordinate to the Barbican charm.  A
plugin provides the barbican-hsm interface that provides sufficient
details to the Barbican charm to be able to configure barbican to access the
HSM's PKCS11 libary.

The barbican-hsm interface transfers `login`, `slot_id` and
`library_path` parameters to the Barbican charm, which uses them to configure
Barbican to access the PKCS11 compliant library of the HSM.

Barbican assumes that the slot & token are configured and that with the `login`
(or pin) that Barbican will be able to access the token to store keys, etc. In
this case of softhsm2, this charm initialises the token, creates the login and
provides those details across the relation.
