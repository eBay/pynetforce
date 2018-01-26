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
from netforce.tests.unit.napalm import base


class NapalmBaseEbayInterfaceValidationMixin(base.DietTestCase):
    """NapalmBase Interface ValidationMixin Test Suite

    This test suite performs setup and teardown functions for this file's
    unit tests. Each unit test class should inherit from this class, and
    implement a single "runTest" function.

    """

    def setUp(self):
        """Perform setup activities

        """
        self.mixin = base_validator.ValidatorMixin()


class test_check_traffic_on_interfaces(
    NapalmBaseEbayInterfaceValidationMixin):
    def get_mock_traffic(self, interfaces):
        mock_base = mock.Mock()
        mock_base.get_traffic_on_interface(interfaces).return_value = (0, 496)
        return mock_base

    def runTest(self):
        interfaces = ['xe-0/0/0:1']
        self.mixin.get_traffic_on_interface = self.get_mock_traffic(
            interfaces)
        self.mixin.check_traffic_on_interface(interfaces)
