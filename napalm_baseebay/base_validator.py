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


import napalm_baseebay.ebay_exceptions as exceptions
import netaddr
from oslo_config import cfg
from oslo_log import log as logging
import socket

LOG = logging.getLogger(__name__)

device_traffic_opts = [
    cfg.StrOpt('traffic_threshold_on_interface',
               default='60',
               help='in and out traffic threshold in kbps'),
    cfg.BoolOpt('enable_traffic_check', default=False,
               help="Enable/disable flag for traffic check"),
    cfg.IntOpt('max_subnets_each_interface',
               default='8',
               help='Maximum subnets configured on a vlan interface.')
]

cfg.CONF.register_opts(device_traffic_opts)


"""
    A validator mixin used in conjunction with driver implementations.
"""


class ValidatorMixin(object):

    def post_change_validate_vlan(self, number):
        vlan = self.get_vlan(number)
        if not vlan:
            raise exceptions.PostChangeValidationException(
                'vlan %s does not exist' % str(number))

    def pre_change_validate_vlan(self, number):
        vlan = self.get_vlan(number)
        if not vlan:
            raise exceptions.EntityDoesNotExistsException(
                'vlan %s does not exist' % str(number))

    def _check_overlapping_subnets(self, existing_subnets, subnet):
        ipnetwork_a = netaddr.IPNetwork(subnet)
        for sub in existing_subnets:
            ipnetwork_b = netaddr.IPNetwork(sub)
            if ipnetwork_a.prefixlen < ipnetwork_b.prefixlen:
                if ipnetwork_b in ipnetwork_a:
                    return sub
            else:
                if ipnetwork_a in ipnetwork_b:
                    return sub
        return None

    def pre_change_validate_subnet(self, subnet, vlan_l3_interface_name):
        existing_subnets = self. \
            get_ip_addrs_on_interface(vlan_l3_interface_name)
        if len(existing_subnets) >= cfg.CONF.max_subnets_each_interface:
            raise exceptions.MaxNumberOfAllowedSubnetsAlreadyConfigured(
                cfg.CONF.max_subnets_each_interface, vlan_l3_interface_name)

        overlapping_subnet = self._check_overlapping_subnets(existing_subnets,
                                                             subnet)
        if overlapping_subnet:
            int_name = vlan_l3_interface_name
            raise \
                exceptions.SubnetAlreadyConfiguredException(
                    subnet=subnet,
                    vlan_interface_name=int_name,
                    overlapping_subnet=overlapping_subnet)
        return existing_subnets

    def post_change_validate_subnet(self, subnet, vlan_l3_interface_name):
        configured_subnets = self.\
            get_ip_addrs_on_interface(vlan_l3_interface_name)

        if subnet not in configured_subnets:
            raise exceptions.PostChangeValidationException(
                'subnet %s not configured on vlan interface %s. Found %s'
                % (subnet, vlan_l3_interface_name, configured_subnets))

    def check_traffic_on_interface(self, interface):
        check_traffic = cfg.CONF.enable_traffic_check
        if check_traffic:
            input_bits, output_bits = self.get_traffic_on_interface(
                interface)
            self.parse_and_compare_traffic_on_interface(
                interface, input_bits, output_bits)

    def parse_and_compare_traffic_on_interface(self, interface_name,
                                               input_bits, output_bits):
        # Each vendor returns traffic in bits per second.
        # Hence, we convert default kbps threshold to bits per second.
        traffic_threshold = cfg.CONF.traffic_threshold_on_interface
        traffic_threshold_bits = traffic_threshold * 1000
        if input_bits > traffic_threshold_bits or output_bits > \
                traffic_threshold_bits:
            message = "input  %s traffic and output %s traffic on " \
                      "interface %s is above the threshold %skbps" % \
                      (input_bits, output_bits,
                       interface_name, traffic_threshold)
            raise exceptions.PortTrafficAboveThreshold(message)
        LOG.debug("Traffic stats OK for port %s" % interface_name)

    def compare_vlan_config(self, interface, port, vlan_data):

        vlan_tags = self.get_requested_vlans(port['vlans'])
        current_trunk_vlan_tags = vlan_data.get('trunk_vlans', None)
        current_access_vlan = vlan_data.get('access_vlan', None)
        if current_trunk_vlan_tags:
            current_trunk_vlan_tags = self._parse_vlan_range(
                [str(member) for member in current_trunk_vlan_tags])
        current_switchport_mode = vlan_data.get('switch_port_mode', None)
        if port['switch_port_mode'] != current_switchport_mode:
            return False
        if current_trunk_vlan_tags:
            if set(current_trunk_vlan_tags) != set(vlan_tags):
                return False

        if current_access_vlan:
            if set(current_access_vlan) != set(vlan_tags):
                return False

        native_vlan_id = vlan_data.get('native_vlan', None)
        requested_native_vlan_id = str(self._get_requested_native_vlan(
            port['vlans']))
        if native_vlan_id != requested_native_vlan_id and \
           current_switchport_mode == 'trunk':
            return False
        return True

    def get_requested_vlans(self, vlans):

        vlan_tags = []
        if vlans:
            for vlan in vlans:
                if vlan.get('vlan', None):
                    vlan_data = vlan['vlan']
                    if vlan_data.get('tag', None):
                        vlan_tags.append(str(vlan_data['tag']))
        return vlan_tags

    def _get_requested_native_vlan(self, vlans):

        for vlan in vlans:
            if vlan.get('vlan', None):
                vlan_data = vlan['vlan']
                if vlan_data.get('is_native', None):
                    return vlan_data.get('tag', None)

    def _parse_vlan_range(self, vlan_members):
        # Iterate the members and parse '-' and get the range of vlan members.
        # e.g. vlan members = ['51-60']. Convert it to ['51', '52'..].
        # e.g. vlan_members = ['1', '20', '31-33', 'tatat'] =>
        # ['1', '20', '31', '32', '33']
        all_members = []
        LOG.debug("vlan members are %s" % vlan_members)
        for mem in vlan_members:
            if mem.isdigit():
                all_members.append(str(mem))
            elif '-' in mem:
                vlan_range = mem.split('-')
                for i in range(int(vlan_range[0]), int(vlan_range[1]) + 1):
                    all_members.append(str(i))
                continue
        return all_members

    def pre_check_update_switch_port_vlans(
            self, interface, mode, port):
        if mode not in ('access', 'trunk'):
            raise exceptions.InvalidValueForParameterException(
                'invalid value [%s] for parameter switch_port_mode. '
                'valid values are trunk and access' % (mode))

        self.check_traffic_on_interface([interface])
        requested_vlan_tags = self.get_requested_vlans(port['vlans'])
        current_running_config = self.get_vlans_on_interface(interface)
        # Compare the tags and make sure that tags exist on device
        self._validate_vlan_tags(requested_vlan_tags)
        # check the current member list on port before pushing changes.
        # If request is to push same settings as current running config,
        # just return and do nothing.
        if self.compare_vlan_config(interface, port, current_running_config):
            LOG.info("Current configuration %s is same as requested"
                     " configuration %s. Hence changes will not be pushed." %
                     (current_running_config, requested_vlan_tags))
            return
        return (requested_vlan_tags, current_running_config)

    def post_check_update_switch_port_vlans(
            self, interface, current_running_config, port,
            requested_vlan_tags):
        # Ensure the configuration is same as the one requested.
        vlan_config = self.get_vlans_on_interface(interface)
        if not self.compare_vlan_config(interface, port, vlan_config):
            msg = 'Unable to push changes to device from current config %s' \
                  ' to requested vlans: %s' \
                  % (current_running_config, requested_vlan_tags)
            raise exceptions.PostChangeValidationException(msg)
        LOG.debug("successfully pushed changes to device for interface %s" %
                  interface)

    def filter_invalid_cidr(self, device_cidr_list):
        cidr_list = []
        for cidr in device_cidr_list:
            try:
                if '/' in cidr:
                    ip_addr = cidr.split('/')[0]
                    socket.inet_aton(ip_addr)
                    cidr_list.append(cidr)
            except Exception:
                    continue
        return cidr_list

    def check_vrf_exist(self, vrf_name):
        vrf_list = self._get_vrfs()
        if vrf_name not in vrf_list:
            raise exceptions.EntityDoesNotExistsException(
                'vrf %s does not exist.' % vrf_name)

    def _check_interface_config(self, interface):
        interfaces_data = self.get_interfaces_by_name(interface)
        if interface not in interfaces_data:
            raise exceptions.EntityDoesNotExistsException(
                'interface %s does not exists' % interface)
        self.check_traffic_on_interface(interface)
        is_enabled = self.is_interface_enabled(interface)
        current_running_config = self.get_interface_running_config(
            interface)
        return is_enabled, current_running_config

    def pre_check_enable_interface(self, interface):
        # Ensure the configuration is not same as the one requested.
        is_enabled, current_running_config = self._check_interface_config(
            interface)
        if is_enabled:
            # If port is already enabled, just return saying current is same
            # as requested.
            LOG.info("Port %s is already enabled. Hence changes will not be"
                     " pushed.", interface)
            return
        return current_running_config

    def post_check_enable_interface(self, interface,
                                    previous_running_config):
        # Ensure the configuration is not same as the one requested.
        is_enabled, current_running_config = self._check_interface_config(
            interface)
        if previous_running_config == current_running_config and not \
                is_enabled:
            msg = 'Unable to enable port for current config %s' \
                  % current_running_config
            raise exceptions.PostChangeValidationException(msg)
        LOG.debug("successfully enabled port %s", interface)

    def pre_check_disable_interface(self, interface):
        # Ensure the configuration is not same as the one requested.
        is_enabled, current_running_config = self._check_interface_config(
            interface)
        if not is_enabled:
            # If port is already disabled, just return saying current is same
            # as requested.
            LOG.info("Since port %s is already disabled, no changes will be"
                     " pushed." % interface)
            return
        return current_running_config

    def post_check_disable_interface(self, interface,
                                     previous_running_config):
        # Ensure the configuration is not same as the one requested.
        is_enabled, current_running_config = self._check_interface_config(
            interface)
        if is_enabled:
            msg = 'Unable to shutdown port for current config %s',\
                  current_running_config
            raise exceptions.PostChangeValidationException(msg)
        LOG.debug("successfully disabled port %s", interface)

    def convert_to_bits_per_sec(self, trans_unit, bits):
        trans_unit = trans_unit.lower()
        if trans_unit == 'bps' or trans_unit == 'bits/sec':
            return int(bits)
        elif trans_unit == 'kbps':
            return int(bits) * 1000
        elif trans_unit == 'mbps':
            return int(bits) * 1000000
        else:
            raise exceptions.InvalidValueForParameterException(
                'invalid value [%s] for parameter bits transmission unit. '
                'Supported values are bps, mbps and kbps' % (trans_unit))
