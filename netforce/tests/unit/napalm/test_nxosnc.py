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
from napalm_base import get_network_driver
from napalm_baseebay import ebay_exceptions
from netforce.tests.unit.napalm import base


class NexusOSTestSuite(base.DietTestCase):
    """Nexus OS  Test Suite

    This test suite performs setup and teardown functions for this file's
    unit tests. Each unit test class should inherit from this class, and
    implement a single "runTest" function.

    """

    def setUp(self):
        """Perform setup activities

        """
        super(NexusOSTestSuite, self).setUp()
        driver = get_network_driver('ebaynxos')
        self.driver = driver(
            hostname='127.0.0.1',
            username='cisco',
            password='cisco'
        )
        self.interface_names = ["Ethernet1", "Ethernet2"]
        mock_mgr = mock.Mock()
        self.driver.manager = mock_mgr
        self.stdout = None

    def tearDown(self):
        """Perform teardown activities

        """

        super(NexusOSTestSuite, self).tearDown()


class test_update_switch_port_on_interface_vlan_suspended(NexusOSTestSuite):

    def mock_get_vlan(self, *args, **kwargs):
        return {
                    'name': 'test-vlan-2',
                    'status': 'suspend'
        }

    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as get_vlan_mocks:
            with mock.patch.object(self.driver, 'compare_vlan_config') \
                    as compare_config:
                with mock.patch.object(self.driver, 'get_vlans_on_interface') \
                        as get_vlan_interface_mock:
                    with mock.patch.object(self.driver, '_exec_command') \
                            as push_changes:
                        with mock.patch.object(
                                self.driver, '_check_if_connected') \
                                as check_connected:
                            check_connected.return_value = None
                            push_changes.return_value = None
                            get_vlan_interface_mock.return_vlaue = {
                                'switch_port_mode': u'trunk',
                                'native_vlan': u'3', 'trunk_vlans': u'3-4'
                            }
                            compare_config.side_effect = [False, True]
                            get_vlan_mocks.side_effect = self.mock_get_vlan

                            port = {
                                "switch_port_mode": "access",
                                "admin_status": "SUSPENDED",
                                "vlans": [
                                    {
                                        "vlan": {
                                            "tag": "2"
                                        }
                                    }
                                ]
                            }

                            self.assertRaises(
                                ebay_exceptions.EntityInSuspendedModeException,
                                self.driver.update_switch_port_vlans,
                                'Ethernet1', port)


class test_update_switch_port_on_int_multi_vlan_not_support_acc_mode(
        NexusOSTestSuite):

    def mock_get_vlan(self, *args, **kwargs):

        return {
            'name': 'test-vlan-2',
            'status': 'active'
        }

    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as get_vlan_mocks:
            with mock.patch.object(self.driver, 'compare_vlan_config') \
                    as compare_config:
                with mock.patch.object(self.driver, 'get_vlans_on_interface') \
                        as get_vlan_interface_mock:
                    with mock.patch.object(self.driver, '_exec_command') \
                            as push_changes:
                        with mock.patch.object(
                                self.driver, '_check_if_connected') \
                                as check_connected:
                            check_connected.return_value = None
                            push_changes.return_value = None
                            get_vlan_interface_mock.return_vlaue = {
                                'switch_port_mode': u'trunk',
                                'native_vlan': u'3', 'trunk_vlans': u'3-4'
                            }
                            compare_config.side_effect = [False, True]
                            get_vlan_mocks.side_effect = self.mock_get_vlan
                            port = {
                                "switch_port_mode": "access",
                                "admin_status": "SUSPENDED",
                                "vlans": [
                                    {
                                        "vlan": {
                                            "tag": "2"
                                        }
                                    },
                                    {
                                        "vlan": {
                                            "tag": "3"
                                        }
                                    }
                                ]
                            }
                            self.assertRaises(
                                ebay_exceptions.MoreThanOneAccessVlan,
                                self.driver.update_switch_port_vlans,
                                'Ethernet1', port)


class test_update_switch_port_on_interface_invalid_switch_port_mode(
                NexusOSTestSuite):

    def mock_get_vlan(self, *args, **kwargs):
        if kwargs['number'] == 2:
            return {
                'name': 'test-vlan-2',
                'status': 'active'
            }
        else:
            return {
                'name': 'test-vlan-3',
                'status': 'active'
            }

    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as get_vlan_mocks:
            get_vlan_mocks.side_effect = self.mock_get_vlan
            with mock.patch.object(self.driver, '_exec_command') \
                    as push_changes:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    check_connected.return_value = None
                    push_changes.return_value = None
                    port = {
                        "switch_port_mode": "invalid",
                        "admin_status": "ACTIVE",
                        "vlans": [
                            {
                                "vlan": {
                                    "tag": "2",
                                    "is_native": False
                                },
                            },
                            {
                                "vlan": {
                                    "tag": "3",
                                    "is_native": True
                                }
                            }
                        ]
                    }

                    self.assertRaises(ebay_exceptions.
                                      InvalidValueForParameterException,
                                      self.driver.update_switch_port_vlans,
                                      'Et1', port)


class test_update_switch_port_on_interface_access_mode_success(
    NexusOSTestSuite):

    def validate_commands(self, config):
        self.assertIs(5, len(config))

    def mock_get_vlan(self, *args, **kwargs):
        return {
            'name': 'test-vlan-2',
            'status': 'active'
        }

    def mock_get_vlans_on_interfaces(self, interfaces):
        return {
            'access_vlan': '2'
        }

    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as get_vlan_mocks:
            get_vlan_mocks.side_effect = self.mock_get_vlan

            with mock.patch.object(self.driver, '_exec_command') \
                    as push_changes:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    check_connected.return_value = None
                    push_changes.exec_command.return_value = None
                    port = {
                        "switch_port_mode": "access",
                        "admin_status": "ACTIVE",
                        "vlans": [
                            {
                                "vlan": {
                                    "tag": "2"
                                }
                            }
                        ]
                    }

                    with mock.patch.object(self.driver,
                                           'get_vlans_on_interface')\
                            as vlan_if_mock:
                        with mock.patch.object(self.driver, 'compare_vlan_config') \
                                as compare_config:
                            compare_config.side_effect = [False, True]
                            vlan_if_mock.side_effect = \
                                self.mock_get_vlans_on_interfaces
                            self.driver.update_switch_port_vlans('Ethernet1',
                                                                 port)


class test_update_switch_port_prevalidation_success(
    NexusOSTestSuite):

    def validate_commands(self, config):
        self.assertIs(5, len(config))

    def mock_get_vlan(self, *args, **kwargs):
        return {
            'name': 'test-vlan-2',
            'status': 'active'
        }

    def mock_get_vlans_on_interfaces(self, interfaces):
        return {
            'access_vlan': '2'
        }

    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as get_vlan_mocks:
            get_vlan_mocks.side_effect = self.mock_get_vlan

            with mock.patch.object(self.driver, '_exec_command') \
                    as push_changes:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    check_connected.return_value = None
                    push_changes.return_value = None

                    port = {
                        "switch_port_mode": "access",
                        "admin_status": "ACTIVE",
                        "vlans": [
                            {
                                "vlan": {
                                    "tag": "2"
                                }
                            }
                        ]
                    }

                    with mock.patch.object(self.driver,
                                           'get_vlans_on_interface')\
                            as vlan_if_mock:
                        with mock.patch.object(self.driver, 'compare_vlan_config') \
                                as compare_config:
                            compare_config.side_effect = [True, True]
                            vlan_if_mock.side_effect = \
                                self.mock_get_vlans_on_interfaces
                            self.driver.update_switch_port_vlans('Ethernet1',
                                                                 port)


class test_update_switch_port_postvalidation_failure(
    NexusOSTestSuite):

    def validate_commands(self, config):
        self.assertIs(5, len(config))

    def mock_get_vlan(self, *args, **kwargs):
        return {
            'name': 'test-vlan-2',
            'status': 'active'
        }

    def mock_get_vlans_on_interfaces(self, interfaces):
        return {
            'access_vlan': '2'
        }

    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as get_vlan_mocks:
            get_vlan_mocks.side_effect = self.mock_get_vlan
            port = {
                "switch_port_mode": "access",
                "admin_status": "ACTIVE",
                "vlans": [
                    {
                        "vlan": {
                            "tag": "2"
                        }
                    }
                ]
            }

            with mock.patch.object(self.driver,
                                   'get_vlans_on_interface')\
                    as vlan_if_mock:
                with mock.patch.object(self.driver, 'compare_vlan_config') \
                        as compare_config:
                    with mock.patch.object(self.driver, '_exec_command') \
                            as push_changes:
                        with mock.patch.object(
                                self.driver, '_check_if_connected') \
                                as check_connected:
                            check_connected.return_value = None
                            push_changes.exec_command.return_value = None
                            compare_config.side_effect = [False, False]
                            vlan_if_mock.side_effect = \
                                self.mock_get_vlans_on_interfaces
                            self.assertRaises(ebay_exceptions.
                                              PostChangeValidationException,
                                              self.driver.
                                              update_switch_port_vlans,
                                              'Ethernet1', port)


class test_interface_label_validation_success(NexusOSTestSuite):

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


class test_interface_label_post_change_validation_failure(NexusOSTestSuite):

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


class test_create_subnet_success(NexusOSTestSuite):

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


class test_create_subnet_failure_vlan_not_found(NexusOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as vlan_mock:
            vlan_mock.return_value = None

            with mock.patch.object(self.driver,
                                   'get_ip_addrs_on_interface') \
                    as get_subnets_mock:
                with mock.patch.object(self.driver, '_exec_command') \
                        as push_changes:
                    with mock.patch.object(
                            self.driver, '_check_if_connected') \
                            as check_connected:
                        check_connected.return_value = None
                        push_changes.return_value = None
                        get_subnets_mock.side_effect = [[], ['1.1.1.1/24']]
                        self.assertRaises(ebay_exceptions.
                                          EntityDoesNotExistsException,
                                          self.driver.create_subnet,
                                          '1.1.1.1/24',
                                          2)


class test_create_subnet_failure_in_config_push(NexusOSTestSuite):

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
                                get_subnets_mock.side_effect = [[], []]
                                self.assertRaises(
                                    ebay_exceptions.
                                    PostChangeValidationException,
                                    self.driver.create_subnet,
                                    '1.1.1.1/24', 2)


class test_create_subnet_failure_subnet_already_exists(NexusOSTestSuite):

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
                        check_connected.return_value = None
                        push_changes.return_value = None
                        get_subnets_mock.side_effect = [['1.1.1.1/24']]
                        self.assertRaises(ebay_exceptions.
                                          SubnetAlreadyConfiguredException,
                                          self.driver.create_subnet,
                                          '1.1.1.1/24',
                                          2)


class test_get_mac_addresses_on_interface(NexusOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_exec_command') \
                as push_changes:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                check_connected.return_value = None
                push_changes.return_value \
                    = '''<?xml version="1.0" encoding="ISO-8859-1"?>
                <nf:rpc-reply>
                  <nf:data>
                    <show>
                      <mac>
                        <address-table>
                          <__XML__OPT_Cmd_show_mac_addr_tbl_static>
                            <__XML__OPT_Cmd_show_mac_addr_tbl_address>
                              <__XML__OPT_Cmd_show_mac_addr_tbl___readonly__>
                                <__readonly__>
                                  <TABLE_mac_address>
                                    <ROW_mac_address>
                                      <disp_mac_addr>dead.dead.dead</disp_mac_addr>
                                      <disp_type>* </disp_type>
                                      <disp_vlan>2</disp_vlan>
                                      <disp_is_static>disabled</disp_is_static>
                                      <disp_age>0</disp_age>
                                      <disp_is_secure>disabled</disp_is_secure>
                                      <disp_is_ntfy>disabled</disp_is_ntfy>
                                      <disp_port>Ethernet1/1</disp_port>
                                    </ROW_mac_address>
                                  </TABLE_mac_address>
                                </__readonly__>
                              </__XML__OPT_Cmd_show_mac_addr_tbl___readonly__>
                            </__XML__OPT_Cmd_show_mac_addr_tbl_address>
                          </__XML__OPT_Cmd_show_mac_addr_tbl_static>
                        </address-table>
                      </mac>
                    </show>
                  </nf:data>
                </nf:rpc-reply>
                ]]>]]>
                '''
                ret = self.driver.get_mac_addresses_on_interface(
                    'Ethernet1/1', 2)
                expected = [{'mac_address': 'dead.dead.dead', 'vlan': 2}]
                self.assertEqual(expected, ret)
        #cmd = 'show mac address-table interface %s vlan %s' % ('Ethernet1/1',
        #                                                       2)
        #self.driver.manager.exec_command.assert_called_once_with(cmd)


class test_get_mac_addresses_on_interface_more_than_one_row(NexusOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_exec_command') \
                as push_changes:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                check_connected.return_value = None
                push_changes.return_value \
                    = '''<?xml version="1.0" encoding="ISO-8859-1"?>
                <nf:rpc-reply>
                  <nf:data>
                    <show>
                      <mac>
                        <address-table>
                          <__XML__OPT_Cmd_show_mac_addr_tbl_static>
                            <__XML__OPT_Cmd_show_mac_addr_tbl_address>
                              <__XML__OPT_Cmd_show_mac_addr_tbl___readonly__>
                                <__readonly__>
                                  <TABLE_mac_address>
                                    <ROW_mac_address>
                                      <disp_mac_addr>dead.dead.dead</disp_mac_addr>
                                      <disp_type>* </disp_type>
                                      <disp_vlan>2</disp_vlan>
                                      <disp_is_static>disabled</disp_is_static>
                                      <disp_age>0</disp_age>
                                      <disp_is_secure>disabled</disp_is_secure>
                                      <disp_is_ntfy>disabled</disp_is_ntfy>
                                      <disp_port>Ethernet1/1</disp_port>
                                    </ROW_mac_address>
                                    <ROW_mac_address>
                                      <disp_mac_addr>beef.beef.beef</disp_mac_addr>
                                      <disp_type>* </disp_type>
                                      <disp_vlan>2</disp_vlan>
                                      <disp_is_static>disabled</disp_is_static>
                                      <disp_age>0</disp_age>
                                      <disp_is_secure>disabled</disp_is_secure>
                                      <disp_is_ntfy>disabled</disp_is_ntfy>
                                      <disp_port>Ethernet1/1</disp_port>
                                    </ROW_mac_address>
                                  </TABLE_mac_address>
                                </__readonly__>
                              </__XML__OPT_Cmd_show_mac_addr_tbl___readonly__>
                            </__XML__OPT_Cmd_show_mac_addr_tbl_address>
                          </__XML__OPT_Cmd_show_mac_addr_tbl_static>
                        </address-table>
                      </mac>
                    </show>
                  </nf:data>
                </nf:rpc-reply>
                ]]>]]>
                '''
                ret = self.driver.get_mac_addresses_on_interface(
                    'Ethernet1/1', 2)
                expected = [{'mac_address': 'dead.dead.dead', 'vlan': 2},
                            {'mac_address': 'beef.beef.beef', 'vlan': 2}]
                self.assertEqual(expected, ret)
        #cmd = 'show mac address-table interface %s vlan %s' % ('Ethernet1/1',
        #                                                       2)
        #self.driver.manager.exec_command.assert_called_once_with([cmd])


class test_get_mac_addresses_on_interface_empty(NexusOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_exec_command') \
                as push_changes:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                check_connected.return_value = None
                push_changes.return_value \
                    = '''<?xml version="1.0" encoding="ISO-8859-1"?>
                <nf:rpc-reply>
                  <nf:data>
                    <show>
                      <mac>
                        <address-table>
                          <__XML__OPT_Cmd_show_mac_addr_tbl_static>
                            <__XML__OPT_Cmd_show_mac_addr_tbl_address>
                              <__XML__OPT_Cmd_show_mac_addr_tbl___readonly__>
                                <__readonly__>
                                <header>fake header</header>
                                </__readonly__>
                              </__XML__OPT_Cmd_show_mac_addr_tbl___readonly__>
                            </__XML__OPT_Cmd_show_mac_addr_tbl_address>
                          </__XML__OPT_Cmd_show_mac_addr_tbl_static>
                        </address-table>
                      </mac>
                    </show>
                  </nf:data>
                </nf:rpc-reply>
                ]]>]]>
                '''
                ret = self.driver.get_mac_addresses_on_interface(
                    'Ethernet1/1', 2)
                expected = []
                self.assertEqual(expected, ret)
        #cmd = 'show mac address-table interface %s vlan %s' % ('Ethernet1/1',
        #                                                       2)
        #self.driver.manager.exec_command.assert_called_once_with([cmd])


class test_get_traffic_on_interface(NexusOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_exec_command') \
                as push_changes:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                check_connected.return_value = None
                push_changes.return_value \
                    = " input rate 3.27 Kbps, 0 pps; output rate 3.78 Kbps," \
                      " 1 pps\n"
                data = self.driver.get_traffic_on_interface('Ethernet1/1')
                expected = (3000, 4000)
                self.assertEqual(expected, data)

routes_string = '''<?xml version="1.0" encoding="ISO-8859-1"?>
                    <nf:rpc-reply>
                    <nf:data>
                      <show>
                        <__XML__BLK_Cmd_urib_show_routing_command_routing>
                          <__XML__OPT_Cmd_urib_show_routing_command_vrf>
                        <__XML__OPT_Cmd_urib_show_routing_command_ip>
                          <ip/>
                          </__XML__OPT_Cmd_urib_show_routing_command_ip>
                        </__XML__OPT_Cmd_urib_show_routing_command_vrf>
                          <ip>
                          <route/>
                          </ip>
                        <__XML__OPT_Cmd_urib_show_routing_command_vrf>
                          <__XML__OPT_Cmd_urib_show_routing_command_ip>
                            <__XML__OPT_Cmd_urib_show_routing_command_unicast>
                              <__XML__OPT_Cmd_urib_show_routing_command_topology>
                                <__XML__OPT_Cmd_urib_show_routing_command_l3vm-info>
                                  <__XML__OPT_Cmd_urib_show_routing_command_rpf>
                                    <__XML__OPT_Cmd_urib_show_routing_command_ip-addr>
                                      <__XML__OPT_Cmd_urib_show_routing_command_protocol>
                                        <__XML__OPT_Cmd_urib_show_routing_command_summary>
                                          <__XML__OPT_Cmd_urib_show_routing_command_vrf>
                                            <__XML__OPT_Cmd_urib_show_routing_command___readonly__>
                                              <__readonly__>
                                                <TABLE_vrf>
                                                  <ROW_vrf>
                                                    <vrf-name-out>default</vrf-name-out>
                                                    <TABLE_addrf>
                                                      <ROW_addrf>
                                                        <addrf>ipv4</addrf>
                                                        <TABLE_prefix>
                                                          <ROW_prefix>
                                                            <ipprefix>192.168.12.0/24</ipprefix>
                                                            <ucast-nhops>1</ucast-nhops>
                                                            <mcast-nhops>0</mcast-nhops>
                                                            <attached>false</attached>
                                                            <TABLE_path>
                                                              <ROW_path>
                                                                <uptime>P19DT37M39S</uptime>
                                                                <pref>20</pref>
                                                                <metric>0</metric>
                                                                <clientname>bgp-65001</clientname>
                                                                <type>external</type>
                                                                <tag>65002</tag>
                                                                <ubest>true</ubest>
                                                              </ROW_path>
                                                            </TABLE_path>
                                                          </ROW_prefix>
                                                             <ROW_prefix>
                                                            <ipprefix>10.1.0.0/24</ipprefix>
                                                            <ucast-nhops>1</ucast-nhops>
                                                            <mcast-nhops>0</mcast-nhops>
                                                            <attached>false</attached>
                                                            <TABLE_path>
                                                              <ROW_path>
                                                                <uptime>P19DT37M39S</uptime>
                                                                <pref>20</pref>
                                                                <metric>0</metric>
                                                                <clientname>bgp-65001</clientname>
                                                                <type>external</type>
                                                                <tag>65002</tag>
                                                                <ubest>true</ubest>
                                                              </ROW_path>
                                                            </TABLE_path>
                                                          </ROW_prefix>
                                                        </TABLE_prefix>
                                                      </ROW_addrf>
                                                    </TABLE_addrf>
                                                  </ROW_vrf>
                                                </TABLE_vrf>
                                              </__readonly__>
                                            </__XML__OPT_Cmd_urib_show_routing_command___readonly__>
                                          </__XML__OPT_Cmd_urib_show_routing_command_vrf>
                                        </__XML__OPT_Cmd_urib_show_routing_command_summary>
                                      </__XML__OPT_Cmd_urib_show_routing_command_protocol>
                                    </__XML__OPT_Cmd_urib_show_routing_command_ip-addr>
                                  </__XML__OPT_Cmd_urib_show_routing_command_rpf>
                                </__XML__OPT_Cmd_urib_show_routing_command_l3vm-info>
                              </__XML__OPT_Cmd_urib_show_routing_command_topology>
                            </__XML__OPT_Cmd_urib_show_routing_command_unicast>
                          </__XML__OPT_Cmd_urib_show_routing_command_ip>
                        </__XML__OPT_Cmd_urib_show_routing_command_vrf>
                      </__XML__BLK_Cmd_urib_show_routing_command_routing>
                    </show>
                  </nf:data>
                </nf:rpc-reply>
                ]]>]]>
                '''


class test_get_routes(NexusOSTestSuite):
    def runTest(self):
        with mock.patch.object(self.driver, '_get_vrfs') as vrf_mock:
            with mock.patch.object(self.driver, '_exec_command') \
                    as push_changes:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    check_connected.return_value = None
                    push_changes.return_value \
                        = routes_string
                    with mock.patch.object(self.driver,
                                           'get_routes_aggregate') \
                            as routes_aggregate:
                        routes_aggregate.return_value = []
                        vrf_mock.return_value = ['test']
                        data = self.driver.get_routes('test')
                        expected = [u'192.168.12.0/24', u'10.1.0.0/24']
                        self.assertEqual(sorted(expected),
                                         sorted(data))
                        # test with no-vrf
                        data = self.driver.get_routes()
                        expected = []
                        self.assertEqual(sorted(expected),
                                         sorted(data))


class test_get_routes_aggregates_exist(NexusOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_get_vrfs') as vrf_mock:
            with mock.patch.object(self.driver, '_exec_command') \
                    as push_changes:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    check_connected.return_value = None
                    push_changes.return_value \
                        = routes_string
                    with mock.patch.object(self.driver,
                                           'get_routes_aggregate') \
                            as routes_aggregate:
                        vrf_mock.return_value = ['test']
                        routes_aggregate.side_effect = [[u'192.168.12.0/24'],
                                                        []]
                        data = self.driver.get_routes('test')
                        expected = [u'10.1.0.0/24']
                        # vrf_list =['lab1-10', 'lab1-20', 'lab1-30']
                        self.assertEqual(expected, data)
                        # test with no-vrf
                        data = self.driver.get_routes()
                        expected = []
                        # vrf_list =['lab1-10', 'lab1-20', 'lab1-30']
                        self.assertEqual(sorted(expected),
                                         sorted(data))


class test_get_vrfs(NexusOSTestSuite):
    vrf_string = '''<?xml version="1.0" encoding="ISO-8859-1"?>
                  <nf:rpc-reply xmlns:if="http://">
                  <nf:data>
                    <show>
                      <vrf>
                        <__XML__OPT_Cmd_l3vm_show_vrf_cmd_vrf-name>
                          <__XML__OPT_Cmd_l3vm_show_vrf_cmd_detail>
                            <__XML__OPT_Cmd_l3vm_show_vrf_cmd___readonly__>
                              <__readonly__>
                                <TABLE_vrf>
                                  <ROW_vrf>
                                    <vrf_name>default</vrf_name>
                                    <vrf_id>1</vrf_id>
                                    <vrf_state>Up</vrf_state>
                                    <vrf_reason>--</vrf_reason>
                                  </ROW_vrf>
                                  <ROW_vrf>
                                    <vrf_name>test1</vrf_name>
                                    <vrf_id>1</vrf_id>
                                    <vrf_state>Up</vrf_state>
                                    <vrf_reason>--</vrf_reason>
                                  </ROW_vrf>
                                </TABLE_vrf>
                              </__readonly__>
                            </__XML__OPT_Cmd_l3vm_show_vrf_cmd___readonly__>
                          </__XML__OPT_Cmd_l3vm_show_vrf_cmd_detail>
                        </__XML__OPT_Cmd_l3vm_show_vrf_cmd_vrf-name>
                      </vrf>
                    </show>
                 </nf:data>
                </nf:rpc-reply>
                ]]>]]>
                '''

    def runTest(self):

            with mock.patch.object(self.driver, '_exec_command') \
                    as push_changes:
                push_changes.return_value = self.vrf_string
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    check_connected.return_value = None
                    expected = [u'default', u'test1']
                    data = self.driver._get_vrfs()
                    self.assertEqual(expected, data)


class test_get_ip_addrs_on_interface(NexusOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_exec_command') \
                as push_changes:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                check_connected.return_value = None
                push_changes.return_value \
                    = """ip address 2.2.2.2/24\nip address 1.1.1.1/24 secondary\n
                    """
                data = self.driver.get_ip_addrs_on_interface('vlan2')
                expected = [u'2.2.2.2/24', u'1.1.1.1/24']
                self.assertEqual(sorted(expected), sorted(data))


class test_get_ip_addrs_on_interface_no_subnet(NexusOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_exec_command') \
                as push_changes:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                check_connected.return_value = None
                push_changes.return_value = " "
                data = self.driver.get_ip_addrs_on_interface('vlan2')
                expected = []
                self.assertEqual(expected, data)


class test_get_ip_addrs_on_interface_ip_addr_in_description(
    NexusOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_exec_command') \
                as push_changes:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                check_connected.return_value = None
                push_changes.return_value = """description ip address\n
                ip address 2.2.2.2/24\n
                ip address 1.1.1.1/24 secondary\n
                    """
                data = self.driver.get_ip_addrs_on_interface('vlan2')
                expected = [u'2.2.2.2/24', u'1.1.1.1/24']
                self.assertEqual(expected, data)


class test_get_routes_aggregates_no_vrf(NexusOSTestSuite):
    aggregates = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<nf:rpc-reply xmlns:nf="urn:ietf:params:xml:ns:netconf:base:1.0">
 <nf:data>
  <show>
   <__XML__BLK_Cmd_urib_show_routing_command_routing>
    <__XML__OPT_Cmd_urib_show_routing_command_vrf>
     <__XML__OPT_Cmd_urib_show_routing_command_ip>
      <ip/>
     </__XML__OPT_Cmd_urib_show_routing_command_ip>
    </__XML__OPT_Cmd_urib_show_routing_command_vrf>
    <ip>
     <route/>
    </ip>
    <__XML__OPT_Cmd_urib_show_routing_command_vrf>
     <__XML__OPT_Cmd_urib_show_routing_command_ip>
      <__XML__OPT_Cmd_urib_show_routing_command_unicast>
       <__XML__OPT_Cmd_urib_show_routing_command_topology>
        <__XML__OPT_Cmd_urib_show_routing_command_l3vm-info>
         <__XML__OPT_Cmd_urib_show_routing_command_rpf>
          <__XML__OPT_Cmd_urib_show_routing_command_ip-addr>
           <__XML__OPT_Cmd_urib_show_routing_command_protocol>
            <__XML__ALL_og_Cmd_urib_show_routing_command_protocol>
             <protocol>
              <__XML__PARAM_value>static</__XML__PARAM_value>
             </protocol>
            </__XML__ALL_og_Cmd_urib_show_routing_command_protocol>
            <__XML__OPT_Cmd_urib_show_routing_command_summary>
             <__XML__OPT_Cmd_urib_show_routing_command_vrf>
              <__XML__OPT_Cmd_urib_show_routing_command___readonly__>
               <__readonly__>
                <TABLE_vrf>
                 <ROW_vrf>
                  <vrf-name-out>default</vrf-name-out>
                  <TABLE_addrf>
                   <ROW_addrf>
                    <addrf>ipv4</addrf>
                    <TABLE_prefix>
                     <ROW_prefix>
                      <ipprefix>0.0.0.0/0</ipprefix>
                      <ucast-nhops>1</ucast-nhops>
                      <mcast-nhops>0</mcast-nhops>
                      <attached>false</attached>
                      <TABLE_path>
                       <ROW_path>
                        <uptime>PT8H19M19S</uptime>
                        <pref>20</pref>
                        <metric>101</metric>
                        <clientname>bgp-65001</clientname>
                        <type>external</type>
                        <tag>65000</tag>
                        <ubest>true</ubest>
                       </ROW_path>
                      </TABLE_path>
                     </ROW_prefix>
                     <ROW_prefix>
                      <ipprefix>1.1.1.0/24</ipprefix>
                      <ucast-nhops>1</ucast-nhops>
                      <mcast-nhops>0</mcast-nhops>
                      <attached>false</attached>
                      <TABLE_path>
                       <ROW_path>
                        <uptime>P3M10DT6H30M4S</uptime>
                        <pref>20</pref>
                        <metric>0</metric>
                        <clientname>bgp-65001</clientname>
                        <type>external</type>
                        <tag>65002</tag>
                        <ubest>true</ubest>
                       </ROW_path>
                      </TABLE_path>
                     </ROW_prefix>
                     </TABLE_prefix>
                   </ROW_addrf>
                  </TABLE_addrf>
                 </ROW_vrf>
                </TABLE_vrf>
               </__readonly__>
              </__XML__OPT_Cmd_urib_show_routing_command___readonly__>
             </__XML__OPT_Cmd_urib_show_routing_command_vrf>
            </__XML__OPT_Cmd_urib_show_routing_command_summary>
           </__XML__OPT_Cmd_urib_show_routing_command_protocol>
          </__XML__OPT_Cmd_urib_show_routing_command_ip-addr>
         </__XML__OPT_Cmd_urib_show_routing_command_rpf>
        </__XML__OPT_Cmd_urib_show_routing_command_l3vm-info>
       </__XML__OPT_Cmd_urib_show_routing_command_topology>
      </__XML__OPT_Cmd_urib_show_routing_command_unicast>
     </__XML__OPT_Cmd_urib_show_routing_command_ip>
    </__XML__OPT_Cmd_urib_show_routing_command_vrf>
   </__XML__BLK_Cmd_urib_show_routing_command_routing>
  </show>
 </nf:data>
</nf:rpc-reply>
]]>]]>
'''

    def runTest(self):
        with mock.patch.object(self.driver, '_get_vrfs') as vrf_mock:
            with mock.patch.object(self.driver, '_exec_command') \
                    as push_changes:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    check_connected.return_value = None
                    push_changes.return_value \
                        = self.aggregates
                    vrf_mock.return_value = ['test']
                    data = self.driver.get_routes_aggregate()
                    expected = []
                    # vrf_list =['lab1-10', 'lab1-20', 'lab1-30']
                    self.assertEqual(expected, data)


class test_get_routes_aggregates_with_vrf(NexusOSTestSuite):
    vrf_aggregates = '''<nf:rpc-reply xmlns:nf="urn:ietf:">
 <nf:data>
  <show>
   <__XML__BLK_Cmd_urib_show_routing_command_routing>
    <__XML__OPT_Cmd_urib_show_routing_command_vrf>
     <__XML__OPT_Cmd_urib_show_routing_command_ip>
      <ip/>
     </__XML__OPT_Cmd_urib_show_routing_command_ip>
    </__XML__OPT_Cmd_urib_show_routing_command_vrf>
    <ip>
     <route/>
    </ip>
    <__XML__OPT_Cmd_urib_show_routing_command_vrf>
     <__XML__OPT_Cmd_urib_show_routing_command_ip>
      <__XML__OPT_Cmd_urib_show_routing_command_unicast>
       <__XML__OPT_Cmd_urib_show_routing_command_topology>
        <__XML__OPT_Cmd_urib_show_routing_command_l3vm-info>
         <__XML__OPT_Cmd_urib_show_routing_command_rpf>
          <__XML__OPT_Cmd_urib_show_routing_command_ip-addr>
           <__XML__OPT_Cmd_urib_show_routing_command_protocol>
            <__XML__OPT_Cmd_urib_show_routing_command_summary>
             <__XML__OPT_Cmd_urib_show_routing_command_vrf>
              <vrf>
               <__XML__BLK_Cmd_urib_show_routing_command_vrf-name>
                <vrf-known-name>fake-20</vrf-known-name>
               </__XML__BLK_Cmd_urib_show_routing_command_vrf-name>
              </vrf>
              <__XML__OPT_Cmd_urib_show_routing_command___readonly__>
               <__readonly__>
                <TABLE_vrf>
                 <ROW_vrf>
                  <vrf-name-out>fake-20</vrf-name-out>
                  <TABLE_addrf>
                   <ROW_addrf>
                    <addrf>ipv4</addrf>
                    <TABLE_prefix>
                     <ROW_prefix>
                      <ipprefix>10.167.128.0/18</ipprefix>
                      <ucast-nhops>1</ucast-nhops>
                      <mcast-nhops>0</mcast-nhops>
                      <attached>FALSE</attached>
                      <TABLE_path>
                       <ROW_path>
                        <ifname>Null0</ifname>
                        <uptime>P4M29DT3H35M12S</uptime>
                        <pref>220</pref>
                        <metric>0</metric>
                        <clientname>bgp-64615</clientname>
                        <type>discard</type>
                        <tag>64615</tag>
                        <ubest>TRUE</ubest>
                       </ROW_path>
                      </TABLE_path>
                     </ROW_prefix>
                     </TABLE_prefix>
                   </ROW_addrf>
                  </TABLE_addrf>
                 </ROW_vrf>
                </TABLE_vrf>
               </__readonly__>
              </__XML__OPT_Cmd_urib_show_routing_command___readonly__>
             </__XML__OPT_Cmd_urib_show_routing_command_vrf>
            </__XML__OPT_Cmd_urib_show_routing_command_summary>
           </__XML__OPT_Cmd_urib_show_routing_command_protocol>
          </__XML__OPT_Cmd_urib_show_routing_command_ip-addr>
         </__XML__OPT_Cmd_urib_show_routing_command_rpf>
        </__XML__OPT_Cmd_urib_show_routing_command_l3vm-info>
       </__XML__OPT_Cmd_urib_show_routing_command_topology>
      </__XML__OPT_Cmd_urib_show_routing_command_unicast>
     </__XML__OPT_Cmd_urib_show_routing_command_ip>
    </__XML__OPT_Cmd_urib_show_routing_command_vrf>
   </__XML__BLK_Cmd_urib_show_routing_command_routing>
  </show>
 </nf:data>
</nf:rpc-reply>
]]>]]>
'''

    def runTest(self):
        with mock.patch.object(self.driver, '_get_vrfs') as vrf_mock:
            with mock.patch.object(self.driver, '_exec_command') \
                    as push_changes:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    check_connected.return_value = None
                    push_changes.return_value \
                        = self.vrf_aggregates
                    vrf_mock.return_value = ['test']
                    data = self.driver.get_routes_aggregate('test')
                    expected = [u'10.167.128.0/18']
                    # vrf_list =['lab1-10', 'lab1-20', 'lab1-30']
                    self.assertEqual(expected, data)


class test_get_routes_aggregates_wrong_vrf(NexusOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_get_vrfs') \
                as vrfs:
            with mock.patch.object(
                    self.driver, '_check_if_connected') \
                    as check_connected:
                check_connected.return_value = None
                vrfs.return_value = ['lab1-10']
                vrf_name = 'fake'
                self.assertRaises(ebay_exceptions.
                                  EntityDoesNotExistsException,
                                  self.driver.get_routes_aggregate,
                                  vrf_name)


class test_delete_subnet_success(NexusOSTestSuite):
    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as vlan_mock:
            vlan_mock.return_value = {
                'name': 'test-vlan',
                'status': 'active'
            }

            with mock.patch.object(self.driver,
                                   'get_ip_addrs_on_interface') \
                    as get_subnets_mock:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    with mock.patch.object(self.driver, '_exec_command') \
                            as push_changes:
                        push_changes.return_value = None
                        check_connected.return_value = None
                        get_subnets_mock.side_effect = [['1.1.1.1/24'], []]
                        commands = self.driver.delete_subnet_on_device(
                            '1.1.1.1/24', 2)
                        self.assertIsNotNone(commands)


class test_get_routes_aggregates_with_vrf_other_type(NexusOSTestSuite):
    vrf_aggregates = '''<nf:rpc-reply xmlns:nf="urn:ietf:">
 <nf:data>
  <show>
    <ip>
     <route>
     <vrf>
     <__XML__PARAM__vrf-known-name'>
        <__readonly__>
            <TABLE_vrf>
             <ROW_vrf>
              <vrf-name-out>fake-20</vrf-name-out>
              <TABLE_addrf>
               <ROW_addrf>
                <addrf>ipv4</addrf>
                <TABLE_prefix>
                 <ROW_prefix>
                  <ipprefix>10.167.128.0/18</ipprefix>
                  <ucast-nhops>1</ucast-nhops>
                  <mcast-nhops>0</mcast-nhops>
                  <attached>FALSE</attached>
                  <TABLE_path>
                   <ROW_path>
                    <ifname>Null0</ifname>
                    <uptime>P4M29DT3H35M12S</uptime>
                    <pref>220</pref>
                    <metric>0</metric>
                    <clientname>bgp-64615</clientname>
                    <type>discard</type>
                    <tag>64615</tag>
                    <ubest>TRUE</ubest>
                   </ROW_path>
                  </TABLE_path>
                 </ROW_prefix>
                 </TABLE_prefix>
               </ROW_addrf>
              </TABLE_addrf>
             </ROW_vrf>
            </TABLE_vrf>
        </__readonly__>
     </__XML__PARAM__vrf-known-name'>
     </vrf>
     </route>
     </ip>
     <__XML__PARAM__vrf-known-name'>
  </show>
 </nf:data>
</nf:rpc-reply>
]]>]]>
'''


class test_check_hidden_routes_aggregates_with_vrf(NexusOSTestSuite):
    hidden_aggregates = '''*>a10.166.0.0/16      0.0.0.0                           100      32768 i\n
    a10.173.160.0/20    0.0.0.0                           100      32768 i\n'''

    def runTest(self):
        with mock.patch.object(self.driver, '_get_vrfs') \
                as vrfs:
            with mock.patch.object(self.driver, '_exec_command') \
                    as push_changes:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    check_connected.return_value = None
                    push_changes.return_value \
                        = self.hidden_aggregates
                    vrfs.return_value = ['lab04-native']
                    data = self.driver.check_hidden_routes_aggregates(
                        'lab04-native')
                    expected = ['10.173.160.0/20', '10.166.0.0/16']
                    self.assertEqual(sorted(expected), sorted(data))


class test_update_switch_port_on_interface_trunk_mode_allowed_vlans(
    NexusOSTestSuite):

    def validate_commands(self, config):
        self.assertIs(5, len(config))

    def mock_get_vlan(self, *args, **kwargs):
        return {
            'name': 'test-vlan-2',
            'status': 'active'
        }

    def mock_get_vlans_on_interfaces(self, interfaces):
        return {
            'native_vlan': '5'
        }

    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as get_vlan_mocks:
            get_vlan_mocks.side_effect = self.mock_get_vlan

            with mock.patch.object(self.driver, '_exec_command') \
                    as push_changes:
                with mock.patch.object(
                        self.driver, '_check_if_connected') \
                        as check_connected:
                    check_connected.return_value = None
                    push_changes.exec_command.return_value = None
                    port = {
                        "switch_port_mode": "trunk",
                        "admin_status": "ACTIVE",
                        "vlans": [
                            {
                                "vlan": {
                                    "tag": "2",
                                    'is_native': False
                                }
                            },
                            {
                                "vlan": {
                                    "tag": "5",
                                    'is_native': True
                                }
                            },
                            {
                                "vlan": {
                                    "tag": "3",
                                    'is_native': True
                                }
                            }
                        ]
                    }

                    with mock.patch.object(self.driver,
                                           'get_vlans_on_interface')\
                            as vlan_if_mock:
                        with mock.patch.object(self.driver, 'compare_vlan_config') \
                                as compare_config:
                            compare_config.side_effect = [False, True]
                            vlan_if_mock.side_effect = \
                                self.mock_get_vlans_on_interfaces
                            commands = self.driver.update_switch_port_vlans(
                                'Ethernet1', port)
                            self.assertIn('2', commands)
