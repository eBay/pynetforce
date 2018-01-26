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


import contextlib

from neutron.common import exceptions
from neutron import context
from neutron.plugins.common import constants

from netforce.common import netforce_exceptions
from netforce.db import netforce_db
from netforce.plugins.common import netforce_constants
from netforce.plugins.plugin import NetforcePlugin
from netforce.tests import base

import mock
from oslo_config import cfg
import testscenarios

CONF = cfg.CONF
load_tests = testscenarios.load_tests_apply_scenarios


class MockDeviceDriver(object):

    def disable_interfaces(self, interfaces):
        return None

    def open(self):
        return None

    def close(self):
        return None

    def get_interfaces(self):
        return {
            "Management1": {
                "is_enabled": True,
                "description": "Management Interface"
            },
            "Ethernet2": {
                "is_enabled": True,
                "description": "Et2 Interface"
            },
            "Ethernet3": {
                "is_enabled": False,
                "description": "Et3 Interface"
            },
            "Ethernet1": {
                "is_enabled": True,
                "description": "Et1 Interface"
            }
        }


class FakeNetforcePlugin(NetforcePlugin):

    def _get_credentials(self):
        return 'test', 'test'


class BaseNetforcePluginSetup(base.NetforceSqlTestCase):

    def setUp(self):
        super(BaseNetforcePluginSetup, self).setUp()
        self.context = context.get_admin_context()
        self.plugin = FakeNetforcePlugin()
        self.bridge_group_db = netforce_db.NetforceDbMixin()
        self.vpc_db = netforce_db.NetforceDbMixin()
        self.device_db_mixin = netforce_db.NetforceDbMixin()
        self.subnet_db = netforce_db.NetforceDbMixin()


class TestNetforcePlugin(BaseNetforcePluginSetup):

    def setUp(self):
        super(TestNetforcePlugin, self).setUp()

    def tearDown(self):
        super(TestNetforcePlugin, self).tearDown()

    def _get_ticket_mock(self):
        ticket_mock = mock.Mock()
        ticket_mock.create_ticket.return_value = \
            {"result": "CHNGE12345678"}
        return ticket_mock

    def _update_ticket_mock(self):
        update_ticket_mock = mock.Mock()
        update_ticket_mock.update_ticket.return_value = None
        return update_ticket_mock

    def create_device(self):
        # create bubble
        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_db = self.plugin.create_bubble(
            self.context, body)
        self.assertIsNotNone(bubble_db)
        device_type = {
            'devicetype': {
                'name': 'Top of the Rack Switch',
                'type': 'TOR'
            }
        }

        device_type_db = self.plugin.create_devicetype(
            self.context, device_type)

        self.assertIsNotNone(device_type_db)

        device_type2 = {
            'devicetype': {
                'name': 'ED Switch',
                'type': 'DISTRIBUTION'
            }
        }

        device_type_db2 = self.plugin.create_devicetype(
            self.context, device_type2)

        self.assertIsNotNone(device_type_db2)

        device = {
            'device': {
                'name': 'test-device',
                'description': 'test device',
                'management_ip': '1.1.1.1',
                'username': 'arista',
                'password': 'arista',
                'type': 'TOR',
                'os_type': 'junos',
                'bubble_id': bubble_db['id']
            }
        }

        device2 = {
            'device': {
                'name': 'test-ED',
                'description': 'test ED',
                'management_ip': '1.1.1.2',
                'username': 'arista',
                'password': 'arista',
                'type': 'DISTRIBUTION',
                'os_type': 'junos',
                'bubble_id': bubble_db['id'],
                'device_type_id': device_type_db2['id']
            }
        }
        with mock.patch.object(self.plugin, '_discover_ports_on_device')\
                as discover_ports:
            discover_ports.return_value = None
            device_db = self.plugin.create_device(self.context, device)
            device_db2 = self.plugin.create_device(self.context, device2)
            self.assertIsNotNone(device_db)
            self.assertIsNotNone(device_db2)
            self.assertIs(0, len(device_db['ports']))

        return device_db

    def create_vlan_for_port_flip(self, device_db):
        # create vpc
        bg_name = 'test-bg'

        bridgegroup = {
            'name': bg_name,
            'description': 'test-bg'
        }

        bg_db = self.bridge_group_db.create_bridgegroup(
            self.context, bridgegroup)
        bg_db.devices.append(self.device_db_mixin.get_device_db(
            self.context, device_db['id']))
        bg_db.save(self.context.session)
        self.assertIs(True, 'id' in bg_db)
        vpc_name = 'fake-vpc1'
        vpc = {
            'name': vpc_name,
            'label': vpc_name,
            'description': vpc_name
        }
        vpc_db_obj = self.vpc_db.create_vpc(self.context, vpc)

        self.assertIs(True, 'id' in vpc_db_obj)

        with mock.patch.object(self.plugin, 'config_vlan_on_devices') \
                as config_vlans:
            vlan = {
                'vlan': {
                    'name': 'test-vlan',
                    'bridge_group_name': bg_name,
                    'vpc_name': vpc_name,
                    'tag': 2
                }
            }
            config_vlans.return_value = None

            vlan_db = self.plugin.create_vlan(self.context, vlan)
        return vlan_db

    def create_port(self, device, name, description='',
                    admin_status=constants.ACTIVE,
                    switch_port_mode=netforce_constants.TRUNK_MODE):

        port = {
            'port': {
                'name': name,
                'description': description,
                'admin_status': admin_status,
                'switch_port_mode': 'trunk',
                'device_id': device['id']
            }
        }

        return self.plugin.create_port(self.context, port)

    def test_update_port_flipping(self):
        def get_device_driver_mock():
            data = [{'mac_address': 'fake:macf:akem:acfa',
                     'vlan': 2}]
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock. \
                get_mac_addresses_on_interface.return_value = data
            device_driver_mock.close.return_value = None
            return device_driver_mock
        device_db = self.create_device()
        port_db = self.create_port(device_db, 'eth1', description='test port')
        vlan_db = self.create_vlan_for_port_flip(device_db)
        with mock.patch.object(self.plugin, '_get_device_driver'):
            update_port = {
                'port': {
                    'switch_port_mode': 'access',
                    "vlans": [{
                        "vlan": {
                            "tag": vlan_db['tag'],
                            "is_native": True
                        }
                    }]
                }
            }
            updated_port_db = self.plugin.update_port(self.context,
                                                      port_db['id'],
                                                      update_port)
            self.assertEqual(constants.ACTIVE,
                             updated_port_db['admin_status'],
                             'port is in ')

    def test_create_device(self):
        # create bubble
        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_db = self.plugin.create_bubble(
            self.context, body)
        self.assertIsNotNone(bubble_db)

        device_type = {
            'devicetype': {
                'name': 'Top of the Rack Switch',
                'type': 'TOR'
            }
        }

        device_type_db = self.plugin.create_devicetype(
            self.context, device_type)
        self.assertIsNotNone(device_type_db)

        device = {
            'device': {
                'name': 'test-device',
                'description': 'test device',
                'management_ip': '1.1.1.1',
                'username': 'arista',
                'password': 'arista',
                'type': 'TOR',
                'os_type': 'ebayjunos'
            }
        }
        #with mock.patch.object(self.plugin, '_get_device_driver') \
        #        as device_ops_driver:
        #    device_ops_driver.return_value = MockDeviceDriver()
        device_db = self.plugin.create_device(self.context, device)
        self.assertIsNotNone(device_db)
        """    self.assertIs(4, len(device_db['ports']))
            for port_id in device_db['ports']:
                port = self.plugin.get_port_db(self.context, port_id)
                self.assertIsNotNone(port)
                if port['name'] == 'Ethernet3':
                    self.assertEqual(
                        netforce_constants.SUSPENDED, port['admin_status'])
                else:
                    self.assertEqual(constants.ACTIVE, port['admin_status'])
        """

    def test_create_vlan(self):
        # create bubble
        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_db = self.plugin.create_bubble(
            self.context, body)
        self.assertIsNotNone(bubble_db)
        # create distribution switch
        device_type1 = {
            'devicetype': {
                'name': 'Distribution Switch',
                'type': 'DISTRIBUTION'
            }
        }

        device_type_db1 = self.plugin.create_devicetype(
            self.context, device_type1)
        self.assertIsNotNone(device_type_db1)

        # create device
        device1 = {
            'device': {
                'name': 'ten1-1',
                'description': 'test device1',
                'management_ip': '1.1.1.2',
                'type': 'DISTRIBUTION',
                'os_type': 'ebayjunos',
                'bubble_id': bubble_db['id'],
                'device_type_id': device_type_db1['id']
            }
        }
        device_db1 = {}
        with mock.patch.object(self.plugin, '_discover_ports_on_device') \
                as discover_ports:
            discover_ports.return_value = None
            device_db1 = self.plugin.create_device(self.context, device1)

        # create device 2
        device2 = {
            'device': {
                'name': 'ten1-2',
                'description': 'test device1',
                'management_ip': '1.1.1.3',
                'type': 'DISTRIBUTION',
                'os_type': 'ebayjunos',
                'bubble_id': bubble_db['id'],
                'device_type_id': device_type_db1['id']
            }
        }

        device_db2 = {}
        with mock.patch.object(self.plugin, '_discover_ports_on_device') \
                as discover_ports:
            discover_ports.return_value = None
            device_db2 = self.plugin.create_device(self.context, device2)

        # create device type
        device_type = {
            'devicetype': {
                'name': 'Top of the Rack Switch',
                'type': 'TORS'
            }
        }

        device_type_db = self.plugin.create_devicetype(
            self.context, device_type)
        self.assertIsNotNone(device_type_db)
        # create device
        device = {
            'device': {
                'name': 'pages',
                'description': 'test device',
                'management_ip': '1.1.1.1',
                'username': 'arista',
                'password': 'arista',
                'type': 'TORS',
                'os_type': 'ebayjunos',
                'bubble_id': bubble_db['id']
            }
        }

        device_db = {}
        with mock.patch.object(self.plugin, '_discover_ports_on_device') \
                as discover_ports:
            discover_ports.return_value = None
            device_db = self.plugin.create_device(self.context, device)

        # create bg
        bg_name = 'test-bg'

        bridgegroup = {
            'name': bg_name,
            'description': 'test-bg'
        }

        bg_db = self.bridge_group_db.create_bridgegroup(
            self.context, bridgegroup)
        bg_db.devices.append(self.device_db_mixin.get_device_db(
            self.context, device_db['id']))
        bg_db.save(self.context.session)
        self.assertIs(True, 'id' in bg_db)

        #create bg1
        bg_name1 = 'ten1-1'

        bridgegroup1 = {
            'name': bg_name1,
            'description': 'ten1-1'
        }

        bg_db1 = self.bridge_group_db.create_bridgegroup(
            self.context, bridgegroup1)
        bg_db1.devices.append(self.device_db_mixin.get_device_db(
            self.context, device_db1['id']))
        bg_db1.save(self.context.session)
        self.assertIs(True, 'id' in bg_db1)

        # create bg2
        bg_name1 = 'ten1-2'

        bridgegroup2 = {
            'name': bg_name1,
            'description': 'ten1-2'
        }

        bg_db2 = self.bridge_group_db.create_bridgegroup(
            self.context, bridgegroup2)
        bg_db2.devices.append(self.device_db_mixin.get_device_db(
            self.context, device_db2['id']))
        bg_db2.save(self.context.session)
        self.assertIs(True, 'id' in bg_db2)
        # create vpc
        vpc_name = 'fake-vpc1'
        vpc = {
            'name': vpc_name,
            'label': vpc_name,
            'description': vpc_name
        }
        vpc_db_obj = self.vpc_db.create_vpc(self.context, vpc)

        self.assertIs(True, 'id' in vpc_db_obj)
        # create vpc2
        vpc_name2 = 'test-vpc2'
        vpc = {
            'name': vpc_name2,
            'label': vpc_name2,
            'description': vpc_name2
        }
        vpc_db_obj2 = self.vpc_db.create_vpc(self.context, vpc)

        self.assertIs(True, 'id' in vpc_db_obj)
        # vrf body
        vrf_body = {
            "vrf": {
                "name": "fake-vrf",
                "description": "fake",
                "bubble_id": bubble_db['id'],
                "vpc_id": vpc_db_obj['id'],
                "tenant_id": "1232"
            }
        }
        vrf_db = self.plugin.create_vrf(self.context, vrf_body)
        self.assertIs(True, 'id' in vrf_db)
        # vrf body2
        vrf_body = {
            "vrf": {
                "name": "fake-vrf2",
                "description": "fake2",
                "bubble_id": bubble_db['id'],
                "vpc_id": vpc_db_obj2['id'],
                "tenant_id": "1232"
            }
        }
        vrf_db2 = self.plugin.create_vrf(self.context, vrf_body)
        self.assertIs(True, 'id' in vrf_db2)

        vlan = {
            'vlan': {
                'name': 'test-vlan',
                'bridge_group_name': bg_name,
                'vpc_name': vpc_name,
                'tag': 3
            }
        }

        vlan_db_1 = self.plugin.create_vlan(self.context, vlan)
        self.assertIsNotNone(vlan_db_1)
        self.assertIs(1, len(bg_db.vlans))
        self.assertIs(1, len(vpc_db_obj.vlans))
        self.assertIs(3, vlan_db_1['tag'])
        self.assertIs(constants.ACTIVE, vlan_db_1['status'])

        # create vlan2

        vlan = {
            'vlan': {
                'name': 'test-vlan2',
                'bridge_group_name': bg_name,
                'vpc_name': vpc_name2,
                'tag': 2
            }
        }
        vlan_db_2 = self.plugin.create_vlan(self.context, vlan)
        self.assertIsNotNone(vlan_db_2)
        self.assertIs(2, len(bg_db.vlans))
        self.assertIs(1, len(vpc_db_obj2.vlans))
        self.assertIs(2, vlan_db_2['tag'])
        self.assertIs(constants.ACTIVE, vlan_db_2['status'])

        # create vlan4
        # This case is same as the one passed from neutron
        vlan = {
            'vlan': {
                'bridge_group_name': bg_name,
                'vpc_name': vpc_name2,
            }
        }

        vlan_db_2 = self.plugin.create_vlan(self.context, vlan)
        self.assertIsNotNone(vlan_db_2)
        self.assertIs(2, len(bg_db.vlans))
        self.assertIs(1, len(vpc_db_obj2.vlans))
        self.assertIs(2, vlan_db_2['tag'])
        self.assertIs(constants.ACTIVE, vlan_db_2['status'])
        # create vlan5
        # This case is same as the one passed from neutron
        vlan = {
            'vlan': {
                'bridge_group_name': bg_name,
                'name': 'test-5',
                'tag': 5
            }
        }

        vlan_db_5 = self.plugin.create_vlan(self.context, vlan)
        self.assertIsNotNone(vlan_db_5)
        # This case is same as the one passed from neutron
        vlan = {
            'vlan': {
                'bridge_group_name': bg_name,
                'name': 'test-6',
                'tag': 6
            }
        }

        vlan_db_6 = self.plugin.create_vlan(self.context, vlan)
        self.assertIsNotNone(vlan_db_6)
        # This case is same as the one passed from neutron
        vlan = {
            'vlan': {
                'bridge_group_name': bg_name,
                'name': 'test-6',
                'tag': 7
            }
        }

        self.assertRaises(
            netforce_exceptions.ConfiguredVlanConflictsWithRequested,
            self.plugin.create_vlan, self.context, vlan)
        return [vlan_db_1, vlan_db_2]

    def test_create_vlan_working_bubble_devices(self):
        # create bubble
        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_db = self.plugin.create_bubble(
            self.context, body)
        self.assertIsNotNone(bubble_db)
        # create distribution switch
        device_type1 = {
            'devicetype': {
                'name': 'Distribution Switch',
                'type': 'DISTRIBUTION'
            }
        }

        device_type_db1 = self.plugin.create_devicetype(
            self.context, device_type1)
        self.assertIsNotNone(device_type_db1)

        # create device
        device1 = {
            'device': {
                'name': 'ten1-1',
                'description': 'test device1',
                'management_ip': '8.8.8.8',
                'type': 'DISTRIBUTION',
                'os_type': 'ebayjunos',
                'bubble_id': bubble_db['id'],
                'device_type_id': device_type_db1['id']
            }
        }
        device_db1 = {}
        with mock.patch.object(self.plugin, '_discover_ports_on_device') \
                as discover_ports:
            discover_ports.return_value = None
            device_db1 = self.plugin.create_device(self.context, device1)

        # create device 2
        device2 = {
            'device': {
                'name': 'ten1-2',
                'description': 'test device1',
                'management_ip': '1.1.4.4',
                'type': 'DISTRIBUTION',
                'os_type': 'ebayjunos',
                'bubble_id': bubble_db['id'],
                'device_type_id': device_type_db1['id']
            }
        }

        device_db2 = {}
        with mock.patch.object(self.plugin, '_discover_ports_on_device') \
                as discover_ports:
            discover_ports.return_value = None
            device_db2 = self.plugin.create_device(self.context, device2)

        # create device type
        device_type = {
            'devicetype': {
                'name': 'Top of the Rack Switch',
                'type': 'TORS'
            }
        }

        device_type_db = self.plugin.create_devicetype(
            self.context, device_type)
        self.assertIsNotNone(device_type_db)
        # create device
        device = {
            'device': {
                'name': 'pages',
                'description': 'test device',
                'management_ip': '1.1.1.1',
                'username': 'arista',
                'password': 'arista',
                'type': 'TORS',
                'os_type': 'ebayjunos',
                'bubble_id': bubble_db['id']
            }
        }

        device_db = {}
        with mock.patch.object(self.plugin, '_discover_ports_on_device') \
                as discover_ports:
            discover_ports.return_value = None
            device_db = self.plugin.create_device(self.context, device)

        # create bg
        bg_name = 'test-bg'

        bridgegroup = {
            'name': bg_name,
            'description': 'test-bg'
        }

        bg_db = self.bridge_group_db.create_bridgegroup(
            self.context, bridgegroup)
        bg_db.devices.append(self.device_db_mixin.get_device_db(
            self.context, device_db['id']))
        bg_db.save(self.context.session)
        self.assertIs(True, 'id' in bg_db)

        #create bg1
        bg_name1 = 'ten1-1'

        bridgegroup1 = {
            'name': bg_name1,
            'description': 'ten1-1'
        }

        bg_db1 = self.bridge_group_db.create_bridgegroup(
            self.context, bridgegroup1)
        bg_db1.devices.append(self.device_db_mixin.get_device_db(
            self.context, device_db1['id']))
        bg_db1.save(self.context.session)
        self.assertIs(True, 'id' in bg_db1)

        # create bg2
        bg_name1 = 'ten1-2'

        bridgegroup2 = {
            'name': bg_name1,
            'description': 'ten1-2'
        }

        bg_db2 = self.bridge_group_db.create_bridgegroup(
            self.context, bridgegroup2)
        bg_db2.devices.append(self.device_db_mixin.get_device_db(
            self.context, device_db2['id']))
        bg_db2.save(self.context.session)
        self.assertIs(True, 'id' in bg_db2)

        # create vpc
        vpc_name = 'fake-vpc1'
        vpc = {
            'name': vpc_name,
            'label': vpc_name,
            'description': vpc_name
        }
        vpc_db_obj = self.vpc_db.create_vpc(self.context, vpc)

        self.assertIs(True, 'id' in vpc_db_obj)
        # create vpc2
        vpc_name2 = 'test-vpc2'
        vpc = {
            'name': vpc_name2,
            'label': vpc_name2,
            'description': vpc_name2
        }
        vpc_db_obj2 = self.vpc_db.create_vpc(self.context, vpc)

        self.assertIs(True, 'id' in vpc_db_obj)
        # vrf body
        vrf_body = {
            "vrf": {
                "name": "fake-vrf",
                "description": "fake",
                "bubble_id": bubble_db['id'],
                "vpc_id": vpc_db_obj['id'],
                "tenant_id": "1232"
            }
        }
        vrf_db = self.plugin.create_vrf(self.context, vrf_body)
        self.assertIs(True, 'id' in vrf_db)
        # vrf body2
        vrf_body = {
            "vrf": {
                "name": "fake-vrf2",
                "description": "fake2",
                "bubble_id": bubble_db['id'],
                "vpc_id": vpc_db_obj2['id'],
                "tenant_id": "1232"
            }
        }
        vrf_db2 = self.plugin.create_vrf(self.context, vrf_body)
        self.assertIs(True, 'id' in vrf_db2)

        vlan = {
            'vlan': {
                'name': 'test-vlan',
                'bridge_group_name': bg_name,
                'vpc_name': vpc_name,
                'tag': 3
            }
        }

        vlan_db_1 = self.plugin.create_vlan(self.context, vlan)
        self.assertIsNotNone(vlan_db_1)
        self.assertIs(1, len(bg_db.vlans))
        self.assertIs(1, len(vpc_db_obj.vlans))
        self.assertIs(3, vlan_db_1['tag'])
        self.assertIs(constants.ACTIVE, vlan_db_1['status'])

        # create vlan2

        vlan = {
            'vlan': {
                'name': 'test-vlan2',
                'bridge_group_name': bg_name,
                'vpc_name': vpc_name2,
                'tag': 2
            }
        }
        vlan_db_2 = self.plugin.create_vlan(self.context, vlan)
        self.assertIsNotNone(vlan_db_2)
        self.assertIs(2, len(bg_db.vlans))
        self.assertIs(1, len(vpc_db_obj2.vlans))
        self.assertIs(2, vlan_db_2['tag'])
        self.assertIs(constants.ACTIVE, vlan_db_2['status'])

        # create vlan4
        # This case is same as the one passed from neutron
        vlan = {
            'vlan': {
                'bridge_group_name': bg_name,
                'vpc_name': vpc_name2,
            }
        }

        vlan_db_2 = self.plugin.create_vlan(self.context, vlan)
        self.assertIsNotNone(vlan_db_2)
        self.assertIs(2, len(bg_db.vlans))
        self.assertIs(1, len(vpc_db_obj2.vlans))
        self.assertIs(2, vlan_db_2['tag'])
        self.assertIs(constants.ACTIVE, vlan_db_2['status'])
        # create vlan5
        # This case is same as the one passed from neutron
        vlan = {
            'vlan': {
                'bridge_group_name': bg_name,
                'name': 'test-5',
                'tag': 5
            }
        }

        vlan_db_5 = self.plugin.create_vlan(self.context, vlan)
        self.assertIsNotNone(vlan_db_5)
        # This case is same as the one passed from neutron
        vlan = {
            'vlan': {
                'bridge_group_name': bg_name,
                'name': 'test-6',
                'tag': 6
            }
        }

        vlan_db_6 = self.plugin.create_vlan(self.context, vlan)
        self.assertIsNotNone(vlan_db_6)
        # This case is same as the one passed from neutron
        vlan = {
            'vlan': {
                'bridge_group_name': bg_name,
                'name': 'test-6',
                'tag': 7
            }
        }

        self.assertRaises(
            netforce_exceptions.ConfiguredVlanConflictsWithRequested,
            self.plugin.create_vlan, self.context, vlan)
        return [vlan_db_1, vlan_db_2]

    def test__validate_subnet_is_allowed(self):
        cfg.CONF.set_override('allowed_subnet', '10.0.0.0/8')

        self.plugin._validate_subnet_is_allowed('10.1.1.0/24')

        self.assertRaises(netforce_exceptions.SubnetIsNotAllowed,
                          self.plugin._validate_subnet_is_allowed,
                          '172.1.1.1/24')

        self.assertRaises(netforce_exceptions.SubnetIsNotAllowed,
                          self.plugin._validate_subnet_is_allowed,
                          '8.0.0.0/8')

    def test_create_subnet(self):
        vlan_model = self.test_create_vlan_working_bubble_devices()
        self.assertIsNotNone(vlan_model)
        subnet = {
            'subnet': {
                'tenant_id': '12345',
                'name': 'test-prod-routed-subnet',
                'cidr': '66.135.216.189/24',
                'gateway_ip': '66.135.216.190',
                'broadcast_ip': '66.135.216.255',
                'netmask': '255.255.255.0',
                'vlan_id': vlan_model[0]['id']
            }
        }

        with contextlib.nested(
            mock.patch.object(self.plugin, '_get_device_driver'),
            mock.patch.object(self.plugin, '_validate_subnet_is_allowed'),
            mock.patch.object(self.plugin, '_check_cidr_overlap_on_bubble'),
            mock.patch.object(self.plugin, '_get_pingable_bubble_device_'),
        ) as (device_ops_driver,
              validate_allowed,
              cidr_overlap,
              ping_bubble_devices):

            cidr_overlap.return_value = None
            validate_allowed.return_value = None

            device_driver = device_ops_driver()
            device_driver.open.return_value = None

            device_driver.get_vlan_interface_name.\
                return_value = None
            device_driver.get_subnets_on_vlan_interface.\
                return_value = None
            device_driver.get_routes.return_value =\
                ['1.1.1.1/24', '0.0.0.0/0']
            commands = "fake commands run for create_subnet"
            ping_bubble_devices.side_effect = lambda x: x[0]
            device_driver.create_subnet.return_value = commands
            subnet_model = self.plugin.create_subnet(
                self.context, subnet)
        self.assertIs(True, 'id' in subnet_model)
        self.assertIs(vlan_model[0]['id'], subnet_model['vlan_id'])
        self.assertIn('start_ip', subnet_model)
        self.assertIn('end_ip', subnet_model)

    def test_create_subnet_overlapping(self):
        cfg.CONF.set_override('allowed_subnet', '172.0.0.0/8')
        vlan_model = self.test_create_vlan_working_bubble_devices()
        self.assertIsNotNone(vlan_model)
        subnet1 = {
            'subnet': {
                'tenant_id': '12345',
                'name': 'test-prod-routed-subnet',
                'cidr': '172.1.1.0/24',
                'gateway_ip': '172.1.1.1',
                'broadcast_ip': '172.1.1.255',
                'netmask': '255.255.255.0',
                'vlan_id': vlan_model[0]['id']
            }
        }

        subnet2 = {
            'subnet': {
                'tenant_id': '12345',
                'name': 'test-prod-routed-subnet',
                'cidr': '172.2.1.0/24',
                'gateway_ip': '172.1.2.1',
                'broadcast_ip': '172.1.2.255',
                'netmask': '255.255.255.0',
                'vlan_id': vlan_model[0]['id']
            }
        }

        subnet3 = {
            'subnet': {
                'tenant_id': '12345',
                'name': 'test-prod-routed-subnet',
                'cidr': '172.1.0.0/16',
                'gateway_ip': '172.1.0.1',
                'broadcast_ip': '172.1.0.255',
                'netmask': '255.255.0.0',
                'vlan_id': vlan_model[0]['id']
            }
        }

        subnet4 = {
            'subnet': {
                'tenant_id': '12345',
                'name': 'test-prod-routed-subnet',
                'cidr': '172.1.1.0/24',
                'gateway_ip': '172.1.1.1',
                'broadcast_ip': '172.1.1.255',
                'netmask': '255.255.255.0',
                'vlan_id': vlan_model[0]['id']
            }
        }

        with contextlib.nested(
            mock.patch.object(self.plugin, '_get_device_driver'),
            mock.patch.object(self.plugin, '_validate_subnet_is_allowed'),
            mock.patch.object(self.plugin, '_check_cidr_overlap_on_bubble'),
                mock.patch.object(self.plugin, '_get_pingable_bubble_device_'),
        ) as (device_ops_driver, validate_allowed,
              cidr_overlap,
              ping_bubble_devices):

            validate_allowed.return_value = None
            cidr_overlap.return_value = None
            ping_bubble_devices.side_effect = lambda x: x[0]
            device_driver = device_ops_driver()
            device_driver.open.return_value = None
            device_driver.get_vlan_interface_name.\
                return_value = None
            device_driver.get_subnets_on_vlan_interface.\
                return_value = None
            commands = "fake commands run for" \
                       " create_subnet"
            device_driver.create_subnet.return_value =\
                commands
            subnet_dict1 = self.plugin.create_subnet(
                self.context, subnet1)
            self.plugin.create_subnet(self.context,
                                      subnet2)
            subnet_dict4 = self.plugin.create_subnet(
                self.context, subnet4)
            self.assertEqual(subnet_dict4['cidr'],
                             subnet_dict1['cidr'])
            (self.
             assertRaises(netforce_exceptions.
                          SubnetAlreadyConfigured,
                          self.plugin.create_subnet, self.context,
                          subnet3))

    def test_create_subnet_overlapping_on_bubble(self):
        cfg.CONF.set_override('allowed_subnet', '172.0.0.0/8')
        vlan_model = self.test_create_vlan_working_bubble_devices()
        self.assertIsNotNone(vlan_model)
        subnet1 = {
            'subnet': {
                'tenant_id': '12345',
                'name': 'test-prod-routed-subnet',
                'cidr': '172.1.1.0/24',
                'gateway_ip': '172.1.1.1',
                'broadcast_ip': '172.1.1.255',
                'netmask': '255.255.255.0',
                'vlan_id': vlan_model[0]['id']
            }
        }

        with contextlib.nested(
            mock.patch.object(self.plugin, '_get_device_driver'),
            mock.patch.object(self.plugin, '_get_pingable_bubble_device_'),
        ) as (device_ops_driver,
              ping_bubble_devices):
            ping_bubble_devices.side_effect = lambda x: x[0]
            device_driver = device_ops_driver()
            device_driver.open.return_value = None
            device_driver.get_vlan_interface_name.return_value = None
            device_driver.get_subnets_on_vlan_interface.return_value\
                = None
            device_driver.get_routes.return_value = ['172.1.1.0/24']
            commands = "fake commands run for create_subnet"
            device_driver.create_subnet.return_value = commands
            self.assertRaises(
                netforce_exceptions.SubnetAlreadyConfiguredOnBubble,
                self.plugin.create_subnet, self.context,
                subnet1)

    def test_create_subnet_delete_for_failure(self):
        vlan_model = self.test_create_vlan_working_bubble_devices()
        self.assertIsNotNone(vlan_model)
        subnet = {
            'subnet': {
                'tenant_id': '12345',
                'name': 'test-prod-routed-subnet',
                'cidr': '66.135.216.189/24',
                'gateway_ip': '66.135.216.190',
                'broadcast_ip': '66.135.216.255',
                'netmask': '255.255.255.0',
                'vlan_id': vlan_model[0]['id']
            }
        }
        with contextlib.nested(
                mock.patch.object(self.plugin,
                                  '_get_device_driver'),
                mock.patch.object(self.plugin,
                                  '_validate_subnet_is_allowed'),
                mock.patch.object(self.plugin,
                                  '_check_cidr_overlap_on_bubble'),
                mock.patch.object(self.plugin,
                                  '_validate_subnet_push'),
                mock.patch.object(self.plugin,
                                  '_delete_subnet_on_device'),
        ) as (device_ops_driver,
              validate_allowed,
              cidr_overlap,
              validate_cidr_push,
              _delete_subnet_on_device):

                cidr_overlap.return_value = None
                validate_allowed.return_value = None
                device_driver = device_ops_driver()
                device_driver.open.return_value = None

                device_driver.get_vlan_interface_name.\
                    return_value = None
                device_driver.get_subnets_on_vlan_interface.\
                    return_value = None
                device_driver.get_routes.return_value =\
                    ['1.1.1.1/24']
                device_driver.create_subnet.\
                    return_value = None
                device_driver.delete_subnet.\
                    return_value = None
                validate_cidr_push.side_effect = [
                    None, exceptions.BadRequest]
                (self.assertRaises(
                    netforce_exceptions.DevicePostChangeValidationError,
                    self.plugin.create_subnet,
                    self.context, subnet))
                _delete_subnet_on_device.assert_called_once()

    def test_create_subnet_rollback_failed(self):
        vlan_model = self.test_create_vlan_working_bubble_devices()
        self.assertIsNotNone(vlan_model)
        subnet = {
            'subnet': {
                'tenant_id': '12345',
                'name': 'test-prod-routed-subnet',
                'cidr': '66.135.216.189/24',
                'gateway_ip': '66.135.216.190',
                'broadcast_ip': '66.135.216.255',
                'netmask': '255.255.255.0',
                'vlan_id': vlan_model[0]['id']
            }
        }
        with contextlib.nested(
                mock.patch.object(self.plugin,
                                  '_get_device_driver'),
                mock.patch.object(self.plugin,
                                  '_validate_subnet_is_allowed'),
                mock.patch.object(self.plugin,
                                  '_check_cidr_overlap_on_bubble'),
                mock.patch.object(self.plugin,
                                  '_validate_subnet_push'),
        ) as (device_ops_driver,
              validate_allowed,
              cidr_overlap,
              validate_cidr_push):

                cidr_overlap.return_value = None
                validate_allowed.return_value = None
                device_driver = device_ops_driver()
                device_driver.open.return_value = None

                device_driver.get_vlan_interface_name.\
                    return_value = None
                device_driver.get_subnets_on_vlan_interface.\
                    return_value = None
                device_driver.get_routes.return_value =\
                    ['1.1.1.1/24']
                device_driver.create_subnet.\
                    return_value = None
                device_driver.delete_subnet.\
                    return_value = None
                validate_cidr_push.side_effect = [
                    None, exceptions.BadRequest]
                device_driver.delete_subnet_on_device.side_effect = \
                    Exception("Boom!")
                (self.assertRaises(
                    netforce_exceptions.DevicePostChangeValidationError,
                    self.plugin.create_subnet,
                    self.context, subnet))

    def test_get_port_wiri(self):
        device_db = self.create_device()
        port_db = self.create_port(device_db, 'Ethernet1',
                                   description='test port')

        with mock.patch.object(self.plugin,
                              '_get_device_driver') as device_ops_driver:

            device_driver = device_ops_driver()
            vlans_on_interface = {'access_vlan': u'4', 'native_vlan': u'1'}
            port_data = {
                u'Ethernet1':
                    {
                        'is_enabled': True, 'description': u'test port',
                        'last_flapped': 1471986099.8475888, 'is_up': True,
                        'mac_address': u'74:db:d1:e0:fe:d8', 'speed': 0
                    }
            }
            device_driver.get_interfaces_by_name.return_value = port_data
            device_driver.get_vlans_on_interface.return_value =\
                vlans_on_interface
            cxt = context.get_admin_context()
            current_data = self.plugin.get_port(cxt, port_db['id'],
                                                ['check_device'])
            self.assertIn('device_data', current_data)

    def test_create_subnet_with_reserve_ip_count(self):
        vlan_model = self.test_create_vlan_working_bubble_devices()
        self.assertIsNotNone(vlan_model)
        subnet = {
            'subnet': {
                'tenant_id': '12345',
                'name': 'fake',
                'cidr': '10.1.1.0/24',
                'gateway_ip': '10.1.1.1',
                'broadcast_ip': '10.1.1.255',
                'netmask': '255.255.255.0',
                'vlan_id': vlan_model[0]['id'],
                'reserve_ip_count': 2
            }
        }

        with mock.patch.object(self.plugin,
                              '_get_device_driver') as device_ops_driver:
                    device_driver = device_ops_driver()
                    device_driver.open.return_value = None

                    device_driver.get_vlan_interface_name.return_value = None
                    device_driver.get_subnets_on_vlan_interface.return_value =\
                        None
                    commands = "fake commands run for create_subnet"

                    device_driver.create_subnet.return_value = commands
                    net_ex = netforce_exceptions
                    self.assertRaises(
                        net_ex.GivenReserveIPCountLessThanDefaultCount,
                        self.plugin.create_subnet, self.context, subnet)

    def test_create_subnet_with_trace_route_skip_for_fake_vpc(self):
        vlan_model = self.test_create_vlan_working_bubble_devices()
        self.assertIsNotNone(vlan_model)
        subnet = {
            'subnet': {
                'tenant_id': '12345',
                'name': 'test-prod-routed-subnet',
                'cidr': '66.135.216.189/24',
                'gateway_ip': '66.135.216.190',
                'broadcast_ip': '66.135.216.255',
                'netmask': '255.255.255.0',
                'vlan_id': vlan_model[0]['id']
            }
        }

        with contextlib.nested(
            mock.patch.object(self.plugin, '_get_device_driver'),
            mock.patch.object(self.plugin, '_validate_subnet_is_allowed'),
            mock.patch.object(self.plugin, '_check_cidr_overlap_on_bubble'),
            mock.patch.object(self.plugin, '_get_pingable_bubble_device_'),

        ) as (device_ops_driver, validate_allowed,
              cidr_overlap,
              ping_bubble_devices):

            CONF.vpcs_for_traceroute_check = ['fake']
            cidr_overlap.return_value = None
            validate_allowed.return_value = None

            device_driver = device_ops_driver()
            device_driver.open.return_value = None
            ping_bubble_devices.side_effect = lambda x: x[0]
            device_driver.get_vlan_interface_name.return_value = None
            device_driver.get_subnets_on_vlan_interface.return_value = None
            device_driver.get_routes.return_value = ['1.1.1.1/24']
            commands = "fake commands run for create_subnet"
            device_driver.create_subnet.return_value = commands
            subnet_model = self.plugin.create_subnet(self.context, subnet)

        self.assertIs(True, 'id' in subnet_model)
        self.assertIs(vlan_model[0]['id'], subnet_model['vlan_id'])
        self.assertIn('start_ip', subnet_model)
        self.assertIn('end_ip', subnet_model)


class TestVlanFlippingOnPort(BaseNetforcePluginSetup):

    def setUp(self):
        super(TestVlanFlippingOnPort, self).setUp()

        # create vpc
        self.vpc = {
            "vpc": {
                "name": "test-vpc",
                "description": "test vpc description",
                "label": "test-vpc-label"
            }
        }
        self.vpc_db = self.plugin.create_vpc(self.context, self.vpc)

        # create vpc2
        self.vpc2 = {
            "vpc": {
                "name": "test-vpc2",
                "description": "test vpc description",
                "label": "test-vpc-label"
            }
        }
        self.vpc_db2 = self.plugin.create_vpc(self.context, self.vpc2)

        # device type creation
        self.device_type = {
            'devicetype': {
                'name': 'Top of the Rack Switch',
                'type': 'TOR'
            }
        }

        self.device_type_db = self.plugin.create_devicetype(
            self.context, self.device_type)
        self.assertIsNotNone(self.device_type_db)

        # bridgegroup creation
        self.bridge_group = {
            'bridgegroup': {
                'name': 'test-bridgegroup',
                'description': 'test bridge group'
            }
        }

        self.bridge_group_db = self.plugin.create_bridgegroup(
            self.context, self.bridge_group)

        # create device
        device = {
            'device': {
                'name': 'test-device',
                'description': 'test device',
                'management_ip': '1.1.1.1',
                'username': 'arista',
                'password': 'arista',
                'type': 'TOR',
                'bridge_group_id': self.bridge_group_db['id'],
                'os_type': 'ebayjunos'
            }
        }

        # mock port discovery and create port
        with mock.patch.object(self.plugin, '_discover_ports_on_device') \
                as discover_ports:
            discover_ports.return_value = None
            device_db = self.plugin.create_device(self.context, device)
            self.assertIsNotNone(device_db)
            self.assertIs(0, len(device_db['ports']))
            self.port = {
                'port': {
                    'name': 'eth1',
                    'description': 'test port',
                    'admin_status': constants.ACTIVE,
                    'switch_port_mode': netforce_constants.TRUNK_MODE,
                    'device_id': device_db['id'],
                    'asset_id': 'ASSET00419247'
                }
            }
        self.port_db = self.plugin.create_port(self.context, self.port)

        # create vlans.
        self.vlan = {
            "vlan": {
                "name": "test-vlan-1",
                "bridge_group_name": "test-bridgegroup",
                "vpc_name": "test-vpc",
                "admin_status": "ACTIVE",
                'tag': 2
            }
        }
        # create vlans.
        self.vlan2 = {
            "vlan": {
                "name": "test-vlan-2",
                "bridge_group_name": "test-bridgegroup",
                "vpc_name": "test-vpc2",
                "admin_status": "ACTIVE",
                'tag': 3
            }
        }
        with mock.patch.object(self.plugin, 'config_vlan_on_devices') \
                as vlan_config_mock:
            vlan_config_mock.return_value = None
            self.vlan_db = self.plugin.create_vlan(self.context, self.vlan)
            self.vlan_db2 = self.plugin.create_vlan(self.context, self.vlan2)

    def test_update_port_vlan_tagging_by_vpc_name(self):

        # tag port using vpc_label
        port = {
            "port": {
                "switch_port_mode": "access",
                "vlans": [
                    {
                        "vlan": {
                            "vpc_name": 'test-vpc',
                            "is_native": True
                        }
                    }
                ]
            }
        }

        def get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock.\
                update_switch_port_vlans.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with mock.patch.object(self.plugin, '_get_device_driver') \
                as device_driver:
            device_driver.return_value = get_device_driver_mock()
            updated_port_db = self.plugin.update_port(
                self.context, self.port_db['id'], port)
            self.assertIs(True, 'id' in updated_port_db)
            self.assertIsNone(updated_port_db['ticket'])

    def test_update_port_vlan_tagging_by_vlan_tag(self):
        port = {
            "port": {
                "switch_port_mode": "access",
                "vlans": [
                    {
                        "vlan": {
                            "tag": '2',
                            "is_native": True
                        }
                    }
                ]
            }
        }

        def get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock.\
                update_switch_port_vlans.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with mock.patch.object(self.plugin, '_get_device_driver') \
                as device_driver:
            device_driver.return_value = get_device_driver_mock()
            updated_port_db = self.plugin.update_port(
                self.context, self.port_db['id'], port)
            self.assertIs(True, 'id' in updated_port_db)
            self.assertIs(True, 'vlans' in updated_port_db)
            self.assertEqual(self.vlan_db['tag'], updated_port_db[
                              'vlans'][0]['vlan']['tag'])

    def test_update_port_vlan_tagging_by_vlan_id(self):
        port = {
            "port": {
                "switch_port_mode": "access",
                "vlans": [
                    {
                        "vlan": {
                            "id": self.vlan_db['id'],
                            "is_native": True
                        }
                    }
                ]
            }
        }

        def get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock.\
                update_switch_port_vlans.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with mock.patch.object(self.plugin, '_get_device_driver') \
                as device_driver:
            device_driver.return_value = get_device_driver_mock()
            updated_port_db = self.plugin.update_port(
                self.context, self.port_db['id'], port)
            self.assertIs(True, 'id' in updated_port_db)
            self.assertIs(True, 'vlans' in updated_port_db)
            self.assertEqual(self.vlan_db['id'], updated_port_db[
                'vlans'][0]['vlan']['id'])
            self.assertEqual(self.vlan_db['tag'], updated_port_db[
                'vlans'][0]['vlan']['tag'])

    def test_update_port_with_mac_address(self):
        mac_address = "08:00:27:31:9c:b8"
        vlan_tag = self.vlan_db['tag']
        port = {
            "port": {
                "switch_port_mode": "access",
                "vlans": [{
                    "vlan": {
                        "id": self.vlan_db['id'],
                        "is_native": True}}],
                'mac_address': mac_address
            }
        }

        with contextlib.nested(
                    mock.patch.object(self.plugin,
                               'push_vlanportassociation_to_device'),
                    mock.patch.object(self.plugin,
                              '_get_device_driver')) as (_, device_ops_driver):

            device_driver = device_ops_driver()
            data = [{'mac_address': mac_address,
                    'vlan': vlan_tag}]
            device_driver.get_mac_addresses_on_interface.return_value = data
            self.plugin.update_port(self.context, self.port_db['id'], port)

            device_driver.get_mac_addresses_on_interface \
                .assert_called_once_with(self.port_db['name'], vlan_tag)

    def test_update_port_with_mac_address_no_native_vlan(self):
        mac_address = "08:00:27:31:9c:b8"
        port = {
            "port": {
                "vlans": [{
                    "vlan": {
                        "id": self.vlan_db['id'],
                        "is_native": False}}],
                'mac_address': mac_address,
                "switch_port_mode": "access",
            }
        }
        with contextlib.nested(
                mock.patch.object(self.plugin,
                                  'push_vlanportassociation_to_device'),
                mock.patch.object(self.plugin,
                                  '_get_device_driver')) as (
                _, device_ops_driver):
            device_driver = device_ops_driver()
            device_driver.get_mac_addresses_on_interface.return_value = []
            self.assertRaises(
                netforce_exceptions.NoNativeVlan,
                self.plugin.update_port,
                self.context, self.port_db['id'], port)
            self.assertEqual(
                0, device_driver.get_mac_addresses_on_interface.call_count)

    def test_update_port_with_mac_address_validated_failed(self):
        mac_address = "dead:dead:dead"
        vlan_tag = self.vlan_db['tag']
        port = {
            "port": {
                "switch_port_mode": "access",
                "vlans": [{
                    "vlan": {
                        "id": self.vlan_db['id'],
                        "is_native": True}}],
                'mac_address': mac_address
            }
        }

        with contextlib.nested(
                    mock.patch.object(self.plugin,
                               'push_vlanportassociation_to_device'),
                    mock.patch.object(self.plugin,
                              '_get_device_driver')) as (_, device_ops_driver):

            device_driver = device_ops_driver()
            data = [{'mac_address': 'beef:beef:beef',
                    'vlan': vlan_tag}]
            device_driver.get_mac_addresses_on_interface.return_value = data

            self.assertRaises(
                    netforce_exceptions.MacAddressNotFoundOnInterface,
                    self.plugin.update_port,
                    self.context, self.port_db['id'], port)

            device_driver.get_mac_addresses_on_interface \
                .assert_called_once_with(self.port_db['name'], vlan_tag)

    def test_update_port_vlan_device_error(self):
        port = {
            "port": {
                "switch_port_mode": "access",
                "vlans": [
                    {
                        "vlan": {
                            "id": self.vlan_db['id'],
                            "is_native": True
                        }
                    }
                ]
            }
        }

        port2 = {
            "port": {
                "switch_port_mode": "trunk",
                "vlans": [
                    {
                        "vlan": {
                            "id": self.vlan_db2['id'],
                            "is_native": True
                        }
                    }
                ]
            }
        }

        def get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock.\
                update_switch_port_vlans.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        def get_device_driver_mock_error():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock.\
                update_switch_port_vlans.side_effect = \
                netforce_exceptions.DeviceError
            device_driver_mock.close.return_value = None
            return device_driver_mock
        with mock.patch.object(self.plugin, '_get_device_driver') \
                as device_driver:
            device_driver.return_value = get_device_driver_mock()
            updated_port_db = self.plugin.update_port(
                self.context, self.port_db['id'], port)
            current_vlan_id = updated_port_db['vlans'][0]['vlan']['id']
            self.assertIs(True, 'id' in
                          updated_port_db['vlans'][0]['vlan'])
            self.assertEqual("access",
                             updated_port_db['switch_port_mode'])
            device_driver.return_value = \
                get_device_driver_mock_error()
            self.assertRaises(
                netforce_exceptions.DeviceError,
                self.plugin.update_port, self.context,
                self.port_db['id'], port2)
            # On rollback, db status is also set to old status
            rolled_back_data = self.plugin.get_port(
                self.context, updated_port_db['id'])
            self.assertEqual("access",
                             rolled_back_data['switch_port_mode'])
            self.assertEqual(current_vlan_id, self.vlan_db['id'])

    def test_create_port_with_duplicate_asset_id(self):
        # bridgegroup creation
        bridge_group = {
            'bridgegroup': {
                'name': 'test-bridgegroup1',
                'description': 'test bridge group'
            }
        }

        bridge_group_db = self.plugin.create_bridgegroup(
            self.context, bridge_group)
        # create device
        device = {
            'device': {
                'name': 'test-device1',
                'description': 'test device1',
                'management_ip': '1.1.1.2',
                'username': 'arista',
                'password': 'arista',
                'type': 'TOR',
                'bridge_group_id': bridge_group_db['id'],
                'device_type_id': self.device_type_db['id'],
                'os_type': 'ebayeos'
            }
        }
        # mock port discovery and create port
        with mock.patch.object(self.plugin, '_discover_ports_on_device') \
                as discover_ports:
            discover_ports.return_value = None
            device_db = self.plugin.create_device(self.context, device)
            self.assertIsNotNone(device_db)
            self.assertIs(0, len(device_db['ports']))
            port = {
                'port': {
                    'name': 'eth1',
                    'description': 'test port',
                    'admin_status': constants.ACTIVE,
                    'switch_port_mode': netforce_constants.TRUNK_MODE,
                    'device_id': device_db['id'],
                    'asset_id': 'ASSET00419246'
                }
            }
            port2 = {
                'port': {
                    'name': 'eth2',
                    'description': 'test port2',
                    'admin_status': constants.ACTIVE,
                    'switch_port_mode': netforce_constants.TRUNK_MODE,
                    'device_id': device_db['id'],
                    'asset_id': 'ASSET00419246'
                }
            }

        self.plugin.create_port(self.context, port)
        self.assertRaises(
            netforce_exceptions.ResourceAlreadyExists,
            self.plugin.create_port, self.context, port2)

    def test_device_with_duplicate_name(self):
        # bridgegroup creation
        bridge_group = {
            'bridgegroup': {
                'name': 'test-bridgegroup1',
                'description': 'test bridge group'
            }
        }

        bridge_group_db = self.plugin.create_bridgegroup(
            self.context, bridge_group)
        # create device
        device = {
            'device': {
                'name': 'test-device',
                'description': 'test device',
                'management_ip': '1.1.1.2',
                'username': 'arista',
                'password': 'arista',
                'type': 'TOR',
                'bridge_group_id': bridge_group_db['id'],
                'device_type_id': self.device_type_db['id'],
                'os_type': 'ebayeos'
            }
        }
        # mock port discovery and create port
        with mock.patch.object(self.plugin, '_discover_ports_on_device') \
                as discover_ports:
            discover_ports.return_value = None
            self.assertRaises(
                netforce_exceptions.ResourceAlreadyExists,
                self.plugin.create_device, self.context, device)

    def test_device_with_duplicate_ip(self):
        # bridgegroup creation
        bridge_group = {
            'bridgegroup': {
                'name': 'test-bridgegroup1',
                'description': 'test bridge group'
            }
        }

        bridge_group_db = self.plugin.create_bridgegroup(
            self.context, bridge_group)
        # create device
        device = {
            'device': {
                'name': 'test-device1',
                'description': 'test device1',
                'management_ip': '1.1.1.1',
                'username': 'arista',
                'password': 'arista',
                'type': 'TOR',
                'bridge_group_id': bridge_group_db['id'],
                'device_type_id': self.device_type_db['id'],
                'os_type': 'ebayeos'
            }
        }
        # mock port discovery and create port
        with mock.patch.object(self.plugin, '_discover_ports_on_device') \
                as discover_ports:
            discover_ports.return_value = None
            self.assertRaises(
                netforce_exceptions.ResourceAlreadyExists,
                self.plugin.create_device, self.context, device)

    def test_get_port_by_asset_id_not_found(self):
        # bridgegroup creation
        bridge_group = {
            'bridgegroup': {
                'name': 'test-bridgegroup1',
                'description': 'test bridge group'
            }
        }

        bridge_group_db = self.plugin.create_bridgegroup(
            self.context, bridge_group)
        # create device
        device = {
            'device': {
                'name': 'test-device1',
                'description': 'test device1',
                'management_ip': '1.1.1.2',
                'username': 'arista',
                'password': 'arista',
                'type': 'TOR',
                'bridge_group_id': bridge_group_db['id'],
                'device_type_id': self.device_type_db['id'],
                'os_type': 'ebayeos'
            }
        }
        # mock port discovery and create port
        with mock.patch.object(self.plugin, '_discover_ports_on_device') \
                as discover_ports:
            discover_ports.return_value = None
            device_db = self.plugin.create_device(self.context, device)
            self.assertIsNotNone(device_db)
            self.assertIs(0, len(device_db['ports']))
            port = {
                'port': {
                    'name': 'eth1',
                    'description': 'test port',
                    'admin_status': constants.ACTIVE,
                    'switch_port_mode': netforce_constants.TRUNK_MODE,
                    'device_id': device_db['id'],
                    'asset_id': 'ASSET00419246'
                }
            }

            self.plugin.create_port(self.context, port)
            self.assertRaises(
                netforce_exceptions.PortNotFoundByAssetId,
                self.device_db_mixin.get_port_by_asset_id,
                self.context, 'ASSET00411247')
