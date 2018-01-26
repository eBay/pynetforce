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


import webob
import webob.dec
import webob.request

from neutron import context
from neutron import wsgi


class HTTPRequest(webob.Request):

    @classmethod
    def blank(cls, *args, **kwargs):
        if args is not None:
            if args[0].find('v1') == 0:
                kwargs['base_url'] = 'http://localhost/v1'
            else:
                kwargs['base_url'] = 'http://localhost/v2'

        out = wsgi.Request.blank(*args, **kwargs)
        ctxt = context.Context('fake_user', 'fake_tenant')
        out.environ['neutron.context'] = ctxt
        out.environ['context'] = ctxt
        return out
