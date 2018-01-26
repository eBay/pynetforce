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

# Initial operations for sessions
# This module only manages the 'sessions' table.

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('req_id', sa.String(length=40), nullable=False,
                  server_default=''),
        sa.Column('req_api_start', sa.Numeric(precision=20, scale=10),
                  nullable=False, server_default='0'),
        sa.Column('req_api_end', sa.Numeric(precision=20, scale=10),
                  nullable=False, server_default='0'),
        sa.Column('user_agent', sa.String(length=255), nullable=False,
                  server_default=''),
        sa.Column('http_rtn', sa.String(length=64), nullable=False,
                  server_default=''),
        sa.Column('rtn_bytes', sa.Integer(), nullable=False,
                  server_default='0'),
        sa.Column('tid', sa.String(length=36), nullable=False,
                  server_default=''),
        sa.Column('username', sa.String(length=64), nullable=False,
                  server_default=''),
        sa.Column('auth_strategy', sa.String(length=32), nullable=False,
                  server_default='NONE'),
        sa.Column('auth_state', sa.Enum('FAIL', 'SUCCESS', 'PENDING'),
                  nullable=False, server_default='PENDING'),
        sa.Column('api_vers', sa.String(length=16), nullable=False,
                  server_default=''),
        sa.Column('url', sa.String(length=255), nullable=False,
                  server_default=''),
        sa.Column('msg_fmt', sa.String(length=8), nullable=False,
                  server_default='json'),
        sa.Column('remote_addr', sa.String(length=255), nullable=False,
                  server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  onupdate=sa.func.new()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_username', 'username'),
        sa.Index('idx_tid', 'tid'),
        sa.Index('idx_remote_addr', 'remote_addr'),
        sa.Index('idx_auth_state', 'auth_state'),
        sa.Index('idx_req_id', 'req_id'))


def downgrade():
    op.drop_table('sessions')
