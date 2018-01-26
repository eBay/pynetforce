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


from neutron import context
from neutron.plugins.common import constants

from netforce.common import netforce_exceptions
from netforce.db import netforce_db
from netforce.plugins.common import netforce_constants
from netforce.tests import base

import testscenarios

load_tests = testscenarios.load_tests_apply_scenarios


class TestBridgeGroupDbBase(base.NetforceSqlTestCase):

    def setUp(self):
        super(TestBridgeGroupDbBase, self).setUp()
        self.context = context.get_admin_context()
        self.device_db = netforce_db.NetforceDbMixin()
        self.port_db = netforce_db.NetforceDbMixin()
        self.bridge_group_db = netforce_db.NetforceDbMixin()
        self.vlan_db = netforce_db.NetforceDbMixin()
        self.vpc_db = netforce_db.NetforceDbMixin()


class TestBridgeGroupDbMixin(TestBridgeGroupDbBase):

    def setUp(self):
        super(TestBridgeGroupDbMixin, self).setUp()

        device_type = {
            'name': 'TOR switch',
            'type': 'TOR'
        }
        port = {
            'name': 'test-port',
            'description': 'test port',
            'admin_status': constants.ACTIVE,
            'switch_port_mode': netforce_constants.TRUNK_MODE
        }

        device = {
            'name': 'test-device',
            'description': 'test device',
            'management_ip': '1.1.1.1',
            'username': 'arista',
            'password': 'arista'
        }

        device_type_db = self.device_db.create_devicetype(
            self.context, device_type)
        device['device_type_id'] = device_type_db['id']

        device_db = self.device_db.create_device(self.context, device)

        self.device_id = device_db['id']
        self.assertIsNotNone(device_db['id'])

        port['device_id'] = device_db['id']
        port_db = self.port_db.create_port(self.context, port)
        self.assertIsNotNone(port_db['id'])

        device_data_from_db = self.device_db.get_device_db(
            self.context, device_db['id'])
        self.assertIsNotNone(device_data_from_db.ports)
        self.assertIs(1, len(device_data_from_db.ports))
        self.assertIs(port_db['id'], device_data_from_db.ports[0].id)
        self.assertIs(device_db['id'], device_data_from_db.ports[0].device.id)

    def test_create_bg(self):
        bridgegroup = {
            'name': 'test-bg',
            'description': 'test-bg'
        }
        bg_db = self.bridge_group_db.create_bridgegroup(
            self.context, bridgegroup)
        bg_db.devices.append(self.device_db.get_device_db(
            self.context, self.device_id))
        bg_db.save(self.context.session)
        self.assertIs(True, 'id' in bg_db)
        bg_from_db = self.bridge_group_db.get_bridgegroup_db(
            self.context, bg_db['id'])
        self.assertIs(1, len(bg_from_db.devices))
        self.assertEqual(self.device_id, bg_from_db.devices[0].id)

        self.assertRaises(netforce_exceptions.DevicesAssociatedToBridgeGroup,
                          self.bridge_group_db.delete_bridgegroup,
                          self.context,
                          bg_db.id)

    def test_delete_bg_with_vlan(self):
        # bridge group creation
        bridgegroup = {
            'name': 'test-bg',
            'description': 'test-bg'
        }
        bg_db = self.bridge_group_db.create_bridgegroup(
            self.context, bridgegroup)

        # create vpc
        vpc = {
            "name": "test-vpc",
            "description": "test vpc description",
            "label": "test-vpc-label"
        }

        vpc_db = self.vpc_db.create_vpc(self.context, vpc)

        vlan = {
            'name': 'test-vlan-1',
            'tag': 2,
            'admin_status': constants.ACTIVE
        }

        # vlan creation
        vlan_model = self.vlan_db.create_vlan_by_bg_and_vpc(
            self.context, vlan, bg_db, vpc_db)
        self.assertIsNotNone(vlan_model)

        self.assertRaises(netforce_exceptions.VlanAssociatedToBridgeGroup,
                          self.bridge_group_db.delete_bridgegroup,
                          self.context,
                          bg_db.id)
