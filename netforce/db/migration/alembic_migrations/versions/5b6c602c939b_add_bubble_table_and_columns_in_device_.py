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

"""Add bubble table and columns in device to enforce bubble level subnet
 validation data-model

Revision ID: 5b6c602c939b
Revises: 7c915542757f
Create Date: 2016-11-22 23:25:38.092694

"""

# revision identifiers, used by Alembic.
revision = '5b6c602c939b'
down_revision = '7c915542757f'
branch_labels = None
depends_on = None

from alembic import op
import datetime
from netforce.db.migration.alembic_migrations import status_enums
import sqlalchemy as sa


def upgrade():
    op.create_table('nf_bubbles',
                    sa.Column('id', sa.String(36), nullable=False),
                    sa.Column('tenant_id', sa.String(36)),
                    sa.Column('name', sa.String(255), nullable=False),
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
    op.add_column('nf_devices', sa.Column('bubble_id', sa.String(36),
                                          sa.ForeignKey('nf_bubbles.id')))


def downgrade():
    op.drop_column('nf_devices', 'bubble_id')
    op.drop_table('nf_bubbles')
