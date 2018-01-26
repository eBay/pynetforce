# Copyright 2018 eBay Inc.
# Copyright 2012 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


import abc
import netforce.common.netforce_constants as constants
from neutron.services import service_base
import six


@six.add_metaclass(abc.ABCMeta)
class NetForceServicePlugin(service_base.ServicePluginBase):

    def get_plugin_type(self):
        return constants.NETFORCE_PLUGIN

    def get_plugin_name(self):
        return constants.NETFORCE_PLUGIN

    def get_plugin_description(self):
        return constants.NETFORCE_DESCRIPTION

    @abc.abstractmethod
    def create_vpc(self, context, vpc):
        pass

    @abc.abstractmethod
    def get_vpc(self, context, vpc_id, fields=None):
        pass

    @abc.abstractmethod
    def delete_vpc(self, context, vpc_id):
        pass

    @abc.abstractmethod
    def update_vpc(self, context, vpc_id, vpc):
        pass

    @abc.abstractmethod
    def get_vpcs(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def create_bridgegroup(self, context, bridgegroup):
        pass

    @abc.abstractmethod
    def get_bridgegroup(self, context, bridgegroup_id, fields=None):
        pass

    @abc.abstractmethod
    def delete_bridgegroup(self, context, bridgegroup_id):
        pass

    @abc.abstractmethod
    def get_bridgegroups(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def update_bridgegroup(self, context, bridgegroup_id, bridgegroup):
        pass

    @abc.abstractmethod
    def create_vlan(self, context, vlan):
        pass

    @abc.abstractmethod
    def get_vlan(self, context, vlan_id, fields=None):
        pass

    @abc.abstractmethod
    def delete_vlan(self, context, vlan_id):
        pass

    @abc.abstractmethod
    def update_vlan(self, context, vlan_id, vlan):
        pass

    @abc.abstractmethod
    def create_vlanportassociation(self, context, vlan_id, port_id, is_native):
        pass

    @abc.abstractmethod
    def get_vlanportassociation(self, context, vlanportassociation_id,
                                fields=None):
        pass

    @abc.abstractmethod
    def delete_vlanportassociation(self, context, vlanportassociation_id):
        pass

    @abc.abstractmethod
    def update_vlanportassociation(self, context, vlanportassociation_id,
                                   vlanportassociation):
        pass

    @abc.abstractmethod
    def get_vlans(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def create_device(self, context, device):
        pass

    @abc.abstractmethod
    def update_device(self, context, device_id, device):
        pass

    @abc.abstractmethod
    def delete_device(self, context, device_id):
        pass

    @abc.abstractmethod
    def get_device(self, context, device_id, fields=None):
        pass

    @abc.abstractmethod
    def delete_devicetype(self, context, device_type_id):
        pass

    @abc.abstractmethod
    def create_devicetype(self, context, device_type):
        pass

    @abc.abstractmethod
    def update_devicetype(self, context, device_type_id, device_type):
        pass

    @abc.abstractmethod
    def get_devicetype(self, context, device_type_id, fields=None):
        pass

    @abc.abstractmethod
    def get_devices(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def create_port(self, context, port):
        pass

    @abc.abstractmethod
    def update_port(self, context, port_id, port):
        pass

    @abc.abstractmethod
    def get_port(self, context, port_id, fields=None):
        pass

    @abc.abstractmethod
    def get_ports(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def delete_port(self, context, port_id):
        pass

    @abc.abstractmethod
    def create_subnet(self, context, subnet):
        pass

    @abc.abstractmethod
    def get_subnet(self, context, subnet_id, fields=None):
        pass

    @abc.abstractmethod
    def get_subnets(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_subnet_by_vlan_id(self, context, vlan_id):
        pass

    @abc.abstractmethod
    def get_subnet_by_cidr(self, context, vlan_id):
        pass

    @abc.abstractmethod
    def update_subnet(self, context, subnet_id, subnet):
        pass

    @abc.abstractmethod
    def delete_subnet(self, context, subnet_id):
        pass

    @abc.abstractmethod
    def create_bubble(self, context, bubble):
        pass

    @abc.abstractmethod
    def get_bubble(self, context, bubble_id, fields=None):
        pass

    @abc.abstractmethod
    def get_bubbles(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_bubble_by_name(self, context, bubble_name):
        pass

    @abc.abstractmethod
    def update_bubble(self, context, bubble_id, bubble):
        pass

    @abc.abstractmethod
    def delete_bubble(self, context, bubble_id):
        pass
