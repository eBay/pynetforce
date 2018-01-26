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


import fixtures

from neutron.db import api as db_api
from neutron.tests import base
from neutron import wsgi

from netforce.db.netforce_model import BASEV2


class NetforceSqlTestFixture(fixtures.Fixture):

    def setUp(self):
        super(NetforceSqlTestFixture, self).setUp()
        engine = db_api.get_engine()
        BASEV2.metadata.create_all(engine)

        def clear_tables():
            with engine.begin() as conn:
                for table in reversed(BASEV2.metadata.sorted_tables):
                    conn.execute(table.delete())

        self.addCleanup(clear_tables)


class NetforceSqlTestCase(base.BaseTestCase):

    def setUp(self):
        super(NetforceSqlTestCase, self).setUp()
        self.useFixture(NetforceSqlTestFixture())


class NetforceWebTestCase(NetforceSqlTestCase):
    fmt = 'json'

    def setUp(self):
        super(NetforceWebTestCase, self).setUp()
        json_deserializer = wsgi.JSONDeserializer()
        self._deserializers = {
            'application/json': json_deserializer,
        }

    def deserialize(self, response):
        ctype = 'application/%s' % self.fmt
        data = self._deserializers[ctype].deserialize(response.body)['body']
        return data

    def serialize(self, data):
        ctype = 'application/%s' % self.fmt
        result = wsgi.Serializer().serialize(data, ctype)
        return result
