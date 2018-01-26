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

# pylint: disable=W0614
from neutron.api.v2 import attributes as attr
from neutron.api.v2.attributes import *  # NOQA
from neutron.api.v2.attributes import _validate_boolean
from neutron.api.v2.attributes import _validate_non_negative
from neutron.api.v2.attributes import _validate_uuid


NAME_MAX_LEN = 255
TENANT_ID_MAX_LEN = 255
DESCRIPTION_MAX_LEN = 255
DEVICE_ID_MAX_LEN = 255
DEVICE_OWNER_MAX_LEN = 255


def convert_to_int_if_not_none(data):
    if data is not None:
        return attr.convert_to_int(data)
