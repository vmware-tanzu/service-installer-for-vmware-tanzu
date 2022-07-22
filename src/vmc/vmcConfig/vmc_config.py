import sys

import requests
from flask import current_app, Blueprint, jsonify, request

sys.path.append(".../")
from vmc.vmcConfig.nsxt_workflow import NsxtWorkflow
from common.model.vmcSpec import VmcMasterSpec
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

vmc_config = Blueprint("vmc_config", __name__, static_folder="vmcConfig")


@vmc_config.route('/api/tanzu/vmc/envconfig', methods=['POST'])
def config_vmc_env():
    try:
        spec_json = request.get_json(force=True)
        spec: VmcMasterSpec = VmcMasterSpec.parse_obj(spec_json)
        NsxtWorkflow(spec, current_app.config, current_app.logger).execute_workflow()
    except ValueError as ex:
        response_body = {
            "responseType": "ERROR",
            "msg": str(ex),
            "ERROR_CODE": 500
        }
        return jsonify(response_body), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Vmc configured Successfully",
        "ERROR_CODE": 200
    }
    current_app.logger.info("Vmc configured Successfully ")
    return jsonify(d), 200


# Removed following endpoints as all operations are covered by NsxtWorkflow::execute_workflow()
# Also, since all of the above operations are idempotent, we don't need specific APIs
# The spec should be used for driving the operations being done.
# e.g.: If users override network names with existing nw in the spec, a new network won't be created using that name,
# it will be skipped during checks.

# @vmc_config.route('/api/tanzu/vmc/env/groups/mgmt', methods=['POST'])
# def groupsConfig():
#     pass
#
#
# @vmc_config.route('/api/tanzu/vmc/env/firewall/mgmt', methods=['POST'])
# def firewallConfig():
#     pass
#
#
# @vmc_config.route('/api/tanzu/vmc/env/networks/mgmt', methods=['POST'])
# def create_segments():
#     pass
#
#
# @vmc_config.route('/api/tanzu/vmc/env/groups/cgw', methods=['POST'])
# def createGroupsOnCGW():
#     pass
#
#
# @vmc_config.route('/api/tanzu/vmc/env/groups/mgw', methods=['POST'])
# def createGroupsOnMGW():
#     pass
#
#
# @vmc_config.route('/api/v1/tanzu/vmc/env/createservice', methods=['POST'])
# def createKubeService():
#     pass
#
#
# @vmc_config.route('/api/tanzu/vmc/env/firewall/mgmt/cgw', methods=['POST'])
# def createFirewallCgw():
#     pass
#
#
# @vmc_config.route('/api/tanzu/vmc/env/firewall/mgmt/mgw', methods=['POST'])
# def createFirewallMgw():
#     pass
