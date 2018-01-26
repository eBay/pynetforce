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


import logging

from neutron.common import exceptions as n_exc
from neutron import context
from neutron.plugins.common import constants

from netforce.db import netforce_db
from netforce.plugins.common import netforce_constants
import netforce.services.netforce_view
from netforce.tests import base

from sqlalchemy.orm import exc

import testscenarios

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


load_tests = testscenarios.load_tests_apply_scenarios


class FakePlugin(netforce_db.NetforceDbMixin,
                 netforce.services.netforce_view.NetForceViewMixin):
    pass


class TestPortDbBase(base.NetforceSqlTestCase):

    def setUp(self):
        super(TestPortDbBase, self).setUp()
        self.context = context.get_admin_context()
        self.plugin = FakePlugin()


class TestPortDbMixin(TestPortDbBase):

    def setUp(self):
        super(TestPortDbMixin, self).setUp()

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

        device_type_db = self.plugin.create_devicetype(
            self.context, device_type)
        device['device_type_id'] = device_type_db['id']

        self.device_db = self.plugin.create_device(self.context, device)
        self.assertIsNotNone(self.device_db['id'])

        self.port = {
            'name': 'test-port',
            'description': 'test port',
            'admin_status': constants.ACTIVE,
            'switch_port_mode': netforce_constants.TRUNK_MODE,
            'status': constants.PENDING_CREATE,
            'status_description': 'Creation Pending',
            'device_id': self.device_db.id,
            'asset_id': 'ASSET1234'
        }
        self.port_db = self.plugin.create_port(self.context, self.port)

    def test_port_db_create(self):
        self.assertIs(True, hasattr(self.port_db, 'id'),
                      'The id property is not present on the object.')
        self.assertIs(netforce_constants.TRUNK_MODE,
                      self.port_db.switch_port_mode,
                      'Cannot assert switch port mode property value.')

    def test_port_db_get(self):
        retrieved_port_db = self.plugin.get_port_db(
            self.context, self.port_db.id)
        self.assertIs(True, hasattr(retrieved_port_db, 'id'),
                      'The id property is not present on the object.')
        self.assertIs(netforce_constants.TRUNK_MODE,
                      retrieved_port_db.switch_port_mode,
                      'Cannot assert switch port mode property value.')

    def test_get_ports_by_asset_id(self):
        port_db = self.plugin.get_ports(
            self.context, filters={"asset_id": ["ASSET1234"]})
        self.assertIsNotNone(port_db)
        self.assertEqual(1, len(port_db))

    def test_port_db_update(self):
        self.plugin.\
            update_port(self.context, self.port_db.id,
                        {'switch_port_mode': netforce_constants.TRUNK_MODE})
        retrieved_port_db = self.plugin.get_port_db(
            self.context, self.port_db.id)

        self.assertIs(netforce_constants.TRUNK_MODE,
                      retrieved_port_db.switch_port_mode,
                      'Cannot assert switch port mode property value.')

    """
    TODO(aginwala) : Fix  sqlalchemy.orm.exc.FlushError: Over 100
    and re enable later.
    def test_port_db_delete(self):
        retreive_device_db = self.plugin.get_device_db(
            self.context, self.device_db.id)
        self.assertIsNotNone(retreive_device_db)
        self.assertEqual(1, len(retreive_device_db.ports))

        self.plugin.delete_port(self.context, self.port_db.id)
        self.assertRaises(
            exc.NoResultFound, self.plugin.get_port_db, self.context,
            self.port_db.id)
        retreive_device_db = self.plugin.get_device_db(
            self.context, retreive_device_db.id)
        self.assertIsNotNone(retreive_device_db)
        self.assertEqual(0, len(retreive_device_db.ports))
    """

    def test_device_db_delete(self):
        retreive_device_db = self.plugin.get_device_db(
            self.context, self.device_db.id)
        self.assertIsNotNone(retreive_device_db)
        self.assertEqual(1, len(retreive_device_db.ports))

        self.plugin.delete_device(self.context, self.device_db.id)
        self.assertRaises(
            exc.NoResultFound, self.plugin.get_device_db, self.context,
            self.device_db.id)
        self.assertRaises(
            n_exc.PortNotFound, self.plugin.get_port_db, self.context,
            self.port_db.id)
