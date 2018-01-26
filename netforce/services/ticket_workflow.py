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


from netforce.api_client import ticket_api_client
from neutron.common import exceptions
from oslo_config import cfg
from oslo_log import log as logging
LOG = logging.getLogger(__name__)


CONF = cfg.CONF
CR_TYPE_VLAN = "VLAN"
CR_TYPE_PORT = "Port"
CR_TYPE_SUBTYPE_MAP = {CR_TYPE_PORT: "Port_Modify_Auto",
                       CR_TYPE_VLAN: "Create Subnet Auto"
                       }


def create_and_mark_cr_inprogress(auto_cr):
    ticket_work_flow = ticketWorkFlow()

    def create_cr(*args, **kwargs):
        ticket_data = auto_cr(*args, **kwargs)
        try:
            ticket_client = ticket_work_flow.get_ticket_client()
            ticket_resp = ticket_client.create_ticket(
                ticket_data['verification_plan'],
                ticket_data['busines_justification'],
                ticket_data['action_plan'], ticket_data['site_components'],
                ticket_data['rollback_plan'], ticket_data['requester_login'],
                ticket_data['cr_type'], ticket_data['cr_subtype'])
            ticket_num = ticket_resp.get('result', None)
            if not ticket_num:
                message = "No ticket Number returned from ticket."
                raise exceptions.BadRequest(resource='port', msg=message)
            LOG.debug("Created Auto CR %s" % ticket_num)
        except Exception as ex:
            LOG.debug("Exception while creating CR is %s" % ex)
            raise exceptions.BadRequest(resource='port',
                                        msg=ex.message)
        # Take the CR to ReadyToStart after create
        # Also no need to error out in case of update.
        ticket_status = "ReadyToStart"
        ticket_work_flow.update_cr(ticket_num, ticket_status,
                                 commands=None, close_code=None)

        return ticket_num
    return create_cr


class ticketWorkFlow(object):

    def get_ticket_client(self):
        ticket_client = ticket_api_client.ticketApiClient(
            cfg.CONF.ticket_service_url, cfg.CONF.ticket_api_user,
            cfg.CONF.ticket_api_password)
        return ticket_client

    def update_cr(self, ticket_num, ticket_status, commands, close_code):
        ticket_client = self.get_ticket_client()
        ticket_dict = self._make_update_ticket_dict(ticket_status, commands,
                                                    close_code)
        try:
            updated = ticket_client.update_ticket(ticket_num, ticket_dict)
            if updated['success']:
                LOG.debug("Auto CR %s is %s " % (ticket_num, ticket_status))
            return True
        except Exception as ex:
            # Dont break the device operations even if update CR fails.
            LOG.warn("Unable to update CR %s due to %s" % (ticket_num, ex))
            return False

    def complete_cr(self, ticket_num, msg):
        close_code = 'Completed as Planned'
        ticket_status = "Complete"
        self.update_cr(ticket_num, ticket_status, msg, close_code)

    def cancel_cr(self, ticket_num, msg):
        close_code = 'Change No Longer Needed'
        ticket_status = "Complete"
        if ticket_num:
            self.update_cr(ticket_num, ticket_status, msg, close_code)

    def make_ticket_data_dict(self, busines_justification, action_plan,
                             verification_plan, rollback_plan, cr_type,
                             requester_login, site_components):
        ticket_data = {
            "busines_justification": busines_justification,
            "action_plan": action_plan,
            "verification_plan": verification_plan,
            "rollback_plan": rollback_plan,
            "cr_type": cr_type,
            "cr_subtype": CR_TYPE_SUBTYPE_MAP[cr_type],
            "requester_login": requester_login,
            "site_components": site_components
        }
        return ticket_data

    def _make_update_ticket_dict(self, ticket_status, commands, close_code):
        ticket_data = {"changeimplementation_status": ticket_status,
                       "modifiedBy": cfg.CONF.modifiedBy
                       }
        if close_code:
            ticket_data['close_code'] = close_code
        if commands:
            ticket_data['message_update'] = commands
        return ticket_data


class SubnetticketWorkflow(ticketWorkFlow):

    def __init__(self):
        super(SubnetticketWorkflow, self)

    @create_and_mark_cr_inprogress
    def create_subnet_cr(self, vlans, ip, name, rollback_data,
                         requester_login):
        business_justification = "Subnet association to vlan via network" \
                                " automation."
        action_plan = "Create Subnet %s on device %s for vlans %s  ." \
                      % (name, ip, vlans)
        verification_plan = "Subnet %s on device %s should be associated to" \
                            " vlans %s  ." % (name, ip, vlans)
        rollback_plan = "Rollback to current subnet config %s" % rollback_data
        site_components = "Switch %s" % ip
        return self.make_ticket_data_dict(
            business_justification, action_plan, verification_plan,
            rollback_plan, CR_TYPE_VLAN, requester_login, site_components)


class PortFlipticketWorkflow(ticketWorkFlow):

    def __init__(self):
        super(PortFlipticketWorkflow, self)

    @create_and_mark_cr_inprogress
    def create_port_flip_cr(self, vlans, ip, name, rollback_data,
                            requester_login):
        business_justification = "Port association to vlan via network" \
                                     " automation."
        action_plan = "Associate port %s on device %s to vlans %s  ." % (
            name, ip, vlans)
        verification_plan = "Port %s on device %s should be associated to" \
                            " vlans %s  ." % (name, ip, vlans)
        rollback_plan = "Rollback to current port config %s" % rollback_data
        site_components = "Switch %s" % ip
        return self.make_ticket_data_dict(
            business_justification, action_plan, verification_plan,
            rollback_plan, CR_TYPE_PORT, requester_login, site_components)


class PortEnableticketWorkflow(ticketWorkFlow):

    def __init__(self):
        super(PortEnableticketWorkflow, self)

    @create_and_mark_cr_inprogress
    def create_port_enable_cr(self, ip, name, rollback_data,
                              requester_login):
        business_justification = "Enable Port via network" \
                                 " automation."
        action_plan = "Enable port %s on device %s." % (
            name, ip)
        verification_plan = "Port %s on device %s should be enabled." \
                            % (name, ip)
        rollback_plan = "Rollback to current port config %s." % rollback_data
        site_components = "Switch %s" % ip
        return self.make_ticket_data_dict(
            business_justification, action_plan, verification_plan,
            rollback_plan, CR_TYPE_PORT, requester_login, site_components)

    @create_and_mark_cr_inprogress
    def create_port_disable_cr(self, ip, name, rollback_data,
                              requester_login):
        business_justification = "Disable Port via network" \
                                 " automation."
        action_plan = "Shutdown port %s on device %s." % (
            name, ip)
        verification_plan = "Port %s on device %s should be Disabled." \
                            % (name, ip)
        rollback_plan = "Rollback to current port config %s." % rollback_data
        site_components = "Switch %s" % ip
        return self.make_ticket_data_dict(
            business_justification, action_plan, verification_plan,
            rollback_plan, CR_TYPE_PORT, requester_login, site_components)
