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


import contextlib
import uuid

from oslo_config import cfg
from oslo_log import log as logging

from netforce.common import local
from netforce.common import netforce_exceptions as n_exc
from tooz import coordination

CONF = cfg.CONF
dist_lock_conf = [
    cfg.StrOpt('backend_url', default='etcd://',
               help='distributed lock backend url'),
    cfg.IntOpt('timeout', default=45,
               help='lock timeout time'),
]
CONF.register_opts(dist_lock_conf, group='dist_lock')

LOG = logging.getLogger(__name__)


@contextlib.contextmanager
def lock(name, blocking=True):
    """distributed lock
    :param blocking: can be a bool or double value; if is double value, the
      value indicate the block duration.

        1. blocking lock - wait forever:
            with lockutils.lock('name', blocking=True):
                ...

        2. blocking lock - wait certain timeout, e.g block 5 seconds:
           with lockutils.lock('name', blocking=5)
                ...

        3. nonblocking lock - no wait if lock is hold by someone else:
           with lockutils.lock('name', blocking=False)
                ...
    """

    if not hasattr(local.strong_store, 'coordinator'):
        try:
            backend_url = CONF.dist_lock.backend_url
            coordinator = coordination.get_coordinator(backend_url,
                                               str(uuid.uuid4()),
                                               timeout=CONF.dist_lock.timeout)
            coordinator.start(start_heart=True)
        except coordination.ToozError as e:
            LOG.warning('Initializing distribute lock failed, %s' % e)
            raise n_exc.DistributedLockError(message=str(e))

        local.strong_store.coordinator = coordinator

    lock = local.strong_store.coordinator.get_lock(name)
    try:
        with lock(blocking):
            LOG.debug('Acquired distributed lock "%(lock)s"',
                      {'lock': name})

            try:
                yield lock
            finally:
                LOG.debug('Releasing distributed lock "%(lock)s"',
                          {'lock': name})
    except coordination.LockAcquireFailed:
        raise n_exc.AcquireDistributedLockFailed(name=name)
