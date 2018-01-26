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


from netforce.api.v2 import attributes as netforce_attr
from netforce.common import netforce_exceptions as netforce_exc
from netforce.plugins.common import netforce_constants

from neutron.api import api_common
from neutron.api import extensions
from neutron.api.v2 import attributes as attr
from neutron.api.v2 import base
from neutron.api.v2 import resource as resource_creator
from neutron import manager
from neutron import wsgi
import urlparse

# Resource names and their collections
SUBNETS = 'subnets'
SUBNET = 'subnet'

PORTS = 'ports'
PORT = 'port'

DEVICES = 'devices'
DEVICE = 'device'

DEVICE_TYPES = 'devicetypes'
DEVICE_TYPE = 'devicetype'

VLANS = 'vlans'
VLAN = 'vlan'

BRIDGEGROUPS = 'bridgegroups'
BRIDGEGROUP = 'bridgegroup'

VPCS = 'vpcs'
VPC = 'vpc'

VLANPORTASSOCIATIONS = 'vlanportassociations'
VLANPORTASSOCIATION = 'vlanportassociation'

BUBBLES = 'bubbles'
BUBBLE = 'bubble'

VRFS = 'vrfs'
VRF = 'vrf'

# Defining resource payloads
RESOURCE_ATTRIBUTE_MAP = {
    SUBNETS: {
        'name': {
            'allow_post': True,
            'default': None,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'id': {
            'allow_post': False,
            'allow_put': True,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'cidr': {
            'allow_post': True,
            'default': None,
            'validate': {'type:subnet': None},
            'is_visible': True
        },
        'gateway_ip': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:ip_address_or_none': None},
            'is_visible': True
        },
        'broadcast_ip': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:ip_address_or_none': None},
            'is_visible': True
        },
        'netmask': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:ip_address_or_none': None},
            'is_visible': True
        },
        'vlan_id': {
            'allow_put': False,
            'allow_post': True,
            'validate': {'type:uuid': None},
            'is_visible': True
        },
        'tenant_id': {
             'allow_post': True,
             'allow_put': False,
             'validate': {'type:string': None},
             'required_by_policy': True,
             'is_visible': True
        },
        'start_ip': {
            'allow_post': False,
            'allow_put': False,
            'default': {},
            'validate': {'type:string': None},
            'is_visible': True
        },
        'end_ip': {
            'allow_post': False,
            'allow_put': False,
            'default': {},
            'validate': {'type:string': None},
            'is_visible': True
        },
        'reserve_ip_count': {
            'allow_post': True,
            'allow_put': False,
            'default': 0,
            'is_visible': True,
            'convert_to': attr.convert_to_int,
        }
    },

    PORTS: {
        'name': {
            'allow_post': True,
            'allow_put': False,
            'default': None,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'id': {
            'allow_post': False,
            'allow_put': True,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'admin_status': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:values': ['ACTIVE', 'SUSPENDED']},
            'is_visible': True
        },
        'label': {
            'allow_post': False,
            'allow_put': True,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'asset_id': {
            'allow_post': True,
            'allow_put': True,
            'default': None,
            'is_visible': True
        },
        'switch_port_mode': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:values': ['trunk', 'native', 'access', 'none']},
            'is_visible': True
        },
        'description': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'device_id': {
            'allow_put': False,
            'allow_post': True,
            'validate': {'type:uuid': None},
            'is_visible': True
        },
        'vlans': {
            'allow_post': False,
            'allow_put': True,
            'convert_to': attr.convert_to_list,
            'is_visible': True
        },
        'tenant_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        },
        'mac_address': {
            'allow_post': False,
            'allow_put': True,
            'validate': {'type:mac_address_or_none': None},
            'is_visible': True
        },
        'ticket': {
            'allow_post': False,
            'allow_put': False,
            'default': None,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'device_data': {
            'allow_post': False,
            'allow_put': False,
            'default': None,
            'validate': {'type:dict': None},
            'is_visible': True
        }
    },

    DEVICES: {
        'name': {
            'allow_post': True,
            'default': None,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'id': {
            'allow_post': False,
            'allow_put': True,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'type': {
            'allow_put': True,
            'allow_post': True,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'management_ip': {
            'allow_put': True,
            'allow_post': True,
            'validate': {'type:ip_address_or_none': None},
            'is_visible': True
        },
        'username': {
            'allow_put': True,
            'allow_post': True,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'password': {
            'allow_put': True,
            'allow_post': True,
            'validate': {'type:string': None},
            'is_visible': False
        },
        'description': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'bridge_group_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:uuid_or_none': None},
            'is_visible': True
        },
        'ports': {
            'allow_put': False,
            'allow_post': False,
            'convert_to': attr.convert_to_list,
            'is_visible': True
        },
        'os_type': {
            'allow_put': False,
            'allow_post': True,
            'validate': {'type:values': ['eos', 'junos', 'nxos', 'ios']},
            'is_visible': True
        },
        'tenant_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        },
        'bubble_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        }
    },

    DEVICE_TYPES: {
        'name': {
            'allow_post': True,
            'allow_put': False,
            'default': None,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'id': {
            'allow_post': False,
            'allow_put': True,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'type': {
            'allow_put': True,
            'allow_post': True,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'tenant_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        },
        'description': {
            'allow_post': False,
            'allow_put': True,
            'validate': {'type:string': None},
            'is_visible': True
        }
    },

    VLANS: {
        'name': {
            'allow_post': True,
            'allow_put': False,
            'default': None,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'id': {
            'allow_post': False,
            'allow_put': True,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'tag': {
            'allow_post': True,
            'allow_put': True,
            'convert_to': netforce_attr.convert_to_int_if_not_none,
            'is_visible': True,
            'default': None,
        },
        'bridge_group_name': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'bridge_group_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True
        },
        'vpc_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True
        },
        'admin_status': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:values': ['ACTIVE', 'SUSPENDED']},
            'is_visible': True
        },
        'vpc_name': {
            'allow_post': True,
            'allow_put': False,
            'is_visible': True
        },
        'tenant_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        }
    },
    BRIDGEGROUPS: {
        'name': {
            'allow_post': True,
            'allow_put': False,
            'default': None,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'id': {
            'allow_post': False,
            'allow_put': True,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'description': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'tenant_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        }
    },
    VPCS: {
        'name': {
            'allow_post': True,
            'allow_put': False,
            'default': None,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'id': {
            'allow_post': False,
            'allow_put': True,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'description': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'label': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'tenant_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        }
    },
    BUBBLES: {
        'name': {
            'allow_post': True,
            'allow_put': True,
            'default': None,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'tenant_id': {
             'allow_post': True,
             'allow_put': False,
             'validate': {'type:string': None},
             'required_by_policy': True,
             'is_visible': True
        }
    },
    VRFS: {
        'name': {
            'allow_post': True,
            'allow_put': True,
            'default': None,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'tenant_id': {
             'allow_post': True,
             'allow_put': False,
             'validate': {'type:string': None},
             'required_by_policy': True,
             'is_visible': True
        },
        'bubble_id': {
             'allow_post': True,
             'allow_put': False,
             'validate': {'type:string': None},
             'required_by_policy': True,
             'is_visible': True
        },
        'vpc_id': {
             'allow_post': True,
             'allow_put': False,
             'validate': {'type:string': None},
             'required_by_policy': True,
             'is_visible': True
        },
        'description': {
             'allow_post': True,
             'allow_put': False,
             'validate': {'type:string': None},
             'required_by_policy': True,
             'is_visible': True
        }
    }
}


class NetForceController(base.Controller, wsgi.Controller):

    def __init__(self, resource, collection, res_attr_map, plugin=None):
        if not plugin:
            self._plugin = manager.NeutronManager.get_plugin()
        else:
            self._plugin = plugin
        super(NetForceController, self).__init__(
            self._plugin, collection, resource, res_attr_map)

    def create(self, request, **kwargs):
        # TODO(aginwala): Make sure to enforce policy enforcement in future.
        body = kwargs.get('body')
        kwargs.pop('body', None)
        url = request.url
        params = urlparse.parse_qs(urlparse.urlparse(url).query,
                                   keep_blank_values=True)
        if params:
            if 'skip_device' in params:
                kwargs.update({"skip_device": True})
            # Note: patch_primary_junos_subnets is for temporary to patch
            # all junos TORs:
            if 'patch_primary_junos_subnets' in params:
                kwargs.update({"patch_primary_junos_subnets": True})
            if 'one_subnet_only' in params:
                kwargs.update(
                    {"one_subnet_only": params['one_subnet_only'][0]})
        # Creates a new instance of the requested entity.
        # Over-riding upstream neutron stable/juno base.py
        body = base.Controller.prepare_request_body(
            request.context, body, True, self._resource, self._attr_info,
            allow_bulk=self._allow_bulk)
        action = self._plugin_handlers[self.CREATE]
        obj_creator = getattr(self._plugin, action)
        kwargs.update({self._resource: body})
        obj = obj_creator(request.context, **kwargs)
        return {self._resource: self._view(request.context,
                                           obj)}

    def show(self, request, **kwargs):

        """Returns detailed information about the requested entity."""
        dsid = kwargs.pop('id', None)

        field_list, added_fields = self._do_field_list(
            api_common.list_args(request, "fields"))
        return {self._resource: self._view(request.context,
                                           self._item(request, dsid,
                                                      do_authz=False,
                                                      field_list=field_list,
                                                      parent_id=None),
                                           fields_to_strip=added_fields)}

    def update(self, request, **kwargs):
        # TODO(aginwala): Make sure to enforce policy enforcement in future.
        dsid = kwargs.pop('id', None)
        body = kwargs.pop('body', None)
        url = request.url
        params = urlparse.parse_qs(urlparse.urlparse(url).query,
                                   keep_blank_values=True)
        if params:
            if 'skip_mac_check' in params:
                kwargs.update({"check_mac": False})
            if 'skip_cms_check' in params:
                kwargs.update({"check_cms": False})
        try:
            payload = body.copy()
        except AttributeError:
            msg = "Invalid format: %s" % request.body
            raise netforce_exc.BadRequest(resource='body', msg=msg)
        payload['id'] = dsid
        body = base.Controller.prepare_request_body(
            request.context, body, False, self._resource, self._attr_info,
            allow_bulk=self._allow_bulk)
        action = self._plugin_handlers[self.UPDATE]
        obj_updater = getattr(self._plugin, action)
        kwargs.update({self._resource: body})
        obj = obj_updater(request.context, dsid, **kwargs)
        result = {self._resource: self._view(request.context, obj)}
        return result

    def delete(self, request, **kwargs):
        """Deletes the specified entity."""
        # TODO(aginwala): Make sure to enforce policy enforcement in future.
        dsid = kwargs.pop('id', None)
        action = self._plugin_handlers[self.DELETE]
        obj_deleter = getattr(self._plugin, action)
        obj_deleter(request.context, dsid, **kwargs)

    def index(self, request, **kwargs):
        """Returns a list of the requested entity."""
        return self._items(request, True, None)


def create_port_resource():
    controller = resource_creator.\
        Resource(NetForceController(PORT, PORTS,
                                    RESOURCE_ATTRIBUTE_MAP[PORTS]),
                 faults=base.FAULT_MAP)
    resource = extensions.\
        ResourceExtension(PORTS,
                          controller,
                          path_prefix=netforce_constants.
                          COMMON_PREFIXES[netforce_constants.NETFORCE],
                          attr_map=RESOURCE_ATTRIBUTE_MAP.get(PORTS))
    return resource


def create_device_resource():
    controller = resource_creator.\
        Resource(NetForceController(DEVICE, DEVICES,
                                    RESOURCE_ATTRIBUTE_MAP[DEVICES]),
                 faults=base.FAULT_MAP)
    resource = extensions.\
        ResourceExtension(DEVICES,
                          controller,
                          path_prefix=netforce_constants.COMMON_PREFIXES[
                                                netforce_constants.NETFORCE],
                          attr_map=RESOURCE_ATTRIBUTE_MAP.get(DEVICES))
    return resource


def create_device_type_resource():
    controller = resource_creator.\
        Resource(NetForceController(DEVICE_TYPE, DEVICE_TYPES,
                                    RESOURCE_ATTRIBUTE_MAP[DEVICE_TYPES]),
                 faults=base.FAULT_MAP)
    resource = extensions.\
        ResourceExtension(DEVICE_TYPES,
                          controller,
                          path_prefix=netforce_constants.COMMON_PREFIXES[
                                                netforce_constants.NETFORCE],
                          attr_map=RESOURCE_ATTRIBUTE_MAP.get(DEVICE_TYPES))
    return resource


def create_vlan_resource():
    controller = resource_creator.\
        Resource(NetForceController(VLAN, VLANS,
                                    RESOURCE_ATTRIBUTE_MAP[VLANS]),
                 faults=base.FAULT_MAP)
    resource = extensions.\
        ResourceExtension(VLANS,
                          controller,
                          path_prefix=netforce_constants.
                          COMMON_PREFIXES[netforce_constants.NETFORCE],
                          attr_map=RESOURCE_ATTRIBUTE_MAP.get(VLANS))
    return resource


def create_vpc_resource():
    controller = resource_creator.\
        Resource(NetForceController(VPC, VPCS,
                                    RESOURCE_ATTRIBUTE_MAP[VPCS]),
                 faults=base.FAULT_MAP)
    resource = extensions.\
        ResourceExtension(VPCS,
                          controller,
                          path_prefix=netforce_constants.
                          COMMON_PREFIXES[netforce_constants.NETFORCE],
                          attr_map=RESOURCE_ATTRIBUTE_MAP.get(VPCS))
    return resource


def create_bg_resource():
    controller = resource_creator.\
        Resource(NetForceController(BRIDGEGROUP, BRIDGEGROUPS,
                                    RESOURCE_ATTRIBUTE_MAP[BRIDGEGROUPS]),
                 faults=base.FAULT_MAP)
    resource = extensions\
        .ResourceExtension(BRIDGEGROUPS,
                           controller,
                           path_prefix=netforce_constants.
                           COMMON_PREFIXES[netforce_constants.NETFORCE],
                           attr_map=RESOURCE_ATTRIBUTE_MAP.get(BRIDGEGROUPS))
    return resource


def create_vlanportassociation_resource():
    controller = resource_creator.\
        Resource(NetForceController(VLANPORTASSOCIATION,
                                    VLANPORTASSOCIATIONS,
                                    RESOURCE_ATTRIBUTE_MAP[
                                                         VLANPORTASSOCIATIONS]
                                    ),
                 faults=base.FAULT_MAP)
    resource = extensions.\
        ResourceExtension(VLANPORTASSOCIATIONS,
                          controller,
                          path_prefix=netforce_constants.
                          COMMON_PREFIXES[netforce_constants.NETFORCE],
                          attr_map=RESOURCE_ATTRIBUTE_MAP
                          .get(VLANPORTASSOCIATIONS))
    return resource


def create_subnet_resource():
    controller = resource_creator. \
        Resource(NetForceController(SUBNET, SUBNETS,
                                    RESOURCE_ATTRIBUTE_MAP[SUBNETS]),
                 faults=base.FAULT_MAP)
    resource = extensions. \
        ResourceExtension(SUBNETS, controller, path_prefix=netforce_constants.
                          COMMON_PREFIXES[netforce_constants.NETFORCE],
                          attr_map=RESOURCE_ATTRIBUTE_MAP.get(SUBNETS))
    return resource


def create_bubble_resource():
    controller = resource_creator. \
        Resource(NetForceController(BUBBLE, BUBBLES,
                                    RESOURCE_ATTRIBUTE_MAP[BUBBLES]),
                 faults=base.FAULT_MAP)
    resource = extensions. \
        ResourceExtension(BUBBLES, controller, path_prefix=netforce_constants.
                          COMMON_PREFIXES[netforce_constants.NETFORCE],
                          attr_map=RESOURCE_ATTRIBUTE_MAP.get(BUBBLES))
    return resource


def create_vrf_resource():
    controller = resource_creator. \
        Resource(NetForceController(VRF, VRFS,
                                    RESOURCE_ATTRIBUTE_MAP[VRFS]),
                 faults=base.FAULT_MAP)
    resource = extensions. \
        ResourceExtension(VRFS, controller, path_prefix=netforce_constants.
                          COMMON_PREFIXES[netforce_constants.NETFORCE],
                          attr_map=RESOURCE_ATTRIBUTE_MAP.get(VRFS))
    return resource


class Netforceext(extensions.ExtensionDescriptor):
    """Netforce extension."""

    @classmethod
    def get_name(cls):
        return "netforce"

    @classmethod
    def get_alias(cls):
        return "netforce"

    @classmethod
    def get_description(cls):
        return "An extension for netforce"

    @classmethod
    def get_namespace(cls):
        # FIXME(lhuang8): netforce namespace?
        return "http://docs.openstack.org/netforce/v2.0"

    @classmethod
    def get_updated(cls):
        return "2016-08-17T10:00:00-00:00"

    @classmethod
    def get_resources(cls):
        resources = []
        resources.append(create_port_resource())
        resources.append(create_device_resource())
        resources.append(create_device_type_resource())
        resources.append(create_vlan_resource())
        resources.append(create_bg_resource())
        resources.append(create_vpc_resource())
        resources.append(create_subnet_resource())
        resources.append(create_bubble_resource())
        resources.append(create_vrf_resource())
        return resources
