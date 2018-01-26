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


import datetime
from netforce.api.v2 import attributes
from netforce.plugins.common import netforce_constants
from neutron.db import model_base
from neutron.db import models_v2
from neutron.plugins.common import constants

import sqlalchemy as sa
from sqlalchemy import orm, ForeignKey
from sqlalchemy.ext import declarative


class NetforceBase(model_base.NeutronBase):

    @declarative.declared_attr
    def __tablename__(cls):
        return 'nf_' + cls.__name__.lower() + 's'


BASEV2 = declarative.declarative_base(cls=NetforceBase)


class HasAuditInformation(object):
    created_at = sa.Column(sa.DateTime, default=datetime.datetime.now)
    updated_at = sa.Column(sa.DateTime, onupdate=datetime.datetime.now)
    created_by = sa.Column(sa.String(255), nullable=True)
    last_updated_by = sa.Column(sa.String(255), nullable=True)


class VPC(BASEV2, models_v2.HasId,
          models_v2.HasStatusDescription,
          models_v2.HasTenant, HasAuditInformation):
    name = sa.Column(sa.String(attributes.NAME_MAX_LEN), nullable=False)
    label = sa.Column(sa.String(attributes.NAME_MAX_LEN), nullable=False)
    description = sa.Column(sa.String(attributes.DESCRIPTION_MAX_LEN))
    vlans = orm.relationship('Vlan', backref='vpc', cascade='save-update')


class Subnet(BASEV2, models_v2.HasId,
             models_v2.HasStatusDescription,
             models_v2.HasTenant, HasAuditInformation):
    name = sa.Column(sa.String(attributes.NAME_MAX_LEN), nullable=False)
    cidr = sa.Column(sa.String(64), nullable=False)
    gateway_ip = sa.Column(sa.String(64), nullable=False)
    broadcast_ip = sa.Column(sa.String(64), nullable=False)
    netmask = sa.Column(sa.String(64), nullable=False)
    vlan_id = sa.Column(sa.String(36), ForeignKey('nf_vlans.id'))
    start_ip = sa.Column(sa.String(64), nullable=True)
    end_ip = sa.Column(sa.String(64), nullable=True)


class VlanPortAssociation(BASEV2, models_v2.HasId,
                          models_v2.HasStatusDescription,
                          models_v2.HasTenant,
                          HasAuditInformation):

    __table_args__ = (
        sa.schema.UniqueConstraint(
            'port_id', 'vlan_id', name='uniq_port_id_and_vlan_id'),
    )
    port_id = sa.Column(sa.String(36), ForeignKey('nf_ports.id'))
    vlan_id = sa.Column(sa.String(36), ForeignKey('nf_vlans.id'))
    is_native_vlan = sa.Column(sa.Boolean(), default=False)


class Vlan(BASEV2, models_v2.HasId,
           models_v2.HasStatusDescription, models_v2.HasTenant,
           HasAuditInformation):
    name = sa.Column(sa.String(attributes.NAME_MAX_LEN), nullable=False)

    __table_args__ = (
        sa.schema.UniqueConstraint(
            'vpc_id', 'bridge_group_id',
            name='uniq_vpc_id_and_bridge_group_id'),
    )
    tag = sa.Column(sa.Integer, nullable=False)
    bridge_group_id = sa.Column(
        sa.String(36), ForeignKey('nf_bridgegroups.id'))
    vpc_id = sa.Column(sa.String(36), ForeignKey(
        'nf_vpcs.id'), nullable=True)

    bridgegroups = orm.relationship('BridgeGroup',
                                    back_populates='vlans')
    vpcs = orm.relationship('VPC', back_populates='vlans')
    admin_status = sa.Column(
        sa.Enum(constants.ACTIVE, netforce_constants.SUSPENDED))
    ports = orm.relationship(
        VlanPortAssociation, backref='vlan', cascade='save-update',
        lazy="joined")
    subnets = orm.relationship('Subnet', backref='vlan', cascade='save-update')


class BridgeGroup(BASEV2, models_v2.HasId,
                  models_v2.HasStatusDescription, models_v2.HasTenant,
                  HasAuditInformation):

    __table_args__ = (
        sa.schema.UniqueConstraint('name', name='uniq_name'),
    )
    name = sa.Column(sa.String(attributes.NAME_MAX_LEN), nullable=False)
    description = sa.Column(sa.String(attributes.DESCRIPTION_MAX_LEN))
    vlans = orm.relationship('Vlan', backref='bridgegroup',
                             cascade='save-update',
                             order_by='Vlan.tag')
    devices = orm.relationship(
        'Device', backref='bridgegroup', cascade='save-update')


class DeviceType(BASEV2, models_v2.HasId,
                 models_v2.HasStatusDescription, models_v2.HasTenant,
                 HasAuditInformation):
    name = sa.Column(sa.String(attributes.NAME_MAX_LEN))
    type = sa.Column(sa.String(64), nullable=False, unique=True)
    description = sa.Column(sa.String(attributes.DESCRIPTION_MAX_LEN))


class Port(BASEV2, models_v2.HasId,
           models_v2.HasStatusDescription, models_v2.HasTenant,
           HasAuditInformation):
    __table_args__ = (
        sa.schema.UniqueConstraint('asset_id', name='uniq_asset_id'),
    )
    name = sa.Column(sa.String(attributes.NAME_MAX_LEN))
    description = sa.Column(sa.String(attributes.DESCRIPTION_MAX_LEN))
    label = sa.Column(sa.String(attributes.NAME_MAX_LEN), nullable=True)
    asset_id = sa.Column(sa.String(attributes.NAME_MAX_LEN), nullable=True)
    admin_status = sa.Column(
        sa.Enum(constants.ACTIVE, netforce_constants.SUSPENDED))
    switch_port_mode = sa.Column(sa.Enum(netforce_constants.TRUNK_MODE,
                                         netforce_constants.ACCESS_MODE))
    device_id = sa.Column(sa.String(36), ForeignKey(
        'nf_devices.id'), nullable=False)
    vlans = orm.relationship(
        VlanPortAssociation, backref='port', cascade='all, delete-orphan')


class Device(BASEV2, models_v2.HasId,
             models_v2.HasStatusDescription, models_v2.HasTenant,
             HasAuditInformation):
    __table_args__ = (
        sa.schema.UniqueConstraint('name', name='uniq_name'),
        sa.schema.UniqueConstraint('management_ip', name='uniq_mgmt_ip')
    )
    name = sa.Column(sa.String(attributes.NAME_MAX_LEN))
    description = sa.Column(sa.String(attributes.DESCRIPTION_MAX_LEN))
    device_type_id = sa.Column(sa.String(36), ForeignKey('nf_devicetypes.id'))
    device_type = orm.relationship(DeviceType, backref='devicetypes')
    management_ip = sa.Column(sa.String(64))
    username = sa.Column(sa.String(64))
    password = sa.Column(sa.String(64))
    ports = orm.relationship(Port, backref='device',
                             cascade='all, delete-orphan')
    bridge_group_id = sa.Column(
        sa.String(36), ForeignKey('nf_bridgegroups.id'), nullable=True)
    os_type = sa.Column(sa.String(36))
    bubble_id = sa.Column(sa.String(36), ForeignKey('nf_bubbles.id'))


class Bubble(BASEV2, models_v2.HasId,
             models_v2.HasStatusDescription, models_v2.HasTenant,
             HasAuditInformation):
    __table_args__ = (
        sa.schema.UniqueConstraint('name', name='uniq_name'),
    )
    name = sa.Column(sa.String(attributes.NAME_MAX_LEN))


class Vrf(BASEV2, models_v2.HasId,
          models_v2.HasStatusDescription, models_v2.HasTenant,
          HasAuditInformation):
    __table_args__ = (
        sa.schema.UniqueConstraint('name', name='uniq_name'),
    )
    name = sa.Column(sa.String(attributes.NAME_MAX_LEN))
    description = sa.Column(sa.String(attributes.NAME_MAX_LEN))
    bubble_id = sa.Column(sa.String(36), ForeignKey('nf_bubbles.id'))
    vpc_id = sa.Column(sa.String(36), ForeignKey('nf_vpcs.id'))
