# Copyright 2018 eBay Inc.
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


from netforce.common import netforce_exceptions as netforce_exc
from oslo_log import log as logging
import paramiko
import socket

LOG = logging.getLogger(__name__)


class OpenNotInvokedException(Exception):

    def __init__(self):
        self.message = 'Please invoke open() before calling the ' \
                       'close() method.'


class SSHConnectionMixin(object):

    def open(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._connect()

    def _connect(self):
        try:
            self.ssh.connect(hostname=self.device_hostname,
                             username=self.device_username,
                             password=self.device_password,
                             timeout=self.tout,
                             compress=True,
                             look_for_keys=False,
                             allow_agent=False)
        except (socket.error, paramiko.AuthenticationException,
                paramiko.SSHException) as ex:
            LOG.error(" SSH connection to " + self.device_hostname +
                      " failed: " + str(ex))
            raise ex

    def close(self):
        if self.stdin:
            self.stdin.flush()
        if self.ssh:
            self.ssh.close()
            self.ssh = None

    def _check_if_connected(self):
        if not self.ssh:
            raise OpenNotInvokedException()

    def _exec_command(self, cmd):
        """TODO(aginwala): We are explicitly closing and opening the ssh
            connection before executing any commands on the device as a
            temporary workaround because ssh channel stalls due to known bug
            in paramiko ssh client that causes ssh exception.
            Relevant issue is noted @ http://stackoverflow.com/questions
            /31477121/python-paramiko-ssh-exception-ssh-session-not-active.
        """
        try:

            self.close()
            self.open()
            self.stdin, self.stdout, self.ssh_stderr = self.ssh.\
                exec_command(cmd)
        except netforce_exc.DeviceError:
            raise netforce_exc.DeviceError(device_error=self.ssh_stderr)
        return self.stdout.read() if self.stdout else None
