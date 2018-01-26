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


from netforce.common import netforce_exceptions
from netforce.db import netforce_model
from netforce.plugins.common import netforce_constants
from netforce.services.netforce_service_plugin import plugin as netforce_plugin
from neutron.common import exceptions as n_exc
from neutron.db import common_db_mixin
from neutron.plugins.common import constants

from oslo_db import exception as db_exc
from sqlalchemy.orm import exc as orm_exc

_author__ = 'kugandhi'


class NetforceDbMixin(netforce_plugin.NetForceServicePlugin,
                      common_db_mixin.CommonDbMixin):

    def update_vlanportassociation(self, context, vlanportassociation_id,
                                   vlanportassociation):
        with context.session.begin(subtransactions=True):
            vlanportassociation_db = self.\
                _get_vlanportassociation_db_by_id(context,
                                                  vlanportassociation_id)
            vlanportassociation_db.update(vlanportassociation)
            return vlanportassociation_db

    def create_device(self, context, device):
        with context.session.begin(subtransactions=True):
            device_db = netforce_model.Device(**device)
            device_db.status = constants.ACTIVE
            device_db.status_description = \
                netforce_constants.ACTIVE_STATUS_DESCRIPTION
            try:
                context.session.add(device_db)
                context.session.flush()
            except db_exc.DBDuplicateEntry:
                raise netforce_exceptions.ResourceAlreadyExists(
                    resource='Device', name=device['name'])
            return device_db

    def get_device_db(self, context, device_id):
        return self._get_by_id(context, netforce_model.Device, device_id)

    def get_device(self, context, device_id, fields=None):
        return self.make_device_dict(self.get_device_db(context, device_id),
                                     fields)

    def get_devices(self, context, filters=None, fields=None):
        return self._get_collection(context, netforce_model.Device,
                                    self.make_device_dict,
                                    filters=filters, fields=fields)

    def get_devices_by_type_and_bubble_id(self, context, device_type_id,
                                          bubble_id):
        query = self._model_query(context, netforce_model.Device)
        return query.filter(
            netforce_model.Device.device_type_id == device_type_id).filter(
            netforce_model.Device.bubble_id == bubble_id).all()

    def update_device(self, context, device_id, device_dict):
        with context.session.begin(subtransactions=True):
            device_db = self.get_device_db(context, device_id)

            if device_db:
                device_db.update(device_dict)
            return device_db

    def delete_device(self, context, device_id):
        with context.session.begin(subtransactions=True):
            device_db = self._get_by_id(context, netforce_model.Device,
                                        device_id)

            if device_db:
                context.session.delete(device_db)
                context.session.flush()

    def create_devicetype(self, context, device_type):
        with context.session.begin(subtransactions=True):
            device_type_db = netforce_model.DeviceType(**device_type)
            device_type_db.status = constants.ACTIVE
            device_type_db.status_description = 'Active'
            try:
                context.session.add(device_type_db)
                context.session.flush()
            except db_exc.DBDuplicateEntry:
                netforce_exceptions.ResourceAlreadyExists(
                    resource='DeviceType', name=device_type['name'])
            return device_type_db

    def get_devicetype_db(self, context, device_type_id):
        return self._get_by_id(context, netforce_model.DeviceType,
                               device_type_id)

    def get_devicetype(self, context, device_type_id, fields=None):
        return self.make_devicetype_dict(self.
                                         get_devicetype_db(context,
                                                           device_type_id),
                                         fields)

    def get_devicetypes(self, context, filters=None, fields=None):
        return self._get_collection(context, netforce_model.DeviceType,
                                    self.make_devicetype_dict,
                                    filters=filters, fields=fields)

    def get_devicetype_by_type(self, context, type):
        query = self._model_query(context, netforce_model.DeviceType)
        try:
            device_type = query.filter(
                netforce_model.DeviceType.type == type).one()
        except orm_exc.NoResultFound:
            raise netforce_exceptions.DeviceTypeNotFound(type=type)
        return device_type

    def update_devicetype(self, context, device_type_id, device_type_dict):
        with context.session.begin(subtransactions=True):
            device_type_db = self.get_devicetype_db(context, device_type_id)
            if device_type_db:
                device_type_db.update(device_type_dict)
            return device_type_db

    def delete_devicetype(self, context, device_type_id):
        with context.session.begin(subtransactions=True):
            device_db = self._get_by_id(context, netforce_model.DeviceType,
                                        device_type_id)

            if device_db:
                context.session.delete(device_db)
                context.session.flush()

    def create_port(self, context, port):
        with context.session.begin(subtransactions=True):
            port_db = netforce_model.Port(**port)
            port_db.status = constants.ACTIVE
            port_db.status_description = 'Active'
            try:
                context.session.add(port_db)
                context.session.flush()
            except db_exc.DBDuplicateEntry:
                raise netforce_exceptions.ResourceAlreadyExists(
                    resource='Port', name=port['name'])
            return port_db

    def get_port_db(self, context, port_id):
        try:
            port = self._get_by_id(context, netforce_model.Port, port_id)
        except orm_exc.NoResultFound:
            raise n_exc.PortNotFound(port_id=port_id)
        return port

    def get_port(self, context, port_id, fields=None):
        port_db = self.get_port_db(context, port_id)
        return self.make_port_dict(port_db, fields)

    def get_port_by_asset_id(self, context, asset_id):
        try:
            query = self._model_query(context, netforce_model.Port)
            port_db = query.filter(netforce_model.Port.asset_id == asset_id).\
                one()
        except orm_exc.NoResultFound:
            raise netforce_exceptions.PortNotFoundByAssetId(
                asset_id=asset_id)
        return port_db

    def get_ports(self, context, filters=None, fields=None):
        return self._get_collection(context, netforce_model.Port,
                                    self.make_port_dict,
                                    filters=filters, fields=fields)

    def update_port(self, context, port_id, port_dict):
        with context.session.begin(subtransactions=True):
            port_db = self.get_port_db(context, port_id)

            if port_db:
                port_db.update(port_dict)
            return port_db

    def delete_port(self, context, port_id):
        with context.session.begin(subtransactions=True):
            port_db = self._get_by_id(context, netforce_model.Port, port_id)

            if port_db:
                if len(port_db.vlans) > 0:
                    raise netforce_exceptions.VlansAssociatedToPort(
                        port_name=port_db.name)
                device_db = self.get_device_db(context, port_db.device_id)
                if device_db:
                    device_db.ports.remove(port_db)
                    device_db.save(context.session)
                context.session.delete(port_db)
                context.session.flush()

    def get_vlan_db(self, context, vlan_id):
        return self._get_by_id(context, netforce_model.Vlan, vlan_id)

    def delete_vlan(self, context, vlan_id):
        with context.session.begin(subtransactions=True):
            vlan_db = self.get_vlan_db(context, vlan_id)

            if vlan_db:
                vlanportassociations = self.\
                    _get_vlanportassociations_by_vlan_id(context, vlan_db.id)
                for each_assc in vlanportassociations:
                    self.delete_vlanportassociation(context, each_assc.id)
                context.session.delete(vlan_db)
                context.session.flush()

    def create_vlan_by_bg_and_vpc(self, context, vlan, bridgegroup, vpc=None):
        with context.session.begin(subtransactions=True):
            vlan_db = netforce_model.Vlan(**vlan)
            vlan_db.status = constants.ACTIVE
            vlan_db.status_description = \
                netforce_constants.ACTIVE_STATUS_DESCRIPTION

            with context.session.no_autoflush:
                bridgegroup.vlans.append(vlan_db)
                if vpc:
                    vpc.vlans.append(vlan_db)
            try:
                context.session.add(vlan_db)
                context.session.flush()
            except db_exc.DBDuplicateEntry:
                netforce_exceptions.ResourceAlreadyExists(
                    resource='Vlan', name=vlan_db['name'])
            return vlan_db

    def update_vlan(self, context, vlan_id, vlan_dict):
        with context.session.begin(subtransactions=True):
            vlan_db = self.get_vlan_db(context, vlan_id)

            if vlan_db:
                vlan_db.update(vlan_dict)
            return vlan_db

    def create_vlan(self, context, vlan):
        with context.session.begin(subtransactions=True):
            bridgegroup = self.get_bridgegroup_db(
                context, vlan.pop('bridgegroup_id'))
            vpc = self.get_vpc_db(context, vlan.pop('vpc_id'))
            vlan_db = netforce_model.Vlan(**vlan)
            vlan_db.status = constants.ACTIVE
            vlan_db.status_description = 'Active'

            with context.session.no_autoflush:
                bridgegroup.vlans.append(vlan_db)
                vpc.vlans.append(vlan_db)
            try:
                context.session.add(vlan_db)
                context.session.flush()
            except db_exc.DBDuplicateEntry:
                netforce_exceptions.ResourceAlreadyExists(
                    resource='Vlan', name=vlan_db['name'])
            return vlan_db

    def get_vlan(self, context, vlan_id, fields=None):
        return self.make_vlan_dict(self.get_vlan_db(context, vlan_id), fields)

    def get_vlans(self, context, filters=None, fields=None):
        # TODO(aginwala): NTWK-3384 Handle all error cases if bg
        # or vpc not found in db.
        if filters:
            bg = filters.pop('bridge_group_name', None)
            if bg:
                bg_db = self.get_bridgegroup_by_name(context, bg[0])
                if bg_db:
                    filters['bridge_group_id'] = [bg_db['id']]
            vpc = filters.pop('vpc_name', None)
            if vpc:
                vpc_db = self.get_vpc_by_name(context, vpc[0])
                if vpc_db:
                    filters['vpc_id'] = [vpc_db['id']]
        return self._get_collection(context, netforce_model.Vlan,
                                    self.make_vlan_dict,
                                    filters=filters, fields=fields)

    def get_vlan_by_tag_and_port_id(self, context, vlan_tag, port_id):
        port_db = self.get_port_db(context, port_id)
        vlans_associated = port_db.device.bridgegroup.vlans
        for assc_vlan in vlans_associated:
            if assc_vlan.tag == int(vlan_tag):
                return assc_vlan
        return None

    def get_vlan_by_vpc_name_and_port_id(self, context, vpc_name, port_id):
        port_db = self.get_port_db(context, port_id)
        vlans_associated = port_db.device.bridgegroup.vlans
        for assc_vlan in vlans_associated:
            if assc_vlan.vpc.name == vpc_name:
                return assc_vlan
        return None

    def create_vlanportassociation(self, context, vlan_id, port_id, is_native):
        with context.session.begin(subtransactions=True):

            vlan_db = netforce_model.\
                VlanPortAssociation(port_id=port_id,
                                    vlan_id=vlan_id,
                                    tenant_id=context.tenant_id,
                                    is_native_vlan=is_native)
            vlan_db.status = constants.ACTIVE
            try:
                context.session.add(vlan_db)
                context.session.flush()
            except db_exc.DBDuplicateEntry:
                netforce_exceptions.\
                    ResourceAlreadyExists(resource='VlanPortAssociation',
                                          name='port id [' + port_id + '] '
                                               'and vlan id [' + vlan_id + ']'
                                          )
            return vlan_db

    def _get_vlanportassociation_db_by_id(self, context,
                                         vlanportassociation_id):
        return self._get_by_id(context, netforce_model.VlanPortAssociation,
                               vlanportassociation_id)

    def delete_vlanportassociation(self, context, vlanportassociation_id):
        with context.session.begin(subtransactions=True):
            vlan_port_assocation = self.\
                _get_vlanportassociation_db_by_id(context,
                                                  vlanportassociation_id)

            if vlan_port_assocation:
                context.session.delete(vlan_port_assocation)
                context.session.flush()

    def get_vlan_port_association_db(self, context, vlan_id, port_id):
        query = self._model_query(context, netforce_model.VlanPortAssociation)
        return query.filter(netforce_model.VlanPortAssociation.vlan_id ==
                            vlan_id,
                            netforce_model.VlanPortAssociation.port_id ==
                            port_id).one()

    def get_vlanportassociation(self, context, id, fields=None):
        db = self._get_vlanportassociation_db_by_id(context, id)
        self.make_vlanportassociation_dict(db, fields)

    def _get_vlanportassociations_by_vlan_id(self, context, vlan_id):
        query = self._model_query(context, netforce_model.VlanPortAssociation)
        return query.filter(netforce_model.VlanPortAssociation.vlan_id ==
                            vlan_id).all()

    def delete_vpc(self, context, vpc_id):
        with context.session.begin(subtransactions=True):
            vpc_db = self.get_vpc_db(context, vpc_id)

            if vpc_db:
                if len(vpc_db.vlans) > 0:
                    raise netforce_exceptions.VlansAssociatedtoVPC(
                        vpc_name=vpc_db.name)
                context.session.delete(vpc_db)
                context.session.flush()

    def create_vpc(self, context, vpc):
        with context.session.begin(subtransactions=True):
            vpc_db = netforce_model.VPC(**vpc)
            vpc_db.status = constants.ACTIVE
            vpc_db.status_description = 'Active'
            try:
                context.session.add(vpc_db)
                context.session.flush()
            except db_exc.DBDuplicateEntry:
                netforce_exceptions.ResourceAlreadyExists(
                    resource='Vpc', name=vpc_db['name'])
            return vpc_db

    def get_vpc_db(self, context, vpc_id):
        vpc_db = self._get_by_id(context, netforce_model.VPC, vpc_id)
        return vpc_db

    def get_vpc(self, context, vpc_id, fields=None):
        vpc_db = self.get_vpc_db(context, vpc_id)
        return self.make_vpc_dict(vpc_db, fields)

    def get_vpc_by_name(self, context, vpc_name):
        query = self._model_query(context, netforce_model.VPC)
        return query.filter(netforce_model.VPC.name == vpc_name).first()

    def get_vpcs(self, context, filters=None, fields=None):
        return self._get_collection(context, netforce_model.VPC,
                                    self.make_vpc_dict,
                                    filters=filters, fields=fields)

    def update_vpc(self, context, vpc_id, vpc_dict):
        with context.session.begin(subtransactions=True):
            vpc_db = self.get_vpc_db(context, vpc_id)

            if vpc_db:
                vpc_db.update(vpc_dict)
            return vpc_db

    def get_bridgegroup_db(self, context, bridgegroup_id):
        return self._get_by_id(context, netforce_model.BridgeGroup,
                               bridgegroup_id)

    def delete_bridgegroup(self, context, bridgegroup_id):
        with context.session.begin(subtransactions=True):
            bg_db = self._get_by_id(context, netforce_model.BridgeGroup,
                                    bridgegroup_id)

            if bg_db:
                if len(bg_db.vlans) > 0:
                    raise netforce_exceptions.VlanAssociatedToBridgeGroup(
                        bridge_group_name=bg_db.name)

                if len(bg_db.devices) > 0:
                    raise netforce_exceptions.DevicesAssociatedToBridgeGroup(
                        bridge_group_name=bg_db.name)

                context.session.delete(bg_db)
                context.session.flush()

    def delete_vlanportassociation_by_port_id(self, context, port_id):
        query = self._model_query(context, netforce_model.VlanPortAssociation)
        return query.filter(netforce_model.VlanPortAssociation.port_id ==
                            port_id).delete()

    def _get_vlanportassociation_by_port_id(self, context, port_id):
        query = self._model_query(context, netforce_model.VlanPortAssociation)
        return query.filter(netforce_model.VlanPortAssociation.port_id ==
                            port_id).all()

    def create_bridgegroup(self, context, bridgegroup_db):
        with context.session.begin(subtransactions=True):
            bridgegroup_db = netforce_model.BridgeGroup(**bridgegroup_db)
            bridgegroup_db.status = constants.ACTIVE
            bridgegroup_db.status_description = \
                netforce_constants.ACTIVE_STATUS_DESCRIPTION
            try:
                context.session.add(bridgegroup_db)
                context.session.flush()
            except db_exc.DBDuplicateEntry:
                netforce_exceptions.\
                    ResourceAlreadyExists(resource='BridgeGroup',
                                          name=bridgegroup_db['name'])
            return bridgegroup_db

    def get_bridgegroup(self, context, bridgegroup_id, fields=None):
        bg_db = self.get_bridgegroup_db(context, bridgegroup_id)
        return self.make_bridgegroup_dict(bg_db, fields)

    def get_bridgegroup_by_name(self, context, bridgegroup_name):
        query = self._model_query(context, netforce_model.BridgeGroup)
        return query.filter(netforce_model.BridgeGroup.name ==
                            bridgegroup_name).one()

    def get_bridgegroups(self, context, filters=None, fields=None):
        return self._get_collection(context, netforce_model.BridgeGroup,
                                    self.make_bridgegroup_dict,
                                    filters=filters, fields=fields)

    def update_bridgegroup(self, context, bridgegroup_id, bridgegroup):
        with context.session.begin(subtransactions=True):
            bridgegroup_db = self.get_bridgegroup_db(context, bridgegroup_id)

            if bridgegroup_db:
                bridgegroup_db.update(bridgegroup)
            return bridgegroup_db

    def get_subnet_db(self, context, subnet_id):
        return self._get_by_id(context, netforce_model.Subnet,
                               subnet_id)

    def create_subnet(self, context, subnet):
        # TODO(lhuang8): check if vlan id is valid, if not, raise a exception;
        #       otherwise, a internal server error will be raise
        with context.session.begin(subtransactions=True):
            subnet_db = netforce_model.Subnet(**subnet)
            subnet_db.status = constants.ACTIVE
            try:
                context.session.add(subnet_db)
                context.session.flush()
            except db_exc.DBDuplicateEntry:
                netforce_exceptions.\
                    ResourceAlreadyExists(resource='Subnet',
                                          name=subnet_db['name'])
            return subnet_db

    def get_subnet(self, context, subnet_id, fields=None):
        subnet_db = self.get_subnet_db(context, subnet_id)
        return self.make_subnet_dict(subnet_db, fields)

    def get_subnets(self, context, filters=None, fields=None):
        return self._get_collection(context, netforce_model.Subnet,
                                    self.make_subnet_dict,
                                    filters=filters, fields=fields)

    def get_subnet_by_vlan_id(self, context, vlan_id):
        query = self._model_query(context, netforce_model.Subnet)
        return query.filter(netforce_model.Subnet.name ==
                            vlan_id).first()

    def get_subnet_by_cidr(self, context, cidr):
        query = self._model_query(context, netforce_model.Subnet)
        return query.filter(netforce_model.Subnet.cidr == cidr).first()

    def update_subnet(self, context, subnet_id, subnet):
        with context.session.begin(subtransactions=True):
            subnet_db = self.get_subnet_db(context, subnet_id)

            if subnet_db:
                subnet_db.update(subnet)
            return subnet_db

    def delete_subnet(self, context, subnet_id):
        query = self._model_query(context, netforce_model.Subnet)
        return query.filter(netforce_model.Subnet.id ==
                            subnet_id).delete()

    def create_bubble(self, context, bubble):
        with context.session.begin(subtransactions=True):
            bubble_db = netforce_model.Bubble(**bubble)
            bubble_db.status = constants.ACTIVE
            try:
                context.session.add(bubble_db)
                context.session.flush()
            except db_exc.DBDuplicateEntry:
                netforce_exceptions.ResourceAlreadyExists(
                    resource='Bubble', name=bubble_db['name'])
            return bubble_db

    def get_bubbles(self, context, filters=None, fields=None):
        return self._get_collection(context, netforce_model.Bubble,
                                    self.make_bubble_dict,
                                    filters=filters, fields=fields)

    def get_bubble(self, context, bubble_id, fields=None):
        return self._get_by_id(context, netforce_model.Bubble, bubble_id)

    def get_bubble_by_name(self, context, bubble_name):
        query = self._model_query(context, netforce_model.Bubble)
        return query.filter(netforce_model.Bubble.name == bubble_name).one()

    def update_bubble(self, context, bubble_id, bubble_dict):
        with context.session.begin(subtransactions=True):
            bubble_db = self.get_bubble(context, bubble_id)
            bubble_db.update(bubble_dict)
            return bubble_db

    def delete_bubble(self, context, bubble_id):
        with context.session.begin(subtransactions=True):
            bubble_db = self.get_bubble(context, bubble_id)
            query = self._model_query(context, netforce_model.Device)
            device_db = query.filter(
                netforce_model.Device.bubble_id == bubble_id).first()
            if device_db:
                raise netforce_exceptions.DevicesAssociatedToTheBubble(
                    bubble_name=bubble_db.name)
            context.session.delete(bubble_db)
            context.session.flush()

    def create_vrf(self, context, vrf):
        with context.session.begin(subtransactions=True):
            vrf_db = netforce_model.Vrf(**vrf)
            vrf_db.status = constants.ACTIVE
            try:
                context.session.add(vrf_db)
                context.session.flush()
            except db_exc.DBDuplicateEntry:
                netforce_exceptions.ResourceAlreadyExists(
                    resource='Vrf', name=vrf_db['name'])
            return vrf_db

    def get_vrfs(self, context, filters=None, fields=None):
        return self._get_collection(context, netforce_model.Vrf,
                                    self.make_vrf_dict,
                                    filters=filters, fields=fields)

    def get_vrf(self, context, vrf_id, fields=None):
        return self._get_by_id(context, netforce_model.Vrf, vrf_id)

    def get_vrf_by_name(self, context, vrf_name):
        query = self._model_query(context, netforce_model.Vrf)
        return query.filter(netforce_model.Vrf.name == vrf_name).one()

    def get_vrf_by_bubble_id_and_vpc_id(self, context, bubble_id, vpc_id):
        query = self._model_query(context, netforce_model.Vrf)
        return query.filter(
            netforce_model.Vrf.bubble_id == bubble_id).filter(
            netforce_model.Vrf.vpc_id == vpc_id).all()

    def update_vrf(self, context, vrf_id, vrf_dict):
        with context.session.begin(subtransactions=True):
            vrf_db = self.get_vrf(context, vrf_id)
            vrf_db.update(vrf_dict)
            return vrf_db

    def delete_vrf(self, context, vrf_id):
        with context.session.begin(subtransactions=True):
            vrf_db = self.get_vrf(context, vrf_id)
            context.session.delete(vrf_db)
            context.session.flush()
