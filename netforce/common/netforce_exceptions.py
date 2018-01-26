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


from neutron.common import exceptions


class SessionNotFound(exceptions.NotFound):
    message = _("Session %(session_id)s could not be found")


class SubnetPoolDeleteError(exceptions.BadRequest):
    message = _("Unable to delete subnet pool: %(reason)s")


class SubnetPoolQuotaExceeded(exceptions.OverQuota):
    message = _("Per-tenant subnet pool prefix quota exceeded")


class ResourceAlreadyExists(exceptions.Conflict):
    message = _('%(resource)s object with name %(name)s already exists.')


class VlanTagDoesNotExistError(exceptions.NotFound):
    message = _("A Vlan with tag %(tag)s not found")


class VlanAssociatedToBridgeGroup(exceptions.InUse):
    message = _("BridgeGroup %(bridge_group_name)s has vlan's associated.")


class DevicesAssociatedToBridgeGroup(exceptions.InUse):
    message = _("BridgeGroup %(bridge_group_name)s has devices associated.")


class VlansAssociatedtoVPC(exceptions.InUse):
    message = _("VPC %(vpc_name)s has vlans associated.")


class VlansAssociatedToPort(exceptions.InUse):
    message = _('Port %(port_name)s has Vlans associated.')


class VlanExistsForVpcAndBridgeGroup(exceptions.Conflict):
    message = _(
        'Vlan %(tag)s already associated to bridgegroup %(bridge_group_name)s '
        'and vpc %(vpc_name)%s')


class ReachVlanTagLimit(exceptions.OverQuota):
    message = _('Vlan reaches limit %(upper_tag_limit)d in'
                ' bridge group %(bridge_group_name)s')


class ResourceNotFound(exceptions.NotFound):
    message = _('%(resource)s object with name %(name)s not found.')


class MoreThanOneAccessVlan(exceptions.BadRequest):
    message = _("Only one access vlan expected: %(reason)s")


class NoNativeVlan(exceptions.BadRequest):
    message = _("one native vlan expected for trunk mode: %(reason)s")


class NoAllowedVlans(exceptions.BadRequest):
    message = _("At least one allowed vlan is expected for trunk mode:"
                " %(reason)s")


class NoDevicesAssociatedToBridgeGroup(exceptions.BadRequest):
    message = _('%(bridge_group_name)s has no associated devices.')


class DeviceConfigPushFailure(Exception):

    """
        This exception is raised so that the database entry call be rolled
        back.
    """

    def __init__(self, ex, model_id, **kwargs):
        self.inner_exception = ex
        self.id = model_id
        super(DeviceConfigPushFailure, self).__init__(**kwargs)


class DeviceError(exceptions.NeutronException):
    message = _('%(device_error)s')


class DeviceLoginCredentialsNotFound(DeviceError):
    message = _('Device login credentials not found: %(reason)s')


class DeviceDriverNotFound(DeviceError):
    message = _('Device driver not found: %(reason)s')


class DeviceGetInterfacesError(DeviceError):
    message = _('Get device interfaces failed: %(reason)s')


class DevicePostChangeValidationError(DeviceError):
    message = _('The post-change validation failed: %(reason)s')


class SubnetAlreadyConfigured(exceptions.Conflict):
    message = _(
        'CIDR %(cidr)s is overlapping with existing CIDR %(existing_cidr)s,'
        ' which is used by subnet %(id)s, associated with vlan %(vlan)s')


class SubnetIsNotAllowed(exceptions.BadRequest):
    message = _('Subnet %(requested)s is not under %(allowed)s')


class DistributedLockError(exceptions.NeutronException):
    message = _('Distributed lock error: %(message)s')


class AcquireDistributedLockFailed(DistributedLockError):
    message = _('Acquiring distribute lock %(name)s failed')


class MacAddressNotFoundOnInterface(exceptions.BadRequest):
    message = _('Mac address %(mac)s not found on interface %(interface)s')


class OnlyOneNativeVlansAllowed(exceptions.NeutronException):
    message = _('Only one native vlan allowed for a port')


class SmallSubnetNotAllowed(exceptions.BadRequest):
    message = _('Small subnet creation is not allowed: %(reason)s')


class OnlyOneDeviceAllowedForTorBridgeGroup(exceptions.NeutronException):
    message = _('Only one device allowd for TOR bridge group %(bridge_group)s')


class BadDeviceType(exceptions.NeutronException):
    message = _('Bad device type: %(type)s')


class NoDeviceFound(exceptions.NotFound):
    message = _('No device found for bridge group %(bridge_group)s')


class OperationNotSupported(exceptions.BadRequest):
    message = _('Operation %(operation)s not supported yet.')


class UdnsARecordAlreadyExistError(exceptions.BadRequest):
    message = _('UDNS A record already exist')


class UdnsPTRRecordAlreadyExistError(exceptions.BadRequest):
    message = _('UDNS PTR record already exist')


class UndsServiceError(exceptions.ServiceUnavailable):
    message = _('UDNS service error: %(message)s')


class GivenReserveIPCountLessThanDefaultCount(exceptions.BadRequest):
    message = _('Given reserve IP count %(reserve_ip_count)s is less than'
                ' default %(default_count)s')


class BubbleNotFound(exceptions.BadRequest):
    message = _('Bubble ID %(bubble_id)s not found in netforce.')


class BubbleDeviceNotFound(exceptions.Conflict):
    message = _('Bubble device not found: %(reason)s')


class DevicesAssociatedToTheBubble(exceptions.BadRequest):
    message = _('Cannot delete Bubble %(bubble_name)s as there are devices'
                ' associated to the bubble.')


class InvalidSubnetCIDR(exceptions.BadRequest):
    message = _('Invalid CIDR format %(message)s for subnet %(cidr)s')


class SubnetAlreadyConfiguredOnBubble(exceptions.Conflict):
    message = _(
        'CIDR %(cidr)s is overlapping with existing CIDR %(existing_cidr)s,'
        ' on Bubble device %(device_ip)s')


class NoBubbleDevicesConfigured(exceptions.BadRequest):
    message = _(
        'No bubble devices are configured yet. Please configure them'
        ' in netforce.')


class NoHealthyBubbleDevices(exceptions.Conflict):
    message = _('No healthy bubble devices found for bubble %(bubble_id)s.')


class NewSubnetCIDRNotReflectingOnBubble(exceptions.BadRequest):
    message = _(
         'Unable to find new subnet %(cidr)s on bubble device %(device_ip)s'
         ' while post validating subnet configuration.')


class TraceRouteDoesNotResolve(exceptions.BadRequest):
    message = _(
         'New cidr %(cidr)s route is not configured for the bubble devices'
         ' %(device_list)s when tried with traceroute')


class ConfiguredSubnetConflictsWithRequested(exceptions.Conflict):
    message = _(
        'Current subnet attribute %(key)s has value %(current)s; it conflicts'
        ' with  requested value %(requested)s')


class VPCNotConfigured(exceptions.Conflict):
    message = _(
        'VPC %(vpc)s is not configured in Netforce.')


class ConfiguredVlanConflictsWithRequested(exceptions.Conflict):
    message = _(
        'Current vlan attribute on %(key)s has value %(current)s; it conflicts'
        ' with  requested value %(requested)s')


class MacAddressNotPassed(exceptions.BadRequest):
    message = _('Please pass mac address for any port shut/no_shut operations'
                ' for interface %(interface)s')


class PortFlipAndPortEnableDisableNotSupportedAtSameTime(
        exceptions.BadRequest):
    message = _('Operation %(operation)s not supported together.')


class AssetServerActiveInCMS(exceptions.Conflict):
    message = _(
        'Please make sure asset server with mac %(mac)s is in decomm or'
        ' SACheck in cms before shutting down the port')


class PatchSubnetNotReflectingInBubbleRoutes(exceptions.Conflict):
    message = _(
        'CIDR %(cidr)s is not refliecting on Bubble device %(device_ip)s')


class AllBubbleDevicesAreDown(exceptions.Conflict):
    message = _(
        'All bubble devices %(bubble_devices)s are not pingable.'
        ' Please reach out to net engg for the same.')


class DeviceTypeNotFound(exceptions.Conflict):
    message = _(
        'device with %(type)s is not configured. Please create one.')


class PortNotFoundByAssetId(exceptions.NotFound):
    message = _("Port with %(asset_id)s not present in Netforce.")
