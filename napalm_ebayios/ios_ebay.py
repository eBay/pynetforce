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
from napalm_baseebay import ebay_exceptions

from netforce.plugins.common import netforce_constants
from oslo_log import log as logging
import re
import time
import xmltodict

LOG = logging.getLogger(__name__)

MAC_REGEX = r"[a-fA-F0-9]{4}\.[a-fA-F0-9]{4}\.[a-fA-F0-9]{4}"
VLAN_REGEX = r"\d{1,4}"
RE_MAC = re.compile(r"{}".format(MAC_REGEX))


class IOSDriver(base_connection.SSHConnectionMixin,
                napalm_base.base.NetworkDriver,
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

    def _exec_command_xml(self, cmd):
        cmd += '| xml'
        output = self._exec_command(cmd)
        output = output.replace(']]>]]>', "")
        response_dict = json.dumps(
            xmltodict.parse(str(output), process_namespaces=False))
        response_dict = json.loads(response_dict)
        if 'nf:rpc-reply' in response_dict and 'nf:data' in\
                response_dict['nf:rpc-reply']:
            return response_dict['nf:rpc-reply']['nf:data']
        else:
            raise ebay_exceptions.InvalidValueForParameterException(
                response=response_dict)

    def _push_config(self, commands):
        """TODO(aginwala): We are explicitly closing and opening the ssh
            connection before executing any commands on the device as a
            temporary workaround because ssh channel stalls due to known bug
            in paramiko ssh client that causes ssh exception.
            Relevant issue is noted @ http://stackoverflow.com/questions
            /31477121/python-paramiko-ssh-exception-ssh-session-not-active.
        """
        self.close()
        self.open()
        remote_conn = self.ssh.invoke_shell()
        remote_conn.recv(65535)
        remote_conn.send_ready()
        for cmd in commands:
            remote_conn.send(cmd + "\n")
            time.sleep(3)
            remote_conn.recv(65535)
        # Interactive shell needs to closed as get functions do not need
        # interactive mode.
        self.close()
        self.open()

    def update_interface_label(self, interface, label):
        pass

    def _parse_interfaces_data(self, interface_table_list):
        interface_result_list = {}
        for interface_props in interface_table_list:
            interface_result_list[interface_props['interface']] =\
                self._parse_interface_props(interface_props)
        return interface_result_list

    def _parse_interface_props(self, interface_props):

        interface_data = {}
        if 'desc' in interface_props:
            interface_data['description'] = interface_props['desc']
        else:
            interface_data['description'] = None
        if 'eth_speed' in interface_props:
            interface_data['speed'] = interface_props['eth_speed']
        else:
            interface_data['speed'] = None
        if 'eth_link_flapped' in interface_props:
            interface_data['last_flapped'] = \
                interface_props['eth_link_flapped']
        else:
            interface_data['last_flapped'] = None
        if 'eth_hw_addr' in interface_props:
            interface_data['mac_address'] = interface_props['eth_hw_addr']
        else:
            interface_data['mac_address'] = None
        if 'state' in interface_props and interface_props['state']\
                == 'up':
            interface_data['is_up'] = True
        else:
            interface_data['is_up'] = False
        if 'admin_state' in interface_props and interface_props['admin_state']\
                == 'up':
            interface_data['is_enabled'] = True
        else:
            interface_data['is_enabled'] = False
        return interface_data

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

    def get_vlan(self, number):
        pass

    def get_vlans_on_interface(self, interface):
        pass

    def update_switch_port_vlans_on_device(self, interface, port):
        pass

    def create_vlan(self, name, number, is_active):
        pass

    def enable_interface_on_device(self, interface):
        """Enable device interface

        :param interface: An interface to enable
        :return: commands
        """
        self._check_if_connected()
        commands = list()
        commands.append('configure terminal')
        commands.append('interface  %s' % (interface))
        commands.append('no shutdown')
        commands.append('end')
        commands.append('copy running-config startup-config')
        cmd_string = ' ; '.join(commands)
        self._push_config(commands)
        return cmd_string

    def disable_interface_on_device(self, interface):
        """Disable device interface

        :param interface: An interface to disable
        :return: commands
        """
        self._check_if_connected()
        commands = list()
        commands.append('configure terminal')
        commands.append('interface  %s' % (interface))
        commands.append('shutdown')
        commands.append('end')
        commands.append('write memory')
        cmd_string = ' ; '.join(commands)
        self._push_config(commands)
        return cmd_string

    def get_interface_running_config(self, interface):
        self._check_if_connected()
        found = False
        for i in self.get_interfaces():
            if interface in i:
                found = True
                break
        if not found:
            raise ebay_exceptions.EntityDoesNotExistsException(
                'interface %s does not exists' % interface)
        command = 'show running-config interface %s' % interface
        current_running_config = self._exec_command(command)
        current_running_config = current_running_config.split('\n')
        current_running_config = \
            [conf.strip() for conf in current_running_config]
        return current_running_config

    def is_interface_enabled(self, interface):
        current_running_config = self.get_interface_running_config(
            interface)
        is_enabled = True
        for conf in current_running_config:
            if netforce_constants.DISABLE_PORT in conf:
                is_enabled = False
        return is_enabled

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
        Destination Address  Address Type  VLAN  Destination Port
        -------------------  ------------  ----  --------------------
        6400.f1cf.2cc6          Dynamic       1     Wlan-GigabitEthernet0
        Cat 6500:
        Legend: * - primary entry
                age - seconds since last seen
                n/a - not available
          vlan   mac address     type    learn     age              ports
        ------+----------------+--------+-----+----------+--------------------------
        *  999  1111.2222.3333   dynamic  Yes          0   Port-channel1
           999  1111.2222.3333   dynamic  Yes          0   Port-channel1
        Cat 4948
        Unicast Entries
         vlan   mac address     type        protocols               port
        -------+---------------+--------+---------------------+--------------------
         999    1111.2222.3333   dynamic ip                    Port-channel1
        Cat 2960
        Mac Address Table
        -------------------------------------------
        Vlan    Mac Address       Type        Ports
        ----    -----------       --------    -----
        All    1111.2222.3333    STATIC      CPU
        """
        self._check_if_connected()
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
        cmd = 'show mac address-table'

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
            # Cat6500 format
            elif (re.search(RE_MACTABLE_6500_1, line) or re.search(
                    RE_MACTABLE_6500_2, line)) \
                    and len(line.split()) >= 6:
                if len(line.split()) == 7:
                    _, vlan, mac, mac_type, _, _, interface = line.split()
                elif len(line.split()) == 6:
                    vlan, mac, mac_type, _, _, interface = line.split()
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
            # Cat4500 format
            elif re.search(RE_MACTABLE_4500_1, line) \
                    and len(line.split()) == 5:
                vlan, mac, mac_type, _, interface = line.split()
                mac_address_table.append(_process_mac_fields(
                    vlan, mac, mac_type, interface))
            # Cat2960 format - ignore extra header line
            elif re.search(r"^Vlan\s+Mac Address\s+", line):
                continue
            # Cat2960 format (Cat4500 format multicast entries)
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
        interface_name = interface_name.replace('GigabitEthernet', 'Gi')
        interface_name = interface_name.replace('TenGigabitEthernet', 'Ti')
        if mac_address_table:
            for mac_address in mac_address_table:
                if interface_name == mac_address['interface']:
                    result.append(
                        {
                            'mac_address': mac_address['mac'],
                            'vlan': int(mac_address['vlan'])
                        }
                    )
                    break
                if vlan and vlan == mac_address['vlan']:
                    result.append(
                        {
                            'mac_address': mac_address['mac'],
                            'vlan': int(mac_address['vlan'])
                        }
                    )
                    break

        return result

    def get_traffic_on_interface(self, interface_name):
        self._check_if_connected()
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

    def create_subnet(self, subnet, vlan_id):
        pass

    def get_ip_addrs_on_interface(self, interface_name):
        pass

    def get_vlan_interface_name(self, vlan_tag):
        pass

    def _fetch_routes(self, vrf_name=None):
        pass

    def get_routes(self, vrf_name=None):
        pass

    def _get_vrfs(self):
        pass

    def get_routes_aggregate(self, vrf_name=None):
        pass

    def _get_routes_data(self, cmd):
        pass

    def delete_subnet_on_device(self, subnet, vlan_id):
        pass

    def set_subnet_primary(self, subnet, vlan_id, one_subnet_only):
        pass

    def check_hidden_routes_aggregates(self, vrf_name=None):
        pass
