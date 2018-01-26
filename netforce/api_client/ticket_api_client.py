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

from datetime import datetime
from datetime import timedelta
import httplib2
import netforce.api_client.exceptions as ticket_exceptions
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
import pytz
from pytz import timezone

LOG = logging.getLogger(__name__)

GENERATION_ID_TIMEOUT = -1
DEFAULT_CONCURRENT_CONNECTIONS = 3
DEFAULT_CONNECT_TIMEOUT = 5

HTTP_GET = "GET"
HTTP_POST = "POST"
HTTP_DELETE = "DELETE"
HTTP_PUT = "PUT"

ticket_opts = [
    cfg.StrOpt('ticket_service_url',
               default='fake_url',
               help='ticket service URL'),
    cfg.StrOpt('ticket_api_user', default="fake_user",
               help="ticket Api User "),
    cfg.StrOpt('ticket_api_password', default="fake",
               help='ticket Api Password'),
    cfg.StrOpt('service_category', default="Network Service Request",
               help='Service Category'),
    cfg.StrOpt('cr_type', default='Port', help='ticket CR Type'),
    cfg.StrOpt('cr_sub_type', default='Port_Modify_Auto',
               help='ticket CR Sub Type'),
    cfg.StrOpt('requester_contact_info', default='fake',
               help='CR requester_contact_info'),
    cfg.StrOpt('modifiedBy', default='api_netforce', help='Cr modified by'),
    cfg.StrOpt('requester_login', default='netforce',
               help='CR requester userid'),
    cfg.StrOpt('assigned_group', default='fake', help='Assigned Group'),
    cfg.StrOpt('planned_duration', default="5",
               help='Duration of CR in minutes'),
    cfg.StrOpt('ticket_transport_mode', default="https",
               help='access ticket with either http or https'),
    cfg.StrOpt('zone_name', default="US/Pacific",
               help='Zone name for ticket.'),

]

cfg.CONF.register_opts(ticket_opts)


class ticketApiClient(object):
    """The ticket API Client.

    A simple HTTP client for POC.
    """

    errors = {
        303: ticket_exceptions.ResourceRedirect,
        400: ticket_exceptions.RequestBad,
        403: ticket_exceptions.Forbidden,
        404: ticket_exceptions.ResourceNotFound,
        415: ticket_exceptions.MediaTypeUnsupport,
        503: ticket_exceptions.ServiceUnavailable,
        412: ticket_exceptions.ChangeStopActive
    }

    headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
              }

    def __init__(self, ticket_service_url, ticket_api_user,
                 ticket_api_password,
                 connect_timeout=DEFAULT_CONNECT_TIMEOUT, http_timeout=75,
                 retries=2, redirects=2):
        LOG.debug("ticket url %s", ticket_service_url)
        self.ticket_host = ticket_service_url
        self.ticket_user = ticket_api_user
        self.ticket_password = ticket_api_password
        self.request_timeout = http_timeout * retries
        self.http_timeout = http_timeout
        self.retries = retries
        self.redirects = redirects
        self.version = None

    def request(self, method, url, body=None,
                content_type="application/json",
                decode=True):
        '''Issues request to controller.'''

        headers = self.headers.copy()
        headers['username'] = self.ticket_user
        headers['password'] = self.ticket_password
        uri = "http://" + self.ticket_host + "/" + url

        try:
            if body:
                body = jsonutils.dumps(body)
            else:
                body = ''

            conn = httplib2.Http()
            LOG.debug("Send request to ticket, method %s, url %s, "
                      "headers %s, body %s",
                      method, uri, headers, body)
            response, content = conn.request(uri, method, body,
                                             headers=headers)
        except Exception as e:
            LOG.warn("Exception: %s" % e)
            raise e

        LOG.debug('Request returns: %s' % content)
        status = int(response['status'])
        if 200 <= status < 300:

            if content == '':
                return {}

            if decode:
                content = jsonutils.loads(content)
            return content

        if status in self.errors:
            cls = self.errors[status]
        else:
            cls = ticket_exceptions.RequestBad

        raise cls(uri=uri, status=status, response=response, content=content)

    def _create_ticket_request_body(self, requester_login, cr_type,
                                    cr_subtype):
        contact_info = "For issues, please contact " + \
                       cfg.CONF.requester_contact_info + \
                       "\n Link to contacts is @ " \
                       "fake"
        res = {
                "serviceName": "CREATE_CHNGE",
                "keyValues": {
                    "title": "(Netforce) Port modify operations via"
                             " NWAUTOMATION",
                    "change_action_plan": "Set of commands to be executed on"
                                          " device",
                    "change_rollback_plan": "NWAUTOMATION does not handle"
                                            " rollback.",
                    "site_components": "N/A",
                    "requester_login": requester_login,
                    "requester_contact_info": contact_info,

                    "service_category": cfg.CONF.service_category,
                    "type": cr_type,
                    "subtype": cr_subtype,
                    "software_release_train": "N/A",
                    "assigned_group": cfg.CONF.assigned_group,
                    "site": "",
                    "environment": "Production",
                    "changeimplementation_priority": "Standard",
                    "planned_duration": cfg.CONF.planned_duration,
                    "project_id": "N/A",
                    "time_of_day_window": "Anytime",
                    "business_justification": "This Change ticket is for"
                                              " Network automation.",
                    "siteuser_impacted": "No"
                }
        }

        return res

    def _check_change_allowed_request_body(self):
        # just call status check service for verifying whether there
        # is an active moritoriam.
        res = {
                "serviceName": "FIND_STOP_CHANGE_STATUS",
                "keyValues": {}

        }

        return res

    def _update_ticket_request_body(self, ticket_num):
        res = {
                "serviceName": "UPDATE_CHNGE",
                "keyValues": {
                    "task_id": ticket_num,
                    "modifiedBy": "api_netforce"
                }

        }

        return res

    def _get_gmt_date_time(self):
        # Get date time converted in ticket supported format:
        # yyyy - MM - dd HH:mm:ss SSS zzzz
        # e.g. 2016-08-30 14:40:30 000 GMT+00:00

        date_format = '%Y-%m-%d %H:%M:%S'
        date = datetime.now(tz=pytz.utc)
        zone_name = cfg.CONF.zone_name
        date = date.astimezone(timezone(zone_name))
        time_now = date.strftime(date_format)
        gmt_zone = " 000 "
        if self._is_daylight_shift_on(zone_name):
            gmt_zone += "GMT-07:00"
        else:
            gmt_zone += "GMT-08:00"
        current_gmt_time = time_now + gmt_zone
        return current_gmt_time

    def _is_daylight_shift_on(self, zone_name):
        tz = pytz.timezone(zone_name)
        now = pytz.utc.localize(datetime.utcnow())
        return now.astimezone(tz).dst() != timedelta(0)

    def _is_change_creation_allowed(self):
        url = "findTicket"
        body = self._check_change_allowed_request_body()
        response = self.request(HTTP_POST, url, body)
        change_allowed = True
        for resp in response['result'][0]:
            if resp['key'] == "stop_changes" and resp['value'] == "STOP":
                change_allowed = False
                break
        if not change_allowed:
            raise ticket_exceptions.ChangeStopActive()
        return change_allowed

    def create_ticket(self, verification_plan, busines_justification,
                      action_plan, site_components, rollback_plan,
                      requester_login, cr_type, cr_subtype):
        # Note: CR goes to status Approved on create.
        # Check if change creation is allowed before create CR
        if self._is_change_creation_allowed():
            url = "createTicket"
            body = self._create_ticket_request_body(requester_login, cr_type,
                                                    cr_subtype)
            body['keyValues']["planned_start_time"] = self._get_gmt_date_time()
            body['keyValues']["change_verification_plan"] = verification_plan
            body['keyValues']["change_action_plan"] = action_plan
            body['keyValues']["business_justification"] = busines_justification
            body['keyValues']["site_components"] = site_components
            body['keyValues']["change_rollback_plan"] = rollback_plan
            return self.request(HTTP_POST, url, body)

    def update_ticket(self, ticket_num, ticket_dict):
        # Note: Need to call update twice as per the CR workflow;
        # one for changing the status to ReadyToStart,
        # second for marking it complete .
        # We can always cancel it in any case.

        url = "updateTicket"
        body = self._update_ticket_request_body(ticket_num)

        # add  parameters for update ticket to ensure it works for both cases
        # 1. to update CR in progress
        # 2. to mark the CR to complete/cancel

        body['keyValues']["changeimplementation_status"] = \
            ticket_dict['changeimplementation_status']
        if "message_update" in ticket_dict:
            body['keyValues']["message_update"] = ticket_dict['message_update']
        if "close_code" in ticket_dict:
            body['keyValues']["close_code"] = \
                ticket_dict['close_code']
        return self.request(HTTP_POST, url, body)
