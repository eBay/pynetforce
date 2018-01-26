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


import mock
from oslo_config import cfg
from oslotest import base

from netforce.common import lockutils
from netforce.common import netforce_exceptions as n_exc
import six
import threading
import time
from tooz.drivers import etcd
from tooz.drivers.etcd import _Client as EtcdClient

FT_COUNT_KEY = 'keys/ft-count'
CONF = cfg.CONF


class TestLock(base.BaseTestCase):

    def setUp(self):
        super(TestLock, self).setUp()

    def test_lock_bad_backend_url(self):
        CONF.set_override('backend_url', 'etcd://127.0.0.1:1', 'dist_lock')

        def _lock():
            with lockutils.lock('test', blocking=False):
                self.assertTrue(False)

        self.assertRaises(n_exc.DistributedLockError, _lock)

    def test_lock(self):
        locked = False
        with lockutils.lock('test'):
            locked = True

        self.assertTrue(locked)

    def test_lock_acquire_non_blocking_failed(self):
        def _lock():
            with lockutils.lock('test', blocking=False):
                self.assertTrue(False)

        with lockutils.lock('test'):
            self.assertRaises(n_exc.AcquireDistributedLockFailed, _lock)

    def test_lock_block_timeout(self):
        def _lock():
            with lockutils.lock('test', blocking=3):
                self.assertTrue(False)

        with lockutils.lock('test'):
            self.assertTrue(True)
            self.assertRaises(n_exc.AcquireDistributedLockFailed, _lock)

    def test_lock_heartbeat(self):
        CONF.set_override('timeout', 2, 'dist_lock')

        origin_heartbeat = etcd.EtcdLock.heartbeat

        with lockutils.lock('test') as lock:
            with mock.patch.object(etcd.EtcdLock, 'heartbeat') as heart_beat:
                def side_effect():
                    six.print_('lock heartbeat: %s' % lock._node)
                    return origin_heartbeat(lock)
                heart_beat.side_effect = side_effect

                time.sleep(5)

                self.assertEqual(2, heart_beat.call_count)

    def test_lock_concurrency(self):

        cli = EtcdClient('localhost', 2379, 'http')
        cli.delete(FT_COUNT_KEY)
        cli.put(FT_COUNT_KEY, data={"value": 0, "prevExist": "false"})
        count = cli.get(FT_COUNT_KEY)
        count = int(count['node']['value'])
        self.assertEqual(0, count)

        def _worker():
            with lockutils.lock('test'):
                cli = EtcdClient('localhost', 2379, 'http')

                count = cli.get(FT_COUNT_KEY)
                count = int(count['node']['value'])
                reply = cli.put(FT_COUNT_KEY, data={"value": count + 1})

                self.assertEqual(count + 1, int(reply['node']['value']))
                thread = threading.currentThread()
                six.print_('%s count: %d' % (thread.name, count + 1))

        threads = []
        for i in range(20):
            t = threading.Thread(name='thread-%d' % i, target=_worker)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        count = cli.get(FT_COUNT_KEY)
        count = int(count['node']['value'])
        self.assertEqual(len(threads), count)
