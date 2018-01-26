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


import abc
import six


@six.add_metaclass(abc.ABCMeta)
class EbayNetworkDriver(object):

    def update_switch_port_vlans(self, interface, port):
        """
            updating switch port mode and tag the port with specified vlans.

        :param interface:
        :param port: {
                        "switch_port_mode":"trunk",
                        "admin_status":"ACTIVE",
                        "vlans":[
                        {
                            "vlan":{
                            "tag":"3",
                            "is_native":true
                            }
                        },
                        {
                            "vlan":{
                            "tag":"4",
                            "is_native":false
                            }
                        }
                        ]
                     }
        :param old_switch_port_mode This is temporary until pre-validation
                                    is ready.
        :return: commands
        """
        #pass
        interface = str(interface)
        mode = port['switch_port_mode']
        pre_check_data = self.pre_check_update_switch_port_vlans(
            interface, mode, port)
        if not pre_check_data:
            return
        requested_vlan_tags, current_running_config = pre_check_data
        commands = self.update_switch_port_vlans_on_device(interface, port)
        self.post_check_update_switch_port_vlans(
            interface, current_running_config, port, requested_vlan_tags)
        return commands

    @abc.abstractmethod
    def get_vlan(self, number):
        """
            Get vlan by number
        :param number
        :return:{'status': u'active', 'name': u'test-vlan-2'}
        """
        pass

    @abc.abstractmethod
    def create_vlan(self, name, number, is_active):
        """
        Create a new vlan.

        :param name:
        :param number:
        :param is_active:
        :return:
        """
        pass

    @abc.abstractmethod
    def update_interface_label(self, interface, label):
        """

        :param interface:
        :param label
        :return:
        """
        pass

    @abc.abstractmethod
    def get_vlans_on_interface(self, interface_number):
        """

        :param interface_number:
        :return: get vlans configured on interface.

        {'native_vlan': u'2', 'access_vlan': u'1', 'trunk_vlans': u'2-3'}
        """
        pass

    @abc.abstractmethod
    def get_interfaces_by_name(self, interface_names):
        """
        Provide
        :param interface_names:
        :return:
          Returns a dictionary of dictionaries. The keys for the first
        dictionary will be the interfaces in the devices. The inner
        dictionary will containing the following data for
        the interface_names:

         * is_up (True/False)
         * is_enabled (True/False)
         * description (string)
         * last_flapped (int in seconds)
         * speed (int in Mbit)
         * mac_address (string)

        For example::

            {
            u'Management1':
                {
                'is_up': False,
                'is_enabled': False,
                'description': u'',
                'last_flapped': -1,
                'speed': 1000,
                'mac_address': u'dead:beef:dead',
                },
            u'Ethernet1':
                {
                'is_up': True,
                'is_enabled': True,
                'description': u'foo',
                'last_flapped': 1429978575.1554043,
                'speed': 1000,
                'mac_address': u'beef:dead:beef',
                }
            }
        """
        pass

    def disable_interface(self, interface):
        """Disable device interface

        :param interface: An interface to disable
        :return: commands
        """
        interface = str(interface)
        current_running_config = self.pre_check_disable_interface(interface)
        if not current_running_config:
            return
        commands = self.disable_interface_on_device(interface)
        self.post_check_disable_interface(interface,
                                         current_running_config)
        return commands

    def enable_interface(self, interface):
        """Enable device interface

        :param interface: An interface to enable
        :return: commands
        """
        interface = str(interface)
        pre_check_data = self.pre_check_enable_interface(interface)
        if not pre_check_data:
            return
        current_running_config = pre_check_data
        commands = self.enable_interface_on_device(interface)
        self.post_check_enable_interface(interface,
                                         current_running_config)
        return commands

    @abc.abstractmethod
    def get_interface_running_config(self, interface):
        """

        :param interface:
        :return: running configuration of an interface
        """
        pass

    @abc.abstractmethod
    def get_mac_addresses_on_interface(self, interface_name, vlan=None):
        """
        :param interface_name:
        :return: a list of list which has elements in order: mac address, vlan.
                e.g: [{'mac_address': 'dead.dead.dead', 'vlan': 2},
                      {'mac_address': 'beef.beef.beef', 'vlan': 3}]
        """
        pass

    @abc.abstractmethod
    def get_traffic_on_interface(self, interface_name):
        """
        :param interface_name:
        :return:  {
            "input_bits": "111",
            "output_bits": "3000"
            }
        """

    @abc.abstractmethod
    def create_subnet(self, subnet, vlan_id):
        """
        :param subnet:
        :param vlan_id:
        :return: return a list of commands executed
        """
        pass

    @abc.abstractmethod
    def get_ip_addrs_on_interface(self, interface_name):
        """

        :param vlan_interface_name:
        :return: configured subnets on the vlan interface
        """
        pass

    @abc.abstractmethod
    def get_vlan_interface_name(self, vlan_tag):
        """

        :param vlan_tag:
        :return: vlan_l3_interface_name

        """
        pass

    @abc.abstractmethod
    def get_routes(self, vrf_name=None):
        """

        :param vrf_name
        :return: subnet_cidr_list

        """
        pass

    @abc.abstractmethod
    def update_switch_port_vlans_on_device(self, interface, port):
        """
            updating switch port mode and tag the port with specified vlans.

        :param interface:
        :param port: {
                        "switch_port_mode":"trunk",
                        "admin_status":"ACTIVE",
                        "vlans":[
                        {
                            "vlan":{
                            "tag":"3",
                            "is_native":true
                            }
                        },
                        {
                            "vlan":{
                            "tag":"4",
                            "is_native":false
                            }
                        }
                        ]
                     }
        :param old_switch_port_mode This is temporary until pre-validation
                                    is ready.
        :return: commands
        """

    @abc.abstractmethod
    def get_routes_aggregate(self, vrf_name=None):
        """

        :return: subnet_cidr_list

        """
        pass

    @abc.abstractmethod
    def delete_subnet_on_device(self, subnet, vlan_id):
        """
        :param subnet:
        :param vlan_id:
        :return: return a list of commands executed
        """
        pass

    @abc.abstractmethod
    def set_subnet_primary(self, subnet, vlan_id,
                           one_subnet_only):
        """
        :param subnet_cidr e.g. 10.x.x.1/24:
        :param vlan_id:
        :param enable_set_primary_for_one_subnet:
        :return: return a list of commands executed
        """
        pass

    @abc.abstractmethod
    def enable_interface_on_device(self, interface):
        """
            Enable Port on TOR/LC switch.
        :param interface: 'et3'
        :return: commands
        """
        pass

    @abc.abstractmethod
    def is_interface_enabled(self, interface):
        """
            Check if port is enabled/disabled
        :param interface: 'et3'
        :return: boolean
        """
        pass

    @abc.abstractmethod
    def disable_interface_on_device(self, interface):
        """
            Disable Port on TOR/LC switch.
        :param interface: 'et3'
        :return: commands
        """
        pass

    @abc.abstractmethod
    def check_hidden_routes_aggregates(self, vrf_name=None):
        """
            Check if this subnet is not part of big block for which no subnet
            is yet released.

        :param vrf_name: 'eaz'
        :return: list of hidden_routes_aggregate
        """
        pass
