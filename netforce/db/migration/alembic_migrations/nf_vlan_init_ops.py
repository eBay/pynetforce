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


from alembic import op
import datetime
from netforce.db.migration.alembic_migrations import status_enums
from netforce.plugins.common import netforce_constants
from neutron.plugins.common import constants
import sqlalchemy as sa


def upgrade():
    op.create_table('nf_vlans',
                    sa.Column('id', sa.String(length=36), nullable=False),
                    sa.Column('tenant_id', sa.String(36), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('tag', sa.Integer, nullable=False),
                    sa.Column('admin_status',
                              sa.Enum(constants.ACTIVE,
                                      netforce_constants.SUSPENDED,
                                      name='admin_status'),
                              nullable=False),
                    sa.Column('status', status_enums, nullable=False),
                    sa.Column('status_description', sa.String(length=255)),
                    sa.Column('bridge_group_id',
                              sa.String(36), nullable=False),
                    sa.Column('vpc_id', sa.String(36), nullable=False),
                    sa.Column('created_at', sa.DateTime,
                              default=datetime.datetime.now),
                    sa.Column('updated_at', sa.DateTime,
                              onupdate=datetime.datetime.now),
                    sa.Column('created_by', sa.String(length=255)),
                    sa.Column('last_updated_by', sa.String(length=255)),
                    sa.ForeignKeyConstraint(
                        ['bridge_group_id'], ['nf_bridgegroups.id']),
                    sa.ForeignKeyConstraint(['vpc_id'], ['nf_vpcs.id']),
                    sa.UniqueConstraint('bridge_group_id', 'vpc_id'),
                    sa.PrimaryKeyConstraint('id')
                    )

    op.create_table('nf_vlanportassociations',
                    sa.Column('id', sa.String(length=36), nullable=False),
                    sa.Column('tenant_id', sa.String(36), nullable=False),
                    sa.Column('port_id', sa.String(36), nullable=False),
                    sa.Column('vlan_id', sa.String(36), nullable=False),
                    sa.Column('status', status_enums, nullable=False),
                    sa.Column('status_description', sa.String(length=255)),
                    sa.Column('created_at', sa.DateTime,
                              default=datetime.datetime.now),
                    sa.Column('updated_at', sa.DateTime,
                              onupdate=datetime.datetime.now),
                    sa.Column('created_by', sa.String(length=255)),
                    sa.Column('last_updated_by', sa.String(length=255)),
                    sa.Column('is_native_vlan', sa.Boolean(), default=False),
                    sa.UniqueConstraint('port_id', 'vlan_id'),
                    sa.ForeignKeyConstraint(['port_id'], ['nf_ports.id']),
                    sa.ForeignKeyConstraint(['vlan_id'], ['nf_vlans.id']),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade():
    op.drop_table('nf_vlanportassociations')
    op.drop_table('nf_vlans')
