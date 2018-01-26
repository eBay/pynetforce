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
    op.create_table('nf_ports',
                    sa.Column('id', sa.String(length=36), nullable=False),
                    sa.Column('tenant_id', sa.String(36), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('description', sa.String(length=255)),
                    sa.Column('admin_status',
                              sa.Enum(constants.ACTIVE,
                                      netforce_constants.SUSPENDED,
                                      name='admin_status'),
                              nullable=False),
                    sa.Column('switch_port_mode',
                              sa.Enum(netforce_constants.ACCESS_MODE,
                                      netforce_constants.TRUNK_MODE),
                              nullable=False),
                    sa.Column('status', status_enums, nullable=False),
                    sa.Column('status_description', sa.String(length=255)),
                    sa.Column('label', sa.String(length=255), nullable=True),
                    sa.Column('asset_id', sa.String(
                        length=255), nullable=True),
                    sa.Column('device_id', sa.String(36), nullable=False),
                    sa.Column('created_at', sa.DateTime,
                              default=datetime.datetime.now),
                    sa.Column('updated_at', sa.DateTime,
                              onupdate=datetime.datetime.now),
                    sa.Column('created_by', sa.String(length=255)),
                    sa.Column('last_updated_by', sa.String(length=255)),
                    sa.ForeignKeyConstraint(['device_id'], ['nf_devices.id']),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('asset_id'),
                    sa.UniqueConstraint('label')
                    )


def downgrade():
    op.drop_table('nf_ports')
