# Copyright 2018 eBay Inc.
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

# This class leverages Juniper python library:
# https://github.com/Juniper/py-junos-eznc

from jnpr.junos.exception import ConnectTimeoutError
from jnpr.junos.utils.config import Config

from napalm_base.exceptions import ConnectionException
from napalm_baseebay import base_ebay
from napalm_baseebay import base_validator
import napalm_baseebay.ebay_exceptions as exceptions
from napalm_ebayjunos.utils import junos_views
import napalm_junos as base_junos_driver
from netforce.common import netforce_constants as netforce_const

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class JunOsEbayDriver(base_junos_driver.JunOSDriver,
                      base_ebay.EbayNetworkDriver,
                      base_validator.ValidatorMixin):

    def __init__(self, hostname, username, password, timeout=60,
                 optional_args=None):
        super(JunOsEbayDriver, self).__init__(hostname, username, password,
                                              timeout, optional_args)

    def open(self):
        try:
            self.device.open(normalize=False, gather_facts=False)
        except ConnectTimeoutError as cte:
            raise ConnectionException(cte.message)
        self.device.timeout = self.timeout
        if hasattr(self.device, "cu"):
            # make sure to remove the cu attr from previous session
            # ValueError: requested attribute name cu already exists
            del self.device.cu
        self.device.bind(cu=Config)
        if self.config_lock:
            self._lock()

    def _get_interfaces_description(self):
        result = {}
        interfaces = junos_views.junos_config_iface_table(self.device)
        interfaces.get()

        # interfaces
        for iface in interfaces.keys():
            result[iface] = {
                'description': interfaces[iface]['description']
            }
        return result

    def create_vlan(self, name, number, is_active):
        """

        :param name: vlan name
        :param number: vlan number (tag)
        :param is_active: active or suspended state for the new vlan.
        :return:
        """
        # Validate if the vlans exists on device
        vlans = junos_views.junos_vlan_table(self.device)
        vlans.get()
        if str(number) not in vlans:
            raise exceptions.PostChangeValidationException('vlan %s does not '
                                                           'exist' %
                                                           str(number))
        str_commands = """
                        edit
                        set vlans %s vlan-id %s
                        set vlans %s l3-interface irb.%s
                       """ % (name, str(number), name, str(number))
        self.device.cu.load(str_commands, format="set")
        self.device.cu.commit()

    def update_interface_label(self, interface, label):
        """
            This function is use to update port label
        :param interface:
        :param label: it should be one continuous word, no space allowed
        :return:
        """
        set_conf = """
                   set interfaces %s description %s
                   """ % (interface, label)
        self.device.cu.load(set_conf, format="set")
        self.device.cu.commit()

        # post validate label changes
        interfaces_data = self._get_interfaces_description()
        if interface in interfaces_data:
            if interfaces_data[interface]['description'] != label:
                raise exceptions.PostChangeValidationException(
                    "label not updated on interface [%s]. Current value [%s]"
                    % (interface, interfaces_data[interface]['description'])
                )
        else:
            raise exceptions.\
                EntityDoesNotExistsException('interface [%s] '
                                             'does not exist on device.'
                                             % (interface))

    def get_vlans_on_interface(self, interface):
        result = {}
        interfaces = junos_views.junos_config_iface_table(self.device)
        interfaces.get()
        # interfaces
        if interface in interfaces:
            vlan_members = interfaces[interface]['members']
            if isinstance(vlan_members, unicode):
                vlan_members = [str(vlan_members)]
            else:
                vlan_members = [str(mem) for mem in vlan_members]
            result['native_vlan'] = str(interfaces[interface]
                                        ['native-vlan-id']) \
                if interfaces[interface]['native-vlan-id'] else None

            if interfaces[interface]['interface-mode'] == "access":
                result['access_vlan'] = [vlan_members[0]]
            else:
                result['trunk_vlans'] = vlan_members
            result['switch_port_mode'] =\
                interfaces[interface]['interface-mode']
            return result
        raise exceptions.EntityDoesNotExistsException(
            'interface %s does not exists' % interface)

    def get_all_vlans_on_device(self):
        """
        :return: [{'status': None, 'tag': '10', 'name': 'INFRA-lab1-10-10',
        'members': 'ae0.0*'}]
        """
        vlans = junos_views.junos_vlan_table(self.device)
        vlans.get()
        # convert list of tuples to list of dictionary
        all_vlans_on_dev = [dict((k, v) for k, v in vlan) for vlan in
                            vlans.values()]
        LOG.debug("All vlans configured on device are %s" % all_vlans_on_dev)
        return all_vlans_on_dev

    def _validate_vlan_tags(self, vlan_tags):
        """
        :param vlans:
        :return:
        """
        valid_tags = []
        all_vlans_on_dev = self.get_all_vlans_on_device()
        # all_vlans_on_dev = [{'status': None, 'tag': '10', 'name':
        # 'INFRA-lab1-10-10', 'members': 'ae0.0*'}]
        # Here compare two lists , one is requested vlan_list with one on
        # device. We also want to compare the status of vlans and make sure
        # the status is active before pushing any changes.
        for tag in vlan_tags:
            for vlan in all_vlans_on_dev:
                if vlan['status'] == 'suspend':
                    raise exceptions.EntityInSuspendedModeException(
                        'vlan_tag %s' % vlan['tag'])
                if tag == vlan['tag']:
                    valid_tags.append(tag)
        if set(valid_tags) == set(vlan_tags):
            return
        msg = 'vlans does not exist on device. %s' % vlan_tags
        raise exceptions.InvalidValueForParameterException(msg)

    def _check_native_vlan_id(self, interface):

        # check if native-vlan-id is present for the port
        vlan_data = self.get_vlans_on_interface(interface)
        return True if vlan_data["native_vlan"] else False

    def update_switch_port_vlans_on_device(self, interface, port):

        # Do pre-validation before pushing any changes to device.
        # check the tags are valid
        # check the current configuration is not same as the requested
        # make sure the vlan status is not suspended as any configuration
        # pushed will not be effective

        switch_port_mode = port['switch_port_mode']
        vlans_allowed = []
        vlans = port['vlans']
        native_vlan = None
        set_commands = ""
        no_native_command = ""

        if switch_port_mode == 'access':
            if len(vlans) > 1:
                raise exceptions.MoreThanOneAccessVlan(reason=str(vlans))
            vlan_data = vlans[0]['vlan']
            if self._check_native_vlan_id(interface):
                no_native_command = "delete interfaces %s native-vlan-id" % \
                            interface
            set_commands = """
                           %s
                           delete interfaces %s unit 0 family \
                           ethernet-switching vlan members
                           set interfaces %s unit 0 family \
                           ethernet-switching interface-mode access vlan \
                           members %s
                           """ % (no_native_command, interface, interface,
                                  vlan_data['tag'])
        else:
            for vlan in vlans:
                vlan_data = vlan['vlan']

                vlans_allowed.append(str(vlan_data['tag']))
                if vlan_data['is_native']:
                    native_vlan = str(vlan_data['tag'])

            if not native_vlan:
                raise exceptions.NoNativeVlan(reason=str(vlans))

            set_commands = """
                           delete interfaces %s unit 0 family \
                           ethernet-switching vlan members
                           set interfaces %s native-vlan-id %s unit 0 \
                           family ethernet-switching interface-mode \
                           trunk vlan members [ %s ]
                           """ % (interface, interface, native_vlan,
                                  ' '.join(vlans_allowed))
        self.device.cu.load(set_commands, format="set")
        self.device.cu.commit(sync=True)
        return set_commands

    def disable_interface_on_device(self, interface):
        """Disable device interface

        :param interface: An interface to disable
        :return: commands
        """
        set_commands = 'set interfaces %s disable' % interface
        self.device.cu.load(set_commands, format="set")
        self.device.cu.commit(sync=True)
        LOG.debug("Disabled interface %s", interface)
        return set_commands

    def enable_interface_on_device(self, interface):
        """Enable device interface

        :param interface: An interface to enable
        :return: commands
        """
        set_commands = 'delete interfaces %s disable' % interface
        self.device.cu.load(set_commands, format="set")
        self.device.cu.commit(sync=True)
        LOG.debug("enabled interface %s" % interface)
        return set_commands

    def is_interface_enabled(self, interface):
        command = "show configuration interfaces %s" % interface
        if "disable" in self.device.cli(command):
            return False
        return True

    def get_interfaces_by_name(self, interface_names):
        interfaces_dict = {}
        interfaces = self.get_interfaces()
        for int_name in interface_names:
            if int_name in interfaces:
                interfaces_dict[int_name] = interfaces[int_name]
        return interfaces_dict

    def get_vlan(self, number):
        vlans = junos_views.junos_vlan_table(self.device)
        vlans.get()
        for vlan_name in vlans.keys():
            if str(number) == vlans[vlan_name]['tag']:
                return {
                    'status': vlans[vlan_name]['status'],
                    'name': vlans[vlan_name]['name']
                }
        return None

    def get_interface_running_config(self, interface):

        interfaces = junos_views.junos_config_iface_table(self.device)
        interfaces.get()
        if interface not in interfaces:
            raise exceptions.EntityDoesNotExistsException(
                'interface %s does not exists' % interface)
        command = "show configuration interfaces %s" % interface
        current_running_conf = self.device.cli(command)
        return current_running_conf

    def get_mac_addresses_on_interface(self, interface_name, vlan=None):
        result = {}
        data = junos_views.junos_mac_address_interface_table(self.device)
        if vlan:
            data.get(interface_name=interface_name, vlan_id=str(vlan))
        else:
            data.get(interface_name=interface_name)

        result = []
        for vlan in data.keys():
            entry = data[vlan]
            result.append(
                {
                    'mac_address': entry['mac_address'],
                    'vlan': int(vlan)
                }
            )

        return result

    def get_traffic_on_interface(self, interface_name):
        command = "show interfaces %s extensive" % interface_name
        data = self.device.cli(command)
        data_list = data.split('\n')
        data_list = [d.strip() for d in data_list]
        traffic_dict = {}

        for bytes in data_list:
            if "Input  bytes" in bytes:
                traffic_data = [b.strip() for b in bytes.split(':')]
                traffic_dict.update(dict([tuple(traffic_data)]))
                break
        for bytes in data_list:
            if "Output bytes" in bytes:
                traffic_data = [b.strip() for b in bytes.split(':')]
                traffic_dict.update(dict([tuple(traffic_data)]))
                break
        trans_unit = traffic_dict['Input  bytes'].split(' ')[-1]
        input_bits = traffic_dict['Input  bytes'].split(' ')[-2]
        input_bits = self.convert_to_bits_per_sec(trans_unit, input_bits)

        trans_unit = traffic_dict['Output bytes'].split(' ')[-1]
        output_bits = traffic_dict['Output bytes'].split(' ')[-2]
        output_bits = self.convert_to_bits_per_sec(trans_unit, output_bits)
        return input_bits, output_bits

    def create_subnet(self, subnet, vlan_id):
        self.pre_change_validate_vlan(vlan_id)
        vlan_l3_interface_name = self.get_vlan_interface_name(vlan_id)
        self._check_primary_subnet(vlan_l3_interface_name)
        if '.' not in vlan_l3_interface_name:
            # Juniper l3-interface name should always be in format:
            # irb.<unit_number>
            msg = 'l3-interface name %s is not a valid format.'\
                  % vlan_l3_interface_name
            raise exceptions.InvalidValueForParameterException(msg)
        self.pre_change_validate_subnet(subnet, vlan_l3_interface_name)

        unit = vlan_l3_interface_name.split('.')[1]
        set_commands = """
                        set interfaces irb unit %s family inet address %s
                       """ % (unit, subnet)
        self.device.cu.load(set_commands, format="set")
        self.device.cu.commit(sync=True)
        self.post_change_validate_subnet(subnet, vlan_l3_interface_name)
        return set_commands

    def get_ip_addrs_on_interface(self, interface_name):
        interfaces = junos_views.junos_config_irbiface_table(self.device)
        unit_id = interface_name.split('.')[1]
        interfaces.get(interface='irb', unit=unit_id)
        ip_addrs = interfaces[unit_id]['subnets']
        if not isinstance(ip_addrs, list):
            return [ip_addrs]
        return ip_addrs

    def get_vlan_interface_name(self, vlan_tag):
        vlan_data = self.get_vlan(vlan_tag)
        if not vlan_data:
            raise exceptions.EntityDoesNotExistsException(
                'vlan %s does not exists' % vlan_tag)
        # Always pass vlan name on device to get the irb unit
        cmd = "show configuration vlans %s" % vlan_data['name']
        data = self.device.cli(cmd)
        data = data.split('\n')
        irb_unit = None
        for d in data:
            if 'l3-interface' in d:
                irb_unit = d.replace('l3-interface', '')
                irb_unit = irb_unit.replace(';', '')
                irb_unit = irb_unit.strip()
                break
        if not irb_unit:
            raise exceptions. \
                EntityDoesNotExistsException('no l3-interface configured'
                                             ' for vlan %s:'
                                             % (vlan_tag))
        return irb_unit

    def get_routes(self, vrf_name=None):
        # For non-vrf bubbles, get all the routes
        is_native = self._is_native_vrf(vrf_name)
        if not is_native:
            self.check_vrf_exist(vrf_name)
            # we use inet.0 table For IPv4 unicast routes since it stores
            # interface local and direct routes,
            # static routes, and dynamically learned routes.
            cmd = 'show route table %s.inet.0' % vrf_name
        else:
            cmd = 'show route table inet.0'
        data = self.device.cli(cmd)
        all_routes = self._parse_routes(data)
        route_aggregates = self.get_routes_aggregate(vrf_name)
        cidr_list = list(set(all_routes) - set(route_aggregates))
        return cidr_list

    def _get_vrfs(self):
        data = junos_views.junos_vrf_table(self.device)
        data.get()
        return data.keys()

    def _parse_routes(self, data):

        data = data.split('\n')
        cidr_list = []
        for d in data:
            each_route = d.split()
            for route in each_route:
                if '/' in route:
                    cidr_list.append(route.strip())
        cidr_list = self.filter_invalid_cidr(cidr_list)
        return cidr_list

    def get_routes_aggregate(self, vrf_name=None):
        # we use inet.0 table For IPv4 unicast routes since it stores
        # interface local and direct routes,
        # static routes, and dynamically learned routes.
        is_native = self._is_native_vrf(vrf_name)
        if not is_native:
            self.check_vrf_exist(vrf_name)
            cmd = 'show route protocol aggregate table %s.inet.0' % vrf_name
            data = self.device.cli(cmd)
            return self._parse_routes(data)
        else:
            cmd = 'show route protocol aggregate table inet.0'
            data = self.device.cli(cmd)
            aggregates = self._parse_routes(data)
            # For flat network if there is no vrf, use static routes instead
            # of aggregates.
            cmd = 'show route protocol static table inet.0'
            data = self.device.cli(cmd)
            static_aggregates = self._parse_routes(data)
            return static_aggregates + aggregates

    def delete_subnet_on_device(self, subnet, vlan_id):
        # Need to get the irb unit number for the vlan tag,
        # e.g. irb unit will be 0 in case of vlan tag 1(production).
        irb_unit = self.get_vlan_interface_name(vlan_id)
        unit_id = irb_unit.split('.')[1]
        set_commands = """
                        delete interfaces irb unit %s family inet address %s
                       """ % (unit_id, subnet)
        self.device.cu.load(set_commands, format="set")
        self.device.cu.commit(sync=True)
        return set_commands

    def _is_native_vrf(self, vrf_name=None):
        # In case of juniper, native vrf is inet.0.
        # e.g. fake-native doesn't exist. Hence no need to
        # pass vrf_name in that case.
        if vrf_name is None or 'native' in vrf_name:
            return True
        return False

    def _check_primary_subnet(self, vlan_interface=None):
        # This is an additional validation just for junos.
        # The reason is all the Juniper TORs that have been on-boarded, are
        # missing primary statement for all the first subnets on native vlan.
        if vlan_interface:
            cmd = "show configuration interfaces %s family inet"\
                  % vlan_interface
            data = self.device.cli(cmd)
            data = data.split('\n')
            found_primary = False
            for d in data:
                if netforce_const.SUBNET_TYPE_PRIMARY in d:
                    found_primary = True
                    break
            if not found_primary:
                raise exceptions. \
                    NoPrimarySubnetOnVlanInterface(
                        vlan_interface_name=vlan_interface)

    def _check_patch_subnet_on_interface(self, req_subnet, vlan_interface,
                                         one_subnet_only):
        # First of all check if there is only one subnet on the vlan interface.
        existing_subnets = self.get_ip_addrs_on_interface(vlan_interface)
        total_subnets = len(existing_subnets)
        if total_subnets != 1 and one_subnet_only is True:
            raise exceptions.PatchingNotSupported(
                vlan_interface_name=vlan_interface)
        found_requested = False
        for subnet in existing_subnets:
            if subnet == req_subnet:
                found_requested = True
        if not found_requested:
            raise exceptions.RequestedPrimaryConflictsWithConfigured(
                req=req_subnet, configured=existing_subnets)
        # Finally check for primary. Here if there is primary then just raise
        #  error.
        cmd = "show configuration interfaces %s family inet" \
              % vlan_interface
        data = self.device.cli(cmd)
        data = data.split('\n')
        for d in data:
            if netforce_const.SUBNET_TYPE_PRIMARY in d:
                raise exceptions.PrimarySubnetExistsOnVlanInterface(
                    vlan_interface_name=vlan_interface)

    def set_subnet_primary(self, subnet, vlan_id, one_subnet_only):
        self.pre_change_validate_vlan(vlan_id)
        vlan_l3_interface_name = self.get_vlan_interface_name(vlan_id)
        self._check_patch_subnet_on_interface(
            subnet, vlan_l3_interface_name, one_subnet_only)
        if not vlan_l3_interface_name.startswith('irb.'):
            # Juniper l3-interface name should always be in format:
            # irb.<unit_number>
            msg = 'l3-interface name %s is not a valid format.' \
                  % vlan_l3_interface_name
            raise exceptions.InvalidValueForParameterException(msg)
        unit = vlan_l3_interface_name.split('.')[1]
        set_commands = """
                    set interfaces irb unit %s family inet address %s primary
                    """ % (unit, subnet)
        self.device.cu.load(set_commands, format="set")
        self.device.cu.commit(sync=True)
        self.post_change_validate_subnet(subnet, vlan_l3_interface_name)
        return set_commands

    def check_hidden_routes_aggregates(self, vrf_name=None):
        is_native = self._is_native_vrf(vrf_name)
        if not is_native:
            self.check_vrf_exist(vrf_name)
            cmd = 'show route protocol aggregate table %s.inet.0' \
                  ' hidden' % vrf_name
        else:
            cmd = 'show route protocol aggregate table inet.0 hidden'
        data = self.device.cli(cmd)
        return self._parse_routes(data)
