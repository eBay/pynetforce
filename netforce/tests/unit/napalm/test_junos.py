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

import jnpr
import lxml
import mock
from napalm_baseebay import ebay_exceptions

from napalm_base import get_network_driver
from netforce.tests.unit.napalm import base


class MockConfig(object):

    def lock(self):
        pass

    def unlock(self):
        pass

    def load(self, conf, format):
        pass

    def commit(self, sync=True):
        pass


class MockDevice(object):

    def open(self):
        pass

    def close(self):
        pass

    def bind(self, cu):
        self.cu = MockConfig()


class JUNOSTestSuite(base.DietTestCase):
    """Juniper JUNOS Test Suite

    This test suite performs setup and teardown functions for this file's
    unit tests. Each unit test class should inherit from this class, and
    implement a single "runTest" function.

    """

    def setUp(self):
        """Perform setup activities

        """
        super(JUNOSTestSuite, self).setUp()

        driver = get_network_driver('ebayjunos')
        self.driver = driver(
            hostname='127.0.0.1',
            username='junos',
            password='junos'
        )
        self.driver.device = MockDevice()
        self.driver.device.bind(cu=MockConfig)
        self.interface_names = ["ge-0/0/1", "ge-0/0/2"]

    def tearDown(self):
        """Perform teardown activities

        """

        super(JUNOSTestSuite, self).tearDown()

    def get_mock_interface_status(self, interface_names, status):
        """Returns a dict containing mocked up interface status info

        """

        if_dict = {}

        for ifname in interface_names:

            if_dict[ifname] = {
                "is_enabled": status,
                "description": "",
                "last_flapped": 179,
                "is_up": status,
                "mac_address": "08:00:27:0e:5d:fd",
                "speed": "1000mbps"
            }

        return if_dict

    def fakeStatus(self, status):
        status_items = {
            'enabled': True,
            'disabled': False,
        }
        if_status = self.get_mock_interface_status(
            self.interface_names,
            status_items[status]
        )

        def getitem(*args):
            """Retrieves item from dict

            This function overrides the __getitem__ method in the
            mock dict below.

            It's necessary because mock automatically adds a parameter to
            the function call, so we want to support that same number of args

            """

            return if_status[args[1]]

        mock_if_status = mock.Mock()
        mock_if_status.get.return_value = None
        mock_if_status.keys.return_value = if_status.keys()
        mock_if_status.__getitem__ = getitem

        return mock_if_status


class test_interface_label_validation_success(JUNOSTestSuite):

    def mock_interfaces(self):
        ifdict = {}

        for ifname in self.interface_names:
            ifdict[ifname] = {
                "name": ifname,
                "description": 'test-label',

            }

        return ifdict

    def runTest(self):
        with mock.patch.object(self.driver, '_get_interfaces_description') \
                as get_interfaces_mock:
            get_interfaces_mock.side_effect = self.mock_interfaces
            self.driver.update_interface_label('ge-0/0/1',
                                               'test-label')


class test_interface_label_post_change_validation_failure(JUNOSTestSuite):

    def mock_interfaces(self):
        ifdict = {}

        for ifname in self.interface_names:
            ifdict[ifname] = {
                "name": ifname,
                "description": 'test-label-1',

            }

        return ifdict

    def runTest(self):
        with mock.patch.object(self.driver,
                               '_get_interfaces_description') as \
                get_interfaces_mock:
            get_interfaces_mock.side_effect = self.mock_interfaces
            self.assertRaises(ebay_exceptions.PostChangeValidationException,
                              self.driver.update_interface_label,
                              'ge-0/0/1', 'test-label')


class test_interface_label_post_change_empty_interface_failure(JUNOSTestSuite):

    def mock_interfaces(self):
        ifdict = {}
        return ifdict

    def runTest(self):
        with mock.patch.object(self.driver, '_get_interfaces_description') \
                as get_interfaces_mock:
            get_interfaces_mock.side_effect = self.mock_interfaces
            self.assertRaises(ebay_exceptions.EntityDoesNotExistsException,
                              self.driver.update_interface_label,
                              'ge-0/0/1', 'test-label')


class test_interface_label_post_change_interface_not_present_failure(
    JUNOSTestSuite):

    def mock_interfaces(self):
        ifdict = {}

        for ifname in self.interface_names:
            ifdict[ifname] = {
                "name": ifname,
                "description": 'test-label-1',

            }

        return ifdict

    def runTest(self):
        with mock.patch.object(self.driver, '_get_interfaces_description') \
                as get_interfaces_mock:
            get_interfaces_mock.side_effect = self.mock_interfaces
            self.assertRaises(ebay_exceptions.EntityDoesNotExistsException,
                              self.driver.update_interface_label,
                              'ge-0/0/5', 'test-label')


class test_get_mac_addresses_on_interface(JUNOSTestSuite):

    data = '''
        <rpc-reply xmlns:junos="http://xml.juniper.net/junos/14.1X53/junos">
            <l2ng-l2ald-interface-macdb-vlan>
                <l2ng-l2ald-macdb-if-name>ae0.0</l2ng-l2ald-macdb-if-name>
                <l2ng-l2ald-mac-entry-vlan junos:style="brief-rtb">
                    <mac-count-global>1</mac-count-global>
                    <learnt-mac-count>1</learnt-mac-count>
                    <l2ng-l2-mac-routing-instance>default-switch</l2ng-l2-mac-routing-instance>
                    <l2ng-l2-vlan-id>1</l2ng-l2-vlan-id>
                    <l2ng-mac-entry>
                        <l2ng-l2-mac-vlan-name>default</l2ng-l2-mac-vlan-name>
                        <l2ng-l2-mac-address>beef.beef.beef</l2ng-l2-mac-address>
                        <l2ng-l2-mac-flags>D</l2ng-l2-mac-flags>
                        <l2ng-l2-mac-age>-</l2ng-l2-mac-age>
                        <l2ng-l2-mac-logical-interface>ae0.0</l2ng-l2-mac-logical-interface>
                    </l2ng-mac-entry>
                </l2ng-l2ald-mac-entry-vlan>
            </l2ng-l2ald-interface-macdb-vlan>
            <cli>
                <banner>{master:0}</banner>
            </cli>
        </rpc-reply>
    '''

    def runTest(self):

        self.driver.device = mock.Mock(spec=jnpr.junos.Device)
        rpc = mock.Mock()
        rpc_name = 'get-ethernet-switching-table-interface-information'
        rpc_call = getattr(rpc, rpc_name)
        rpc_call.return_value = lxml.etree.XML(self.data)[0]
        self.driver.device.rpc = rpc
        ret = self.driver.get_mac_addresses_on_interface('ae0.0', 1)
        expected = [{'mac_address': 'beef.beef.beef', 'vlan': 1}]
        self.assertEqual(expected, ret)


class test_get_traffic_on_interface(JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        mock_device.cli.return_value = """
        Physical interface: xe-0/0/0:1, Enabled, Physical link is Up
          Interface index: 668, SNMP ifIndex: 618, Generation: 159
          Description: fake-5fzj
          Link-level type: Ethernet, MTU: 9216, MRU: 0, Speed: 10Gbps,
           BPDU Error: None,
          MAC-REWRITE Error: None, Loopback: Disabled, Source filtering:
           Disabled,
          Flow control: Disabled, Media type: Fiber
          Device flags   : Present Running
          Interface flags: SNMP-Traps Internal: 0x4000
          Link flags     : None
          CoS queues     : 12 supported, 12 maximum usable queues
          Hold-times     : Up 0 ms, Down 0 ms
          Current address: 54:1e:56:00:a0:04, Hardware address:
           54:1e:56:00:a0:04
          Last flapped   : 2016-09-19 18:34:29 PDT (3d 04:33 ago)
          Statistics last cleared: Never
          Traffic statistics:
           Input  bytes  :           7574887778                    0 bps
           Output bytes  :          17387017215                  496 bps
           Input  packets:             10159378                    0 pps
           Output packets:             25032846                    0 pps
        """

        return mock_device

    def runTest(self):
        self.driver.device = self.get_mock_device()
        data = self.driver.get_traffic_on_interface('xe-0/0/0:1')
        expected = (0, 496)
        self.assertEqual(expected, data)


class test_create_subnet_success(JUNOSTestSuite):

    def runTest(self):

        with mock.patch.object(self.driver, 'get_vlan') as vlan_mock:
            vlan_mock.return_value = {
                'name': 'test-vlan',
                'status': 'active'
            }

            with mock.patch.object(self.driver,
                                   'get_ip_addrs_on_interface') \
                    as get_subnets_mock:
                with mock.patch.object(self.driver,
                                       'get_vlan_interface_name') \
                        as get_vlan_irb_name:
                    with mock.patch.object(self.driver,
                                           '_check_primary_subnet') \
                            as check_primary:
                        check_primary.return_value = None
                        get_vlan_irb_name.return_value = 'irb.0'
                        get_subnets_mock.side_effect = [[], ['1.1.1.1/24']]
                        commands = self.driver.create_subnet('1.1.1.1/24', 2)
                        self.assertIsNotNone(commands)


class test_create_subnet_failure_vlan_not_found(JUNOSTestSuite):

    def runTest(self):

        with mock.patch.object(self.driver, 'get_vlan') as vlan_mock:
            vlan_mock.return_value = None

            with mock.patch.object(self.driver,
                                   'get_ip_addrs_on_interface') \
                    as get_subnets_mock:
                get_subnets_mock.side_effect = [[], ['1.1.1.1/24']]
                self.assertRaises(ebay_exceptions.
                                  EntityDoesNotExistsException,
                                  self.driver.create_subnet,
                                  '1.1.1.1/24',
                                  2)


class test_create_subnet_failure_in_config_push(JUNOSTestSuite):

    def runTest(self):

        with mock.patch.object(self.driver, 'get_vlan') as vlan_mock:
            vlan_mock.return_value = {
                'name': 'test-vlan',
                'status': 'active'
            }

            with mock.patch.object(self.driver,
                                   'get_ip_addrs_on_interface') \
                    as get_subnets_mock:
                with mock.patch.object(self.driver,
                                       'get_vlan_interface_name') \
                        as get_vlan_irb_name:
                    with mock.patch.object(self.driver,
                                           '_check_primary_subnet') \
                            as check_primary:
                        check_primary.return_value = None
                        get_vlan_irb_name.return_value = 'irb.2'
                        get_subnets_mock.side_effect = [[], []]
                        self.assertRaises(
                            ebay_exceptions.PostChangeValidationException,
                            self.driver.create_subnet, '1.1.1.1/24', 2)


class test_create_subnet_failure_subnet_already_exists(JUNOSTestSuite):

    def runTest(self):

        with mock.patch.object(self.driver, 'get_vlan') as vlan_mock:
            vlan_mock.return_value = {
                'name': 'test-vlan',
                'status': 'active'
            }

            with mock.patch.object(self.driver,
                                   'get_ip_addrs_on_interface') \
                    as get_subnets_mock:
                with mock.patch.object(self.driver,
                                       'get_vlan_interface_name') \
                        as get_vlan_irb_name:
                    with mock.patch.object(self.driver,
                                           '_check_primary_subnet') \
                            as check_primary:
                        check_primary.return_value = None
                        get_vlan_irb_name.return_value = 'irb.2'
                        get_subnets_mock.side_effect = [['1.1.1.1/24']]
                        self.assertRaises(ebay_exceptions.
                                          SubnetAlreadyConfiguredException,
                                          self.driver.create_subnet,
                                          '1.1.1.1/24',
                                          2)


def get_mock_device():
    mock_device = mock.Mock()
    mock_device.cli.return_value = """
    inet.0: 56 destinations, 90 routes (56 active, 0 holddown, 0 hidden)
    + = Active Route, - = Last Active, * = Both

    10.5.0.0/24        *[Direct/0] 1w3d 19:16:12
        > via irb.51
        [BGP/170] 1w3d 19:16:12, localpref 100
          AS path: 65002 65003 I, validation-state: unverified
        > to 10.255.39.42 via et-0/0/21.5
    """

    return mock_device


class test_get_routes(JUNOSTestSuite):

    def runTest(self):
        self.driver.device = get_mock_device()
        with mock.patch.object(self.driver, 'get_routes_aggregate') \
                as route_aggregates:
            route_aggregates.return_value = []
            data = self.driver.get_routes()
            expected = ['10.5.0.0/24']
            self.assertEqual(expected, data)


class test_get_routes_aggregates_exist(JUNOSTestSuite):

    def runTest(self):
        self.driver.device = get_mock_device()
        with mock.patch.object(self.driver, 'get_routes_aggregate') \
                as route_aggregates:
            with mock.patch.object(self.driver, '_get_vrfs') \
                    as vrfs:
                vrfs.return_value = ['test']
                data = self.driver.get_routes('test')
                route_aggregates.side_effect = ['10.5.0.0/24', []]
                expected = ['10.5.0.0/24']
                # vrf_list =['lab1-10', 'lab1-20', 'lab1-30']
                self.assertEqual(expected, data)
                # test with no-vrf
                data = self.driver.get_routes()
                expected = ['10.5.0.0/24']
                # vrf_list =['lab1-10', 'lab1-20', 'lab1-30']
                self.assertEqual(expected, data)


class test_get_vrfs(JUNOSTestSuite):

    data = '''
        <rpc-reply xmlns:junos="http://xml.juniper.net/junos/14.1X53/junos">
            <instance-information xmlns="">
                <instance-core>
                    <instance-name>lab1-30</instance-name>
                    <instance-type>vrf</instance-type>
                    <instance-rib>
                        <irib-name>lab1-30.inet.0</irib-name>
                        <irib-active-count>22</irib-active-count>
                        <irib-holddown-count>0</irib-holddown-count>
                        <irib-hidden-count>4</irib-hidden-count>
                    </instance-rib>
                    <instance-rib>
                        <irib-name>lab1-30.inet6.0</irib-name>
                        <irib-active-count>32</irib-active-count>
                        <irib-holddown-count>0</irib-holddown-count>
                        <irib-hidden-count>0</irib-hidden-count>
                    </instance-rib>
                    <instance-name>lab1-33</instance-name>
                    <instance-type>vrf</instance-type>
                    <instance-rib>
                        <irib-name>lab1-33.inet.0</irib-name>
                        <irib-active-count>22</irib-active-count>
                        <irib-holddown-count>0</irib-holddown-count>
                        <irib-hidden-count>4</irib-hidden-count>
                    </instance-rib>
                    <instance-rib>
                        <irib-name>lab1-33.inet6.0</irib-name>
                        <irib-active-count>32</irib-active-count>
                        <irib-holddown-count>0</irib-holddown-count>
                        <irib-hidden-count>0</irib-hidden-count>
                    </instance-rib>
                </instance-core>
        </instance-information>
        <cli>
            <banner>{master:0}</banner>
        </cli>
        </rpc-reply>
    '''

    def runTest(self):

        self.driver.device = mock.Mock(spec=jnpr.junos.Device)
        rpc = mock.Mock()
        rpc_name = 'get-instance-information'
        rpc_call = getattr(rpc, rpc_name)
        rpc_call.return_value = lxml.etree.XML(self.data)[0]
        self.driver.device.rpc = rpc
        ret = self.driver._get_vrfs()
        expected = ['lab1-30', 'lab1-33']
        self.assertEqual(expected, ret)
        self.driver.device = get_mock_device()
        with mock.patch.object(self.driver, 'get_routes_aggregate') \
                as route_aggregates:
            route_aggregates.return_value = ['10.5.0.0/24']
            data = self.driver.get_routes()
            expected = []
            self.assertEqual(expected, data)


class test_update_switch_port_prevalidation_successful(JUNOSTestSuite):
    def validate_commands(self, config):
        self.assertIs(5, len(config))

    def mock_get_vlan(self, *args, **kwargs):
        return [{'status': None, 'tag': '3', 'name':
            'test3', 'members': '3'},
                {'status': None, 'tag': '22', 'name':
                    'test2', 'members': ['22', '3']}
                ]

    def runTest(self):
        with mock.patch.object(self.driver, 'get_all_vlans_on_device') as\
                get_vlan_mocks:
            get_vlan_mocks.side_effect = self.mock_get_vlan
            with mock.patch.object(self.driver,
                                   'get_vlans_on_interface') as \
                    get_vlan_interface_mock:
                self.driver.device = mock.Mock(spec=jnpr.junos.Device)
                with mock.patch.object(self.driver, 'compare_vlan_config') \
                        as compare_config:
                    compare_config.return_value = True
                    get_vlan_interface_mock.return_vlaue = {
                        'switch_port_mode': u'trunk',
                        'native_vlan': u'3', 'trunk_vlans': u'3-4'
                    }
                    port = {
                        "switch_port_mode": "access",
                        "admin_status": "ACTIVE",
                        "vlans": [
                            {
                                "vlan": {
                                    "tag": "22"
                                }
                            }
                        ]
                    }

                    self.driver.update_switch_port_vlans('xe-0/0/0:0',
                                                         port)


class test_update_switch_port_post_validation_failure(JUNOSTestSuite):
    def validate_commands(self, config):
        self.assertIs(5, len(config))

    def mock_get_vlan(self, *args, **kwargs):
        return [{'status': None, 'tag': '3', 'name':
            'test3', 'members': '3'},
                {'status': None, 'tag': '2', 'name':
                    'test2', 'members': '2'}
                ]

    def runTest(self):
        with mock.patch.object(self.driver, 'get_all_vlans_on_device') as\
                get_vlan_mocks:
            get_vlan_mocks.side_effect = self.mock_get_vlan
            with mock.patch.object(self.driver,
                                   'get_vlans_on_interface') as \
                    get_vlan_interface_mock:
                self.driver.device = mock.Mock(spec=jnpr.junos.Device)
                self.driver.device.cu = mock.Mock(spec=jnpr.junos.Device)
                self.driver.device.cu.load = mock.Mock(spec=jnpr.junos.Device)
                self.driver.device.cu.commit = mock.Mock(
                    spec=jnpr.junos.Device)
                with mock.patch.object(self.driver,
                                       'compare_vlan_config') \
                        as compare_config:
                    compare_config.side_effect = [False, False]
                    get_vlan_interface_mock.return_vlaue = {
                        'switch_port_mode': u'trunk',
                        'native_vlan': u'3', 'trunk_vlans': u'3-4'
                    }
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
                    self.assertRaises(ebay_exceptions.
                                      PostChangeValidationException,
                                      self.driver.update_switch_port_vlans,
                                      'xe-0/0/0:0', port)


class test_get_routes_aggregates_no_vrf(JUNOSTestSuite):

    def get_mock_device(self):
        mock_device = mock.Mock()
        mock_device.cli.side_effect = ["""
        inet.0: 71 destinations, 156 routes (71 active, 0 holddown,
         21 hidden)
        + = Active Route, - = Last Active, * = Both

        10.255.32.0/21     *[Aggregate/130] 22w2d 10:32:56
                      Reject
        10.255.39.0/26     *[Aggregate/130] 21w5d 07:50:35
                      Reject
        """, """
        inet.0: 71 destinations, 156 routes (71 active, 0 holddown,
         21 hidden)
        + = Active Route, - = Last Active, * = Both
        """]
        return mock_device

    def runTest(self):
        self.driver.device = self.get_mock_device()
        data = self.driver.get_routes_aggregate()
        expected = ['10.255.32.0/21', '10.255.39.0/26']
        self.assertEqual(expected, data)


class test_get_routes_aggregates_with_vrf(JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        mock_device.cli.return_value = """
        lab1-10.inet.0: 22 destinations, 33 routes (22 active, 0 holddown,
         4 hidden)
        + = Active Route, - = Last Active, * = Both

        10.255.40.0/21     *[Aggregate/130] 21w5d 08:46:07
                      Reject
        10.255.47.0/26     *[Aggregate/130] 21w5d 07:50:35
                      Reject


        """
        return mock_device

    def runTest(self):
        with mock.patch.object(self.driver, '_get_vrfs') \
                as vrfs:
            vrfs.return_value = ['lab1-10']
            self.driver.device = self.get_mock_device()
            data = self.driver.get_routes_aggregate('lab1-10')
            expected = ['10.255.40.0/21', '10.255.47.0/26']
            self.assertEqual(expected, data)


class test_get_routes_aggregates_wrong_vrf(JUNOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver, '_get_vrfs') \
                as vrfs:
            vrfs.return_value = ['lab1-10']
            vrf_name = 'fake'
            self.assertRaises(ebay_exceptions.
                              EntityDoesNotExistsException,
                              self.driver.get_routes_aggregate,
                              vrf_name)


class test_delete_subnet_success(JUNOSTestSuite):
    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as vlan_mock:
            vlan_mock.return_value = {
                'name': 'test-vlan',
                'status': 'active'
            }

            with mock.patch.object(self.driver,
                                   'get_ip_addrs_on_interface') \
                    as get_subnets_mock:
                with mock.patch.object(self.driver,
                                       'get_vlan_interface_name') \
                        as vlan_irb_name:
                    get_subnets_mock.side_effect = [['1.1.1.1/24'], []]
                    vlan_irb_name.return_value = "irb.2"
                    commands = self.driver.delete_subnet_on_device(
                        '1.1.1.1/24', 2)
                    self.assertIsNotNone(commands)


class test_get_vlan_interface_name(JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        mock_device.cli.return_value = """
        vlan-id 1;
        l3-interface irb.0;
        """
        return mock_device

    def runTest(self):
        with mock.patch.object(self.driver,
                               'get_vlan') as get_vlan:
            get_vlan.return_value = {
                'status': None, 'name': 'default'}
            self.driver.device = self.get_mock_device()
            data = self.driver.get_vlan_interface_name('1')
            expected = 'irb.0'
            self.assertEqual(expected, data)


class test_get_vlan_interface_name_irb_unit_not_configured(JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        mock_device.cli.return_value = """
        vlan-id 1;
        """
        return mock_device

    def runTest(self):
        with mock.patch.object(self.driver,
                               'get_vlan') as get_vlan:
            get_vlan.return_value = {
                'status': None, 'name': 'default'}
            self.driver.device = self.get_mock_device()
            self.assertRaises(ebay_exceptions.
                             EntityDoesNotExistsException,
                             self.driver.get_vlan_interface_name,
                             '1')


class test_check_primary_subnet_on_interface(JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        mock_device.cli.return_value = """
            address 10.158.72.1/22; \n
            address 10.195.140.1/23; \n
        """
        return mock_device

    def runTest(self):
        self.driver.device = self.get_mock_device()
        self.assertRaises(ebay_exceptions.
                          NoPrimarySubnetOnVlanInterface,
                          self.driver._check_primary_subnet,
                          'irb.0')


class test_check_patch_subnet_on_interface_with_more_than_one_subnet(
    JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        return mock_device

    def runTest(self):
        with mock.patch.object(self.driver,
                               'get_ip_addrs_on_interface') \
                as get_subnets_mock:
            self.driver.device = self.get_mock_device()
            get_subnets_mock.side_effect = [['1.1.1.1/24', '1.1.1.1/24']]
            self.assertRaises(ebay_exceptions.
                              PatchingNotSupported,
                              self.driver._check_patch_subnet_on_interface,
                              '2.1.1.1/24', 'irb.0', True)


class test_check_patch_subnet_on_interface_with_no_subnet(
        JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        return mock_device

    def runTest(self):
        with mock.patch.object(self.driver,
                               'get_ip_addrs_on_interface') \
                as get_subnets_mock:
            self.driver.device = self.get_mock_device()
            get_subnets_mock.side_effect = [[]]
            self.assertRaises(ebay_exceptions.
                              PatchingNotSupported,
                              self.driver._check_patch_subnet_on_interface,
                              '2.1.1.1/24', 'irb.0', True)


class test_check_patch_subnet_on_interface_with_conflict_primary(
        JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        return mock_device

    def runTest(self):
        with mock.patch.object(self.driver,
                               'get_ip_addrs_on_interface') \
                as get_subnets_mock:
            self.driver.device = self.get_mock_device()
            get_subnets_mock.side_effect = [['1.1.1.1/24']]
            self.assertRaises(ebay_exceptions.
                              RequestedPrimaryConflictsWithConfigured,
                              self.driver._check_patch_subnet_on_interface,
                              '2.1.1.1/24', 'irb.0', True)


class test_check_patch_subnet_on_interface(JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        mock_device.cli.return_value = """
            address 2.1.1.1/24 { \n
                primary; \n
            }   \n
        """
        return mock_device

    def runTest(self):
        with mock.patch.object(self.driver,
                               'get_ip_addrs_on_interface') \
                as get_subnets_mock:
            self.driver.device = self.get_mock_device()
            get_subnets_mock.side_effect = [['2.1.1.1/24']]
            self.assertRaises(ebay_exceptions.
                              PrimarySubnetExistsOnVlanInterface,
                              self.driver._check_patch_subnet_on_interface,
                              '2.1.1.1/24', 'irb.0', True)


class set_subnet_primary_sucess(JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        mock_device.cli.return_value = """
            address 1.1.1.1/24; \n
        """
        return mock_device

    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as vlan_mock:
            vlan_mock.return_value = {
                'name': 'test-vlan',
                'status': 'active'
            }

            with mock.patch.object(self.driver,
                                   'get_ip_addrs_on_interface') \
                    as get_subnets_mock:
                with mock.patch.object(self.driver,
                                       'get_vlan_interface_name') \
                        as get_vlan_irb_name:
                    with mock.patch.object(self.driver,
                                           '_check_patch_subnet_on_interface') \
                            as check_primary:
                        self.driver.device = self.get_mock_device()
                        check_primary.return_value = None
                        get_vlan_irb_name.return_value = 'irb.0'
                        get_subnets_mock.side_effect = [['1.1.1.1/24']]
                        commands = self.driver.set_subnet_primary(
                            '1.1.1.1/24', 2, True)
                        self.assertIsNotNone(commands)


class set_subnet_primary_for_more_then_one_subnet_sucess(JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        mock_device.cli.return_value = """
            address 1.1.1.1/24 \n
            address 2.1.1.1/24
        """
        return mock_device

    def runTest(self):
        with mock.patch.object(self.driver, 'get_vlan') as vlan_mock:
            vlan_mock.return_value = {
                'name': 'test-vlan',
                'status': 'active'
            }

            with mock.patch.object(self.driver,
                                   'get_ip_addrs_on_interface') \
                    as get_subnets_mock:
                with mock.patch.object(self.driver,
                                       'get_vlan_interface_name') \
                        as get_vlan_irb_name:
                    with mock.patch.object(
                            self.driver, '_check_patch_subnet_on_interface')\
                            as check_primary:
                        self.driver.device = self.get_mock_device()
                        check_primary.return_value = None
                        get_vlan_irb_name.return_value = 'irb.0'
                        get_subnets_mock.side_effect = [['1.1.1.1/24',
                                                         '2.1.1.1/24']]
                        commands = self.driver.set_subnet_primary(
                            '1.1.1.1/24', 2, False)
                        self.assertIsNotNone(commands)


class test_check_hidden_routes_aggregates_with_vrf(JUNOSTestSuite):
    def get_mock_device(self):
        mock_device = mock.Mock()
        mock_device.cli.return_value = """
        lab1-10.inet.0: 22 destinations, 33 routes (22 active, 0 holddown,
         4 hidden)
        + = Active Route, - = Last Active, * = Both

        10.255.40.0/21     *[Aggregate/130] 21w5d 08:46:07
                      Reject
        10.255.47.0/26     *[Aggregate/130] 21w5d 07:50:35
                      Reject


        """
        return mock_device

    def runTest(self):
        with mock.patch.object(self.driver, '_get_vrfs') \
                as vrfs:
            vrfs.return_value = ['lab1-10']
            self.driver.device = self.get_mock_device()
            data = self.driver.check_hidden_routes_aggregates('lab1-10')
            expected = ['10.255.40.0/21', '10.255.47.0/26']
            self.assertEqual(expected, data)


class test_check_native_vlan_id(JUNOSTestSuite):

    def runTest(self):
        with mock.patch.object(self.driver,
                               'get_vlans_on_interface') as \
                get_vlan_interface_mock:
            get_vlan_interface_mock.return_vlaue = [{
                'switch_port_mode': u'access',
                'native_vlan': u'3', 'trunk_vlans': u'3-4'
            }]
            data = self.driver._check_native_vlan_id('xe-0/0/0:3')
            self.assertEqual(True, data)
            get_vlan_interface_mock.side_effect = [{
                'switch_port_mode': u'access',
                'native_vlan': None, 'trunk_vlans': u'3-4'
            }]
            data = self.driver._check_native_vlan_id('xe-0/0/0:3')
            self.assertEqual(False, data)

# class test_enable_interface(JUNOSTestSuite):
#     """Tests the enable_interface function functions correctly
#
#     """
#
#     @mock.patch("netforce.services.napalm.junos.junos_views")
#     def runTest(self, mock_views):
#
#         mock_views.junos_iface_table.return_value =
#       self.fakeStatus('enabled')
#
#         self.driver.enable_interfaces(self.interface_names)
#
#
# class test_enable_interface_failed(JUNOSTestSuite):
#     """Tests the enable_interface function raises the appropriate exception
#
#     """
#
#     @mock.patch("netforce.services.napalm.junos.junos_views")
#     def runTest(self, mock_views):
#
#         mock_views.junos_iface_table.return_value =
#           self.fakeStatus('disabled')
#
#         with self.assertRaises(PostChangeValidationException):
#             self.driver.enable_interfaces(self.interface_names)
#
#
# class test_disable_interface(JUNOSTestSuite):
#     """Tests the disable_interface function functions correctly
#
#     """
#
#     @mock.patch("netforce.services.napalm.junos.junos_views")
#     def runTest(self, mock_views):
#
#         mock_views.junos_iface_table.return_value =
#           self.fakeStatus('disabled')
#
#         self.driver.disable_interfaces(self.interface_names)
#
#
# class test_disable_interface_failed(JUNOSTestSuite):
#     """Tests the disable_interface function raises the appropriate exception
#
#     """
#
#     @mock.patch("netforce.services.napalm.junos.junos_views")
#     def runTest(self, mock_views):
#
#         mock_views.junos_iface_table.return_value =
#        self.fakeStatus('enabled')
#
#         with self.assertRaises(PostChangeValidationException):
#             self.driver.disable_interfaces(self.interface_names)
