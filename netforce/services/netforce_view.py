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


class NetForceViewMixin(object):
    """
        This class is mixin function to define the view payload for each
        resource. The view method name should be make_<resourcename>_dict

    """
    def make_bridgegroup_dict(self, bg, fields=None):
        res = {
            'id': bg.id,
            'name': bg.name,
            'description': bg.description,
            'status': bg.status,
            'status_description': bg.status_description,
            'tenant_id': bg.tenant_id
        }
        return self._fields(res, fields)

    def make_vpc_dict(self, vpc, fields=None):
        res = {
            'id': vpc.id,
            'name': vpc.name,
            'description': vpc.description,
            'label': vpc.label,
            'status': vpc.status,
            'status_description': vpc.status_description,
            'tenant_id': vpc.tenant_id
        }
        return self._fields(res, fields)

    def make_vlan_dict(self, vlan_db, fields=None):
        res = {
            'id': vlan_db.id,
            'name': vlan_db.name,
            'tag': vlan_db.tag,
            'status': vlan_db.status,
            'status_description': vlan_db.status_description,
            'tenant_id': vlan_db.tenant_id,
            'bridge_group_id': vlan_db.bridge_group_id,
            'vpc_id': vlan_db.vpc_id
        }
        if vlan_db.bridgegroup:
            res['bridge_group_name'] = vlan_db.bridgegroup.name
        if vlan_db.vpc:
            res['vpc_name'] = vlan_db.vpc.name
        return self._fields(res, fields)

    def make_port_dict(self, port_db, fields=None):
        res = {
            'id': port_db.id,
            'name': port_db.name,
            'admin_status': port_db.admin_status,
            'switch_port_mode': port_db.switch_port_mode,
            'description': port_db.description,
            'status': port_db.status,
            'status_description': port_db.status_description,
            'tenant_id': port_db.tenant_id
        }
        if port_db.vlans and len(port_db.vlans) > 0:
            res['vlans'] = []
            for vlan_port_assc in port_db.vlans:
                res['vlans'].append({
                    "vlan": {
                        "id": vlan_port_assc.vlan_id,
                        "tag": vlan_port_assc.vlan.tag,
                        "is_native_vlan": vlan_port_assc.is_native_vlan
                    }
                })

        if port_db.asset_id:
            res['asset_id'] = port_db.asset_id

        if port_db.label:
            res['label'] = port_db.label

        return self._fields(res, fields)

    def make_devicetype_dict(self, device_type_db, fields=None):
        res = {
            'id': device_type_db.id,
            'name': device_type_db.name,
            'type': device_type_db.type,
            'status': device_type_db.status,
            'status_description': device_type_db.status_description,
            'tenant_id': device_type_db.tenant_id
        }
        return self._fields(res, fields)

    def make_device_dict(self, device_db, fields=None):
        res = {
            'id': device_db.id,
            'name': device_db.name,
            'description': device_db.description,
            'management_ip': device_db.management_ip,
            'type': device_db.device_type.type,
            'username': device_db.username,
            'ports': [p.id for p in device_db.ports],
            'status': device_db.status,
            'status_description': device_db.status_description,
            'os_type': device_db.os_type,
            'tenant_id': device_db.tenant_id,
            'bubble_id': device_db.bubble_id
        }
        return self._fields(res, fields)

    def make_vlanportassociation_dict(self, vlan_port_association_db,
                                      fields=None):
        res = {
            'id': vlan_port_association_db.id,
            'vlan_id': vlan_port_association_db.vlan_id,
            'port_id': vlan_port_association_db.port_id,
            'status': vlan_port_association_db.status,
            'status_description': vlan_port_association_db.status_description,
            'is_native_vlan': vlan_port_association_db.is_native_vlan,
            'tenant_id': vlan_port_association_db.tenant_id
        }
        return self._fields(res, fields)

    def make_subnet_dict(self, subnet_db, fields=None):
        res = {
            'id': subnet_db.id,
            'tenant_id': subnet_db.tenant_id,
            'name': subnet_db.name,
            'cidr': subnet_db.cidr,
            'gateway_ip': subnet_db.gateway_ip,
            'broadcast_ip': subnet_db.broadcast_ip,
            'netmask': subnet_db.netmask,
            'vlan_id': subnet_db.vlan_id,
            'status': subnet_db.status
        }
        return self._fields(res, fields)

    def _make_get_port_dict(self, port_id, port_name, native_vlan, vlan_tags,
                            mode, status, description, tenant_id, port_db,
                            fields):
        res = {
            'id': port_id,
            'tenant_id': tenant_id,
            'name': port_name,
            'switch_port_mode': mode,
            'description': port_db.description,
            'status': port_db.status,
            'status_description': port_db.status_description,
            'label': description
        }
        res['vlans'] = []
        for vlan in vlan_tags:
            is_native_vlan = False
            if vlan == native_vlan:
                is_native_vlan = True
            res['vlans'].append({
                "vlan": {
                    "tag": vlan,
                    "is_native_vlan": is_native_vlan
                }
            })
        admin_status = 'ACTIVE' if status == 'enabled' else 'SUSPENDED'
        res['admin_status'] = admin_status
        if port_db.asset_id:
            res['asset_id'] = port_db.asset_id

        return self._fields(res, fields)

    def make_bubble_dict(self, bubble_db, fields=None):
        res = {
            'id': bubble_db.id,
            'name': bubble_db.name,
            'tenant_id': bubble_db.tenant_id
        }
        return self._fields(res, fields)

    def make_vrf_dict(self, vrf_db, fields=None):
        res = {
            'id': vrf_db.id,
            'name': vrf_db.name,
            'tenant_id': vrf_db.tenant_id,
            'description': vrf_db.description,
            'bubble_id': vrf_db.bubble_id,
            'vpc_id': vrf_db.vpc_id,

        }
        return self._fields(res, fields)
