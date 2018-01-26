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

from sqlalchemy.orm import exc
import testscenarios

load_tests = testscenarios.load_tests_apply_scenarios


class FakeVlanPlugin(netforce_db.NetforceDbMixin):
    pass


class TestVlanDbBase(base.NetforceSqlTestCase):

    def setUp(self):
        super(TestVlanDbBase, self).setUp()
        self.context = context.get_admin_context()
        self.device_db = netforce_db.NetforceDbMixin()
        self.port_db = netforce_db.NetforceDbMixin()
        self.bridge_group_db = netforce_db.NetforceDbMixin()
        self.vlan_db = FakeVlanPlugin()


class TestVlanDbMixin(TestVlanDbBase):

    def setUp(self):
        super(TestVlanDbMixin, self).setUp()

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

        bridgegroup = {
            'name': 'test-bg',
            'description': 'test-bg'
        }

        self.vpc = {
            "name": "test-vpc",
            "description": "test vpc description",
            "label": "test-vpc-label"
        }

        # create vpc
        self.vpc_db = self.vlan_db.create_vpc(self.context, self.vpc)

        # bridgegroup creation
        bg_db = self.bridge_group_db.create_bridgegroup(
            self.context, bridgegroup)
        device['bridge_group_id'] = bg_db['id']

        # device_type creation
        device_type_db = self.device_db.create_devicetype(
            self.context, device_type)
        device['device_type_id'] = device_type_db['id']

        # device creation
        device_db = self.device_db.create_device(self.context, device)

        self.device_id = device_db['id']
        self.assertIsNotNone(device_db['id'])

        # port creation
        port['device_id'] = device_db['id']
        port_db = self.port_db.create_port(self.context, port)
        self.assertIsNotNone(port_db['id'])

        # all assertions
        device_data_from_db = self.device_db.get_device_db(
            self.context, device_db['id'])
        self.bridgegroup_from_db = self.bridge_group_db.get_bridgegroup_db(
            self.context, bg_db['id'])

        self.assertIsNotNone(device_data_from_db.ports)
        self.assertIs(1, len(device_data_from_db.ports))
        self.assertIs(port_db['id'], device_data_from_db.ports[0].id)
        self.assertIs(device_db['id'], device_data_from_db.ports[0].device.id)
        self.assertIs(bg_db['id'], device_data_from_db.bridgegroup.id)
        self.assertIs(1, len(self.bridgegroup_from_db.devices))
        self.assertIs(device_db['id'], self.bridgegroup_from_db.devices[0].id)

    def test_create_vlan(self):
        vlan = {
            'name': 'test-vlan-1',
            'tag': 2,
            'admin_status': constants.ACTIVE,
            'bridgegroup_id': self.bridgegroup_from_db.id,
            'vpc_id': self.vpc_db.id
        }

        # vlan creation
        vlan_model = self.vlan_db.create_vlan(self.context, vlan)
        self.assertIs(True, 'id' in vlan_model)

        # second port creation
        port = {
            'name': 'test-port-1',
            'description': 'test port 1',
            'admin_status': constants.ACTIVE,
            'switch_port_mode': netforce_constants.TRUNK_MODE,
            'device_id': self.device_id
        }

        port_db = self.port_db.create_port(self.context, port)
        self.assertIsNotNone(port_db['id'])

        # associating vlan to both ports.
        device_db = self.device_db.get_device_db(self.context, self.device_id)

        device_db.ports.append(port_db)
        device_db.save(self.context.session)
        self.assertIs(2, len(device_db.ports))
        for p in device_db.ports:
            self.vlan_db.create_vlanportassociation(self.context,
                                                    vlan_id=vlan_model.id,
                                                    port_id=p.id,
                                                    is_native=False)

        vlan_model.save(self.context.session)

        # assertion
        self.assertIs(2, len(vlan_model.ports))
        self.assertIs(1, len(port_db.vlans))

        # create second bridge group
        bridgegroup_2 = {
            'name': 'test-bg-1',
            'description': 'test-bg'
        }
        bg_db_2 = self.bridge_group_db.create_bridgegroup(
            self.context, bridgegroup_2)

        # create second vlan
        vlan_2_param = {
            'name': 'test-vlan-2',
            'tag': 2,
            'admin_status': constants.ACTIVE,
            'bridgegroup_id': bg_db_2.id,
            'vpc_id': self.vpc_db.id

        }
        vlan_2_model = self.vlan_db.create_vlan(self.context, vlan_2_param)
        self.assertIs(True, 'id' in vlan_2_model)

        # associate this vlan to the second port
        vlan_port_assc = self.vlan_db.\
            create_vlanportassociation(self.context,
                                       vlan_id=vlan_2_model.id,
                                       port_id=port_db.id,
                                       is_native=False)

        port_db.vlans.append(vlan_port_assc)

        # assert the vlans on the port
        vlan_2_model.save(self.context.session)
        self.assertIs(2, len(port_db.vlans))

        # delete the port with vlans
        self.assertRaises(netforce_exceptions.VlansAssociatedToPort,
                          self.port_db.delete_port,
                          self.context, port_db.id)

        # delete the first vlan
        vlan_port_assc_1 = self.vlan_db.\
            _get_vlanportassociations_by_vlan_id(self.context,
                                                 vlan_model.id)
        self.assertEqual(2, len(vlan_port_assc_1))

        self.vlan_db.delete_vlan(self.context, vlan_model.id)
        self.assertRaises(exc.NoResultFound, self.vlan_db.get_vlan_db,
                          self.context,
                          vlan_model.id)

        vlan_port_assc_2 = self.vlan_db\
            ._get_vlanportassociations_by_vlan_id(self.context,
                                                  vlan_model.id)
        self.assertEqual(0, len(vlan_port_assc_2))
