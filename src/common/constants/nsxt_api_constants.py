"""
General convention for adding fields:
- All the API endpoints must start with '/' prefix and the base URL must not have a trailing '/'
"""
from enum import Enum


class NsxTEndpoint(str, Enum):
    VMC_BASE_URL = "{url}/orgs/{org_id}/sddcs/{sddc_id}"
    LIST_SEGMENTS = '/policy/api/v1/infra/tier-1s/{gw_id}/segments/'
    CRUD_SEGMENT = '/policy/api/v1/infra/tier-1s/{gw_id}/segments/{segment_id}'
    LIST_GROUPS = '/policy/api/v1/infra/domains/{gw_id}/groups/'
    CRUD_GROUP = '/policy/api/v1/infra/domains/{gw_id}/groups/{group_id}'
    LIST_SERVICES = '/policy/api/v1/infra/services'
    CRUD_SERVICE = '/policy/api/v1/infra/services/{service_id}'
    LIST_GATEWAY_FIREWALL_RULES = '/policy/api/v1/infra/domains/{gw_id}/gateway-policies/{gw_policy_id}/rules'
    CRUD_GATEWAY_FIREWALL_RULE = '/policy/api/v1/infra/domains/{gw_id}/gateway-policies/{gw_policy_id}/rules/{rule_id}'


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
