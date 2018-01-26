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
import xmltodict

LOG = logging.getLogger(__name__)


class OpenNotInvokedException(Exception):

    def __init__(self):
        self.message = 'Please invoke open() before calling the ' \
                       'close() method.'


class NexusOSNetConfDriver(base_connection.SSHConnectionMixin,
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

    def update_interface_label(self, interface, label):
        self._check_if_connected()
        interface_name = interface[len("Ethernet"):]
        cmd = "configure terminal ; interface %s ; description %s ;" \
              " commands.append('copy running-config startup-config')" %\
              (interface_name, label)
        self._exec_command(cmd)

        # post validate label changes
        interfaces_data = self.get_interfaces_by_name([interface])
        if interface in interfaces_data:
            if interfaces_data[interface]['description'] != label:
                raise ebay_exceptions.\
                    PostChangeValidationException("interface label not "
                                                  "updated. Current value [%s]"
                    % (interfaces_data[interface]['description']))
        else:
            raise ebay_exceptions.EntityDoesNotExistsException(
                'interface does not exist '
                'on device.')

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
        command = "show interface "
        response_dict = self._exec_command_xml(command)
        interface_table_list = (response_dict['show']['interface']
                                ['__XML__OPT_Cmd_show_interface___readonly__']
                                ['__readonly__']['TABLE_interface']
                                ['ROW_interface'])
        return self._parse_interfaces_data(interface_table_list)

    def get_interfaces_by_name(self, interface_names):
        self._check_if_connected()
        command = "show interface %s " % (', '.join(interface_names))
        response_dict = self._exec_command_xml(command)

        interface_table_list = (
            response_dict['show']['interface']
            ['__XML__INTF_ifeth']
            ['__XML__OPT_Cmd_show_interface_if_eth___readonly__']
            ['__readonly__']['TABLE_interface']
            ['ROW_interface'])
        if len(interface_names) == 1:
            interfaces_data = [interface_table_list]
        else:
            interfaces_data = interface_table_list

        return self._parse_interfaces_data(interfaces_data)

    def get_vlan(self, number):
        self._check_if_connected()
        command = "show vlan "
        response_dict = self._exec_command_xml(command)
        vlan_table_list = (
            response_dict['show']['vlan']
            ['__XML__OPT_Cmd_show_vlan___readonly__']
            ['__readonly__']['TABLE_vlanbrief'])
        vlan_result_list = {}
        if 'ROW_vlanbrief' in vlan_table_list:
            for vlan_table_rows in vlan_table_list['ROW_vlanbrief']:
                vlan_result_list[
                    vlan_table_rows['vlanshowbr-vlanid-utf']] = dict()
                vlan_result_list[vlan_table_rows
                ['vlanshowbr-vlanid-utf']]['name'] = \
                    vlan_table_rows['vlanshowbr-vlanname']
                vlan_result_list[
                    vlan_table_rows['vlanshowbr-vlanid-utf']][
                    'status'] = vlan_table_rows['vlanshowbr-vlanstate']
        if str(number) in vlan_result_list:
            return vlan_result_list[str(number)]
        return None

    def get_vlans_on_interface(self, interface):
        self._check_if_connected()
        command = "show interface switchport "
        response_dict = self._exec_command_xml(command)
        vlans_interface_list = (
            response_dict['show']
            ['interface']['switchport'])
        if '__XML__OPT_Cmd_show_interface_switchport___readonly__' \
                in vlans_interface_list:
            vlans_interface_list = (
                vlans_interface_list
                ['__XML__OPT_Cmd_show_interface_switchport___readonly__']
                ['__readonly__']['TABLE_interface'])
        else:
            vlans_interface_list = (vlans_interface_list['__readonly__']
                                    ['TABLE_interface'])
        vlan_data = {}
        if 'ROW_interface' in vlans_interface_list:
            for vlans_if_list in vlans_interface_list['ROW_interface']:
                if vlans_if_list['interface'] != interface:
                    continue
                vlan_list = dict()
                vlan_list['access_vlan'] = vlans_if_list['access_vlan']
                vlan_list['native_vlan'] = vlans_if_list['native_vlan']
                vlan_list['trunk_vlans'] = vlans_if_list['trunk_vlans'].\
                    split(',')
                vlan_list['switch_port_mode'] = vlans_if_list['oper_mode']
                vlan_data[vlans_if_list['interface']] = vlan_list
        if interface in vlan_data:
            vlan_data = vlan_data[interface]
            if vlan_data['switch_port_mode'] == 'access':
                vlan_data.pop('trunk_vlans')
            else:
                vlan_data.pop('access_vlan')
            return vlan_data

        raise ebay_exceptions.EntityDoesNotExistsException(
            'interface %s does not exists' % interface)

    # Validate if the vlans exists
    def _validate_vlan_tags(self, vlan_tags):
        self._check_if_connected()
        for v in vlan_tags:
            vlan_wiri = self.get_vlan(int(v))
            if not vlan_wiri:
                raise ebay_exceptions.EntityDoesNotExistsException(
                    'vlan %s does not exist''' % str(v))

            if vlan_wiri['status'] == 'suspend':
                raise ebay_exceptions.\
                    EntityInSuspendedModeException('vlan_tag %s' % v)

    def update_switch_port_vlans_on_device(self, interface, port):
        self._check_if_connected()
        mode = port['switch_port_mode']
        commands = []
        commands.append('configure terminal')
        interface_number = interface[len("Ethernet"):]
        commands.append('interface ethernet %s' % interface_number)
        vlans_allowed = []
        vlans = port['vlans']
        native_vlan = None

        if mode == 'access':
            if len(vlans) > 1:
                raise ebay_exceptions.MoreThanOneAccessVlan(reason=str(vlans))
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
                raise ebay_exceptions.NoNativeVlan(reason=str(vlans))
            vlan_data = self.get_vlans_on_interface(interface)
            current_native_vlan = vlan_data.get('native_vlan', None)
            commands.append('no switchport access vlan')
            commands.append('switchport mode trunk')
            if current_native_vlan != native_vlan:
                commands.append('switchport trunk native vlan %s' %
                                native_vlan)
            commands.append('switchport trunk allowed vlan %s' % ','.join(
                vlans_allowed))
        commands.append('copy running-config startup-config')
        cmd_string = ' ; '.join(commands)
        self._exec_command(cmd_string)
        return str(commands)

    def create_vlan(self, name, number, is_active):
        """

        :param name: vlan name
        :param number: vlan number (tag)
        :param is_active: active or suspended state for the new vlan.
        :return:
        """
        self._check_if_connected()
        commands = list()
        commands.append('configure terminal')
        commands.append('vlan %s' % (str(number)))
        commands.append('name %s' % (name))
        commands.append('state %s' % ("active" if is_active else "suspend"))
        commands.append('copy running-config startup-config')

        cmd_string = ' ; '.join(commands)
        self._exec_command(cmd_string)

        # Retrieve vlan for verification
        self.post_change_validate_vlan(number)

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
        commands.append('copy running-config startup-config')
        cmd_string = ' ; '.join(commands)
        self._exec_command(cmd_string)
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
        commands.append('copy running-config startup-config')
        cmd_string = ' ; '.join(commands)
        self._exec_command(cmd_string)
        return cmd_string

    def get_interface_running_config(self, interface):
        self._check_if_connected()
        if interface not in self.get_interfaces():
            raise ebay_exceptions.EntityDoesNotExistsException(
                'interface %s does not exists' % interface)
        command = 'show running-config interface %s' % interface
        current_runing_conf = self._exec_command(command)
        return current_runing_conf

    def is_interface_enabled(self, interface):
        current_running_config = self.get_interface_running_config(
            interface)
        is_enabled = True
        for conf in current_running_config:
            if netforce_constants.DISABLE_PORT in conf:
                is_enabled = False
        return is_enabled

    def get_mac_addresses_on_interface(self, interface_name, vlan=None):
        self._check_if_connected()
        if vlan:
            cmd = "show mac address-table vlan %s " % vlan
        else:
            cmd = 'show mac address-table interface %s ' % interface_name

        output = self._exec_command_xml(cmd)
        mac_table = (
            output['show']['mac']['address-table']
            ['__XML__OPT_Cmd_show_mac_addr_tbl_static']
            ['__XML__OPT_Cmd_show_mac_addr_tbl_address']
            ['__XML__OPT_Cmd_show_mac_addr_tbl___readonly__']
            ['__readonly__'].get('TABLE_mac_address'))

        result = []
        if not mac_table:
            return result

        mac_rows = mac_table.get('ROW_mac_address')
        if not mac_rows:
            return result

        if not isinstance(mac_rows, list):
            mac_rows = [mac_rows]

        for mac_row in mac_rows:
            result.append(
                {
                    'mac_address': mac_row['disp_mac_addr'],
                    'vlan': int(mac_row['disp_vlan'])
                }
            )

        return result

    def get_traffic_on_interface(self, interface_name):
        self._check_if_connected()
        cmd = "show interface %s | grep bps  " % interface_name
        traffic_data = self._exec_command(cmd)
        traffic_data = traffic_data.split(';')
        input_data = traffic_data[0].split()
        input_bits = int(round(float(input_data[2])))
        # input_data = ['input', 'rate', '3.27', 'Kbps,']
        trans_unit = input_data[3].replace(',', '')
        input_bits = self.convert_to_bits_per_sec(
            trans_unit, input_bits)
        output_data = traffic_data[1].split()
        output_bits = int(round(float(output_data[2])))
        trans_unit = output_data[3].replace(',', '')
        output_bits = self.convert_to_bits_per_sec(
            trans_unit, output_bits)
        return input_bits, output_bits

    def create_subnet(self, subnet, vlan_id):
        self._check_if_connected()
        self.pre_change_validate_vlan(vlan_id)

        vlan_id_str = str(vlan_id)
        vlan_l3_interface_name = self.get_vlan_interface_name(vlan_id_str)
        existing_subnets = self.\
            pre_change_validate_subnet(subnet, vlan_l3_interface_name)
        commands = []
        commands.append("configure terminal")
        commands.append('interface Vlan %s' % vlan_id_str)

        ip_adress_cmd = 'ip address %s' % subnet
        if len(existing_subnets) > 0:
            ip_adress_cmd += ' secondary'
        commands.append(ip_adress_cmd)
        commands.append('copy running-config startup-config')
        cmd_string = ' ; '.join(commands)
        self._exec_command(cmd_string)
        self.post_change_validate_subnet(subnet, vlan_l3_interface_name)
        return str(commands)

    def get_ip_addrs_on_interface(self, interface_name):
        self._check_if_connected()
        command = 'show running-config interface %s | grep "ip address"' %\
                  (interface_name)
        output = self._exec_command(command).split('\n')
        subnet_list = [cidr.replace('ip address', '').strip().replace(
            'secondary', '').strip() for cidr in output]
        subnet_list = filter(None, subnet_list)
        return self.filter_invalid_cidr(subnet_list)

    def get_vlan_interface_name(self, vlan_tag):
        self._check_if_connected()
        return 'Vlan%s' % (vlan_tag)

    def _fetch_routes(self, vrf_name=None):
        if vrf_name:
            self.check_vrf_exist(vrf_name)
            cmd = 'show ip route vrf %s ' % vrf_name
        else:
            cmd = 'show ip route '
        ip_route_data = self._get_routes_data(cmd)
        # For different nxos versions, the xml keys are different.
        # Hence to over-come that , we need to handle all the possibilities,
        # with and without keys.
        if '__XML__OPT_Cmd_urib_show_routing_command_vrf' \
                not in ip_route_data:
            ip_route_data = ip_route_data['ip']['route']['vrf']
            if '__XML__PARAM__vrf-known-name' in ip_route_data:
                ip_route_data = (ip_route_data
                                 ['__XML__PARAM__vrf-known-name'])
        else:
            ip_route_data = (
                ip_route_data
                ['__XML__OPT_Cmd_urib_show_routing_command_vrf']
                ['__XML__OPT_Cmd_urib_show_routing_command___readonly__'])
        ip_route_data = (ip_route_data
            ['__readonly__']['TABLE_vrf']['ROW_vrf']
            ['TABLE_addrf']['ROW_addrf'])
        return ip_route_data

    def get_routes(self, vrf_name=None):
        self._check_if_connected()
        ip_route_data = self._fetch_routes(vrf_name)
        all_routes = []
        if vrf_name:
            ip_route_data = (ip_route_data['TABLE_prefix']['ROW_prefix'])
            for ip in ip_route_data:
                all_routes.append(ip['ipprefix'])
        else:
            if 'ipprefix' in ip_route_data:
                all_routes.append(ip_route_data['ipprefix'])
        route_aggregates = self.get_routes_aggregate(vrf_name)
        cidr_list = list(set(all_routes) - set(route_aggregates))
        cidr_list = [d.replace('*>', '') for d in cidr_list]
        return cidr_list

    def _get_vrfs(self):
        self._check_if_connected()
        vrf_cmd = 'show vrf '
        response_dict = self._exec_command_xml(vrf_cmd)
        vrf_list = []
        vrf_data = response_dict['show']['vrf']
        if '__XML__OPT_Cmd_l3vm_show_vrf_cmd_vrf-name' in vrf_data:
            vrf_data = (
                vrf_data
                ['__XML__OPT_Cmd_l3vm_show_vrf_cmd_vrf-name']
                ['__XML__OPT_Cmd_l3vm_show_vrf_cmd_detail']
                ['__XML__OPT_Cmd_l3vm_show_vrf_cmd___readonly__'])
        vrf_data = (vrf_data
                    ['__readonly__']['TABLE_vrf']['ROW_vrf'])
        if not isinstance(vrf_data, list):
            for tag, vrf_name in vrf_data.items():
                if tag == 'vrf_name':
                    vrf_list.append(vrf_name)
                    break
        else:
            for vrf in vrf_data:
                vrf_list.append(vrf['vrf_name'])
        return vrf_list

    def get_routes_aggregate(self, vrf_name=None):
        self._check_if_connected()
        ip_route_data = self._fetch_routes(vrf_name)
        route_aggregates = []
        ip_route_data = ip_route_data['TABLE_prefix']['ROW_prefix']
        # As per document and early talk with net engg, all the aggregates are
        # via Null0 as bigger aggregates act as trash which indicates its the
        # bigger block.
        if not isinstance(ip_route_data, list):
            ip_route_data = [ip_route_data]
        for ip in ip_route_data:
            if 'ifname' in ip['TABLE_path']['ROW_path']:
                if ip['TABLE_path']['ROW_path']['ifname'] ==\
                        'Null0':
                    route_aggregates.append(ip['ipprefix'])
        return route_aggregates

    def _get_routes_data(self, cmd):
        response_dict = self._exec_command_xml(cmd)
        ip_route_data = response_dict['show']
        if '__XML__BLK_Cmd_urib_show_routing_command_routing' in ip_route_data:
            ip_route_data = (
                ip_route_data
                ['__XML__BLK_Cmd_urib_show_routing_command_routing']
                ['__XML__OPT_Cmd_urib_show_routing_command_vrf'][1]
                ['__XML__OPT_Cmd_urib_show_routing_command_ip']
                ['__XML__OPT_Cmd_urib_show_routing_command_unicast']
                ['__XML__OPT_Cmd_urib_show_routing_command_topology']
                ['__XML__OPT_Cmd_urib_show_routing_command_l3vm-info']
                ['__XML__OPT_Cmd_urib_show_routing_command_rpf']
                ['__XML__OPT_Cmd_urib_show_routing_command_ip-addr']
                ['__XML__OPT_Cmd_urib_show_routing_command_protocol']
                ['__XML__OPT_Cmd_urib_show_routing_command_summary'])
        return ip_route_data

    def delete_subnet_on_device(self, subnet, vlan_id):
        self._check_if_connected()
        self.pre_change_validate_vlan(vlan_id)
        commands = []
        commands.append('configure terminal')
        commands.append('interface Vlan %s' % vlan_id)
        ip_adress_cmd = 'no ip address %s secondary' % subnet
        commands.append(ip_adress_cmd)
        commands.append('copy running-config startup-config')
        cmd_string = ' ; '.join(commands)
        self._exec_command(cmd_string)
        return str(commands)

    def set_subnet_primary(self, subnet, vlan_id, one_subnet_only):
        pass

    def check_hidden_routes_aggregates(self, vrf_name=None):
        self._check_if_connected()
        # Cisco bgp aggregates start with convention a.
        # Hence, we are greping on a and range of subnets that
        # can start from 1 to 9.
        if vrf_name:
            self.check_vrf_exist(vrf_name)
            cmd = "show ip bgp vrf %s | grep a[1-9]" % vrf_name
        else:
            cmd = "show ip bgp all | grep a[1-9]"
        response_dict = self._exec_command(cmd)
        hidden_aggr = []
        data = response_dict.split('\n')
        data = filter(None, data)
        for d in data:
            hidden_aggr.append(d.split()[0])
        hidden_aggr = [d.replace('a', '') for d in hidden_aggr]
        hidden_aggr = [d.replace('*>', '') for d in hidden_aggr]
        return hidden_aggr
