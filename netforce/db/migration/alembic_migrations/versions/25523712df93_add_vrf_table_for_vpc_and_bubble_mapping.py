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


"""Add vrf table for vpc and bubble mapping

Revision ID: 25523712df93
Revises: 5b6c602c939b
Create Date: 2016-12-16 01:10:19.185397

"""

# revision identifiers, used by Alembic.
revision = '25523712df93'
down_revision = '5b6c602c939b'
branch_labels = None
depends_on = None

from alembic import op
import datetime
from netforce.db.migration.alembic_migrations import status_enums
import sqlalchemy as sa


def upgrade():
    op.create_table('nf_vrfs',
                    sa.Column('id', sa.String(36), nullable=False),
                    sa.Column('tenant_id', sa.String(36)),
                    sa.Column('name', sa.String(255), nullable=False),
                    sa.Column('description', sa.String(255), nullable=False),
                    sa.Column('bubble_id', sa.String(36),
                              sa.ForeignKey('nf_bubbles.id')),
                    sa.Column('vpc_id', sa.String(36),
                              sa.ForeignKey('nf_vpcs.id')),
                    sa.Column('status', status_enums, nullable=False),
                    sa.Column('status_description', sa.String(length=255)),
                    sa.Column('created_at', sa.DateTime,
                              default=datetime.datetime.now),
                    sa.Column('updated_at', sa.DateTime,
                              onupdate=datetime.datetime.now),
                    sa.Column('created_by', sa.String(length=255)),
                    sa.Column('last_updated_by', sa.String(length=255)),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade():
    op.drop_table('nf_vrfs')
