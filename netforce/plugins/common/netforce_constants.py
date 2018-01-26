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


# admin_status
SUSPENDED = "SUSPENDED"

# Switch port mode
TRUNK_MODE = 'trunk'
ACCESS_MODE = 'access'
NO_MODE = 'none'

SWITCH_TYPE_TORS = "TORS"
SWITCH_TYPE_DISTRIBUTION = "DISTRIBUTION"
# switch types
switch_types = [SWITCH_TYPE_TORS, "LBSWITCH", SWITCH_TYPE_DISTRIBUTION,
                "CORE", "BORDER", "BACKBONE", "FABRIC"]


NETFORCE = 'NETFORCE'

COMMON_PREFIXES = {
    NETFORCE: "/netforce"
}
PENDING_STATUS_DESCRIPTION = 'Pending Device Changes'
ACTIVE_STATUS_DESCRIPTION = 'Completed'

VALIDATION_TYPE_PRE = 'pre'
VALIDATION_TYPE_POST = 'post'

DISABLE_PORT = 'shutdown'
ENABLE_PORT = 'noshutdown'
