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
import sqlalchemy as sa


def upgrade():
    op.create_table('nf_subnets',
                    sa.Column('id', sa.String(length=36), nullable=False),
                    sa.Column('tenant_id', sa.String(36), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('cidr', sa.String(64), nullable=False),
                    sa.Column('gateway_ip', sa.String(64), nullable=False),
                    sa.Column('broadcast_ip', sa.String(64), nullable=False),
                    sa.Column('netmask', sa.String(64), nullable=False),
                    sa.Column('vlan_id', sa.String(36), nullable=False),
                    sa.Column('status', status_enums, nullable=False),
                    sa.Column('status_description', sa.String(length=255)),
                    sa.Column('created_at', sa.DateTime,
                              default=datetime.datetime.now),
                    sa.Column('updated_at', sa.DateTime,
                              onupdate=datetime.datetime.now),
                    sa.Column('created_by', sa.String(length=255)),
                    sa.Column('last_updated_by', sa.String(length=255)),
                    sa.ForeignKeyConstraint(['vlan_id'], ['nf_vlans.id']),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade():
    op.drop_table('nf_subnets')
