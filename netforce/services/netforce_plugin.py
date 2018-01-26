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


import ipaddr
from napalm_base import get_network_driver
from napalm_baseebay import ebay_exceptions
import netaddr

from netforce.api.v2 import attributes
from netforce.api_client import exceptions as ticket_exceptions
from netforce.api_client import ticket_api_client
from netforce.common import netforce_exceptions as netforce_exc
from netforce.db import netforce_db
from netforce.plugins.common import netforce_constants
from netforce.services.netforce_view import NetForceViewMixin
from netforce.services.ticket_workflow import PortEnableticketWorkflow
from netforce.services.ticket_workflow import PortFlipticketWorkflow
from netforce.services.ticket_workflow import SubnetticketWorkflow
from netforce.services.transaction_manager import transaction

from neutron.api.v2 import base
from neutron.common import exceptions
from neutron.plugins.common import constants

import os
from oslo_config import cfg
from oslo_db import api as oslo_db_api
from oslo_log import log as logging
import random
import subprocess
import webob


LOG = logging.getLogger(__name__)

LOW_LIMIT_VLAN_TAG = 2
UPPER_LIMIT_VLAN_TAG = 100

CONF = cfg.CONF
plugin_conf = [
            cfg.BoolOpt('account_in_privileged_mode',
                       default=False,
                       help='flag whether the device acct is in privileged '
                            'mode'),
            cfg.BoolOpt('enable_vlan',
                        default=True,
                        help='whether to enable vlan operations support.'),
            cfg.BoolOpt('enable_subnet',
                        default=True,
                        help='whether to enable subnet operations support.')
        ]
CONF.register_opts(plugin_conf)

subnet_conf = [
            cfg.IntOpt('reserve_ip_count',
                       default=10,
                       help='Specify number of IPs to reserve as a part of'
                            ' subnet creation'),
            cfg.StrOpt('allowed_subnet',
                       default='10.0.0.0/8',
                       help='Only subnets under this CIDR be allowed.'),
            cfg.IntOpt('ticketroute_max_hops',
                       default=20,
                       help='ticketroute default hops.'),
            cfg.ListOpt('allowed_vpcs',
                       default=['fake-vpc1'],
                       help='List of vpcs for which ticketroute should be'
                            ' enabled.')
        ]
CONF.register_opts(subnet_conf)


class NetForcePlugin(netforce_db.NetforceDbMixin, NetForceViewMixin,
                     PortFlipticketWorkflow, SubnetticketWorkflow,
                     PortEnableticketWorkflow):
    supported_extension_aliases = ['netforce']

    NETFORCE_FAULT_MAP = {
        netforce_exc.DeviceError: webob.exc.HTTPInternalServerError,
    }

    OS_TYPE_DRIVER_MAP = {
        "eos": "ebayeos",
        "junos": "ebayjunos",
        "nxos": "ebaynxos",
        "ios": "ebayios",
    }

    def __init__(self):
        self.netforce_model = super(NetForcePlugin, self)
        self._extend_fault_map()
        self.username, self.password = self._get_credentials()

    def _get_ticket_client(self):
        ticket_client = ticket_api_client.ticketApiClient(
            cfg.CONF.ticket_service_url, cfg.CONF.ticket_api_user,
            cfg.CONF.ticket_api_password, cfg.CONF.ticket_plan_start_time_zone)
        return ticket_client

    def _extend_fault_map(self):
        """Extend the Fault Map for Netforce exceptions.

        Map exceptions which are specific to the Netforce Plugin
        to standard HTTP exceptions.

        """
        base.FAULT_MAP.update(self.NETFORCE_FAULT_MAP)

    def _get_credentials(self):
        """
        We use our in house security systems to store the service
        password that programs the switch.
        try:
            return fake_client.get_tacacs_credentials()
        except Exception as e:
            LOG.error('error in getting credentials from fake service.')
            LOG.exception(e)
            raise SystemExit(1)
        """
        return None, None

    def _get_device_driver(self, management_ip, db_username, db_password,
                           os_type):

        # create the device driver
        device_user, device_pass = self._get_device_login(db_username,
                                                          db_password)
        try:
            driver = get_network_driver(self.OS_TYPE_DRIVER_MAP[os_type])
        except Exception as e:
            raise netforce_exc.DeviceDriverNotFound(reason=e.message)

        if CONF.account_in_privileged_mode:
            opt_args = {
                "send_enable": False
            }
        else:
            opt_args = {
                "send_enable": True
            }
        # in any case send config_lock as False
        opt_args['config_lock'] = False
        return driver(management_ip, device_user, device_pass,
                      optional_args=opt_args)

    def _validate_vlan_tag(self, tag):
        validate_non_negative = attributes._validate_non_negative(tag)
        if validate_non_negative:
            return validate_non_negative
        int_tag = int(tag)
        if 1 <= int_tag <= 4096:
            return
        else:
            return _('invalid vlan tag %s. valid values are between 1 '
                     'and 4096') % tag

    def _validate_vlans(self, port):
        '''
        vlans and switch_port_mode should come together always, or not at all.

        :param port:
        :return:
        '''
        if 'vlans' not in port and 'switch_port_mode' not in port:
            return

        if 'vlans' in port and 'switch_port_mode' in port:
            vlans = port['vlans']
            is_native_count = 0
            for vlan_data_dict in vlans:

                if 'vlan' not in vlan_data_dict:
                    return _("vlan data not present in payload")

                if 'id' not in vlan_data_dict['vlan'] and 'tag' not in \
                        vlan_data_dict['vlan'] and 'vpc_name' not in \
                        vlan_data_dict['vlan']:
                    return _("vlan id or tag or vpc_name attribute are "
                             "missing.")

                if 'id' in vlan_data_dict['vlan']:
                    validate_uuid = attributes._validate_uuid(
                        vlan_data_dict['vlan']['id'])
                    if validate_uuid:
                        return validate_uuid

                if 'tag' in vlan_data_dict['vlan']:
                    validate_vlan_tag = self._validate_vlan_tag(
                        vlan_data_dict['vlan']['tag'])
                    if validate_vlan_tag:
                        return validate_vlan_tag

                if 'is_native' in vlan_data_dict['vlan']:
                    validate_is_native = attributes._validate_boolean(
                        vlan_data_dict['vlan']['is_native'])
                    if validate_is_native:
                        is_native_count += 1
                        return validate_is_native
            if is_native_count > 1:
                raise netforce_exc.OnlyOneNativeVlansAllowed()
            return

        # If only one of
        return _("vlans and switch_port_mode should exist together")

    def config_vlan_on_devices(self, bridgegroup, vlan_db):
        for device in bridgegroup.devices:
            device_driver = self._get_device_driver(device.management_ip,
                                                    device.username,
                                                    device.password,
                                                    device.os_type)

            try:
                device_driver.open()
                device_driver.create_vlan(vlan_db.name, vlan_db.tag, True if
                vlan_db.admin_status == constants.ACTIVE else False)
            except Exception as ex:
                raise exceptions.BadRequest(resource='vlan', msg=ex.message)
            finally:
                device_driver.close()

    def _discover_ports_on_device(self, context, device_db):
        device_driver = self._get_device_driver(device_db.management_ip,
                                                device_db.username,
                                                device_db.password,
                                                device_db.os_type)

        port_names_in_db = dict((p.name, p.id) for p in device_db.ports)
        interfaces = {}
        try:
            device_driver.open()
            interfaces = device_driver.get_interfaces()
        except Exception as ex:
            # Getting device interfaces failed is a netforce internal error
            raise netforce_exc.DeviceGetInterfacesError(reason=ex.message)
        finally:
            device_driver.close()

        for iif_name in interfaces:
            is_enabled = interfaces[iif_name]['is_enabled']
            if iif_name in port_names_in_db.keys():
                port = {
                    'admin_status': constants.ACTIVE if is_enabled else
                    netforce_constants.SUSPENDED,
                }
                port['status'] = constants.ACTIVE
                port['status_description'] = \
                    netforce_constants.ACTIVE_STATUS_DESCRIPTION
                self.netforce_model.update_port(context,
                                                port_names_in_db[iif_name],
                                                port)
            else:
                port = {
                    'name': iif_name,
                    'description': 'port for %s' % (iif_name),
                    'admin_status': constants.ACTIVE if is_enabled else
                    netforce_constants.SUSPENDED,
                    'switch_port_mode': netforce_constants.ACCESS_MODE,
                    'device_id': device_db.id,
                    'tenant_id': device_db.tenant_id
                }
                port_db = self.netforce_model.create_port(context, port)
                device_db.ports.append(port_db)

    # CRUD on devices.
    def create_device(self, context, device, **kwargs):
        device = device['device']
        type = device['type']
        device.pop('type', None)
        device_type_db = self.netforce_model.get_devicetype_by_type(context,
                                                                    type)
        device['device_type_id'] = device_type_db.id

        with context.session.begin(subtransactions=True):
            device_db = self.netforce_model.create_device(context, device)
            # We do not need to discover ports on the device.
            # In future, we can get the port details from the
            # device and compare the ones from CMS when doing create port.
            # It's not a problem for now.
            #self._discover_ports_on_device(context, device_db)

        return self.netforce_model.get_device(context, device_db.id)

    # CRUD on device_types
    def create_devicetype(self, context, devicetype, **kwargs):
        devicetype = devicetype['devicetype']
        devicetype_db = self.netforce_model.create_devicetype(
            context, devicetype)
        return self.netforce_model.get_devicetype(context, devicetype_db.id)

    def update_devicetype(self, context, devicetype_id, devicetype):
        devicetype = devicetype['devicetype']
        device_type_db = self.netforce_model.update_devicetype(
            context, devicetype_id, devicetype)
        return self.netforce_model.get_devicetype(context, device_type_db.id)

    def _get_device_login(self, db_username, db_password):

        # Always us db_username and db_password
        device_user = db_username
        device_pass = db_password
        if not device_user:
            # if user not in db, use conf
            if self.username:
                device_user = self.username
            else:
                raise netforce_exc.DeviceLoginCredentialsNotFound(
                    reason="No service_username found")

        if not device_pass:
            # if password not in db, use conf
            if self.password:
                device_pass = self.password
            else:
                raise netforce_exc.DeviceLoginCredentialsNotFound(
                    reason="No service_password found")

        return device_user, device_pass

    def push_vlanportassociation_to_device(self, context, port_id, port):

        # get current port WISB
        current_port_db = self.netforce_model.get_port_db(context, port_id)
        # create the device driver
        device_driver = self._get_device_driver(
            current_port_db.device.management_ip,
            current_port_db.device.username, current_port_db.device.password,
            current_port_db.device.os_type)
        # make the changes in the device using NAPALM
        LOG.debug("device ip %s" % current_port_db.device.management_ip)
        # rollback_data = None
        ticket_num = None
        try:
            device_driver.open()
            device_driver.get_interface_running_config(
                current_port_db.name)
        except Exception as ex:
            LOG.debug("exception %s" % ex)
            self._rollback_vlanport_db(context, port_id, port)

            raise netforce_exc.DeviceError(device_error=ex.message)

        finally:
            device_driver.close()
        try:
            device_driver.open()
            device_driver.update_switch_port_vlans(
                current_port_db.name, port)
            # if update to device is successful , complete the CR as planned.
            # self.complete_cr(ticket_num, commands)

        except ticket_exceptions.ChangeStopActive as ex:
            raise exceptions.BadRequest(resource='port',
                                        msg=ex.message)
        except Exception as ex:
            self._rollback_vlanport_db(context, port_id, port)
            LOG.debug("exception %s" % ex)
            # cancel the ticket ticket if something went wrong at device
            # self.cancel_cr(ticket_num, ex.message)
            raise netforce_exc.DeviceError(device_error=ex.message)
        # not caught exceptions are treated as HTTPInternalServerError
        finally:
            device_driver.close()
        return ticket_num

    @oslo_db_api.wrap_db_retry(retry_on_deadlock=True)
    def _rollback_vlanport_db(self, context, port_id, port):
        # If there is exception, rollback the db change
        vlans = None
        if 'vlans' in port['current_port_data']:
            vlans = port['current_port_data'].pop('vlans', None)
        with context.session.begin(subtransactions=True):
            self.delete_vlanportbinding(context, port_id)
            if vlans:
                for vlan in vlans:
                    self.netforce_model.create_vlanportassociation(
                        context, vlan['vlan']['id'],
                        port_id, vlan['vlan']['is_native_vlan'])
            self.netforce_model.update_port(context, port_id,
                                            port['current_port_data'])

    def delete_vlanportbinding(self, context, port_id):
        # get all the vlans associated to the port to delete
        deleted_vlan_binding = self.netforce_model. \
            delete_vlanportassociation_by_port_id(context, port_id)
        LOG.debug("Successfully deleted %s vlan bindings for the port" %
                  deleted_vlan_binding)

    def create_port(self, context, port, **kwargs):
        # FIXME: This now only updates DB, but we should update device, too.
        # Otherwise, WISB & WIRI doesn't match, which can cause problem e.g.
        # during next vlan mode change, because old switch_port_mode may be
        # wrong. We will support this when device onboarding mechanism is
        # clear.
        port_db = self.netforce_model.create_port(context, port['port'])
        return self.make_port_dict(port_db)

    def _update_vlan_association(self, context, port_id, port):
        # This function creates vlanportassociation and also converts vlan data
        # in tags. e.g. even if we pass vpc_name and id in the payload,
        # it should convert to tags as device should always be passed with tags
        # It is possible that within the same vlan payload, one can pass tags
        # id, vpc_name too. However, if tag is there we just use it.
        vlans = port['vlans']

        # flush old association
        self.delete_vlanportbinding(context, port_id)

        for vlan in vlans:
            vlan_data = vlan['vlan']
            is_native = False
            if 'is_native' in vlan_data:
                is_native = attributes.convert_to_boolean_if_not_none(
                    vlan_data['is_native'])
            vlan_data['is_native'] = is_native
            if 'tag' in vlan_data:
                # If tag is in payload use as is, post db validation.
                vlan_db = self.netforce_model.get_vlan_by_tag_and_port_id(
                    context, vlan_data['tag'], port_id)
                if not vlan_db:
                    msg = "vlan_tag %s does not exist" % vlan_data['tag']
                    raise exceptions.BadRequest(resource='port', msg=msg)
            else:
                if 'id' in vlan_data:
                    # If id is present, get the corresponding vlan tag.
                    vlan_db = self.netforce_model.get_vlan(context,
                                                           vlan_data['id'])
                    if not vlan_db:
                        msg = "vlan_id %s does not exist" % vlan_data['id']
                        raise exceptions.BadRequest(resource='port', msg=msg)
                    vlan_data["tag"] = vlan_db['tag']
                    vlan_data.pop('id')
                elif 'vpc_name' in vlan_data:
                    # If vpc is present, get the corresponding vlan tag.
                    vlan_db = self.netforce_model.\
                        get_vlan_by_vpc_name_and_port_id(context,
                                                         vlan_data['vpc_name'],
                                                         port_id)
                    if not vlan_db:
                        msg = "vpc_name %s does not exist" % \
                              vlan_data['vpc_name']
                        raise exceptions.BadRequest(resource='port',
                                                    msg=msg)
                    vlan_data["tag"] = vlan_db.tag
                    vlan_data.pop('vpc_name')

                else:
                    raise exceptions.BadRequest(tag=vlan_data)

            if vlan_db:
                vlan_id = vlan_db['id']
            else:
                raise exceptions.NotFound(tag=vlan_db)
            # create vlan and port association
            self.netforce_model.create_vlanportassociation(context, vlan_id,
                                                           port_id, is_native)

    def _enable_disable_port(self, context, port_id, set_availability):

        # get current port WISB
        current_port_db = self.netforce_model.get_port_db(context, port_id)
        # create the device driver
        device_driver = self._get_device_driver(
            current_port_db.device.management_ip,
            current_port_db.device.username, current_port_db.device.password,
            current_port_db.device.os_type)
        # make the changes in the device using NAPALM
        LOG.debug("device ip %s", current_port_db.device.management_ip)
        # rollback_data = None

        try:
            device_driver.open()
            device_driver.get_interface_running_config(
                current_port_db.name)
        except Exception as ex:
            LOG.debug("exception %s", ex)
            raise ex

        finally:
            device_driver.close()
        # requester_login = context.user_name
        ticket_num = None
        try:
            device_driver.open()
            if set_availability == netforce_constants.ENABLE_PORT:
                device_driver. enable_interface(
                    current_port_db.name)
            elif set_availability == netforce_constants.DISABLE_PORT:
                device_driver.disable_interface(
                    current_port_db.name)
            # self.complete_cr(ticket_num, commands)
        except ticket_exceptions.ChangeStopActive as ex:
            raise exceptions.BadRequest(resource='port',
                                        msg=ex.message)

        except ebay_exceptions.PostChangeValidationException as ex:
            # ROllback the device config to previous config
            if set_availability == netforce_constants.ENABLE_PORT:
                device_driver.\
                    disable_interface_on_device(current_port_db.name)
            elif set_availability == netforce_constants.DISABLE_PORT:
                device_driver.\
                    enable_interface_on_device(current_port_db.name)
            # Finally cancel the ticket ticket.
            # self.cancel_cr(ticket_num, ex.message)
            raise netforce_exc.DevicePostChangeValidationError(
                reason=ex.message)

        except Exception as ex:
            LOG.debug("exception %s", ex)
            # cancel the ticket ticket if something went wrong at device
            # self.cancel_cr(ticket_num, ex.message)
            raise ex
        # not caught exceptions are treated as HTTPInternalServerError
        finally:
            device_driver.close()
        return ticket_num

    @oslo_db_api.wrap_db_retry(retry_on_deadlock=True)
    def update_port(self, context, port_id, port, **kwargs):

        port = port['port']
        ma1 = port.pop('mac_address', None)
        # using this port copy to avoid unhashable dict error since port
        # update needs no vlan tag.
        port_copy = port.copy()

        message = self._validate_vlans(port)
        if message:
            raise exceptions.BadRequest(resource='port', msg=message)
        vlans = port.pop('vlans', None)
        # Port enable/disable and port flip is ideally not good to do in one
        # shot as per updates from net engg.
        if vlans and 'admin_status' in port:
            raise netforce_exc.\
                PortFlipAndPortEnableDisableNotSupportedAtSameTime(
                    operation="Flip Vlan and enable/disable port ")
        # get current port WISB
        current_port_db = self.netforce_model.get_port_db(context, port_id)

        # create the device driver
        device_driver = self._get_device_driver(
            current_port_db.device.management_ip,
            current_port_db.device.username, current_port_db.device.password,
            current_port_db.device.os_type)

        old_admin_status = current_port_db.admin_status

        def _check_mac(mac, interface_name, native_vlan=None):
            try:
                device_driver.open()
                macs = device_driver.get_mac_addresses_on_interface(
                    current_port_db.name, native_vlan)
                macs = [netaddr.EUI(m['mac_address']) for m in macs]
                if not macs:
                    return
                if not netaddr.EUI(mac) in macs:
                    raise netforce_exc.MacAddressNotFoundOnInterface(
                                         mac=mac,
                                         interface=interface_name)
            finally:
                device_driver.close()

        def _validate_mac_address(mac):
            native_vlan = None
            vpss = self.netforce_model._get_vlanportassociation_by_port_id(
                          context, port_id)
            for vps in vpss:
                if vps.is_native_vlan:
                    native_vlan = vps.vlan.tag
                    break

            if not native_vlan:
                raise netforce_exc.NoNativeVlan(
                            reason='can not validate mac address')
            _check_mac(mac, current_port_db.name, native_vlan)

        with context.session.begin(subtransactions=True):
            # update the port model.
            # Copy current port and vlanport data for rollback
            port_copy['current_port_data'] = self.make_port_dict(
                current_port_db)
            self.netforce_model.update_port(context, port_id, port)

            # vlan tag/untagging in model
            if vlans:

                self._update_vlan_association(context, port_id, port_copy)
            # TODO(hzhou8): maybe we can try to optimize to a single device
            # push.
            # admin status update
            if 'admin_status' in port and \
                old_admin_status != port['admin_status']:
                # If mac address is not passed for port shut/no_shut
                # operations raise error.
                if not attributes.is_attr_set(ma1):
                    raise netforce_exc.MacAddressNotPassed(
                        interface=current_port_db.name)
                # only call enable/disable device if WISB is mismatch
                check_mac = kwargs.get('check_mac')
                # check_cms = kwargs.get('check_cms')
                if check_mac or check_mac is None:
                    _check_mac(ma1, current_port_db.name)
                # Before doing any operation, check cms for the asset server
                if port['admin_status'] == constants.ACTIVE:
                    # No need to worry about asset status while enabling
                    # the port.
                    self._enable_disable_port(
                        context, port_id, netforce_constants.ENABLE_PORT)

                elif port['admin_status'] == netforce_constants.SUSPENDED:
                    # TODO(aginwala): As discussed with net engg, only check
                    # cms if link state is up.
                    # Asset status should be either decomm or SACheck in cms.
                    self._enable_disable_port(
                        context, port_id, netforce_constants.DISABLE_PORT)

            # label update
            if 'label' in port:
                try:
                    device_driver.open()
                    device_driver.update_interface_label(current_port_db.name,
                                                         port['label'])
                except ebay_exceptions.PostChangeValidationException as ex:
                    raise netforce_exc.DevicePostChangeValidationError(
                        reason=ex.message)
                except ebay_exceptions.EntityDoesNotExistsException as ex:
                    raise exceptions.BadRequest(resource='port',
                                                msg=ex.message)
                finally:
                    device_driver.close()
        context.session.expire_all()
        # vlan tagging/untagging.
        port_dict = self.make_port_dict(self.netforce_model.get_port_db(
            context, port_id))
        if vlans:
            if attributes.is_attr_set(ma1):
                _validate_mac_address(ma1)
            # push changes to device.
            ticket_num = self.push_vlanportassociation_to_device(context,
                                                                 port_id,
                                                                 port_copy
                                                                 )
            port_dict['ticket'] = ticket_num
        return port_dict

    def _find_vlan_by_vpc_and_bg(self, context, vpc, bridge_group):
        vlans_on_bg = bridge_group.vlans
        for vlan in vlans_on_bg:
            if vlan.vpc and vlan.vpc.name == vpc.name:
                bg_name = bridge_group.name
                # In case the vlan is already created on the device,
                # return 201 along with tag.
                LOG.warn('Vlan is already configured for BG %s for vpc %s'
                         % (bg_name, vlan.vpc.name))
                vlan_dict = self.netforce_model.get_vlan(context, vlan.id)
                return vlan_dict
        return None

    def _check_duplicate_vlans_on_bridge_group(
            self, context, bridge_group, requested_vlan_dict):
        vlans_on_bg = bridge_group.vlans
        bg_name = bridge_group.name
        # check if vlan exists for a bg and has same name and tag.
        # If there is mismatch, return error.
        for vlan in vlans_on_bg:
            if vlan.name == requested_vlan_dict['name'] and \
                            vlan.tag == requested_vlan_dict['tag']:
                bg_name = bridge_group.name
                LOG.warn('Vlan %s is already configured for BG %s with tag %s'
                         % (vlan.name, bg_name, vlan.tag))
                vlan_dict = self.netforce_model.get_vlan(context, vlan.id)
                return vlan_dict
            elif vlan.name == requested_vlan_dict['name'] and vlan.tag !=\
                    requested_vlan_dict['tag']:
                raise netforce_exc.ConfiguredVlanConflictsWithRequested(
                    current=vlan.tag, requested=requested_vlan_dict['tag'],
                    key=bg_name)
            elif vlan.name != requested_vlan_dict['name'] and vlan.tag == \
                    requested_vlan_dict['tag']:
                raise netforce_exc.ConfiguredVlanConflictsWithRequested(
                    current=vlan.name, requested=requested_vlan_dict['name'],
                    key=bg_name)

    def _check_vlan_mismatch(self, vlan_db, vlan_req):
        for k, v in vlan_db.iteritems():
            if k in vlan_req and v != vlan_req[k]:
                raise netforce_exc.ConfiguredVlanConflictsWithRequested(
                    current=vlan_db[k], requested=vlan_req[k], key=k)

    def create_vlan(self, context, vlan, **kwargs):
        if not cfg.CONF.enable_vlan:
            raise netforce_exc.OperationNotSupported(operation="Create Vlan")
        vlan = vlan['vlan']
        requested_vlan_dict = vlan.copy()
        vpc_name = vlan.pop('vpc_name', None)
        bridgegroup_name = vlan.pop('bridge_group_name')
        bridgegroup = self.netforce_model. \
            get_bridgegroup_by_name(context,
                                    bridgegroup_name)
        # check if bridgegroup have devices
        if len(bridgegroup.devices) == 0:
            raise netforce_exc.NoDevicesAssociatedToBridgeGroup(
                bridge_group_name=bridgegroup.name)
        vpc_db = None
        if vpc_name:
            vpc_db = self.netforce_model.get_vpc_by_name(context, vpc_name)
            if not vpc_db:
                raise netforce_exc.VPCNotConfigured(vpc=vpc_name)

            vlan_dict = self._find_vlan_by_vpc_and_bg(
                context, vpc_db, bridgegroup)

        else:
            vlan_dict = self._check_duplicate_vlans_on_bridge_group(
                context, bridgegroup, requested_vlan_dict)
        if vlan_dict:
            return vlan_dict
        # create vlans on each device associated to the bg
        with context.session.begin(subtransactions=True):
            vlan_db = self.netforce_model.create_vlan_by_bg_and_vpc(
                context, vlan, bridgegroup, vpc_db)
        return self.make_vlan_dict(vlan_db)

    #TODO(kugandhi). To be implemented as part of a separate ticket
    def _delete_vlan_on_device(self, vlan_tag):
        pass

    #TODO(kugandhi). To be implemented as part of a separate ticket
    def _validate_vlan_delete(self, context, vlan_id):
        return True

    @transaction
    def delete_vlan(self, context, vlan_id):
        vlan_db = super(NetForcePlugin, self).get_vlan_db(context, vlan_id)
        if self._validate_vlan_delete(context, vlan_id):
            vlan_dict = {
                "status": constants.PENDING_DELETE
            }
            super(NetForcePlugin, self). \
                update_vlan(context, vlan_id, vlan_dict)
            try:
                self._delete_vlan_on_device(vlan_db.tag)
                return super(NetForcePlugin, self).get_vlan(context, vlan_id)
            except Exception as ex:
                bad_request = exceptions.BadRequest(resource='vlan',
                                                    msg=ex.message)
                raise netforce_exc.DeviceConfigPushFailure(bad_request,
                                                           vlan_db.id)

    def create_bridgegroup(self, context, bridgegroup, **kwargs):
        bg_db = self.netforce_model.create_bridgegroup(
            context, bridgegroup['bridgegroup'])
        return self.make_bridgegroup_dict(bg_db)

    def create_vpc(self, context, vpc, **kwargs):
        vpc_db = self.netforce_model.create_vpc(context, vpc['vpc'])
        return self.make_vpc_dict(vpc_db)

    def _get_overlapping_subnet(self, context, cidr):
        subnet_dbs = self.netforce_model.get_subnets(context)
        ipnetwork_a = netaddr.IPNetwork(cidr)
        for s in subnet_dbs:
            ipnetwork_b = netaddr.IPNetwork(s['cidr'])
            if ipnetwork_a.prefixlen < ipnetwork_b.prefixlen:
                if ipnetwork_b in ipnetwork_a:
                    return s
            else:
                if ipnetwork_a in ipnetwork_b:
                    return s
        return None

    def _validate_subnet_is_allowed(self, cidr):
        allowed = cfg.CONF.allowed_subnet
        IPNetwork = netaddr.IPNetwork
        if not IPNetwork(cidr) in IPNetwork(allowed):
            raise netforce_exc.SubnetIsNotAllowed(requested=cidr,
                                                  allowed=allowed)

    def _generate_udns_A_record_name(self, vlan_number, device_name):
        '''primary gateway (or TOR) will get all reservations assigned to it

            format: vlan{{VLAN_NUMBER}}-gw-{{DEVICE_NAME}}
        '''
        ret = "vlan%s-gw-%s" % (vlan_number, device_name)
        return ret

    def _get_reserved_ip_addrs_list(self, cidr, reserve_ip_count):
        net = netaddr.IPNetwork(cidr)
        ip_addrs = []
        for i in range(1, reserve_ip_count + 1):
            ip_addrs.append(str(netaddr.IPAddress(net.first + i)))

        return ip_addrs

    def create_udns_records_for_subnet(self, vpc, cidr,
                                       reserve_ip_count,
                                       hostname):
        LOG.info('create UDNS records for subnet: vpc %s, '
                 'cidr %s, hostname %s', vpc, cidr, hostname)

    def _check_subnet_mismatch(self, subnet_db, subnet_req):
        for k, v in subnet_db.iteritems():
            if k in subnet_req and v != subnet_req[k]:
                raise netforce_exc.ConfiguredSubnetConflictsWithRequested(
                    current=subnet_db[k], requested=subnet_req[k], key=k)

    def create_subnet(self, context, subnet, **kwargs):
        if not cfg.CONF.enable_subnet:
            raise netforce_exc.OperationNotSupported(operation="Create Subnet")
        skip_device = kwargs.get('skip_device')
        patch_primary = kwargs.get('patch_primary_junos_subnets')
        one_subnet_only = kwargs.get('one_subnet_only')
        subnet = subnet['subnet']
        self._validate_cidr_format(subnet['cidr'])
        reserve_ip_count = CONF.reserve_ip_count
        if 'reserve_ip_count' in subnet:
            reserve_ip_count = subnet.pop('reserve_ip_count', None)
        self._validate_subnet_is_allowed(subnet['cidr'])
        # If subnet is already created, just return the existing subnet dict.
        # Skip the over-lapping check.
        subnet_db = self.netforce_model.get_subnet_by_cidr(context,
                                                       subnet['cidr'])
        if subnet_db:
            # In case the subnet is already created on the device,
            # return 201.
            LOG.warn("subnet %s is already configured on vlan %s" %
                     (subnet_db['cidr'], subnet_db['vlan_id']))
            # If subnet already exists, return subnet dictionary.
            # Compare requested dict with db dict. Raise error in case
            # of mismatch.
            subnet_dict = self.netforce_model.get_subnet(context,
                                                         subnet_db['id'])
            self._check_subnet_mismatch(subnet_dict, subnet)
            return subnet_dict
        if not patch_primary and not skip_device:
            if reserve_ip_count < CONF.reserve_ip_count:
                raise \
                    netforce_exc.GivenReserveIPCountLessThanDefaultCount(
                        reserve_ip_count=reserve_ip_count,
                        default_count=CONF.reserve_ip_count)
            subnet_db = self._get_overlapping_subnet(context,
                                                     subnet['cidr'])
            if subnet_db:
                raise netforce_exc.SubnetAlreadyConfigured(
                    cidr=subnet['cidr'],
                    existing_cidr=subnet_db['cidr'],
                    vlan=subnet_db['vlan_id'],
                    id=subnet_db['id'])

        with context.session.begin(subtransactions=True):

            subnet_db = self.netforce_model.create_subnet(context,
                                                          subnet)

            subnet_dict = self.netforce_model.get_subnet(context,
                                                         subnet_db.id)
            # For static subnet import from CMS, we skip adding subnet
            # to device.
            if skip_device:
                return subnet_dict
            associated_vlan = subnet_db.vlan
            vpc = associated_vlan.vpc.name
            if vpc not in CONF.allowed_vpcs:
                LOG.error("create subnet is not supported for vpc %s" % vpc)
                raise netforce_exc.OperationNotSupported(
                    operation="Create Subnet")

            associated_devices = associated_vlan.bridgegroup.devices
            if len(associated_devices) > 1:
                raise netforce_exc.OnlyOneDeviceAllowedForTorBridgeGroup(
                            bridge_group=associated_vlan.bridgegroup.name)
            elif len(associated_devices) < 1:
                raise netforce_exc.NoDeviceFound(
                            bridge_group=associated_vlan.bridgegroup.name)

            device = associated_devices[0]
            if device.device_type.type != netforce_constants.SWITCH_TYPE_TORS:
                raise netforce_exc.BadDeviceType(type=device.device_type.type)
            # cidr = subnet_db.cidr
            subnet_cidr = subnet_db['cidr']
            if not patch_primary:
                #hostname = self._generate_udns_A_record_name(
                #                  associated_vlan.tag,
                #                  device.name.split('.')[0])
                # Before configuring a new subnet, please check your dns
                # systems if a/ptr records exists.
                # self._check_udns_record_available(vpc, cidr,
                #                                  reserve_ip_count,
                #                                  hostname)
                # pre-validation before subnet push
                try:
                    self._validate_subnet_push(
                        context, device, subnet_cidr,
                        netforce_constants.VALIDATION_TYPE_PRE,
                        associated_vlan)
                except Exception as ex:
                    LOG.error("Create subnet pre-validation failed: %s" %
                              ex.message)
                    raise ex

            self._configure_subnet_on_device(
                context, associated_vlan, device, subnet_db, patch_primary,
                one_subnet_only)

            if not patch_primary:
                # post-validation post subnet push
                try:
                    self._validate_subnet_push(
                        context, device, subnet_cidr,
                        netforce_constants.VALIDATION_TYPE_POST,
                        associated_vlan)

                except Exception as ex:
                    # Actually delete the subnet on the device in case of any
                    # failures to skip any networking error.
                    LOG.error('create subnet %s post-validation failed: %s' %
                              (subnet, ex.message))
                    try:
                        self._delete_subnet_on_device(
                            associated_vlan, device, subnet_db)
                    except netforce_exc.DeviceError as del_ex:
                        LOG.error('Delete subnet failed during rollback:'
                                  ' vlan %s, device %s, subnet_db %s,'
                                  ' ex message: %s'
                                  % (associated_vlan, device, subnet_db,
                                     del_ex))

                    raise netforce_exc.DevicePostChangeValidationError(
                        reason=ex.message)

            # Allocate first 10 IP as a part of subnet creation as per mandate
            # from network engineering.
            self._set_allocation_range(context, subnet_db, subnet_dict,
                                       reserve_ip_count)
        return subnet_dict

    def _check_ticket_route(self, device_list, gw_ip):
        max_hops = str(cfg.CONF.ticketroute_max_hops)
        ticketroute = subprocess.Popen(["ticketroute", '-m', max_hops,
                                       gw_ip],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)
        iter_ticketroute = iter(ticketroute.stdout.readline, "")
        next(iter_ticketroute)
        for route in iter_ticketroute:
            for device_name in device_list:
                if device_name in route:
                    return True
        return False

    def _validate_bubble_device_health(self, bubble_device_db_list):
        if not bubble_device_db_list:
            return []

        device_ips = []
        for bubble_device in bubble_device_db_list:
            device_ips.append(bubble_device.management_ip)
        healthy_bubble_devices = []
        return healthy_bubble_devices

    def _get_pingable_bubble_device_(self, device_list):
        # pick any one of the 12 bubble device ip.
        if not device_list:
            return None
        bubble_device = random.choice(device_list)
        device_ip = bubble_device.management_ip
        response = os.system("ping -c 2 " + device_ip)
        if response == 0:
            return bubble_device
        else:
            device_list.remove(bubble_device)
            return self._get_pingable_bubble_device_(device_list)

    def _validate_subnet_push(self, context, device, subnet_cidr,
                              validation_type, vlan):
        device_type_db = self.netforce_model.get_devicetype_by_type(
            context, netforce_constants.SWITCH_TYPE_DISTRIBUTION)

        bubble_device_db_list = self.netforce_model.\
            get_devices_by_type_and_bubble_id(context, device_type_db['id'],
                                              device.bubble_id)

        if not bubble_device_db_list:
            raise netforce_exc.NoBubbleDevicesConfigured()

        def _check_health_and_pick_bubble_devices():
            # Pick a pingable bubble device.
            bubble_device = self._get_pingable_bubble_device_(
                bubble_device_db_list)
            # if bubble_device is None:
            #    raise netforce_exc.AllBubbleDevicesAreDown(
            #        bubble_devices=all_bubble_devices_ip)
            return bubble_device

        bubble_device = _check_health_and_pick_bubble_devices()

        bubble_device_driver = self. \
            _get_device_driver(bubble_device.management_ip,
                               bubble_device.username,
                               bubble_device.password,
                               bubble_device.os_type)
        # get the vrf_name
        vrf_db = self.netforce_model.get_vrf_by_bubble_id_and_vpc_id(
            context, bubble_device.bubble_id, vlan.vpc_id)
        # TODO(aginwala): Make sure to have correct validation in case vrf is
        # not onboarded in netforce even-though bubble has vrfs.
        vrf_name = None
        if vrf_db:
            vrf_name = vrf_db[0]['name']
        # check bubble device for cidr.
        try:
            bubble_device_driver.open()
            device_cidr_list = bubble_device_driver.get_routes(vrf_name)
        except Exception as ex:
            raise netforce_exc.DeviceError(device_error=ex.message)
        finally:
            bubble_device_driver.close()

        # Note: As per consent by net-engg, we donot need ticketroute check.
        self._check_cidr_overlap_on_bubble(subnet_cidr, device_cidr_list,
                                           bubble_device.management_ip,
                                           validation_type)

    def _validate_ticket_route(self, bubble_device_name_list, gw_ip,
                              subnet_cidr, validation_type, device_name):
        # Pre-validation for ticketroute should resolve to any of the bubble
        # devices.
        if validation_type == netforce_constants.VALIDATION_TYPE_PRE:
            if not self._check_ticket_route(bubble_device_name_list, gw_ip):
                LOG.error('ticketroute does not resolve to any of the'
                          ' bubble devices %s for new cidr %s:' %
                          (bubble_device_name_list, subnet_cidr))
                raise netforce_exc.ticketRouteDoesNotResolve(
                    cidr=subnet_cidr, device_list=bubble_device_name_list)
            LOG.info('ticketroute resolves to given bubble devices %s for'
                     ' the new cidr %s' % (bubble_device_name_list,
                                           subnet_cidr))

        # post-validation for ticketroute should resolve to the TOR switch
        # where subnet is getting configured.
        elif validation_type == netforce_constants.VALIDATION_TYPE_POST:
            # Here make sure that we check ticketroute for GW IP and not rely
            # on DNS creation for TOR with this GW_IP.
            if not self._check_ticket_route([gw_ip], gw_ip):
                LOG.error('ticketroute does not resolve to given TOR device %s'
                          ' for the new cidr %s:' % (device_name, subnet_cidr))
                raise netforce_exc.ticketRouteDoesNotResolve(
                    cidr=subnet_cidr, device_list=bubble_device_name_list)
            LOG.info('ticketroute resolves to given TOR device %s for the new'
                     ' cidr %s:' % (device_name, subnet_cidr))

    def _validate_cidr_format(self, subnet_cidr):
        # first of all check whether given cidr is valid
        # if its not valid, just throw error
        try:
            netaddr.IPNetwork(subnet_cidr)
        except Exception as ex:
            raise netforce_exc.InvalidSubnetCIDR(message=ex.message,
                                                 cidr=subnet_cidr)

    def _check_cidr_overlap_on_bubble(self, subnet_cidr, device_cidr_list,
                                      management_ip, validation_type):
        # below logic checks both superblock and subblock;
        # e.g. say if subnet on bubble is 10.0.0.0/22 and request is
        # 10.0.0.0/24, it will return True . Also if other way around,
        # it returns True even for smaller CIDRs
        net1 = ipaddr.IPNetwork(subnet_cidr)
        is_new_cidr_pushed = False
        if device_cidr_list:
            for cidr in device_cidr_list:
                net2 = ipaddr.IPNetwork(cidr)
                # The default route in Internet Protocol Version 4 (IPv4) is
                # designated as the zero-address 0.0.0.0/0. Hence, We need to
                # ignore it since it will always overlap with any subnet CIDR.
                if cidr == '0.0.0.0/0' or not net1.overlaps(net2)\
                        or cidr == '10.0.0.0/8':
                    continue
                elif validation_type == \
                        netforce_constants.VALIDATION_TYPE_PRE:
                    raise netforce_exc.SubnetAlreadyConfiguredOnBubble(
                        cidr=subnet_cidr, existing_cidr=cidr,
                        device_ip=management_ip)
                elif validation_type == \
                        netforce_constants.VALIDATION_TYPE_POST:
                    if cidr == subnet_cidr:
                        is_new_cidr_pushed = True
                else:
                    message = "Call check overlapping with either pre or" \
                              " post validations."
                    raise exceptions.BadRequest(resource='subnet',
                                                msg=message)

        if validation_type == netforce_constants.VALIDATION_TYPE_POST:
            if not is_new_cidr_pushed:
                LOG.error("New cidr %s is not reflecting on the bubble"
                          " devices" % subnet_cidr)
                raise netforce_exc.NewSubnetCIDRNotReflectingOnBubble(
                    cidr=subnet_cidr, device_ip=management_ip)
            else:
                LOG.info('New Subnet CIDR %s is visible on bubble %s' % (
                    subnet_cidr, management_ip))

    def _configure_subnet_on_device(self, context, vlan, device, subnet_db,
                                    patch_primary,
                                    one_subnet_only):
        subnet_cidr = subnet_db['cidr']
        inet = netaddr.IPNetwork(subnet_cidr)
        gw_ip_mask = '%s/%s' % (subnet_db['gateway_ip'], inet.prefixlen)

        # Now connect with TOR switch.
        device_driver = self. \
            _get_device_driver(device.management_ip,
                               device.username,
                               device.password,
                               device.os_type)
        try:
            device_driver.open()
            vlan_l3_interface_name = device_driver.get_vlan_interface_name(
                vlan.tag)
            device_driver.get_ip_addrs_on_interface(vlan_l3_interface_name)
            #requester_login = context.user_name
            # Use org specific ticketing system REST API since each change
            # on the device needs to have a valid CR.
            #ticket_num = self.create_subnet_cr(
            #    subnet_db.vlan_id, device.management_ip, subnet_db.cidr,
            #    rollback_data, requester_login)
            # Only support patching primary statement for Junos TORs
            if patch_primary and device.os_type == 'junos':
                device_driver.set_subnet_primary(
                    gw_ip_mask, vlan.tag, one_subnet_only)
            else:
                device_driver.create_subnet(gw_ip_mask, vlan.tag)
            # self.complete_cr(ticket_num, commands)
        except ebay_exceptions.PostChangeValidationException as ex:
            # For any device operation failure, cancel the Change ticket
            # self.cancel_cr(ticket_num, ex.message)
            raise netforce_exc.DevicePostChangeValidationError(
                reason=ex.message)
        except ebay_exceptions.EntityDoesNotExistsException as ex:
            # For any device operation failure, cancel the Change ticket
            # self.cancel_cr(ticket_num, ex.message)
            raise exceptions.BadRequest(resource='subnet',
                                        msg=ex.message)
        except ticket_exceptions.ChangeStopActive as ex:
            raise exceptions.BadRequest(resource='subnet',
                                        msg=ex.message)
        except Exception as ex:
            # For any device operation failure, cancel the Change ticket
            # self.cancel_cr(ticket_num, ex.message)
            raise netforce_exc.DeviceError(device_error=ex.message)

        finally:
            device_driver.close()

    def _delete_subnet_on_device(self, vlan, device, subnet_db):
        subnet_cidr = subnet_db['cidr']
        inet = netaddr.IPNetwork(subnet_cidr)
        gw_ip_mask = '%s/%s' % (subnet_db['gateway_ip'], inet.prefixlen)
        # Now connect with TOR switch.
        device_driver = self. \
            _get_device_driver(device.management_ip,
                               device.username,
                               device.password,
                               device.os_type)
        try:
            device_driver.open()
            commands = device_driver.delete_subnet_on_device(gw_ip_mask,
                                                             vlan.tag)
            LOG.info("Successfully deleted subnet %s with commands: %s" %
                     (subnet_cidr, commands))
        except Exception as ex:
            LOG.error('Unable to delete subnet %s on device %s due '
                      'to eror: %s' % (subnet_cidr,
                                       device,
                                       ex.message))
            raise netforce_exc.DeviceError(device_error=ex.message)

        finally:
            device_driver.close()

    def _set_allocation_range(self, context, subnet_db, subnet_dict,
                              reserve_ip_count):
        inet = netaddr.IPNetwork(subnet_db['cidr'])
        # We will not support smaller subnet .e.g. if request comes in to
        #  create /31 or /32, we throw error
        if len(inet) < reserve_ip_count:
            message = "CIDR %s cannot be pushed to devices since we donot" \
                      " support subnet creation for smaller subnets." % \
                      subnet_db['cidr']
            raise netforce_exc.SmallSubnetNotAllowed(reason=message)
        # e.g. if cidr is 10.x.x.0/24 and reserve_ip_count = 10,
        #  first_ip = 10.x.x.0 + 10 + 1 where first IP is always reserved
        #  for GW.
        first_ip = str(inet.ip + reserve_ip_count + 1)
        last_ip = str(inet.ip + (len(inet) - 1))
        subnet_dict['start_ip'] = first_ip
        subnet_dict['end_ip'] = last_ip
        subnet_data = {"start_ip": first_ip, 'end_ip': last_ip}
        self.netforce_model.update_subnet(context, subnet_db.id, subnet_data)

    def get_port(self, context, port_id, fields=None):
        # this method is used to check wiri data of port.
        current_port_db = self.netforce_model.get_port_db(context, port_id)
        port_dict = self.make_port_dict(current_port_db, fields=None)

        if fields and 'check_device' in fields:
            # create the device driver
            device_driver = self._get_device_driver(
                current_port_db.device.management_ip,
                current_port_db.device.username,
                current_port_db.device.password,
                current_port_db.device.os_type)
            port_name = current_port_db.name

            try:
                device_driver.open()
                port_data = device_driver.get_interfaces_by_name([port_name])
                port_vlan_data = device_driver.get_vlans_on_interface(
                    port_name)

            except ebay_exceptions.EntityDoesNotExistsException as ex:
                raise exceptions.BadRequest(resource='port',
                                            msg=ex.message)
            except Exception as ex:
                raise netforce_exc.DeviceError(msg=ex.message)

            finally:
                device_driver.close()

            port_data = port_data.pop(port_name, None)
            status = 'enabled' if port_data['is_enabled'] else 'disabled'
            description = port_data['description']
            native_vlan = None
            vlan_tags = []
            device_switch_port_mode = None
            if port_vlan_data.get('access_vlan', None):
                vlan_tags = port_vlan_data['access_vlan']
            if port_vlan_data.get('native_vlan', None):
                native_vlan = port_vlan_data['native_vlan']
            if port_vlan_data.get('trunk_vlans', None):
                vlan_tags = port_vlan_data['trunk_vlans']
            if port_vlan_data.get('switch_port_mode', None):
                device_switch_port_mode = port_vlan_data['switch_port_mode']
            if not isinstance(vlan_tags, list):
                vlan_tags = vlan_tags.split(',')
            vlan_tags = self._parse_vlan_range(vlan_tags)
            vlan_tags = sorted(vlan_tags)
            device_port_vlan_dict = self._make_get_port_dict(
                port_id, port_name, native_vlan, vlan_tags,
                device_switch_port_mode, status, description,
                context.tenant_id, current_port_db, fields=None)
            # compare the wiri and wisb. If mismatch, return entire wiri
            #  data as sub dict.
            if device_port_vlan_dict != port_dict:
                port_dict['device_data'] = device_port_vlan_dict
        # if wiri is not set, return the wisb data
        return port_dict

    def _parse_vlan_range(self, vlan_members):
        # Iterate the members and parse '-' and get the range of vlan members.
        # e.g. vlan members = ['51-60']. Convert it to ['51', '52'..]
        all_members = []
        for mem in vlan_members:
            if '-' in mem:
                vlan_range = mem.split('-')
                for i in range(int(vlan_range[0]), int(vlan_range[1]) + 1):
                    all_members.append(int(i))
            else:
                all_members.append(int(mem))
        return all_members

    def create_bubble(self, context, bubble, **kwargs):
        bubble_db = self.netforce_model.create_bubble(
            context, bubble['bubble'])
        return self.make_bubble_dict(bubble_db)

    def update_bubble(self, context, bubble_id, bubble):
        bubble = bubble['bubble']
        bubble_db = self.netforce_model.update_bubble(
            context, bubble_id, bubble)
        return self.make_bubble_dict(bubble_db)

    def create_vrf(self, context, vrf, **kwargs):
        vrf_db = self.netforce_model.create_vrf(
            context, vrf['vrf'])
        return self.make_vrf_dict(vrf_db)

    def update_vrf(self, context, vrf_id, vrf):
        vrf = vrf['vrf']
        vrf_db = self.netforce_model.update_vrf(
            context, vrf_id, vrf)
        return self.make_vrf_dict(vrf_db)
