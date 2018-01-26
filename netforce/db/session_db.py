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


import time

from eventlet import greenthread
from oslo_utils import timeutils

import sqlalchemy as sa

from netforce.common import netforce_exceptions as net_esc
from neutron.common import exceptions as exc
from neutron.db import common_db_mixin
from neutron.db import model_base
from neutron.db import models_v2
from sqlalchemy.orm import exc as sql_exc


class HasCreatedUpdatedTime(object):
    """created_at updated_at mixin, add to subclasses that have these."""

    created_at = sa.Column(sa.DateTime, default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, default=sa.func.now(),
                           onupdate=sa.func.now())


class Session(model_base.BASEV2, models_v2.HasId,
              HasCreatedUpdatedTime):
    '''Session: this is the sessioning table to track and audit
       netforce activity.
    '''
    __table_args__ = (
        sa.Index('idx_username', 'username'),
        sa.Index('idx_tid', 'tid'),
        sa.Index('idx_remote_addr', 'remote_addr'),
        sa.Index('idx_auth_state', 'auth_state'),
        sa.Index('idx_req_id', 'req_id'),
        model_base.BASEV2.__table_args__
    )

    # column definitions:
    # ===================
    # req_id: the id that is established in the API format is req-8-4-4-4-12
    # req_api_start: the timing when the API starts tracking it
    # # req_api_end: the time when the API returns
    # user_agent: The User-Agent request-header field contains information
    #   about the user agent originating the request. This is for statistical
    #   purposes, the tracing of protocol violations.
    # http_rtn: HTTP return code i.e. 200/500/403, etc..
    # rtn_bytes: Number of bytes returned for thi request.
    # tid: transaction_id
    # username: the user requesting netforce service.
    # auth_strategy: the authentication strategy used.
    # auth_state: the state of the authentication, if Failed, an attempt was
    #   made to access netforce with improper creds.
    # api_vers: the version of the api, i.e. 2.0
    # url: the request
    # msg_fmt: this is the format of the messages, i.e. XML, JSON
    req_id = sa.Column(sa.String(40), nullable=False, server_default='')
    req_api_start = sa.Column(sa.Numeric(precision=20, scale=10),
                              nullable=False, server_default='0.0')
    req_api_end = sa.Column(sa.Numeric(precision=20, scale=10),
                            nullable=False, server_default='0.0')
    user_agent = sa.Column(sa.String(255), nullable=False, server_default='')
    http_rtn = sa.Column(sa.String(64), nullable=False, default='')
    rtn_bytes = sa.Column(sa.Integer, nullable=False, default=0)
    tid = sa.Column(sa.String(36), nullable=False, server_default='')
    username = sa.Column(sa.String(64), nullable=False, server_default='')
    auth_strategy = sa.Column(sa.String(32), nullable=False,
                              server_default='NONE')
    auth_state = sa.Column(sa.Enum('FAIL', 'SUCCESS', 'PENDING',
                                   name='auth_state'), nullable=False,
                           server_default='PENDING')
    api_vers = sa.Column(sa.String(16), nullable=False, server_default='2.0')
    url = sa.Column(sa.String(255), nullable=False, server_default='')
    msg_fmt = sa.Column(sa.String(8), nullable=False, server_default='json')
    remote_addr = sa.Column(sa.String(255), nullable=False, server_default='')
    originating_user = sa.Column(sa.String(255), server_default='')
    originating_ip = sa.Column(sa.String(32), server_default='')


class SessionDbMixin(common_db_mixin.CommonDbMixin):
    '''All the necessary items to provide CRUD a session table.'''

    def get_session(self, context, id):
        return self._get_session_with_id(context, id)

    def _get_session_with_id(self, context, id):
        try:
            session = self._get_by_id(context, Session, id)
        except sql_exc.NoResultFound:
            raise net_esc.SessionNotFound(session_id=id)
        return session

    def get_session_with_req_id(self, context, req_id):
        '''Return a session associated to the req_id.'''
        query = self._model_query(context, Session)
        return query.filter(Session.req_id == req_id).one()

    def get_sessions_with_username(self, context, username, count=0):
        '''Return a list of session belonging to the specified user, if greater
        than 0 then only the latest count of session for this user will be
        returned.
        '''
        query = context.session.query(Session)
        if count:
            rs = query.filter(Session.username == username).order_by(
                Session.updated_at.desc()).limit(count)
        else:
            rs = query.filter(Session.username == username).all()

        return rs

    def _make_session_dict(self, session, fields=None):
        return self._fields(session, fields)

    def update_session(self, context, session):
        id = session['id']
        with context.session.begin(subtransactions=True):
            srec = self._get_session_with_id(context, id)
            # no touch keys, if there being passed in remove them
            no_upd_keys = ['req_api_start', 'created_at']
            upd_rec = {}
            for k, v in session.items():
                if k not in no_upd_keys:
                    upd_rec[k] = v

            srec.update(upd_rec)

        return self._make_session_dict(session)

    def _create_session(self, context, session_state):
        current_time = timeutils.utcnow()
        with context.session.begin(subtransactions=True):
            res_keys = ['req_id', 'username']
            res = dict((k, session_state[k]) for k in res_keys)
            for k, v in session_state.iteritems():
                res[k] = v

            res['created_at'] = current_time
            greenthread.sleep(0)
            sess_db = Session(**res)
            greenthread.sleep(0)
            context.session.add(sess_db)
            greenthread.sleep(0)
            return sess_db

    def session_end(self, context, req_id, req_api_end=None,
                    http_rtn=None, rtn_bytes=0):
        '''Sets the session ending values and updates a session defined by its
        req_id.
        '''
        with context.session.begin(subtransactions=True):
            sessdb = self.get_session_with_req_id(context, req_id)
            srec = self._make_session_dict(sessdb)
            if req_api_end:
                srec['req-api_end'] = req_api_end
            else:
                srec['req_api_end'] = time.time()
            if http_rtn:
                srec['http_rtn'] = http_rtn
            srec['rtn_bytes'] = rtn_bytes
            rtn_dict = self.update_session(context, srec)

        return rtn_dict

    def create_session(self, context, session):
        """Create or update a session."""
        return self._create_session(context, session)

    def get_sessions(self, context, filters=None, sorts=None, limit=None,
                     marker=None, page_reverse=False):
        """Returns all the sessions db records based upon the params, uses the
        underlying base abstractions to collect them.
        """
        marker_obj = self._get_marker_obj(context, 'session', limit, marker)
        return self._get_collection_query(context, Session, filters=filters,
                                          sorts=sorts, limit=limit,
                                          marker_obj=marker_obj,
                                          page_reverse=page_reverse)
