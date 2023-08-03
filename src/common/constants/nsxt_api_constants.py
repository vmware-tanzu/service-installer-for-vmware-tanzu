# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

"""
General convention for adding fields:
- All the API endpoints must start with '/' prefix and the base URL must not have a trailing '/'
"""
from enum import Enum

from common.operation.constants import Env


class NsxTEndpoint:
    VMC_BASE_URL = "{url}/orgs/{org_id}/sddcs/{sddc_id}"
    NSX_BASE_URL = "https://{url}"
    LIST_SEGMENTS = {"vmc": "/policy/api/v1/infra/tier-1s/{gw_id}/segments/", "vcf": "/policy/api/v1/infra/segments"}
    CRUD_SEGMENT = {
        Env.VMC: "/policy/api/v1/infra/tier-1s/{gw_id}/segments/{segment_id}",
        Env.VCF: "/policy/api/v1/infra/segments/{segment_id}",
    }
    LIST_GROUPS = {
        Env.VMC: "/policy/api/v1/infra/domains/{gw_id}/groups/",
        Env.VCF: "/policy/api/v1/infra/domains/{domain_name}/groups/",
    }
    CRUD_GROUP = {
        Env.VMC: "/policy/api/v1/infra/domains/{gw_id}/groups/{group_id}",
        Env.VCF: "/policy/api/v1/infra/domains/{domain_name}/groups/{group_name}",
    }
    LIST_GATEWAY_FIREWALL_RULES = {
        Env.VMC: "/policy/api/v1/infra/domains/{gw_id}/gateway-policies/{gw_policy_id}/rules",
        Env.VCF: "/policy/api/v1/infra/domains/default/gateway-policies/{policy_name}/rules",
    }
    CRUD_GATEWAY_FIREWALL_RULE = {
        Env.VMC: "/policy/api/v1/infra/domains/{gw_id}/gateway-policies/{gw_policy_id}/rules/{rule_id}",
        Env.VCF: "/policy/api/v1/infra/domains/default/gateway-policies/{policy_name}/rules/{rule_id}",
    }
    LIST_SERVICES = "/policy/api/v1/infra/services"
    CRUD_SERVICE = "/policy/api/v1/infra/services/{service_id}"
    LIST_DHCP_SERVERS = "/policy/api/v1/infra/dhcp-server-configs"
    CRUD_DHCP_SERVERS = "/policy/api/v1/infra/dhcp-server-configs/{server_name}"
    LIST_TIER1 = "/policy/api/v1/infra/tier-1s"
    LIST_TRANSPORT_ZONES = "/api/v1/transport-zones/"
    LIST_DOMAINS = "/policy/api/v1/infra/domains/"
    LIST_POLICIES = "/policy/api/v1/infra/domains/default/gateway-policies"
    CREATE_UPDATE_POLICY = "/policy/api/v1/infra"


class NsxTPayload(str, Enum):
    CREATE_UPDATE_SEGMENT = """
    {{ "display_name": "{name}",
      "subnets": [{{
          "gateway_address": "{gateway}",
          "dhcp_ranges": [ "{dhcp_start}-{dhcp_end}" ],
          "dhcp_config": {{
            "resource_type": "SegmentDhcpV4Config",
            "dns_servers": {dns_servers}
          }} }} ] }}
    """

    CREATE_UPDATE_GROUP = """
    {{ "display_name": "{name}",
      "expression": [ {expression} ]
    }}
    """

    PATH_EXPRESSION = """
    {{ "resource_type": "PathExpression",
       "paths": {paths}
    }}
    """

    IP_ADDRESS_EXPRESSION = """
    {{ "resource_type": "IPAddressExpression",
       "ip_addresses": {ip_addresses}
    }}
    """

    CREATE_UPDATE_SERVICE = """
        {{ "service_entries": [ {{
                    "display_name": {service_entry_name},
                    "resource_type": "L4PortSetServiceEntry",
                    "l4_protocol": "TCP",
                    "destination_ports": ["6443"]
                }} ]
        }}
    """

    CREATE_UPDATE_FIREWALL_RULE = """
    {{ "action": "ALLOW",
       "source_groups": {src_groups},
       "destination_groups": {dest_groups},
       "services": {services},
       "scope": {scope}
    }}
    """

    CREATE_DHCP_SERVER = """
    {{ "display_name": {server_name},
       "resource_type": "DhcpServerConfig",
       "lease_time": 86400,
       "id": {server_id},
    }}
    """


class VcfPayload(str, Enum):
    CREATE_UPDATE_SEGMENT = """
    {{
    "display_name": "{name}",
    "subnets": [
    {{
    "gateway_address": "{gateway}"
    }}],
    "replication_mode": "MTEP",
    "transport_zone_path": "/infra/sites/default/enforcement-points/default/transport-zones/{transport_zone}",
    "admin_state": "UP",
    "advanced_config": {{
        "address_pool_paths": [],
        "multicast": "True",
        "urpf_mode": "STRICT",
        "connectivity": "ON"
    }},
    "connectivity_path": "{tier_path}",
    "id": "{name}"
    }}
    """

    CREATE_UPDATE_SEGMENT_WITH_DHCP = """
    {{
    "display_name": "{name}",
    "subnets": [
        {{
            "gateway_address": "{gateway}",
            "dhcp_ranges": ["{dhcp_start}-{dhcp_end}"],
            "dhcp_config": {{
                "resource_type": "SegmentDhcpV4Config",
                "lease_time": 86400,
                "dns_servers": {dns_servers},
                "options": {{
                    "others": [{{"code": 42, "values": {ntp_servers}
                    }}]
                }}
            }},
            "network": "{network}"
        }}
    ],
    "connectivity_path": "{tier_path}",
    "transport_zone_path": "/infra/sites/default/enforcement-points/default/transport-zones/{transport_zone}",
    "id": "{name}"
    }}
    """

    CREATE_UPDATE_SERVICE = """
    {{
    "service_entries": [
        {{
            "display_name": "{service_name}",
            "resource_type": "L4PortSetServiceEntry",
            "l4_protocol": "TCP",
            "destination_ports": [{port}]
        }}
    ],
    "display_name": "{service_name}",
    "id": "{service_name}"
    }}
    """

    CREATE_UPDATE_FIREWALL_RULE = """
    {{
       "action": "ALLOW",
       "display_name": {name},
       "logged": False,
       "source_groups": ["ANY"],
       "destination_groups": [{groups}],
       "services": ["/infra/services/SSH", "/infra/services/" +{service_name}],
       "scope": [{teir1}]
    }}
    """

    CREATE_UPDATE_POLICY = """
    {{
        "resource_type": "Infra",
        "children": [
            {{
                "resource_type": "ChildResourceReference",
                "id": "default",
                "target_type": "Domain",
                "children": [
                    {{
                        "resource_type": "ChildGatewayPolicy",
                        "marked_for_delete": "False",
                        "GatewayPolicy": {{
                            "resource_type": "GatewayPolicy",
                            "display_name": "{policy_name}",
                            "id": "{policy_name}",
                            "marked_for_delete": "False",
                            "tcp_strict": "True",
                            "stateful": "True",
                            "locked": "False",
                            "category": "LocalGatewayRules",
                            "sequence_number": 10,
                            "children": [
                                {{
                                    "resource_type": "ChildRule",
                                    "marked_for_delete": "False",
                                    "Rule": {{
                                        "display_name": "default_rule",
                                        "id": "default_rule",
                                        "resource_type": "Rule",
                                        "marked_for_delete": "False",
                                        "source_groups": ["ANY"],
                                        "sequence_number": 10,
                                        "destination_groups": ["ANY"],
                                        "services": ["ANY"],
                                        "profiles": ["ANY"],
                                        "scope": ["{tier_path}"],
                                        "action": "ALLOW",
                                        "direction": "IN_OUT",
                                        "logged": "False",
                                        "disabled": "False",
                                        "notes": "",
                                        "tag": "",
                                        "ip_protocol": "IPV4_IPV6"
                                    }}
                                }}
                            ]
                        }}
                    }}
                ]
            }}
        ]
    }}
    """

    CREATE_UPDATE_FIREWALL = """
    {{
       "action": "ALLOW",
       "display_name": "{rule_id}",
       "logged": "False",
       "source_groups": {source_groups},
       "destination_groups": {destination_groups},
       "services": {services},
       "scope": ["{tier}"]
    }}
    """


class NsxWorkflows:
    MANAGEMENT = "management"
    WORKLOAD = "workload"
    SHARED = "shared"
