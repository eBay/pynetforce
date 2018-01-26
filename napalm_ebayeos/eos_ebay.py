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


import json
import napalm_base
from napalm_baseebay import base_connection
from napalm_baseebay import base_ebay
from napalm_baseebay import base_validator
import napalm_baseebay.ebay_exceptions as exceptions
import napalm_eos as base_eos_driver
from netforce.plugins.common import netforce_constants
from oslo_log import log as logging
from pyeapi.eapilib import CommandError
import re
import socket

MAC_REGEX = r"[a-fA-F0-9]{4}\.[a-fA-F0-9]{4}\.[a-fA-F0-9]{4}"
VLAN_REGEX = r"\d{1,4}"
RE_MAC = re.compile(r"{}".format(MAC_REGEX))

LOG = logging.getLogger(__name__)


class OpenNotInvokedException(Exception):

    def __init__(self):
        self.message = 'Please invoke open() before calling the ' \
                       'close() method.'


class EbayEosDriver(base_connection.SSHConnectionMixin,
                    base_eos_driver.EOSDriver,
                    base_ebay.EbayNetworkDriver,
                    base_validator.ValidatorMixin):

    def __init__(self, hostname, username, password, port=22,
                 timeout=60, optional_args=None):
        self.device_hostname = hostname
        self.device_username = username
        self.device_password = password
        self.device_port = port
        self.ssh = None
        self.tout = timeout
        self.stdin = None
        self.stdout = None
        self.ssh_stderr = None

    def _exec_command_json(self, cmd):
        cmd += ' | json'
        output = self._exec_command(cmd)
        output = json.loads(output)
        return output

    def disable_interface_on_device(self, interface):
        """Disable device interface

        :param interface: An interface to disable
        :return: commands
        """
        disable_config = ""
        # Append disable configuration for an interface
        disable_config += """
            configure terminal
            interface %s
            shutdown
            copy running-config startup-config
            """ % interface
        self._exec_command(disable_config)
        return disable_config

    def enable_interface_on_device(self, interface):
        """Enable device interface

        :param interface: An interface to enable
        :return: commands
        """
        enable_config = ""
        # Append enable configuration for an interface
        enable_config += """
            configure terminal
            interface %s
            no shutdown
            copy running-config startup-config
            """ % interface
        self._exec_command(enable_config)
        return enable_config

    def update_interface_label(self, interface, label):
        interface_number = interface[len("Ethernet"):]
        commands = '''
            configure terminal
            interface ethernet %s
            description %s
            ''' % (interface_number, label)

        self._exec_command(commands)

        # post validate label changes
        interfaces_data = self.get_interfaces_by_name([interface])
        if interface in interfaces_data:
            if interfaces_data[interface]['description'] != label:
                raise exceptions.PostChangeValidationException(
                    "interface label not updated. Current value [%s]"
                    % (interfaces_data[interface]['description'])
                )
        else:
            raise exceptions.EntityDoesNotExistsException(
                'interface does not exist on device.')

    def get_vlan(self, number):

        cmd = 'show vlan %s' % number
        output = self._exec_command_json(cmd)
        if 'vlans' in output:
            if str(number) in output['vlans']:
                vlan_dict = {
                    'status': output['vlans'][str(number)]['status'],
                    'name': output['vlans'][str(number)]['name']
                }
                return vlan_dict
            return None

    def create_vlan(self, name, number, is_active):
        """

        :param name: vlan name
        :param number: vlan number (tag)
        :param is_active: active or suspended state for the new vlan.
        :return:
        """
        commands = list()
        commands.append('vlan %s' % (str(number)))
        commands.append('name %s' % (name))
        commands.append('state %s' % ("active" if is_active else "suspend"))
        commands.append('interface Vlan %s' % (str(number)))

        self._execute(config=commands, commit=True)

        # Retrieve vlan for verification
        self.post_change_validate_vlan(number)

    def get_vlans_on_interface(self, interface):
        """
            Get vlans configured on an interface
        :param interface_number:
        :return:
        """
        # a dict to map the device property names to driver names.
        device_prop_to_driver_dict = {
            'Trunking VLANs Enabled': 'trunk_vlans',
            'Trunking Native Mode VLAN': 'native_vlan',
            'Access Mode VLAN': 'access_vlan',
            'Operational Mode': 'switch_port_mode'
        }
        commands = list()
        commands.append('show interfaces switchport')
        output = self.device.run_commands(commands, encoding='text',
                                          send_enable=self.send_enable)\
                            .pop(0)['output']

        interface_dict = dict()
        interfaces_output = output.strip().split('\n\n')

        for each_if in interfaces_output:
            if each_if.startswith('Name'):
                interface_props = each_if.split('\n')
                interface_name = None
                for each_prop in interface_props:
                    prop_key_and_value = each_prop.split(': ')

                    if len(prop_key_and_value) == 2:

                        prop_key = prop_key_and_value[0].strip()
                        prop_value = prop_key_and_value[1].strip()

                        if prop_key.lower() == 'name':
                            interface_name = prop_value
                            interface_dict[interface_name] = dict()
                        else:
                            if prop_key in device_prop_to_driver_dict:
                                interface_dict[interface_name][
                                    device_prop_to_driver_dict[prop_key]] = \
                                    prop_value

        interface = interface.replace("hernet", "")
        if interface not in interface_dict:
            raise exceptions.EntityDoesNotExistsException(
                'interface %s does not exists' % interface)

        interface_data = interface_dict[interface]
        access_vlan = interface_data['access_vlan']
        native_vlan = interface_data['native_vlan']
        if '(' in access_vlan:
            access_vlan = access_vlan.split('(')[0].strip()
            interface_data['access_vlan'] = access_vlan
        if '(' in native_vlan:
            native_vlan = native_vlan.split('(')[0].strip()
            interface_data['native_vlan'] = native_vlan
        if interface_data['switch_port_mode'] == 'static access':
            interface_data.pop('trunk_vlans')
        else:
            interface_data.pop('access_vlan')
        return interface_data

    # Validate if the vlans exists
    def _validate_vlan_tags(self, vlan_tags):
        for v in vlan_tags:
            try:
                vlan_wiri = self.get_vlan(int(v))
                if vlan_wiri and vlan_wiri['status'] == 'suspend':
                    raise exceptions.\
                        EntityInSuspendedModeException('vlan_tag %s' % v)
            except CommandError:
                raise exceptions.\
                    EntityDoesNotExistsException('vlan %s does not exist'
                                                 '' % str(v))

    def update_switch_port_vlans_on_device(self, interface, port):
        mode = port['switch_port_mode']
        commands = []
        interface_number = interface[len("Ethernet"):]
        commands.append('interface ethernet %s' % interface_number)
        vlans_allowed = []
        vlans = port['vlans']
        native_vlan = None

        if mode == 'access':
            if len(vlans) > 1:
                raise exceptions.MoreThanOneAccessVlan(reason=str(vlans))
            vlan_data = vlans[0]['vlan']
            access_vlan = str(vlan_data['tag'])
            commands.append('no switchport trunk allowed vlan')
            commands.append('no switchport trunk native vlan')
            commands.append('switchport access vlan %s' % access_vlan)
            commands.append('switchport mode access')

        else:
            for vlan in vlans:
                vlan_data = vlan['vlan']
                vlans_allowed.append(str(vlan_data['tag']))
                if vlan_data['is_native']:
                    native_vlan = str(vlan_data['tag'])

            if not native_vlan:
                raise exceptions.NoNativeVlan(reason=str(vlans))

            commands.append('no switchport access vlan')
            commands.append('switchport trunk native vlan %s' % native_vlan)
            commands.append('switchport mode trunk')
            commands.append('switchport trunk allowed vlan %s' % ','.join(
                vlans_allowed))

        self._execute(config=commands, commit=True)
        return str(commands)

    def _parse_interfaces_output(self, output):
        interfaces = dict()
        for interface, values in output['interfaces'].iteritems():
            interfaces[interface] = dict()

            if values['lineProtocolStatus'] == 'up':
                interfaces[interface]['is_up'] = True
                interfaces[interface]['is_enabled'] = True
            else:
                interfaces[interface]['is_up'] = False
                if values['interfaceStatus'] == 'disabled':
                    interfaces[interface]['is_enabled'] = False
                else:
                    interfaces[interface]['is_enabled'] = True

            interfaces[interface]['description'] = values['description']

            interfaces[interface]['last_flapped'] = values.pop(
                'lastStatusChangeTimestamp', None)

            interfaces[interface]['speed'] = values['bandwidth']
            interfaces[interface]['mac_address'] = values.pop(
                'physicalAddress', u'')
        return interfaces

    def get_interfaces(self):
        self._check_if_connected()
        command = "show interface | include Ethernet"
        response_dict = self._exec_command(command)
        interface_table_list = response_dict.split('\n')
        return interface_table_list

    def get_interfaces_by_name(self, interface_names):
        self._check_if_connected()
        command = "show interface %s | include Ethernet" % interface_names
        response_dict = self._exec_command(command)
        interface_table_list = response_dict.split('\n')
        for i in interface_table_list:
            if interface_names in i and "include Ethernet" not in i:
                return {interface_names: {"present": True}}
        return {}

    def get_interface_running_config(self, interface):
        self._check_if_connected()
        found = False
        for i in self.get_interfaces():
            if interface in i:
                found = True
                break
        if not found:
            raise exceptions.EntityDoesNotExistsException(
                'interface %s does not exists' % interface)
        command = 'show running-config interface %s' % interface
        current_running_config = self._exec_command(command)
        current_running_config = current_running_config.split('\n')
        current_running_config = \
            [conf.strip() for conf in current_running_config]
        return current_running_config

    def _parse_mac_address_table(self, data):
        '''
        data sample:
            {u'multicastTable': {u'tableEntries': []},
              u'unicastTable': {u'tableEntries': [
                        {u'macAddress': u'54:52:00:23:f2:e5',
                        u'lastMove': 1473243754.287243,
                        u'vlanId': 3,
                        u'interface': u'Ethernet1',
                        u'moves': 1,
                        u'entryType': u'dynamic'}]
                        }}
        '''
        rslt = []
        mac_entry = data['unicastTable']['tableEntries']
        if mac_entry:
            elem = {'mac_address': mac_entry['macAddress'],
                    'vlan': mac_entry['vlanId']}
            rslt.append(elem)
            return rslt
        else:
            return rslt

    def get_mac_addresses_on_interface(self, interface_name, vlan=None):
        """
        Returns a lists of dictionaries. Each dictionary represents an entry
         in the MAC Address
        Table, having the following keys
            * mac (string)
            * interface (string)
            * vlan (int)
            * active (boolean)
            * static (boolean)
            * moves (int)
            * last_move (float)
        Format1:
                          Mac Address Table
        ------------------------------------------------------------------

        Vlan    Mac Address       Type        Ports      Moves   Last Move
        ----    -----------       ----        -----      -----   ---------
           1    001c.7315.b96c    STATIC      Router
           1    1cc1.de18.9a42    DYNAMIC     Et38       1       410 days, 8:1
        Total Mac Addresses for this criterion: 1
        """
        self._check_if_connected()
        found = False
        for i in self.get_interfaces():
            if interface_name in i:
                found = True
                break
        if not found:
            raise exceptions.EntityDoesNotExistsException(
                'interface %s does not exists' % interface_name)
        RE_MACTABLE_DEFAULT = r"^" + MAC_REGEX
        RE_MACTABLE_6500_1 = r"^\*\s+{}\s+{}\s+".\
            format(VLAN_REGEX, MAC_REGEX)  # 7 fields
        RE_MACTABLE_6500_2 = r"^{}\s+{}\s+".\
            format(VLAN_REGEX, MAC_REGEX)  # 6 fields
        RE_MACTABLE_6500_3 = r"^\s{51}\S+"  # Fill down from prior
        RE_MACTABLE_4500_1 = r"^{}\s+{}\s+".\
            format(VLAN_REGEX, MAC_REGEX)  # 5 fields
        RE_MACTABLE_4500_2 = r"^\s{32}\S+"  # Fill down from prior
        RE_MACTABLE_2960_1 = r"^All\s+{}".format(MAC_REGEX)
        RE_MACTABLE_GEN_1 = r"^{}\s+{}\s+".\
            format(VLAN_REGEX, MAC_REGEX)  # 4 fields (2960/4500)

        def _process_mac_fields(vlan, mac, mac_type, interface):
            """Return proper data for mac address fields."""
            if mac_type.lower() in ['self', 'static', 'system']:
                static = True
                if vlan.lower() == 'all':
                    vlan = 0
                if interface.lower() == 'cpu' or re.search(r'router', interface.lower()) or \
                        re.search(r'switch', interface.lower()):
                    interface = ''
            else:
                static = False
            if mac_type.lower() in ['dynamic']:
                active = True
            else:
                active = False
            return {
                'mac': napalm_base.helpers.mac(mac),
                'interface': interface,
                'vlan': int(vlan),
                'static': static,
                'active': active,
                'moves': -1,
                'last_move': -1.0
            }

        mac_address_table = []
        if vlan:
            cmd = "show mac address-table vlan %s " % vlan
        else:
            cmd = 'show mac address-table interface %s ' % interface_name
        output = self._exec_command(cmd)
        # Skip the header lines
        output = re.split(r'^----.*', output, flags=re.M)[1:]
        output = "\n".join(output).strip()
        # Strip any leading astericks
        output = re.sub(r"^\*", "", output, flags=re.M)
        fill_down_vlan = fill_down_mac = fill_down_mac_type = ''
        for line in output.splitlines():
            # Cat6500 one off anf 4500 multicast format
            if (re.search(RE_MACTABLE_6500_3, line) or
                    re.search(RE_MACTABLE_4500_2, line)):
                interface = line.strip()
                if ',' in interface:
                    interfaces = interface.split(',')
                else:
                    interfaces = []
                    interfaces.append(interface)
                for single_interface in interfaces:
                    mac_address_table.append(
                        _process_mac_fields(fill_down_vlan, fill_down_mac,
                                            fill_down_mac_type,
                                            single_interface))
                continue
            line = line.strip()
            if line == '':
                continue
            if re.search(r"^---", line):
                # Convert any '---' to VLAN 0
                line = re.sub(r"^---", "0", line, flags=re.M)

            # Format1
            if re.search(RE_MACTABLE_DEFAULT, line):
                if len(line.split()) == 4:
                    mac, mac_type, vlan, interface = line.split()
                    mac_address_table.append(_process_mac_fields(
                        vlan, mac, mac_type, interface))
                else:
                    raise ValueError("Unexpected output from: {}".
                                     format(line.split()))
            elif (re.search(RE_MACTABLE_6500_1, line) or re.search(
                    RE_MACTABLE_6500_2, line)) \
                    and len(line.split()) >= 6:
                if len(line.split()) == 7:
                    _, vlan, mac, mac_type, _, _, interface = line.split()
                elif len(line.split()) == 6:
                    vlan, mac, mac_type, _, _, interface = line.split()
                elif len(line.split()) == 9:
                    vlan, mac, mac_type, interface, _, _, _, _, _ = \
                        line.split()
                if ',' in interface:
                    interfaces = interface.split(',')
                    fill_down_vlan = vlan
                    fill_down_mac = mac
                    fill_down_mac_type = mac_type
                    for single_interface in interfaces:
                        mac_address_table.append(
                            _process_mac_fields(vlan, mac, mac_type,
                                                single_interface))
                else:
                    mac_address_table.append(
                        _process_mac_fields(vlan, mac, mac_type, interface))
            elif re.search(RE_MACTABLE_4500_1, line) \
                    and len(line.split()) == 5:
                vlan, mac, mac_type, _, interface = line.split()
                mac_address_table.append(_process_mac_fields(
                    vlan, mac, mac_type, interface))
            elif re.search(r"^Vlan\s+Mac Address\s+", line):
                continue
            elif (re.search(RE_MACTABLE_2960_1, line)
                  or re.search(RE_MACTABLE_GEN_1, line)) \
                    and len(line.split()) == 4:
                vlan, mac, mac_type, interface = line.split()
                if ',' in interface:
                    interfaces = interface.split(',')
                    fill_down_vlan = vlan
                    fill_down_mac = mac
                    fill_down_mac_type = mac_type
                    for single_interface in interfaces:
                        mac_address_table.append(
                            _process_mac_fields(vlan, mac, mac_type,
                                                single_interface))
                else:
                    mac_address_table.append(
                        _process_mac_fields(vlan, mac, mac_type, interface))
            elif re.search(r"Total Mac Addresses", line):
                continue
            elif re.search(r"Multicast Entries", line):
                continue
            elif re.search(r"vlan.*mac.*address.*type.*", line):
                continue
            else:
                raise ValueError("Unexpected output from: {}".
                                 format(repr(line)))
        result = []
        interface_name = interface_name.replace('Ethernet', 'Et')
        if mac_address_table:
            for mac_address in mac_address_table:
                if interface_name == mac_address['interface']:
                    result.append(
                        {
                            'mac_address': mac_address['mac'],
                            'vlan': int(mac_address['vlan'])
                        }
                    )
                if vlan and vlan == mac_address['vlan']:
                    result.append(
                        {
                            'mac_address': mac_address['mac'],
                            'vlan': int(mac_address['vlan'])
                        }
                    )

        return result

    def get_traffic_on_interface(self, interface_name):
        self._check_if_connected()
        found = False
        for i in self.get_interfaces():
            if interface_name in i:
                found = True
                break
        if not found:
            raise exceptions.EntityDoesNotExistsException(
                'interface %s does not exists' % interface_name)
        cmd = "show interfaces %s | include input rate" % interface_name
        output = self._exec_command(cmd)
        output = output.split('\n')[-2]
        input_bits = int(output.split()[4])
        trans_unit = output.split()[5]
        input_bits = self.convert_to_bits_per_sec(trans_unit, input_bits)
        cmd = "show interfaces %s | include output rate" % interface_name
        output = self._exec_command(cmd)
        output = output.split('\n')[-2]
        output_bits = int(output.split()[4])
        trans_unit = output.split()[5]
        output_bits = self.convert_to_bits_per_sec(trans_unit, output_bits)
        return input_bits, output_bits

    def is_interface_enabled(self, interface):
        current_running_config = self.get_interface_running_config(
            interface)
        is_enabled = True
        for conf in current_running_config:
            if netforce_constants.DISABLE_PORT in conf:
                is_enabled = False
        return is_enabled

    def create_subnet(self, subnet, vlan_id):

        self._check_if_connected()
        self.pre_change_validate_vlan(vlan_id)
        vlan_id_str = str(vlan_id)
        vlan_l3_interface_name = self.get_vlan_interface_name(vlan_id_str)
        existing_subnets = self. \
            pre_change_validate_subnet(subnet, vlan_l3_interface_name)
        commands = []
        commands.append("configure terminal")
        commands.append('interface vlan %s' % vlan_id_str)

        ip_adress_cmd = 'ip address %s' % subnet
        if len(existing_subnets) > 0:
            ip_adress_cmd += ' secondary'
        commands.append(ip_adress_cmd)
        commands.append('copy running-config startup-config')
        cmd_string = """\n""".join(commands)
        self._exec_command(cmd_string)
        self.post_change_validate_subnet(subnet, vlan_l3_interface_name)
        return cmd_string

    def get_ip_addrs_on_interface(self, interface_name):
        cmd = 'show interfaces %s' % (interface_name)
        output = self._exec_command_json(cmd)
        if interface_name not in output['interfaces']:
            raise exceptions.\
                EntityDoesNotExistsException('vlan interface %s does not '
                                             'exist' % (interface_name))

        interface_address = output['interfaces'][interface_name]\
                                  ['interfaceAddress'][0]
        subnets_list = []
        subnets_list.append('%s/%s' % (interface_address['primaryIp']
                                       ['address'],
                                       interface_address['primaryIp']
                                       ['maskLen']))
        if 'secondaryIps' in interface_address:
            for subnet_address in interface_address['secondaryIps']:
                subnets_list.append('%s/%s' % (
                                        interface_address['secondaryIps']
                                        [subnet_address]['address'],
                                        interface_address['secondaryIps']
                                        [subnet_address]['maskLen']))
        return subnets_list

    def get_vlan_interface_name(self, vlan_tag):
        return 'Vlan%s' % (str(vlan_tag))

    def get_routes(self, vrf_name=None):
        cmd = 'show ip route detail'
        if vrf_name:
            self.check_vrf_exist(vrf_name)
            cmd = 'show ip route vrf %s detail' % vrf_name

        output = self._exec_command_json(cmd)
        output = output['vrfs']
        if vrf_name:
            all_routes = output[vrf_name]['routes'].keys()
            route_aggregates = self.get_routes_aggregate(vrf_name)
        else:
            all_routes = output['default']['routes'].keys()
            route_aggregates = self.get_routes_aggregate(vrf_name)
        cidr_list = list(set(all_routes) - set(route_aggregates))
        return cidr_list

    def _get_vrfs(self):
        cmd = "show vrf"
        output = self._exec_command(cmd).split('\n')
        out = [out.strip() for out in output]
        out_data = [i.split(' ') for i in out]
        flatten_data = lambda l: [item for sublist in l for item in sublist]
        return flatten_data(out_data)

    def get_routes_aggregate(self, vrf_name=None):

        cmd = 'show ip route aggregate'
        if vrf_name:
            self.check_vrf_exist(vrf_name)
            cmd = 'show ip route vrf %s aggregate' % vrf_name

        output = self._exec_command_json(cmd)
        output = output['vrfs']
        if vrf_name:
            return output[vrf_name]['routes'].keys()
        aggregates = output['default']['routes'].keys()
        # For flat network if there is no vrf, use static routes instead
        # of aggregates.
        cmd = 'show ip route static'
        output = self._exec_command_json(cmd)
        output = output['vrfs']
        static_aggregates = output['default']['routes'].keys()
        return aggregates + static_aggregates

    def delete_subnet_on_device(self, subnet, vlan_id):
        self._check_if_connected()
        self.pre_change_validate_vlan(vlan_id)
        commands = []
        commands.append("configure terminal")
        commands.append('interface vlan %s' % vlan_id)

        ip_adress_cmd = 'no ip address %s secondary' % subnet
        commands.append(ip_adress_cmd)
        commands.append('copy running-config startup-config')
        cmd_string = """\n""".join(commands)
        self._exec_command(cmd_string)
        return cmd_string

    def set_subnet_primary(self, subnet, vlan_id, one_subnet_only):
        pass

    def check_hidden_routes_aggregates(self, vrf_name=None):
        pass
