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
from napalm_baseebay import base_validator
from napalm_baseebay import ebay_exceptions

from neutron import context
from neutron.plugins.common import constants


from netforce.db import netforce_db
from netforce.plugins.common import netforce_constants
from netforce.tests import base

from sqlalchemy.orm import exc
import testscenarios

load_tests = testscenarios.load_tests_apply_scenarios


class FakeSubnetPlugin(netforce_db.NetforceDbMixin):
    pass


class TestSubnetDbBase(base.NetforceSqlTestCase):

    def setUp(self):
        super(TestSubnetDbBase, self).setUp()
        self.context = context.get_admin_context()
        self.device_db = netforce_db.NetforceDbMixin()
        self.port_db = netforce_db.NetforceDbMixin()
        self.bridge_group_db = netforce_db.NetforceDbMixin()
        self.vlan_db = netforce_db.NetforceDbMixin()
        self.subnet_db = FakeSubnetPlugin()
        self.subnet = {}


class FakeValidatorMixinImpl(base_validator.ValidatorMixin):

    def get_ip_addrs_on_interface(self, vlan_interface_name):
        return []


class TestSubnetValidator(TestSubnetDbBase):

    def setUp(self):
        super(TestSubnetValidator, self).setUp()

    def test_pre_change_subnet_validation_overlapping_subnet_failure(self):
        validator = FakeValidatorMixinImpl()
        with mock.patch.object(validator, 'get_ip_addrs_on_interface')\
            as existing_subnets:
            existing_subnets.return_value = ['192.168.1.0/24']
            self.assertRaises(ebay_exceptions.SubnetAlreadyConfiguredException,
                              validator.pre_change_validate_subnet,
                              '192.168.1.0/25', 'vlan3')

    def test_pre_change_subnet_validation_overlapping_subnet_success(self):
        validator = FakeValidatorMixinImpl()
        with mock.patch.object(validator, 'get_ip_addrs_on_interface') \
                as existing_subnets:
            existing_subnets.return_value = ['192.168.2.0/24']
            validator.pre_change_validate_subnet('192.168.1.0/25', 'vlan3')

    def test_pre_change_subnet_validation_max_limit_crossed(self):
        validator = FakeValidatorMixinImpl()
        with mock.patch.object(validator, 'get_ip_addrs_on_interface') \
                as existing_subnets:
            existing_subnets.return_value = ['', '', '', '',
                                             '', '', '', '']
            self.assertRaises(
                ebay_exceptions.MaxNumberOfAllowedSubnetsAlreadyConfigured,
                validator.pre_change_validate_subnet,
                '192.168.1.0/25', 'vlan3')


class TestSubnetDbMixin(TestSubnetDbBase):

    def setUp(self):
        super(TestSubnetDbMixin, self).setUp()

        device_type = {
            'tenant_id': '12345',
            'name': 'TOR switch',
            'type': 'TOR'
        }
        port = {
            'tenant_id': '12345',
            'name': 'test-port',
            'description': 'test port',
            'admin_status': constants.ACTIVE,
            'switch_port_mode': netforce_constants.TRUNK_MODE
        }

        device = {
            'tenant_id': '12345',
            'name': 'test-device',
            'description': 'test device',
            'management_ip': '1.1.1.1',
            'username': 'arista',
            'password': 'arista'
        }

        bridgegroup = {
            'tenant_id': '12345',
            'name': 'test-bg',
            'description': 'test-bg'
        }

        self.vpc = {
            'tenant_id': '12345',
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

        # vlan creation
        self.bridgegroup_from_db = self.bridge_group_db.get_bridgegroup_db(
            self.context, bg_db['id'])
        vlan = {
            'tenant_id': '12345',
            'name': 'test-vlan-1',
            'tag': 2,
            'admin_status': constants.ACTIVE,
            'bridgegroup_id': self.bridgegroup_from_db.id,
            'vpc_id': self.vpc_db.id
        }
        vlan_model = self.vlan_db.create_vlan(self.context, vlan)

        self.subnet = {
            'tenant_id': '12345',
            'name': 'test-prod-routed-subnet',
            'cidr': '172.1.1.0/24',
            'gateway_ip': '172.1.1.0',
            'broadcast_ip': '172.1.1.255',
            'netmask': '255.255.255.0',
            'vlan_id': vlan_model.id,
            'status': 'ACTIVE'

        }
        vlan_model.save(self.context.session)
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
        self.assertIs(True, 'id' in vlan_model)

    def test_create_subnet(self):
        # subnet creation
        subnet_model = self.subnet_db.create_subnet(self.context, self.subnet)
        self.assertIs(True, 'id' in subnet_model)

        self.subnet_db.delete_subnet(self.context, subnet_model.id)
        self.assertRaises(exc.NoResultFound, self.subnet_db.get_subnet_db,
                          self.context,
                          subnet_model.id)

    def test_update_subnet(self):
        # subnet update
        subnet_model = self.subnet_db.create_subnet(self.context, self.subnet)
        self.subnet = {
            'tenant_id': '12345',
            'cidr': '172.2.1.0/24',
            'status': 'SUSPENDED'
        }
        subnet_model = self.subnet_db.update_subnet(self.context,
                                                    subnet_model.id,
                                                    self.subnet)
        self.assertIs(True, 'id' in subnet_model)
        self.subnet_db.delete_subnet(self.context, subnet_model.id)
        self.assertRaises(exc.NoResultFound, self.subnet_db.get_subnet_db,
                          self.context,
                          subnet_model.id)
