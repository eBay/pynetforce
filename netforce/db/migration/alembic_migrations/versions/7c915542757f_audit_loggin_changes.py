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

"""audit loggin changes

Revision ID: 7c915542757f
Revises: ff9f863d67c7
Create Date: 2016-11-02 16:34:23.629240

"""

# revision identifiers, used by Alembic.
revision = '7c915542757f'
down_revision = 'ff9f863d67c7'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('sessions',
                  sa.Column('originating_user', sa.String(length=255),
                            default=''))
    op.add_column('sessions',
                  sa.Column('originating_ip', sa.String(length=32),
                            default=''))


def downgrade():
    op.drop_column('sessions', 'originating_user')
    op.drop_column('sessions', 'originating_ip')
