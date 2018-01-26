# Copyright (c) 2018 eBay, Inc., All Rights Reserverd.
# Copyright 2010 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Netforce Auth Middleware.

"""

import os
import time

from oslo_config import cfg
from oslo_log import log as logging
from oslo_middleware import request_id
from oslo_serialization import jsonutils
import webob.dec
import webob.exc

from keystoneclient.common import cms

from netforce.db import session_db as sesdb
from neutron import context
from neutron import wsgi

use_forwarded_for_opt = cfg.BoolOpt(
    'use_forwarded_for',
    default=True,
    help=_('Treat X-Forwarded-For as the canonical remote address. '
           'Only enable this if you have a sanitizing proxy.'))


CONF = cfg.CONF
CONF.register_opt(use_forwarded_for_opt)

LOG = logging.getLogger(__name__)


def pipeline_factory(loader, global_conf, **local_conf):
    """A paste pipeline replica that keys off of auth_strategy."""
    pipeline = local_conf[CONF.auth_strategy]
    if not CONF.api_rate_limit:
        limit_name = CONF.auth_strategy + '_nolimit'
        pipeline = local_conf.get(limit_name, pipeline)
    pipeline = pipeline.split()
    filters = [loader.get_filter(n) for n in pipeline[:-1]]
    app = loader.get_app(pipeline[-1])
    filters.reverse()
    for filter in filters:
        app = filter(app)
    return app


def start_session(req, req_id, user_id, a_strategy, auth_state):
    """Insert a session into the sessions table.

    Starts a session, meaning insert a record into the sessions
    tables with the information necessary to track the API request.

    params req: the request object.
    params req_id: the req_id request's context.
    params user_id: the user from the request.
    params a_strategy: which auth strategy used.
    params auth_state: the result of the authentication (SUCESSES/FAILED).
    """

    if 'REMOTE_ADDR' in req.environ.keys():
        raddr = ("%s:%s" % (req.environ['REMOTE_ADDR'],
                            req.environ['REMOTE_PORT']))
    elif 'HTTP_REMOTE_ADDR' in req.environ.keys():
        raddr = ("%s:%s" % (req.environ['HTTP_REMOTE_ADDR'],
                            req.environ['HTTP_REMOTE_PORT']))
    else:
        raddr = ("%s:%s" % ('127.0.0.1', '9696'))

    this_sess = sesdb.Session(
        req_id=req_id, user_agent=req.environ['HTTP_USER_AGENT'],
        req_api_start=time.time(),
        http_rtn=req.environ['webob.adhoc_attrs']['response'].status,
        username=user_id, auth_strategy=a_strategy,
        auth_state=auth_state,
        api_vers=req.environ['SCRIPT_NAME'][1:],
        msg_fmt=req.environ['CONTENT_TYPE'][
            req.environ['CONTENT_TYPE'].rfind('/') + 1:],
        url=req.environ['PATH_INFO'], remote_addr=raddr,
        originating_user=req.headers.get('X_NF_ORIGINATING_USER', ''),
        originating_ip=req.headers.get('X_NF_ORIGINATING_IP', '')
    )

    admin_ctx = context.get_admin_context()
    sesdb.SessionDbMixin().create_session(admin_ctx, this_sess)


class NetforceKeystoneContext(wsgi.Middleware):
    """Add a netforce.context to WSGI environ."""

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        # rtnA = None
        # a_strategy = 'noauth'
        auth_strategy = 'keystone'
        user_id = req.headers.get('X_USER')
        user_id = req.headers.get('X_USER_ID', user_id)
        req_id = req.environ.get(request_id.ENV_REQUEST_ID)
        if user_id is None:
            LOG.debug("Neither X_USER_ID nor X_USER found in request")
            auth_state = "FAIL"
            start_session(req, req_id, user_id, auth_strategy, auth_state)
            return webob.exc.HTTPUnauthorized()

        auth_state = 'PENDING'
        roles = [r.strip() for r in req.headers.get('X_ROLES', '').split(',')]

        if 'X_TENANT_ID' in req.headers:
            # This is the new header since Keystone went to ID/Name
            tenant_id = req.headers['X_TENANT_ID']
        elif 'X_TENANT' in req.headers:
            # This is for legacy compatibility
            tenant_id = req.headers['X_TENANT']
        else:
            tenant_id = req.headers.get('X_PROJECT_ID')

        project_name = req.headers.get('X_PROJECT_NAME')
        tenant_name = project_name
        if not tenant_name:
            tenant_name = req.headers.get('X_TENANT_NAME')

        user_name = req.headers.get('X_USER_NAME')

        # Get the auth token
        auth_token = req.headers.get('X_AUTH_TOKEN',
                                     req.headers.get('X_STORAGE_TOKEN'))

        if req.headers.get('X_SERVICE_CATALOG') is not None:
            try:
                catalog_header = req.headers.get('X_SERVICE_CATALOG')
                jsonutils.loads(catalog_header)
            except ValueError:
                auth_state = "FAIL"
                start_session(req, req_id, user_id, auth_strategy, auth_state)
                raise webob.exc.HTTPInternalServerError(
                    explanation=_('Invalid service catalog json.'))

        auth_state = 'SUCCESS'

        remote_address = req.remote_addr
        if CONF.use_forwarded_for:
            remote_address = req.headers.get('X-Forwarded-For', remote_address)

        # Create a context with the authentication data
        ctx = context.Context(user_id, tenant_id, roles=roles,
                              request_id=req_id, tenant_name=tenant_name,
                              user_name=user_name, auth_token=auth_token)

        start_session(req, req_id, user_id, auth_strategy, auth_state)
        req.environ['neutron.context'] = ctx

        return self.application


class NoAuthMiddleware(wsgi.Middleware):
    """Return a fake token if one isn't specified."""

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        if 'X-Auth-Token' not in req.headers:
            user_id = req.headers.get('X-Auth-User', 'admin')
            project_id = req.headers.get('X-Auth-Project-Id', 'admin')
            os_url = os.path.join(req.url, project_id)
            res = webob.Response()
            res.headers['X-Auth-Token'] = '%s:%s' % (user_id, project_id)
            res.headers['X-Server-Management-Url'] = os_url
            res.content_type = 'text/plain'
            res.status = '204'
            return res

        req_id = req.environ.get(request_id.ENV_REQUEST_ID)
        token = req.headers['X-Auth-Token']
        if cms.is_pkiz(token):
            user_id = ''
            project_id = ''
        else:
            user_id, _sep, project_id = token.partition(':')
        project_id = project_id or user_id
        remote_address = getattr(req, 'remote_address', '127.0.0.1')
        if CONF.use_forwarded_for:
            remote_address = req.headers.get('X-Forwarded-For', remote_address)

        start_session(req, req_id, user_id, 'noauth', 'SUCCESS')
        return self.application
