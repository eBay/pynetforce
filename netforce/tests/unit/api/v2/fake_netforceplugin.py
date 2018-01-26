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


from netforce.extensions import netforceext as netforce_v2_ctl
from netforce.services import netforce_plugin


class FakeNetforcePlugin(netforce_plugin.NetForcePlugin):

    def __init__(self):
        self.netforce_model = super(netforce_plugin.NetForcePlugin, self)
        self._extend_fault_map()
        self.username = 'test'
        self.password = 'test'


class FakeNetForceController(netforce_v2_ctl.NetForceController):

    def __init__(self, resource, collection, res_attr_map):
        super(FakeNetForceController, self).__init__(resource, collection,
                                                     res_attr_map,
                                                     FakeNetforcePlugin())
