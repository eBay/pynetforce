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

""" The first version of netforce database

Revision ID: v1
Revises: None

"""
from netforce.db.migration.alembic_migrations import nf_bridgegroup_init_ops
from netforce.db.migration.alembic_migrations import nf_devices_init_ops
from netforce.db.migration.alembic_migrations import nf_port_init_ops
from netforce.db.migration.alembic_migrations import nf_subnet_init_ops
from netforce.db.migration.alembic_migrations import nf_vlan_init_ops
from netforce.db.migration.alembic_migrations import nf_vpc_init_ops
from netforce.db.migration.alembic_migrations import session_init_ops

# revision identifiers, used by Alembic.
revision = 'v1'
down_revision = None


def upgrade():
    session_init_ops.upgrade()
    nf_vpc_init_ops.upgrade()
    nf_bridgegroup_init_ops.upgrade()
    nf_devices_init_ops.upgrade()
    nf_port_init_ops.upgrade()
    nf_vlan_init_ops.upgrade()
    nf_subnet_init_ops.upgrade()


def downgrade():
    session_init_ops.downgrade()
    nf_subnet_init_ops.downgrade()
    nf_vlan_init_ops.downgrade()
    nf_port_init_ops.downgrade()
    nf_devices_init_ops.downgrade()
    nf_bridgegroup_init_ops.downgrade()
    nf_vpc_init_ops.downgrade()
