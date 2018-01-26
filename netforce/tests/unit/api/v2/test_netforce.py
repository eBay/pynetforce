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


import collections
import contextlib
import mock
from netforce.common import netforce_exceptions
from netforce.extensions import netforceext as netforce_v2_ctl
from netforce.tests import base
from netforce.tests.unit.api import fakes
from netforce.tests.unit.api.v2 import fake_netforceplugin
from neutron.common import exceptions as ex
from neutron.plugins.common import constants
from sqlalchemy.orm import exc as orm_exc
import testscenarios

load_tests = testscenarios.load_tests_apply_scenarios


class TestNetforceController(base.NetforceSqlTestCase):

    def setUp(self):

        super(TestNetforceController, self).setUp()
        res_attr_map = netforce_v2_ctl.RESOURCE_ATTRIBUTE_MAP
        self.port_controller = fake_netforceplugin.\
            FakeNetForceController('port', 'ports',
                                   res_attr_map['ports'])

        self.bg_controller = fake_netforceplugin.\
            FakeNetForceController('bridgegroup', 'bridgegroups',
                                   res_attr_map['bridgegroups'])

        self.devicetype_controller = fake_netforceplugin.\
            FakeNetForceController('devicetype', 'devicetypes',
                                   res_attr_map['devicetypes'])

        self.bubble_controller = fake_netforceplugin \
            .FakeNetForceController('bubble', 'bubbles',
                                    res_attr_map['bubbles'])

        self.vpc_controller = fake_netforceplugin.\
            FakeNetForceController('vpc', 'vpcs',
                                   res_attr_map['vpcs'])

        self.vlan_controller = fake_netforceplugin. \
            FakeNetForceController('vlan', 'vlans',
                                   res_attr_map['vlans'])

        self.subnet_controller = fake_netforceplugin. \
            FakeNetForceController('subnet', 'subnets',
                                   res_attr_map['subnets'])
        # overriding for test cases
        res_attr_map['ports']['device_id']['allow_post'] = True

        self.device_controller = fake_netforceplugin\
            .FakeNetForceController('device', 'devices',
                                    res_attr_map['devices'])
        self.vrf_controller = fake_netforceplugin \
            .FakeNetForceController('vrf', 'vrfs',
                                    res_attr_map['vrfs'])

    def tearDown(self):
        super(TestNetforceController, self).tearDown()

    def _get_ticket_mock(self):
        ticket_mock = mock.Mock()
        ticket_mock.create_ticket.return_value = \
            {"result": "CHNGE12345678"}
        return ticket_mock

    def _create_and_assert_test_port(self):
        # vpc creation
        vpc_req = fakes.HTTPRequest.blank('/vpcs')
        vpc_req.context.is_admin = True

        body = {
            "vpc": {
                "name": "test-vpc",
                "description": "test vpc description",
                "label": "test-vpc-label",
                "tenant_id": "1232"
            }

        }
        vpc_dict = self.vpc_controller.create(vpc_req, body=body)
        self.assertIs(True, 'id' in vpc_dict['vpc'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body = {
            'bridgegroup': {
                "name": "test-bg",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict = self.bg_controller.create(bridgegroup_req, body=body)
        self.assertIs(True, 'id' in bg_dict['bridgegroup'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body = {
            "devicetype": {
                "name": "Top of the Rack Switch",
                "type": "TOR",
                "tenant_id": "1232"
            }

        }
        devicetype_dict = self.devicetype_controller.create(
            devicetpye_req, body=body)

        self.assertIs(True, 'id' in devicetype_dict['devicetype'])

        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True

        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_dict = self.bubble_controller.create(
            bubble_req, body=body)
        self.assertIs(True, 'id' in bubble_dict['bubble'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body = {
            "device":
            {
                "name": "test-device",
                "description": "test device",
                "management_ip": "10.10.11.110",
                "username": "arista",
                "password": "arista",
                "type": "TOR",
                "bridge_group_id": bg_dict['bridgegroup']['id'],
                "os_type": "junos",
                "tenant_id": "1232",
                'bubble_id': bubble_dict['bubble']['id'],
            }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict = self.device_controller.create(device_req, body=body)
        self.assertIs(True, 'id' in device_dict['device'])
        self.assertIs(True, bubble_dict['bubble']['id'] ==
                      device_dict['device']['bubble_id'])

        # vlan
        vlan_req = fakes.HTTPRequest.blank('/vlans')
        vlan_req.context.is_admin = True
        body = {
            "vlan": {
                "name": "test-vlan-1",
                "bridge_group_name": "test-bg",
                "vpc_name": "test-vpc",
                "admin_status": "ACTIVE",
                "tenant_id": "1232",
                'tag': 2
            }
        }

        with mock.patch.object(self.vlan_controller._plugin,
                               'config_vlan_on_devices') as vlan_config_mock:
            vlan_config_mock.return_value = None
            vlan_dict = self.vlan_controller.create(vlan_req, body=body)
        self.assertIs(True, 'id' in vlan_dict['vlan'])

        # port
        req = fakes.HTTPRequest.blank('/ports')
        req.context.is_admin = True
        body = {
            'port': {
                'name': 'eth1',
                'description': 'test port',
                'admin_status': 'SUSPENDED',
                'device_id': device_dict['device']['id'],
                'tenant_id': '1232',
                'switch_port_mode': 'access',
            }
        }

        resp_dict = self.port_controller.create(req, body=body)
        self.assertIsNotNone(resp_dict)
        self.assertEqual('id' in resp_dict[
                         'port'], True, 'id not present in response')

        # port2
        req = fakes.HTTPRequest.blank('/ports')
        req.context.is_admin = True
        body2 = {
            'port': {
                'name': 'eth2',
                'description': 'test port2',
                'admin_status': 'ACTIVE',
                'device_id': device_dict['device']['id'],
                'tenant_id': '1232',
                'switch_port_mode': 'access',
            }
        }

        resp_dict2 = self.port_controller.create(req, body=body2)
        self.assertIsNotNone(resp_dict2)
        resp_dict['port2'] = resp_dict2
        return resp_dict

    def test_create_port(self):
        self._create_and_assert_test_port()

    def test_update_port_enable_matching_mac(self):
        port_dict = self._create_and_assert_test_port()

        def _get_device_driver_mock():
            device_driver_mock = mock.Mock()
            data = [{'mac_address': '08:00:27:31:9c:b8',
                     'vlan': None}]
            device_driver_mock. \
                get_mac_addresses_on_interface.return_value = data
            device_driver_mock.open.return_value = None
            device_driver_mock.disable_interfaces.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with mock.patch.object(self.port_controller._plugin,
                               '_get_device_driver') as device_driver:
                    device_driver.return_value = _get_device_driver_mock()
                    req = fakes.HTTPRequest.blank(
                        '/ports/%s.json' % (port_dict['port']['id']))
                    req.context.tenant_id = port_dict['port']['tenant_id']
                    body = {
                        'port': {
                            'admin_status': constants.ACTIVE,
                            'mac_address': '08:00:27:31:9c:b8'
                        }
                    }
                    resp_dict = self.port_controller.update(
                        req, id=port_dict['port']['id'], body=body)
                    self.assertIsNotNone(resp_dict)

    def test_update_port_enable_no_mac_on_interface(self):
        port_dict = self._create_and_assert_test_port()

        def _get_device_driver_mock():
            device_driver_mock = mock.Mock()
            data = []
            device_driver_mock. \
                get_mac_addresses_on_interface.return_value = data
            device_driver_mock.open.return_value = None
            device_driver_mock.disable_interfaces.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with mock.patch.object(self.port_controller._plugin,
                               '_get_device_driver') as device_driver:
            device_driver.return_value = _get_device_driver_mock()
            req = fakes.HTTPRequest.blank(
                '/ports/%s.json' % (port_dict['port']['id']))
            req.context.tenant_id = port_dict['port']['tenant_id']
            body = {
                'port': {
                    'admin_status': constants.ACTIVE,
                    'mac_address': '08:00:27:31:9c:b8'
                }
            }
            resp_dict = self.port_controller.update(
                req, id=port_dict['port']['id'], body=body)
            self.assertIsNotNone(resp_dict)

    def test_update_port_for_vlan_flipping_success(self):

        port_dict = self._create_and_assert_test_port()

        def _get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock.\
                update_switch_port_mode_on_interface.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with mock.patch.object(self.port_controller._plugin,
                               '_get_device_driver') as device_driver:
            with mock.patch.object(self.port_controller._plugin,
                                   'create_port_flip_cr') as trace:
                device_driver.return_value = _get_device_driver_mock()
                trace.create_port_flip_cr.return_value = None
                req = fakes.HTTPRequest.blank(
                    '/ports/%s.json' % (port_dict['port']['id']))
                req.context.tenant_id = port_dict['port']['tenant_id']

                body = {
                    'port': {
                        'switch_port_mode': 'access',
                        'vlans': [
                            {
                                "vlan": {
                                    "tag": "2"
                                }
                            }
                        ]
                    }
                }
                resp_dict = self.port_controller.update(
                    req, id=port_dict['port']['id'], body=body)
                self.assertIs(True, 'vlans' in resp_dict['port'])

    def test_update_port_for_vlan_flipping_failure_invalid_id(self):

        port_dict = self._create_and_assert_test_port()
        req = fakes.HTTPRequest.blank(
            '/ports/%s.json' % (port_dict['port']['id']))

        req.context.tenant_id = port_dict['port']['tenant_id']
        body = {
            'port': {
                'switch_port_mode': 'access',
                'vlans': [
                    {
                        "vlan": {
                            "id": "invalid-id"
                        }
                    }
                ]
            }
        }

        self.assertRaises(ex.BadRequest,
                          self.port_controller.update,
                          req, id=port_dict['port']['id'], body=body)

    def test_update_port_for_vlan_flipping_failure_invalid_tag(self):
        port_dict = self._create_and_assert_test_port()
        req = fakes.HTTPRequest.blank(
            '/ports/%s.json' % (port_dict['port']['id']))
        req.context.tenant_id = port_dict['port']['tenant_id']

        body = {
            'port': {
                'switch_port_mode': 'access',
                'vlans': [
                    {
                        "vlan": {
                            "tag": "invalid-tag"
                        }
                    }
                ]
            }
        }

        self.assertRaises(ex.BadRequest, self.port_controller.update,
                          req, id=port_dict['port']['id'], body=body)

    def test_create_subnet(self):
        # port_dict = self._create_and_assert_test_port()
        ###
        # vpc creation
        vpc_req = fakes.HTTPRequest.blank('/vpcs')
        vpc_req.context.is_admin = True

        body = {
            "vpc": {
                "name": "fake-vpc1",
                "description": "test vpc description",
                "label": "test-vpc-label",
                "tenant_id": "1232"
            }

        }
        vpc_dict = self.vpc_controller.create(vpc_req, body=body)
        self.assertIs(True, 'id' in vpc_dict['vpc'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body = {
            'bridgegroup': {
                "name": "test-bg5",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict = self.bg_controller.create(bridgegroup_req, body=body)
        self.assertIs(True, 'id' in bg_dict['bridgegroup'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body4 = {
            'bridgegroup': {
                "name": "test-bg55",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict1 = self.bg_controller.create(bridgegroup_req, body=body4)
        self.assertIs(True, 'id' in bg_dict1['bridgegroup'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body = {
            "devicetype": {
                "name": "Top of the Rack Switch",
                "type": "TORS",
                "tenant_id": "1232"
            }

        }
        devicetype_dict = self.devicetype_controller.create(
            devicetpye_req, body=body)

        self.assertIs(True, 'id' in devicetype_dict['devicetype'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body1 = {
            "devicetype": {
                "name": "ED Switch",
                "type": "DISTRIBUTION",
                "tenant_id": "1232"
            }

        }
        devicetype_dict1 = self.devicetype_controller.create(
            devicetpye_req, body=body1)

        self.assertIs(True, 'id' in devicetype_dict1['devicetype'])
        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True

        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_dict = self.bubble_controller.create(
            bubble_req, body=body)
        self.assertIs(True, 'id' in bubble_dict['bubble'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body = {
            "device":
                {
                    "name": "test-device5",
                    "description": "test device",
                    "management_ip": "8.8.4.4",
                    "username": "arista",
                    "password": "arista",
                    "type": "TORS",
                    "bridge_group_id": bg_dict['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict = self.device_controller.create(device_req, body=body)
        self.assertIs(True, 'id' in device_dict['device'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body2 = {
            "device":
                {
                    "name": "test-device7",
                    "description": "test bubble device",
                    "management_ip": "8.8.8.8",
                    "username": "test",
                    "password": "test",
                    "type": "DISTRIBUTION",
                    "bridge_group_id": bg_dict1['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict1 = self.device_controller.create(device_req,
                                                         body=body2)
        self.assertIs(True, 'id' in device_dict1['device'])

        # vlan
        vlan_req = fakes.HTTPRequest.blank('/vlans')
        vlan_req.context.is_admin = True
        body = {
            "vlan": {
                "name": "test-vlan-8",
                "bridge_group_name": "test-bg5",
                "admin_status": "ACTIVE",
                "tenant_id": "1232",
                'tag': 8,
                "vpc_name": None,
            }
        }

        vlan_dict = self.vlan_controller.create(vlan_req, body=body)
        self.assertIs(True, 'id' in vlan_dict['vlan'])

        # vlan
        vlan_req = fakes.HTTPRequest.blank('/vlans')
        vlan_req.context.is_admin = True
        body = {
            "vlan": {
                "name": "test-vlan-5",
                "bridge_group_name": "test-bg5",
                "vpc_name": "fake-vpc1",
                "admin_status": "ACTIVE",
                "tenant_id": "1232",
                'tag': 3
            }
        }
        with mock.patch.object(self.vlan_controller._plugin,
                               'config_vlan_on_devices') as vlan_config_mock:
            vlan_config_mock.return_value = None
            vlan_dict = self.vlan_controller.create(vlan_req, body=body)
        self.assertIs(True, 'id' in vlan_dict['vlan'])

        # create vrf
        vrf_req = fakes.HTTPRequest.blank('/vrfs')
        vrf_req.context.is_admin = True
        body = {
            "vrf": {
                "name": "fake-vrf",
                "description": "fake",
                "bubble_id": bubble_dict['bubble']['id'],
                "vpc_id": vpc_dict['vpc']['id'],
                "tenant_id": "1232"
            }
        }

        vrf_dict = self.vrf_controller.create(vrf_req, body=body)
        self.assertIs(True, 'id' in vrf_dict['vrf'])

        req = fakes.HTTPRequest.blank(
            '/subnets.json')
        req.context.tenant_id = vlan_dict['vlan']['tenant_id']

        body = {
            "subnet": {
                "name": "test-fake50",
                "cidr": "10.8.0.0/24",
                "gateway_ip": "10.8.0.1",
                "broadcast_ip": "10.8.0.255",
                "netmask": "255.255.255.0",
                "vlan_id": vlan_dict['vlan']['id'],
                'reserve_ip_count': "10"
            }
        }

        def _get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock.\
                get_routes.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with contextlib.nested(
            mock.patch.object(self.subnet_controller._plugin,
                              '_get_device_driver'),
            mock.patch.object(self.subnet_controller._plugin,
                              '_configure_subnet_on_device'),
            mock.patch.object(self.subnet_controller._plugin,
                              '_check_cidr_overlap_on_bubble'),
            mock.patch.object(self.subnet_controller._plugin,
                              '_get_pingable_bubble_device_')
        ) as (
                                    device_driver, subnet_config_mock,
                                    cidr_overlap,
                                    ping_bubble_devices):

            cidr_overlap.return_value = None
            device_driver.return_value = _get_device_driver_mock()
            device_driver.device_driver_mock.get_routes.return_value = [
                                '192.168.1.1/24',
                                '10.8.0.0/24']
            subnet_config_mock.return_value = None
            ping_bubble_devices.side_effect = lambda x: x[0]
            subnet_dict = self.subnet_controller.create(req, body=body)

        self.assertIs(True, 'id' in subnet_dict['subnet'])

    def test_update_bubble(self):
        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True

        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_dict = self.bubble_controller.create(
            bubble_req, body=body)
        bubble_id = bubble_dict['bubble']['id']
        body = {
            'bubble': {
                'name': 'fakeBubble1'
            }

        }
        bubble_req = fakes.HTTPRequest.blank('/bubbles/' +
                                             bubble_id + '.json')
        bubble_req.context.is_admin = True
        updated = self.bubble_controller.update(request=bubble_req,
                                                id=bubble_id, body=body)
        self.assertEqual('fakeBubble1', updated['bubble']['name'])

    def test_delete_bubble(self):
        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True

        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_dict = self.bubble_controller.create(
            bubble_req, body=body)
        bubble_id = bubble_dict['bubble']['id']
        bubble_req = fakes.HTTPRequest.blank('/bubbles/' +
                                             bubble_id + '.json')
        bubble_req.context.is_admin = True
        updated = self.bubble_controller.delete(request=bubble_req,
                                                id=bubble_id)
        self.assertEqual(None, updated)

    def test_update_fake_bubble(self):
        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True
        bubble_id = '70662605-ac5e-4cb8-8136-65684c231793'
        body = {
            'bubble': {
                'name': 'fakeBubble1'
            }
        }
        bubble_req = fakes.HTTPRequest.blank('/bubbles/' +
                                             bubble_id + '.json')
        bubble_req.context.is_admin = True
        bubble_req.context.is_admin = True
        self.assertRaises(orm_exc.NoResultFound,
                          self.bubble_controller.update,
                          bubble_req, id=bubble_id, body=body)

    def test_delete_fake_bubble(self):
        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True
        bubble_id = '70662605-ac5e-4cb8-8136-65684c231793'
        bubble_req = fakes.HTTPRequest.blank('/bubbles/' +
                                             bubble_id + '.json')
        bubble_req.context.is_admin = True
        self.assertRaises(orm_exc.NoResultFound,
                          self.bubble_controller.delete,
                          bubble_req, id=bubble_id)

    def test_create_vrf(self):
        # port_dict = self._create_and_assert_test_port()
        ###
        # vpc creation
        vpc_req = fakes.HTTPRequest.blank('/vpcs')
        vpc_req.context.is_admin = True

        body = {
            "vpc": {
                "name": "fake-vpc1",
                "description": "test vpc description",
                "label": "test-vpc-label",
                "tenant_id": "1232"
            }

        }
        vpc_dict = self.vpc_controller.create(vpc_req, body=body)
        self.assertIs(True, 'id' in vpc_dict['vpc'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body = {
            'bridgegroup': {
                "name": "test-bg5",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict = self.bg_controller.create(bridgegroup_req, body=body)
        self.assertIs(True, 'id' in bg_dict['bridgegroup'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body = {
            "devicetype": {
                "name": "Top of the Rack Switch",
                "type": "TORS",
                "tenant_id": "1232"
            }

        }
        devicetype_dict = self.devicetype_controller.create(
            devicetpye_req, body=body)

        self.assertIs(True, 'id' in devicetype_dict['devicetype'])

        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True

        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_dict = self.bubble_controller.create(
            bubble_req, body=body)
        self.assertIs(True, 'id' in bubble_dict['bubble'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body = {
            "device":
                {
                    "name": "test-device5",
                    "description": "test device",
                    "management_ip": "10.10.11.115",
                    "username": "arista",
                    "password": "arista",
                    "type": "TORS",
                    "bridge_group_id": bg_dict['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict = self.device_controller.create(device_req, body=body)
        self.assertIs(True, 'id' in device_dict['device'])

        # vlan
        vlan_req = fakes.HTTPRequest.blank('/vlans')
        vlan_req.context.is_admin = True
        body = {
            "vlan": {
                "name": "test-vlan-5",
                "bridge_group_name": "test-bg5",
                "vpc_name": "fake-vpc1",
                "admin_status": "ACTIVE",
                "tenant_id": "1232",
                'tag': 3

            }
        }
        with mock.patch.object(self.vlan_controller._plugin,
                               'config_vlan_on_devices') as vlan_config_mock:
            vlan_config_mock.return_value = None
            vlan_dict = self.vlan_controller.create(vlan_req, body=body)
        self.assertIs(True, 'id' in vlan_dict['vlan'])
        self.assertIs(True, 'bridge_group_name' in vlan_dict['vlan'])
        self.assertIs(True, 'bridge_group_id' in vlan_dict['vlan'])
        self.assertIs(True, 'vpc_id' in vlan_dict['vlan'])
        self.assertIs(True, 'vpc_name' in vlan_dict['vlan'])

        # create vlan without tag for already created vlan
        vlan_req1 = fakes.HTTPRequest.blank('/vlans')
        vlan_req1.context.is_admin = True
        body_no_tag = {
            "vlan": {
                "name": "test-vlan-5",
                "bridge_group_name": "test-bg5",
                "vpc_name": "fake-vpc1",
                "admin_status": "ACTIVE",
                "tenant_id": "1232",

            }
        }
        with mock.patch.object(self.vlan_controller._plugin,
                               'config_vlan_on_devices') as vlan_config_mock:
            vlan_config_mock.return_value = None
            vlan_dict_notag = self.vlan_controller.create(vlan_req,
                                                          body=body_no_tag)
        self.assertEqual(3, vlan_dict_notag['vlan']['tag'])

        req = fakes.HTTPRequest.blank(
            '/vrfs.json')
        req.context.tenant_id = vlan_dict['vlan']['tenant_id']

        body = {
            "vrf": {
                "name": "fake-vrf",
                "description": "fake",
                "bubble_id": bubble_dict['bubble']['id'],
                "vpc_id": vpc_dict['vpc']['id'],
                "tenant_id": "1232"
            }
        }

        vrf_dict = self.vrf_controller.create(req, body=body)
        self.assertIs(True, 'id' in vrf_dict['vrf'])
        # update vrf
        body2 = {
            "vrf": {
                "name": "fake-vrf2"
            }
        }
        req = fakes.HTTPRequest.blank(
            '/vrfs/%s.json' % (vrf_dict['vrf']['id']))
        req.context.tenant_id = vlan_dict['vlan']['tenant_id']
        vrf_dict = self.vrf_controller.update(req, id=vrf_dict['vrf']['id'],
                                              body=body2)
        self.assertIs(True, 'id' in vrf_dict['vrf'])

    def test_create_subnet_skip_device(self):
        # port_dict = self._create_and_assert_test_port()
        ###
        # vpc creation
        vpc_req = fakes.HTTPRequest.blank('/vpcs')
        vpc_req.context.is_admin = True

        body = {
            "vpc": {
                "name": "fake-vpc1",
                "description": "test vpc description",
                "label": "test-vpc-label",
                "tenant_id": "1232"
            }

        }
        vpc_dict = self.vpc_controller.create(vpc_req, body=body)
        self.assertIs(True, 'id' in vpc_dict['vpc'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body = {
            'bridgegroup': {
                "name": "test-bg5",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict = self.bg_controller.create(bridgegroup_req, body=body)
        self.assertIs(True, 'id' in bg_dict['bridgegroup'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body4 = {
            'bridgegroup': {
                "name": "test-bg55",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict1 = self.bg_controller.create(bridgegroup_req, body=body4)
        self.assertIs(True, 'id' in bg_dict1['bridgegroup'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body = {
            "devicetype": {
                "name": "Top of the Rack Switch",
                "type": "TORS",
                "tenant_id": "1232"
            }

        }
        devicetype_dict = self.devicetype_controller.create(
            devicetpye_req, body=body)

        self.assertIs(True, 'id' in devicetype_dict['devicetype'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body1 = {
            "devicetype": {
                "name": "ED Switch",
                "type": "DISTRIBUTION",
                "tenant_id": "1232"
            }

        }
        devicetype_dict1 = self.devicetype_controller.create(
            devicetpye_req, body=body1)

        self.assertIs(True, 'id' in devicetype_dict1['devicetype'])
        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True

        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_dict = self.bubble_controller.create(
            bubble_req, body=body)
        self.assertIs(True, 'id' in bubble_dict['bubble'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body = {
            "device":
                {
                    "name": "test-device5",
                    "description": "test device",
                    "management_ip": "10.10.11.115",
                    "username": "arista",
                    "password": "arista",
                    "type": "TORS",
                    "bridge_group_id": bg_dict['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict = self.device_controller.create(device_req, body=body)
        self.assertIs(True, 'id' in device_dict['device'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body2 = {
            "device":
                {
                    "name": "test-device7",
                    "description": "test bubble device",
                    "management_ip": "10.10.11.5",
                    "username": "test",
                    "password": "test",
                    "type": "DISTRIBUTION",
                    "bridge_group_id": bg_dict1['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict1 = self.device_controller.create(device_req,
                                                         body=body2)
        self.assertIs(True, 'id' in device_dict1['device'])

        # vlan
        vlan_req = fakes.HTTPRequest.blank('/vlans')
        vlan_req.context.is_admin = True
        body = {
            "vlan": {
                "name": "test-vlan-5",
                "bridge_group_name": "test-bg5",
                "vpc_name": "fake-vpc1",
                "admin_status": "ACTIVE",
                "tenant_id": "1232",
                'tag': 3
            }
        }
        with mock.patch.object(self.vlan_controller._plugin,
                               'config_vlan_on_devices') as vlan_config_mock:
            vlan_config_mock.return_value = None
            vlan_dict = self.vlan_controller.create(vlan_req, body=body)
        self.assertIs(True, 'id' in vlan_dict['vlan'])

        # create vrf
        vrf_req = fakes.HTTPRequest.blank('/vrfs')
        vrf_req.context.is_admin = True
        body = {
            "vrf": {
                "name": "fake-vrf",
                "description": "fake",
                "bubble_id": bubble_dict['bubble']['id'],
                "vpc_id": vpc_dict['vpc']['id'],
                "tenant_id": "1232"
            }
        }

        vrf_dict = self.vrf_controller.create(vrf_req, body=body)
        self.assertIs(True, 'id' in vrf_dict['vrf'])

        req = fakes.HTTPRequest.blank(
            '/subnets.json?skip_device=True')
        req.context.tenant_id = vlan_dict['vlan']['tenant_id']

        body = {
            "subnet": {
                "name": "test-fake50",
                "cidr": "10.8.0.0/24",
                "gateway_ip": "10.8.0.1",
                "broadcast_ip": "10.8.0.255",
                "netmask": "255.255.255.0",
                "vlan_id": vlan_dict['vlan']['id'],
            }
        }

        def _get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock.\
                get_routes.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with contextlib.nested(
            mock.patch.object(self.subnet_controller._plugin,
                              '_get_device_driver'),
            mock.patch.object(self.subnet_controller._plugin,
                              '_configure_subnet_on_device'),
            mock.patch.object(self.subnet_controller._plugin,
                              '_check_cidr_overlap_on_bubble')) as (
                                    device_driver, subnet_config_mock,
                                    cidr_overlap):

            cidr_overlap.return_value = None
            device_driver.return_value = _get_device_driver_mock()
            device_driver.device_driver_mock.get_routes.return_value = [
                                '192.168.1.1/24',
                                '10.8.0.0/24']
            subnet_config_mock.return_value = None
            subnet_dict = self.subnet_controller.create(req, body=body)

        self.assertIs(True, 'id' in subnet_dict['subnet'])

    def test_create_subnet_overlapping(self):
        # port_dict = self._create_and_assert_test_port()
        ###
        # vpc creation
        vpc_req = fakes.HTTPRequest.blank('/vpcs')
        vpc_req.context.is_admin = True

        body = {
            "vpc": {
                "name": "fake-vpc1",
                "description": "test vpc description",
                "label": "test-vpc-label",
                "tenant_id": "1232"
            }

        }
        vpc_dict = self.vpc_controller.create(vpc_req, body=body)
        self.assertIs(True, 'id' in vpc_dict['vpc'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body = {
            'bridgegroup': {
                "name": "test-bg5",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict = self.bg_controller.create(bridgegroup_req, body=body)
        self.assertIs(True, 'id' in bg_dict['bridgegroup'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body4 = {
            'bridgegroup': {
                "name": "test-bg55",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict1 = self.bg_controller.create(bridgegroup_req, body=body4)
        self.assertIs(True, 'id' in bg_dict1['bridgegroup'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body = {
            "devicetype": {
                "name": "Top of the Rack Switch",
                "type": "TORS",
                "tenant_id": "1232"
            }

        }
        devicetype_dict = self.devicetype_controller.create(
            devicetpye_req, body=body)

        self.assertIs(True, 'id' in devicetype_dict['devicetype'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body1 = {
            "devicetype": {
                "name": "ED Switch",
                "type": "DISTRIBUTION",
                "tenant_id": "1232"
            }

        }
        devicetype_dict1 = self.devicetype_controller.create(
            devicetpye_req, body=body1)

        self.assertIs(True, 'id' in devicetype_dict1['devicetype'])
        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True

        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_dict = self.bubble_controller.create(
            bubble_req, body=body)
        self.assertIs(True, 'id' in bubble_dict['bubble'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body = {
            "device":
                {
                    "name": "test-device5",
                    "description": "test device",
                    "management_ip": "10.10.11.115",
                    "username": "arista",
                    "password": "arista",
                    "type": "TORS",
                    "bridge_group_id": bg_dict['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict = self.device_controller.create(device_req, body=body)
        self.assertIs(True, 'id' in device_dict['device'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body2 = {
            "device":
                {
                    "name": "test-device7",
                    "description": "test bubble device",
                    "management_ip": "10.10.11.5",
                    "username": "test",
                    "password": "test",
                    "type": "DISTRIBUTION",
                    "bridge_group_id": bg_dict1['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict1 = self.device_controller.create(device_req,
                                                         body=body2)
        self.assertIs(True, 'id' in device_dict1['device'])

        # vlan
        vlan_req = fakes.HTTPRequest.blank('/vlans')
        vlan_req.context.is_admin = True
        body = {
            "vlan": {
                "name": "test-vlan-5",
                "bridge_group_name": "test-bg5",
                "vpc_name": "fake-vpc1",
                "admin_status": "ACTIVE",
                "tenant_id": "1232",
                'tag': 3
            }
        }
        with mock.patch.object(self.vlan_controller._plugin,
                               'config_vlan_on_devices') as vlan_config_mock:
            vlan_config_mock.return_value = None
            vlan_dict = self.vlan_controller.create(vlan_req, body=body)
        self.assertIs(True, 'id' in vlan_dict['vlan'])

        # create vrf
        vrf_req = fakes.HTTPRequest.blank('/vrfs')
        vrf_req.context.is_admin = True
        body = {
            "vrf": {
                "name": "fake-vrf",
                "description": "fake",
                "bubble_id": bubble_dict['bubble']['id'],
                "vpc_id": vpc_dict['vpc']['id'],
                "tenant_id": "1232"
            }
        }

        vrf_dict = self.vrf_controller.create(vrf_req, body=body)
        self.assertIs(True, 'id' in vrf_dict['vrf'])

        req = fakes.HTTPRequest.blank(
            '/subnets.json?skip_device=True')
        req.context.tenant_id = vlan_dict['vlan']['tenant_id']

        body = {
            "subnet": {
                "name": "test-fake50",
                "cidr": "10.8.0.0/24",
                "gateway_ip": "10.8.0.1",
                "broadcast_ip": "10.8.0.255",
                "netmask": "255.255.255.0",
                "vlan_id": vlan_dict['vlan']['id'],
                'reserve_ip_count': "10"
            }
        }

        def _get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock.\
                get_routes.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with contextlib.nested(
            mock.patch.object(self.subnet_controller._plugin,
                              '_get_device_driver'),
            mock.patch.object(self.subnet_controller._plugin,
                              '_configure_subnet_on_device'),
            mock.patch.object(self.subnet_controller._plugin,
                              '_check_cidr_overlap_on_bubble')) as (
                                    device_driver, subnet_config_mock,
                                    cidr_overlap):

            cidr_overlap.return_value = None
            device_driver.return_value = _get_device_driver_mock()
            device_driver.device_driver_mock.get_routes.return_value = [
                                '192.168.1.1/24',
                                '10.8.0.0/24']
            subnet_config_mock.return_value = None
            subnet_dict = self.subnet_controller.create(req, body=body)

            body2 = {
                "subnet": {
                    "name": "test-fake50",
                    "cidr": "10.8.0.0/24",
                    "gateway_ip": "10.8.0.1",
                    "broadcast_ip": "10.8.0.255",
                    "netmask": "255.255.255.0",
                    "vlan_id": vlan_dict['vlan']['id'],
                }
            }
            subnet_dict2 = self.subnet_controller.create(req, body=body2)
        self.assertIs(True, 'id' in subnet_dict['subnet'])
        self.assertIs(True, 'id' in subnet_dict2['subnet'])
        body3 = {
            "subnet": {
                "name": "test-fake50",
                "cidr": "10.8.0.0/24",
                "gateway_ip": "10.8.0.2",
                "broadcast_ip": "10.8.0.255",
                "netmask": "255.255.255.0",
                "vlan_id": vlan_dict['vlan']['id'],
            }
        }
        #subnet_dict2=3 = self.subnet_controller.create(req, body=body3)
        self.assertRaises(
            netforce_exceptions.ConfiguredSubnetConflictsWithRequested,
            self.subnet_controller.create, req,
            body=body3)

    def test_set_subnet_primary_only_if_one_subnet_on_interface(self):
        # port_dict = self._create_and_assert_test_port()
        ###
        # vpc creation
        vpc_req = fakes.HTTPRequest.blank('/vpcs')
        vpc_req.context.is_admin = True

        body = {
            "vpc": {
                "name": "fake-vpc1",
                "description": "test vpc description",
                "label": "test-vpc-label",
                "tenant_id": "1232"
            }

        }
        vpc_dict = self.vpc_controller.create(vpc_req, body=body)
        self.assertIs(True, 'id' in vpc_dict['vpc'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body = {
            'bridgegroup': {
                "name": "test-bg5",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict = self.bg_controller.create(bridgegroup_req, body=body)
        self.assertIs(True, 'id' in bg_dict['bridgegroup'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body4 = {
            'bridgegroup': {
                "name": "test-bg55",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict1 = self.bg_controller.create(bridgegroup_req, body=body4)
        self.assertIs(True, 'id' in bg_dict1['bridgegroup'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body = {
            "devicetype": {
                "name": "Top of the Rack Switch",
                "type": "TORS",
                "tenant_id": "1232"
            }

        }
        devicetype_dict = self.devicetype_controller.create(
            devicetpye_req, body=body)

        self.assertIs(True, 'id' in devicetype_dict['devicetype'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body1 = {
            "devicetype": {
                "name": "ED Switch",
                "type": "DISTRIBUTION",
                "tenant_id": "1232"
            }

        }
        devicetype_dict1 = self.devicetype_controller.create(
            devicetpye_req, body=body1)

        self.assertIs(True, 'id' in devicetype_dict1['devicetype'])
        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True

        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_dict = self.bubble_controller.create(
            bubble_req, body=body)
        self.assertIs(True, 'id' in bubble_dict['bubble'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body = {
            "device":
                {
                    "name": "test-device5",
                    "description": "test device",
                    "management_ip": "10.10.11.115",
                    "username": "arista",
                    "password": "arista",
                    "type": "TORS",
                    "bridge_group_id": bg_dict['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict = self.device_controller.create(device_req, body=body)
        self.assertIs(True, 'id' in device_dict['device'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body2 = {
            "device":
                {
                    "name": "test-device7",
                    "description": "test bubble device",
                    "management_ip": "10.10.11.5",
                    "username": "test",
                    "password": "test",
                    "type": "DISTRIBUTION",
                    "bridge_group_id": bg_dict1['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict1 = self.device_controller.create(device_req,
                                                         body=body2)
        self.assertIs(True, 'id' in device_dict1['device'])

        # vlan
        vlan_req = fakes.HTTPRequest.blank('/vlans')
        vlan_req.context.is_admin = True
        body = {
            "vlan": {
                "name": "test-vlan-5",
                "bridge_group_name": "test-bg5",
                "vpc_name": "fake-vpc1",
                "admin_status": "ACTIVE",
                "tenant_id": "1232",
                "tag": 56
            }
        }
        with mock.patch.object(self.vlan_controller._plugin,
                               'config_vlan_on_devices') as vlan_config_mock:
            vlan_config_mock.return_value = None
            vlan_dict = self.vlan_controller.create(vlan_req, body=body)
        self.assertIs(True, 'id' in vlan_dict['vlan'])

        # create vrf
        vrf_req = fakes.HTTPRequest.blank('/vrfs')
        vrf_req.context.is_admin = True
        body = {
            "vrf": {
                "name": "fake-vrf",
                "description": "fake",
                "bubble_id": bubble_dict['bubble']['id'],
                "vpc_id": vpc_dict['vpc']['id'],
                "tenant_id": "1232"
            }
        }

        vrf_dict = self.vrf_controller.create(vrf_req, body=body)
        self.assertIs(True, 'id' in vrf_dict['vrf'])

        req = fakes.HTTPRequest.blank(
            '/subnets.json?patch_primary_junos_subnets=True'
            '&one_subnet_only=True')
        req.context.tenant_id = vlan_dict['vlan']['tenant_id']

        body = {
            "subnet": {
                "name": "test-fake50",
                "cidr": "10.8.0.0/24",
                "gateway_ip": "10.8.0.1",
                "broadcast_ip": "10.8.0.255",
                "netmask": "255.255.255.0",
                "vlan_id": vlan_dict['vlan']['id'],
            }
        }

        def _get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock. \
                get_routes.return_value = ['10.8.0.0/24']
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with contextlib.nested(
                mock.patch.object(self.subnet_controller._plugin,
                                  '_get_device_driver'),
                mock.patch.object(self.subnet_controller._plugin,
                                  '_configure_subnet_on_device')) as (
                device_driver, subnet_config_mock):
            device_driver.return_value = _get_device_driver_mock()
            device_driver.device_driver_mock.get_routes.return_value = [
                '192.168.1.1/24',
                '10.8.0.0/24']
            subnet_config_mock.return_value = None
            subnet_dict = self.subnet_controller.create(req, body=body)

        self.assertIs(True, 'id' in subnet_dict['subnet'])

    def test_set_subnet_primary_more_than_one_subnet_on_interface(self):
        # port_dict = self._create_and_assert_test_port()
        ###
        # vpc creation
        vpc_req = fakes.HTTPRequest.blank('/vpcs')
        vpc_req.context.is_admin = True

        body = {
            "vpc": {
                "name": "fake-vpc1",
                "description": "test vpc description",
                "label": "test-vpc-label",
                "tenant_id": "1232"
            }

        }
        vpc_dict = self.vpc_controller.create(vpc_req, body=body)
        self.assertIs(True, 'id' in vpc_dict['vpc'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body = {
            'bridgegroup': {
                "name": "test-bg5",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict = self.bg_controller.create(bridgegroup_req, body=body)
        self.assertIs(True, 'id' in bg_dict['bridgegroup'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body4 = {
            'bridgegroup': {
                "name": "test-bg55",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict1 = self.bg_controller.create(bridgegroup_req, body=body4)
        self.assertIs(True, 'id' in bg_dict1['bridgegroup'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body = {
            "devicetype": {
                "name": "Top of the Rack Switch",
                "type": "TORS",
                "tenant_id": "1232"
            }

        }
        devicetype_dict = self.devicetype_controller.create(
            devicetpye_req, body=body)

        self.assertIs(True, 'id' in devicetype_dict['devicetype'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body1 = {
            "devicetype": {
                "name": "ED Switch",
                "type": "DISTRIBUTION",
                "tenant_id": "1232"
            }

        }
        devicetype_dict1 = self.devicetype_controller.create(
            devicetpye_req, body=body1)

        self.assertIs(True, 'id' in devicetype_dict1['devicetype'])
        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True

        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_dict = self.bubble_controller.create(
            bubble_req, body=body)
        self.assertIs(True, 'id' in bubble_dict['bubble'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body = {
            "device":
                {
                    "name": "test-device5",
                    "description": "test device",
                    "management_ip": "10.10.11.115",
                    "username": "arista",
                    "password": "arista",
                    "type": "TORS",
                    "bridge_group_id": bg_dict['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict = self.device_controller.create(device_req, body=body)
        self.assertIs(True, 'id' in device_dict['device'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body2 = {
            "device":
                {
                    "name": "test-device7",
                    "description": "test bubble device",
                    "management_ip": "10.10.11.5",
                    "username": "test",
                    "password": "test",
                    "type": "DISTRIBUTION",
                    "bridge_group_id": bg_dict1['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict1 = self.device_controller.create(device_req,
                                                         body=body2)
        self.assertIs(True, 'id' in device_dict1['device'])

        # vlan
        vlan_req = fakes.HTTPRequest.blank('/vlans')
        vlan_req.context.is_admin = True
        body = {
            "vlan": {
                "name": "test-vlan-5",
                "bridge_group_name": "test-bg5",
                "vpc_name": "fake-vpc1",
                "admin_status": "ACTIVE",
                "tenant_id": "1232",
                "tag": 56
            }
        }
        with mock.patch.object(self.vlan_controller._plugin,
                               'config_vlan_on_devices') as vlan_config_mock:
            vlan_config_mock.return_value = None
            vlan_dict = self.vlan_controller.create(vlan_req, body=body)
        self.assertIs(True, 'id' in vlan_dict['vlan'])

        # create vrf
        vrf_req = fakes.HTTPRequest.blank('/vrfs.json/skip_device=True')
        vrf_req.context.is_admin = True
        body = {
            "vrf": {
                "name": "fake-vrf",
                "description": "fake",
                "bubble_id": bubble_dict['bubble']['id'],
                "vpc_id": vpc_dict['vpc']['id'],
                "tenant_id": "1232"
            }
        }

        vrf_dict = self.vrf_controller.create(vrf_req, body=body)
        self.assertIs(True, 'id' in vrf_dict['vrf'])

        req = fakes.HTTPRequest.blank(
            '/subnets.json?patch_primary_junos_subnets=True'
            '&one_subnet_only=False')
        req.context.tenant_id = vlan_dict['vlan']['tenant_id']

        body = {
            "subnet": {
                "name": "test-fake50",
                "cidr": "10.8.0.0/24",
                "gateway_ip": "10.8.0.1",
                "broadcast_ip": "10.8.0.255",
                "netmask": "255.255.255.0",
                "vlan_id": vlan_dict['vlan']['id'],
            }
        }

        def _get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock. \
                get_routes.return_value = ['10.8.0.0/24']
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with contextlib.nested(
                mock.patch.object(self.subnet_controller._plugin,
                                  '_get_device_driver'),
                mock.patch.object(self.subnet_controller._plugin,
                                  '_configure_subnet_on_device'),
                mock.patch.object(self.subnet_controller._plugin,
                                  '_check_cidr_overlap_on_bubble')) as (
                device_driver, subnet_config_mock,
                cidr_overlap):
            cidr_overlap.return_value = None
            device_driver.return_value = _get_device_driver_mock()
            device_driver.device_driver_mock.get_routes.return_value = [
                '192.168.1.1/24',
                '10.8.0.0/24']
            device_driver.device_driver_mock.check_hidden_routes_aggregates.\
                return_value = ['172.168.1.1/24']
            subnet_config_mock.return_value = None

            subnet_dict = self.subnet_controller.create(req, body=body)

        self.assertIs(True, 'id' in subnet_dict['subnet'])

    def test_set_subnet_primary_missing_primary_on_bubble(self):
        # port_dict = self._create_and_assert_test_port()
        ###
        # vpc creation
        vpc_req = fakes.HTTPRequest.blank('/vpcs')
        vpc_req.context.is_admin = True

        body = {
            "vpc": {
                "name": "fake-vpc1",
                "description": "test vpc description",
                "label": "test-vpc-label",
                "tenant_id": "1232"
            }

        }
        vpc_dict = self.vpc_controller.create(vpc_req, body=body)
        self.assertIs(True, 'id' in vpc_dict['vpc'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body = {
            'bridgegroup': {
                "name": "test-bg5",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict = self.bg_controller.create(bridgegroup_req, body=body)
        self.assertIs(True, 'id' in bg_dict['bridgegroup'])

        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body4 = {
            'bridgegroup': {
                "name": "test-bg55",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict1 = self.bg_controller.create(bridgegroup_req, body=body4)
        self.assertIs(True, 'id' in bg_dict1['bridgegroup'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body = {
            "devicetype": {
                "name": "Top of the Rack Switch",
                "type": "TORS",
                "tenant_id": "1232"
            }

        }
        devicetype_dict = self.devicetype_controller.create(
            devicetpye_req, body=body)

        self.assertIs(True, 'id' in devicetype_dict['devicetype'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body1 = {
            "devicetype": {
                "name": "ED Switch",
                "type": "DISTRIBUTION",
                "tenant_id": "1232"
            }

        }
        devicetype_dict1 = self.devicetype_controller.create(
            devicetpye_req, body=body1)

        self.assertIs(True, 'id' in devicetype_dict1['devicetype'])
        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True

        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_dict = self.bubble_controller.create(
            bubble_req, body=body)
        self.assertIs(True, 'id' in bubble_dict['bubble'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body = {
            "device":
                {
                    "name": "test-device5",
                    "description": "test device",
                    "management_ip": "10.10.11.115",
                    "username": "arista",
                    "password": "arista",
                    "type": "TORS",
                    "bridge_group_id": bg_dict['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict = self.device_controller.create(device_req, body=body)
        self.assertIs(True, 'id' in device_dict['device'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body2 = {
            "device":
                {
                    "name": "test-device7",
                    "description": "test bubble device",
                    "management_ip": "10.10.11.5",
                    "username": "test",
                    "password": "test",
                    "type": "DISTRIBUTION",
                    "bridge_group_id": bg_dict1['bridgegroup']['id'],
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }

        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict1 = self.device_controller.create(device_req,
                                                         body=body2)
        self.assertIs(True, 'id' in device_dict1['device'])

        # vlan
        vlan_req = fakes.HTTPRequest.blank('/vlans')
        vlan_req.context.is_admin = True
        body = {
            "vlan": {
                "name": "test-vlan-5",
                "bridge_group_name": "test-bg5",
                "vpc_name": "fake-vpc1",
                "admin_status": "ACTIVE",
                "tenant_id": "1232",
                "tag": 56
            }
        }
        with mock.patch.object(self.vlan_controller._plugin,
                               'config_vlan_on_devices') as vlan_config_mock:
            vlan_config_mock.return_value = None
            vlan_dict = self.vlan_controller.create(vlan_req, body=body)
        self.assertIs(True, 'id' in vlan_dict['vlan'])

        # create vrf
        vrf_req = fakes.HTTPRequest.blank('/vrfs')
        vrf_req.context.is_admin = True
        body = {
            "vrf": {
                "name": "fake-vrf",
                "description": "fake",
                "bubble_id": bubble_dict['bubble']['id'],
                "vpc_id": vpc_dict['vpc']['id'],
                "tenant_id": "1232"
            }
        }

        vrf_dict = self.vrf_controller.create(vrf_req, body=body)
        self.assertIs(True, 'id' in vrf_dict['vrf'])

        req = fakes.HTTPRequest.blank(
            '/subnets.json?patch_primary_junos_subnets=True'
            '&one_subnet_only=True')
        req.context.tenant_id = vlan_dict['vlan']['tenant_id']

        body = {
            "subnet": {
                "name": "test-fake50",
                "cidr": "10.8.0.0/24",
                "gateway_ip": "10.8.0.1",
                "broadcast_ip": "10.8.0.255",
                "netmask": "255.255.255.0",
                "vlan_id": vlan_dict['vlan']['id'],
            }
        }

        def _get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock. \
                get_routes.return_value = []
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with contextlib.nested(
                mock.patch.object(self.subnet_controller._plugin,
                                  '_get_device_driver'),
                mock.patch.object(self.subnet_controller._plugin,
                                  '_configure_subnet_on_device'))\
                as (device_driver, subnet_config_mock):
            device_driver.return_value = _get_device_driver_mock()
            subnet_config_mock.return_value = None
            subnet_data = self.subnet_controller.create(req, body=body)
            self.assertEqual("10.8.0.0/24", subnet_data['subnet']['cidr'])

    def test_update_port_disable_bypass_mac(self):
        port_dict = self._create_and_assert_test_port()
        port_dict2 = port_dict.pop('port2', None)

        def _get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock.disable_interfaces.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with mock.patch.object(self.port_controller._plugin,
                               '_get_device_driver') as device_driver:

            device_driver.return_value = _get_device_driver_mock()
            req = fakes.HTTPRequest.blank(
                '/ports/%s.json?skip_mac_check&skip_cms_check' % (
                    port_dict2['port']['id']))
            req.context.tenant_id = port_dict2['port']['tenant_id']
            body = {
                'port': {
                    'admin_status': "SUSPENDED",
                    'mac_address': '08:00:27:31:9c:b8'
                }
            }
            resp_dict = self.port_controller.update(
                req, id=port_dict2['port']['id'], body=body)
            self.assertIsNotNone(resp_dict)

    def test_create_device_no_bg(self):
        # bridge group creation
        bridgegroup_req = fakes.HTTPRequest.blank('/bridgegroups.json')
        bridgegroup_req.context.is_admin = True

        body = {
            'bridgegroup': {
                "name": "test-bg5",
                "description": "test bg description",
                "tenant_id": "1232"
            }
        }

        bg_dict = self.bg_controller.create(bridgegroup_req, body=body)
        self.assertIs(True, 'id' in bg_dict['bridgegroup'])

        # device type
        devicetpye_req = fakes.HTTPRequest.blank('/devicetypes')
        devicetpye_req.context.is_admin = True

        body = {
            "devicetype": {
                "name": "Top of the Rack Switch",
                "type": "TORS",
                "tenant_id": "1232"
            }

        }
        devicetype_dict = self.devicetype_controller.create(
            devicetpye_req, body=body)

        self.assertIs(True, 'id' in devicetype_dict['devicetype'])

        # bubble
        bubble_req = fakes.HTTPRequest.blank('/bubbles')
        bubble_req.context.is_admin = True

        body = {
            "bubble": {
                "name": "fakeBubble",
                "tenant_id": "1232"
            }

        }
        bubble_dict = self.bubble_controller.create(
            bubble_req, body=body)
        self.assertIs(True, 'id' in bubble_dict['bubble'])

        # device
        device_req = fakes.HTTPRequest.blank('/devices')
        device_req.context.is_admin = True
        body = {
            "device":
                {
                    "name": "test-device5",
                    "description": "test device",
                    "management_ip": "10.10.11.115",
                    "username": "arista",
                    "password": "arista",
                    "type": "TORS",
                    "bridge_group_id": None,
                    "os_type": "junos",
                    "tenant_id": "1232",
                    "bubble_id": bubble_dict['bubble']['id']
                }
        }
        with mock.patch.object(self.device_controller._plugin,
                               '_discover_ports_on_device') as \
                port_discovery_mock:
            port_discovery_mock.return_value = None
            device_dict = self.device_controller.create(device_req, body=body)
        self.assertIs(True, 'id' in device_dict['device'])

    def test_update_port_for_vlan_flipping_error_handling(self):
        # port_dict = self._create_and_assert_test_port()

        def _get_device_driver_mock():
            device_driver_mock = mock.Mock()
            device_driver_mock.open.return_value = None
            device_driver_mock. \
                update_switch_port_mode_on_interface.return_value = None
            device_driver_mock.close.return_value = None
            return device_driver_mock

        with mock.patch.object(self.port_controller._plugin,
                               '_get_device_driver') as device_driver:
            with mock.patch.object(self.port_controller._plugin,
                                   'create_port_flip_cr') as trace:
                device_driver.return_value = _get_device_driver_mock()
                trace.create_port_flip_cr.return_value = None
                port_id = '8ed4ae05-d55a-4ce1-82ad-d9ac0f50ca82'
                req = fakes.HTTPRequest.blank(
                    '/ports/%s.json' % port_id)
                req.context.tenant_id = '92cbd99904d44232986f9ae7a24557f6'

                body = {
                    'port': {
                        'switch_port_mode': 'access',
                        'vlans': [
                            {
                                "vlan": {
                                    "tag": "2"
                                }
                            }
                        ]
                    }
                }
                self.assertRaises(ex.PortNotFound,
                                  self.port_controller.update,
                                  req, id=port_id, body=body)
