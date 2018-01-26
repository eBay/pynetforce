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


from neutron.plugins.common import constants

from netforce.common import netforce_exceptions as netforce_exceptions
from netforce.db import netforce_db
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


def transaction(method):
    """
        A decorator used by plugin methods to ensure that the changes in the
        WISB database and device are ATOMIC.

    :param method:
    :return:
    """
    def wrapper(*args, **kwargs):
        db_api = netforce_db.NetforceDbMixin()
        plugin = args[0]
        context = args[1]
        method_name = method.__name__
        action = method_name.split('_')[0]
        resource = method_name.split('_')[1]

        try:
            response_payload = method(*args, **kwargs)
            # on create and update operations, we changes the status to
            # ACTIVE
            if action.startswith('create') or action.startswith('update'):
                res_dict = {
                    'status': constants.ACTIVE,
                    'status_description': 'changes completed'
                }

                try:
                    update_method = getattr(db_api, 'update_%s' % resource)
                except AttributeError as a_ex:
                    msg = (_('Could not find update method for resource '
                             '%(id)s, message %(msg)s') %
                           {'id': response_payload['id'], 'msg': a_ex.message})
                    LOG.exception(msg)
                    return response_payload

                updated_resource_db = update_method(context,
                                                    response_payload['id'],
                                                    res_dict)

                try:
                    view_method = getattr(plugin, 'make_%s_dict' % resource)
                except AttributeError as b_ex:
                    LOG.exception(_('Could not find get method for '
                                    'resource %(id)s, message %(msg)s') %
                                  {'id': response_payload['id'],
                                   'msg': b_ex.message})
                    return response_payload
                return view_method(updated_resource_db)

            # on delete operations, we delete the resource
            elif action.startswith('delete'):
                try:
                    del_method = getattr(db_api, 'delete_%s' % resource)
                except AttributeError as c_ex:
                    LOG.exception(_('Could not find delete method for '
                                    'resource %(id)s, message %(msg)s') %
                                  {'id': response_payload['id'],
                                   'msg': c_ex.message})
                    return None
                del_method(context, response_payload['id'])
                return None

        except netforce_exceptions.DeviceConfigPushFailure as ex:
            # if there is an error in pushing configuration on the device,
            # we mark the resource in error status and raise the inner
            # exception (for delete and update operations)
            if action.startswith('delete') or action.startswith('update'):
                res_dict = {
                    'status': constants.ERROR,
                    'status_description': ex.inner_exception.message if
                    ex.inner_exception.message else 'error in pushing config'
                }
                update_method = getattr(db_api, 'update_%s' % resource)
                update_method(context, ex.id, res_dict)
                raise ex.inner_exception

            # on create operation, we just delete the resource for rollback
            elif action.startswith('create'):
                del_method = getattr(db_api, 'delete_%s' % resource)
                del_method(context, ex.id)
                raise ex.inner_exception

    return wrapper
