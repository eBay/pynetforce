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

from netforce.db import netforce_db
from netforce.plugins.common import netforce_constants
from netforce.tests import base

import testscenarios

load_tests = testscenarios.load_tests_apply_scenarios


class TestDeviceDbBase(base.NetforceSqlTestCase):

    def setUp(self):
        super(TestDeviceDbBase, self).setUp()
        self.context = context.get_admin_context()
        self.device_db = netforce_db.NetforceDbMixin()
        self.port_db = netforce_db.NetforceDbMixin()


class TestDeviceDbMixin(TestDeviceDbBase):

    def setUp(self):
        super(TestDeviceDbMixin, self).setUp()

    def test_create_device(self):
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

        bubble = {
            'name': 'fake-05',
            'status': "ACTIVE"
        }
        bubble_db = self.device_db.create_bubble(self.context, bubble)
        device_type_db = self.device_db.create_devicetype(
            self.context, device_type)
        device['device_type_id'] = device_type_db['id']
        device['bubble_id'] = bubble_db['id']
        device_db = self.device_db.create_device(self.context, device)
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

    def test_update_device(self):
        device_type = {
            'name': 'TOR switch',
            'type': 'TOR'
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
        self.assertIsNotNone(device_db['id'])

        device_update = {
            'password': 'newarista'
        }
        updated_device_db = self.device_db.update_device(self.context,
                                                         device_db['id'],
                                                         device_update)
        self.assertIs(updated_device_db['password'], 'newarista')
