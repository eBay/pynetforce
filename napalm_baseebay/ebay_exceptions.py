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


class EntityDoesNotExistsException(Exception):
    """
        Throws this exception when an entity doesn't exist on the device.
    """
    def __init__(self, entity_name):
        self.message = 'entity %s is in suspended mode.s' % entity_name


class EntityInSuspendedModeException(Exception):

    def __init__(self, message):
        self.message = message


class PostChangeValidationException(Exception):
    """The post-change validation did not see the expected result.

    For example, if you create a function to add an interface description,
    you should go back in to the config and validate that the description
    is there. In the event that it is not there, you should raise this
    exception.

    This exception should be used for any similar validation condition.
    """

    pass


class InvalidValueForParameterException(Exception):
    """
        The exception is a validation error if an invalid value is passed
        for a parameter.
    """
    def __init__(self, response):
        self.message = 'Unsupported response format %s from device' % response


class MultipleVlanTaggingNotSupported(Exception):

    def __init(self, port_name, switch_port):
        self.message = 'multiple vlan tags cannot be associated ' \
                       'to port %s in switch port mode %s' % (
                           port_name, switch_port)


class VlanNotFounOnDevice(Exception):

    def __init__(self, vlan_tag, vlans_on_config):
        self.message = 'vlan %s not found in config. Device has %s' % (
            str(vlan_tag), vlans_on_config)


class MoreThanOneAccessVlan(Exception):

    def __init__(self, reason):
        self.message = "Only one access vlan expected: %s" % reason


class NoNativeVlan(Exception):

    def __init__(self, reason):
        self.message = "one native vlan expected for trunk mode: %s" % \
                       reason


class NoAllowedVlans(Exception):
    def __init__(self, reason):
        self.message = "Atleast one allowed vlan is expected for " \
                       "trunk mode: %s" % reason


class VlanNotConfiguredOnInterface(Exception):
    def __init__(self, vlan, interface):
        self.message = 'vlan %s are not configured on interface %s'(vlan,
                                                                    interface)


class PortTrafficAboveThreshold(Exception):
    """compare the input and output traffic on the port against the threshold.
    """
    pass


class SubnetAlreadyConfiguredException(Exception):
    """
        subnet is already configured
    """
    def __init__(self, subnet, vlan_interface_name, overlapping_subnet):
        self.message = 'subnet %s is already configured on the vlan ' \
                       'interface [%s] as the subnet [%s]' % (
                                                     subnet,
                                                     vlan_interface_name,
                                                     overlapping_subnet)


class MaxNumberOfAllowedSubnetsAlreadyConfigured(Exception):

    def __init__(self, max_subnets, vlan_interface_name):
        self.message = 'max number of subnets [%s] already configured on  ' \
                       'vlan interface [%s]' % (str(max_subnets),
                                                vlan_interface_name)


class SubnetNotConfiguredException(Exception):
    """
        subnet is not configured
    """
    def __init__(self, subnet, vlan_interface_name):
        self.message = 'subnet %s not configured on the vlan ' \
                       'interface [%s]' % (subnet, vlan_interface_name)


class NoPrimarySubnetOnVlanInterface(Exception):
    """
        No primary subnet on vlan interface
    """
    def __init__(self, vlan_interface_name):
        self.message = 'No primary subnet configured on the vlan ' \
                       'interface [%s]' % (vlan_interface_name)


class PatchingNotSupported(Exception):
    """
        Pathing Not Supported if more then one subnets exists on vlan.
    """
    def __init__(self, vlan_interface_name):
        self.message = 'More then one subnet is configured on vlan ' \
                       'interface [%s]. Patching is only supported if there' \
                       ' is single IPV4 address on the vlan interface. Please' \
                       ' contact network engineering to fix the TOR' \
                       % (vlan_interface_name)


class RequestedPrimaryConflictsWithConfigured(Exception):
    """
        Requested subnet conflicts with configured
    """
    def __init__(self, req, configured):
        self.message = 'Requested [%s] cannot be made primary as it conflicts' \
                       ' with [%s] ' % (req, configured)


class PrimarySubnetExistsOnVlanInterface(Exception):
    """
        primary subnet already exists
    """
    def __init__(self, vlan_interface_name):
        self.message = 'Primary subnet already configured on the vlan ' \
                       'interface [%s]' % (vlan_interface_name)
