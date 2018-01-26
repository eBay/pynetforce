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


"""adding allocation pools for subnet in netforce

Revision ID: ff9f863d67c7
Revises: v1
Create Date: 2016-11-01 18:33:09.380346

"""

# revision identifiers, used by Alembic.
revision = 'ff9f863d67c7'
down_revision = 'v1'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('nf_subnets', sa.Column('start_ip', sa.String(64)))
    op.add_column('nf_subnets', sa.Column('end_ip', sa.String(64)))


def downgrade():
    op.drop_column('nf_subnets', 'start_ip')
    op.drop_column('nf_subnets', 'end_ip')
