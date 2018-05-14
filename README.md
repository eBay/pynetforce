# Netforce

Netforce is a network infrastructure automation service for managing and
configuring network devices.

* Since it is using [OpenStack Neutron's] framework, it supports
  [OpenStack Keystone] authentication along with noauth.
* It can also be used as a plugin to Neutron leveraging Neutron's
  [routed networks].

----

# Use cases

* Can be pluged in to Neutron to provide on-demand subnet cap-adds 
  for [OpenStack] VMs and [Kubernetes] Pods running on top of OpenStack.
* Can also be used by [OpenStack Ironic] for provisioning on-demand BMs in
  [VRF] network to place a BM in respective VRF(vlan) to access mode from
  trunk via Neutron update-port operation for different VPCs using
  [routed networks].
* Can be operated individually by a network engineer to configure devices in
  different data centers as a global api service.


## To start as a developer:

```
$ git clone https://github.com/eBay/pynetforce.git
$ virtualenv ~/Downloads/netforce-dev
$ source ~/Downloads/netforce-dev/bin/activate
$ cd netforce
$ tox
```


## Features supported for a network switch:

* Port Enable
* Port Disable
* Port-vlan flip
    * Validation support for VLAN change from trunk to access and vice versa
     for a physical port.
* Create subnet on vlan interface
    * Validation support for BGP configured bubbles using flat/non-flat
     networks.
* Port labelling

## Vendor OS supported:

* Juniper: junos
* Cisco: nxos and ios
* Arista: eos


## TODO:

- [NAPALM integration]: Increase the device driver coverage by adding more
   device driver functions.

- [OpenConfig Integration]: Integrate with OpenConfig to program openconfig
   enabled devices using yang models as Netforce gives a unified api layer.

[Kubernetes]: https://kubernetes.io
[OpenStack]: https://www.openstack.org
[OpenStack Neutron's]: https://wiki.openstack.org/wiki/Neutron
[OpenStack Keystone]: https://wiki.openstack.org/wiki/Keystone
[routed networks]: https://specs.openstack.org/openstack/neutron-specs/specs/newton/routed-networks.html
[VRF]: https://en.wikipedia.org/wiki/Virtual_routing_and_forwarding
[OpenStack Ironic]: https://wiki.openstack.org/wiki/Ironic
[NAPALM integration]: https://github.com/napalm-automation
[OpenConfig Integration]: http://www.openconfig.net/
[Apache License]: http://www.apache.org/licenses/LICENSE-2.0.txt

## Note:

* Not all Vendor device OS versions have been tested.

* e.g. new versions of eos supports json parsing and old versions don't.
  Hence, device drivers are written to support both old and new versions.

## Useful links:

- [Netforce_slideshare]: Presentations for the quick overview of what Netforce can do.

- [Netforce_walkthrough]: Detailed walkthrough of the presentation above.

[Netforce_slideshare]: https://www.slideshare.net/aliasgarginwala/netforce-76964211
[Netforce_walkthrough]: https://www.youtube.com/watch?v=KX0LvsIXsU4 

## License

Licensed under the Apache License, Version 2.0 (the "License").
See [Apache License]
