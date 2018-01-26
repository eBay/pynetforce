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


"""drop foriegn key constraing on nf_vlans table for vpc_id

Revision ID: 931402233d71
Revises: 25523712df93
Create Date: 2017-07-23 21:15:01.847595

"""

# revision identifiers, used by Alembic.
revision = '931402233d71'
down_revision = '25523712df93'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('nf_vlans', 'vpc_id', nullable=True,
                    existing_nullable=False, existing_type=sa.String(36))


def downgrade():
    op.alter_column('nf_vlans', 'vpc_id', nullable=False)
