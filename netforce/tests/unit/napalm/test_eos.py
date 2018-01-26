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


import mock
from napalm_baseebay import ebay_exceptions

from napalm_base import get_network_driver
from netforce.tests.unit.napalm import base
from pyeapi.eapilib import CommandError


class EosTestSuite(base.DietTestCase):
    """Arista EOS Test Suite

    This test suite performs setup and teardown functions for this file's
    unit tests. Each unit test class should inherit from this class, and
    implement a single "runTest" function.

    """
    def setUp(self):
        """Perform setup activities

        """
        super(EosTestSuite, self).setUp()
        driver = get_network_driver('ebayeos')
        self.driver = driver(
            hostname='127.0.0.1',
            username='arista',
            password='arista'
        )
        self.interface_names = ["Ethernet1", "Ethernet2"]
        mock_mgr = mock.Mock()
        self.driver.manager = mock_mgr
        self.stdout = None

    def tearDown(self):
        """Perform teardown activities

        """

        super(EosTestSuite, self).tearDown()


# Test cases for vlan creation
class test_interface_label_validation_success(EosTestSuite):

    def validate_commands(self, config):
        self.assertIs(2, len(config))

    def mock_interfaces(self, interfaces):
        ifdict = {}

        for ifname in self.interface_names:
            ifdict[ifname] = {
                "name": ifname,
                "description": 'test-label',

            }

        return ifdict

    def runTest(self):

        with mock.patch.object(self.driver, 'load_merge_candidate') \
                as load_merge_candidate_mock:

            load_merge_candidate_mock.side_effect = self.validate_commands

            with mock.patch.object(self.driver, 'commit_config') \
                    as commit_config_mock:

                commit_config_mock.return_value = None

                with mock.patch.object(self.driver, 'get_interfaces_by_name') \
                        as \
                        get_interfaces_mock:
                    with mock.patch.object(self.driver, '_exec_command') \
                            as push_changes:
                        with mock.patch.object(
                                self.driver, '_check_if_connected') \
                                as check_connected:
                            check_connected.return_value = None
                            push_changes.return_value = None
                            get_interfaces_mock.side_effect = \
                                self.mock_interfaces
                            self.driver.update_interface_label('Ethernet1',
                                                               'test-label')


class test_interface_label_post_change_validation_failure(EosTestSuite):

    def validate_commands(self, config):
        self.assertIs(2, len(config))

    def mock_interfaces(self, interfaces):
        ifdict = {}

        for ifname in self.interface_names:
            ifdict[ifname] = {
                "name": ifname,
                "description": 'test-label-1',

            }
        return ifdict

    def runTest(self):

        with mock.patch.object(self.driver, 'get_interfaces_by_name') \
                as \
                get_interfaces_mock:
            with mock.patch.object(self.driver, '_exec_command') \
                    as push_changes:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    check_connected.return_value = None
                    push_changes.return_value = None
                    get_interfaces_mock.side_effect = self.mock_interfaces
                    self.assertRaises(ebay_exceptions.
                                      PostChangeValidationException,
                                      self.driver.update_interface_label,
                                      'Ethernet1', 'test-label')


class test_get_routes_with_vrf(EosTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_exec_command_json') \
                as push_changes:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                with mock.patch.object(self.driver,
                                       'get_routes_aggregate') \
                        as routes_aggregate:
                    routes_aggregate.return_value = []
                    with mock.patch.object(self.driver, '_get_vrfs') as\
                            vrf_mock:
                        vrf_mock.return_value = ['fake-native']
                        check_connected.return_value = None
                        push_changes.return_value = \
                            {
                                "vrfs": {
                                    "fake-native": {
                                        "routes": {
                                            "10.215.112.131/32": {
                                                "kernelProgrammed": True,
                                                "directlyConnected": False,
                                                "preference": 200,
                                                "routeAction": "forward",
                                                "vias": [{
                                                    "interface":
                                                        "Ethernet4/28/1.5",
                                                    "interfaceDescription":
                                                    "L3Q-fake-lc04:5:17/1",
                                                    "nexthopAddr":
                                                    "10.215.100.87"
                                                }],
                                                "metric": 0,
                                                "hardwareProgrammed": True,
                                                "routeType": "eBGP"
                                            },
                                        },
                                        "allRoutesProgrammedKernel": True,
                                        "routingDisabled": False,
                                        "allRoutesProgrammedHardware": True,
                                        "defaultRouteState": "reachable"
                                    }
                                }
                            }
                        ret = self.driver.get_routes("fake-native")
                        expected = ["10.215.112.131/32"]
                        self.assertEqual(expected, ret)


class test_get_routes_aggregate_with_vrf(EosTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_exec_command_json') \
                as push_changes:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                with mock.patch.object(self.driver, '_get_vrfs') as vrf_mock:
                    vrf_mock.return_value = ['fake-native']
                    check_connected.return_value = None
                    push_changes.return_value = \
                        {
                            "vrfs": {
                                "fake-native": {
                                    "routes": {
                                        "10.215.0.0/16": {
                                            "kernelProgrammed": True,
                                            "directlyConnected": True,
                                            "routeAction": "drop",
                                            "vias": [],
                                            "hardwareProgrammed": True,
                                            "routeType": "bgpAggregate"
                                        }
                                    },
                                    "allRoutesProgrammedKernel": True,
                                    "routingDisabled": False,
                                    "allRoutesProgrammedHardware": True,
                                    "defaultRouteState": "reachable"
                                }
                            }
                        }
                    ret = self.driver.get_routes_aggregate("fake-native")
                    expected = ["10.215.0.0/16"]
                    self.assertEqual(expected, ret)


class test_get_ip_addrs_on_interface(EosTestSuite):
    def runTest(self):
        with mock.patch.object(self.driver, '_exec_command_json') \
                as push_changes:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                    check_connected.return_value = None
            push_changes.return_value = \
                {
                    "interfaces": {
                        "Vlan1": {
                            "lastStatusChangeTimestamp": 1501719470.7075827,
                            "name": "Vlan1",
                            "interfaceStatus": "connected",
                            "burnedInAddress": "44:4c:a8:e4:18:84",
                            "mtu": 1500,
                            "hardware": "vlan",
                            "bandwidth": 0,
                            "forwardingModel": "routed",
                            "lineProtocolStatus": "up",
                            "interfaceAddress": [{
                                "secondaryIpsOrderedList": [{
                                    "maskLen": 24,
                                    "address": "192.168.1.1"}],
                                "broadcastAddress":
                                    "255.255.255.255",
                                "virtualSecondaryIps": {},
                                "dhcp": False,
                                "secondaryIps": {
                                    "192.168.3.1": {
                                        "maskLen": 24,
                                        "address": "192.168.1.1"
                                    }
                                },
                                "primaryIp": {
                                    "maskLen": 24,
                                    "address": "192.168.2.1"
                                },
                                "virtualSecondaryIpsOrderedList": [],
                                "virtualIp": {
                                    "maskLen": 0,
                                    "address": "0.0.0.0"
                                }}],
                            "physicalAddress": "44:4c:a8:e4:18:84",
                            "description": ""
                        }
                    }
                }
            data = self.driver.get_ip_addrs_on_interface('Vlan1')
            expected = [u'192.168.1.1/24', u'192.168.2.1/24']
            self.assertEqual(sorted(expected), sorted(data))


class test_delete_subnet_success(EosTestSuite):
    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as vlan_mock:
            vlan_mock.return_value = {
                'name': 'test-vlan',
                'status': 'active'
            }
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                with mock.patch.object(self.driver, '_exec_command') \
                        as push_changes:
                    push_changes.return_value = None
                    check_connected.return_value = None
                    commands = self.driver.delete_subnet_on_device(
                        '1.1.1.1/24', 2)
                    self.assertIsNotNone(commands)


class test_create_subnet_success(EosTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as vlan_mock:
            vlan_mock.return_value = {
                'name': 'test-vlan',
                'status': 'active'
            }

            with mock.patch.object(self.driver,
                                   'get_ip_addrs_on_interface') \
                    as get_subnets_mock:
                with mock.patch.object(self.driver, '_exec_command') \
                        as push_changes:
                    with mock.patch.object(
                            self.driver, '_check_if_connected') \
                            as check_connected:
                        with mock.patch.object(self.driver, 'open') \
                                as open:
                            with mock.patch.object(self.driver, 'close') \
                                    as close:
                                open.return_value = None
                                close.return_value = None
                                check_connected.return_value = None
                                push_changes.return_value = None
                                get_subnets_mock.side_effect = \
                                    [[], ['1.1.1.1/24']]
                                commands = self.driver.create_subnet(
                                    '1.1.1.1/24', 2)
                                self.assertIsNotNone(commands)


class test_get_mac_addresses_on_interface(EosTestSuite):
    def runTest(self):
        with mock.patch.object(self.driver, 'get_interfaces') as \
                interface_mock:
            interface_mock.return_value = \
                ['Ethernet38 is up, line protocol is up (connected)',
                 '  Hardware is Ethernet, address is 001c.7312.692f'
                 ' (bia 001c.7312.692f)',
                 '  Ethernet MTU 9214 bytes , BW 10000000 kbit']
            with mock.patch.object(self.driver, '_exec_command') \
                    as exec_command:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    with mock.patch.object(self.driver, 'open') \
                            as open:
                        with mock.patch.object(self.driver, 'close') \
                                as close:
                            open.return_value = None
                            close.return_value = None
                            check_connected.return_value = None
                            exec_command.return_value = """
                      Mac Address Table
------------------------------------------------------------------

Vlan    Mac Address       Type        Ports      Moves   Last Move
----    -----------       ----        -----      -----   ---------
   1    001c.7315.b96c    STATIC      Router
   1    1cc1.de18.9a42    DYNAMIC     Et38       1       410 days, 10:10:18 ag
   1    1cc1.de18.9a44    DYNAMIC     Et38       1       410 days, 9:43:05 ag
Total Mac Addresses for this criterion: 2
                            """
                            data = \
                                self.driver.get_mac_addresses_on_interface(
                                    'Ethernet38')
                            expected = \
                                [{'vlan': 1,
                                  'mac_address': u'1C:C1:DE:18:9A:42'},
                                 {'vlan': 1,
                                  'mac_address': u'1C:C1:DE:18:9A:44'}]
                            self.assertEqual(expected, data)


class test_get_traffic_on_interface(EosTestSuite):
    def runTest(self):
        with mock.patch.object(self.driver, 'get_interfaces') as\
                interface_mock:
            interface_mock.return_value = \
                ['Ethernet38 is up, line protocol is up (connected)',
                 '  Hardware is Ethernet, address is 001c.7312.692f ('
                 'bia 001c.7312.692f)',
                 '  Ethernet MTU 9214 bytes , BW 10000000 kbit']
            with mock.patch.object(self.driver, '_exec_command') \
                    as exec_command:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    with mock.patch.object(self.driver, 'open') \
                            as open:
                        with mock.patch.object(self.driver, 'close') \
                                as close:
                            open.return_value = None
                            close.return_value = None
                            check_connected.return_value = None
                            exec_command.side_effect = [
                                "  5 minutes input rate 830 Mbps (8.4% with"
                                " framing overhead), 69640 packets/sec\n",
                                "  5 minutes output rate 411 Mbps (4.2% with"
                                " framing overhead), 42739 packets/sec\n"]
                            data = self.driver.get_traffic_on_interface(
                                'Ethernet38')
                            expected = (830000000, 411000000)
                            self.assertEqual(expected, data)


class test_get_routes_aggregate_flat_network(EosTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_exec_command_json') \
                as push_changes:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                check_connected.return_value = None
                push_changes.side_effect = \
                    [{u'vrfs': {u'default': {u'routes': {},
                                             u'defaultRouteState': u'notSet',
                                             u'allRoutesProgrammedKernel':
                                                 True, u'routingDisabled':
                                                 False,
                                             u'allRoutesProgrammedHardware':
                                                 True}}}, {
                        "vrfs": {
                            "default": {
                                "routes": {
                                    "10.174.128.0/18": {
                                        "kernelProgrammed": True,
                                        "directlyConnected": True,
                                        "routeAction": "drop",
                                        "vias": [],
                                        "hardwareProgrammed": True,
                                        "routeType": "static"
                                    },
                                    "10.20.125.0/25": {
                                        "kernelProgrammed": True,
                                        "directlyConnected": True,
                                        "routeAction": "drop",
                                        "vias": [],
                                        "hardwareProgrammed": True,
                                        "routeType": "static"
                                    }
                                },
                                "allRoutesProgrammedKernel": True,
                                "routingDisabled": True,
                                "allRoutesProgrammedHardware": True,
                                "defaultRouteState": "notSet"
                            }
                        }
                    }]
                ret = self.driver.get_routes_aggregate()
                expected = [u'10.174.128.0/18', u'10.20.125.0/25']
                self.assertEqual(sorted(expected), sorted(ret))
