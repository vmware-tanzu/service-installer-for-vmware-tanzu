import logging
from flask import Blueprint, Flask, jsonify, request
import requests
import json

logger = logging.getLogger(__name__)
from flask import current_app
import sys
import base64
import time

sys.path.append(".../")
from common.operation.ShellHelper import runShellCommandAndReturnOutput, grabKubectlCommand, grabIpAddress, \
    verifyPodsAreRunning, grabPipeOutput, runShellCommandAndReturnOutputAsList, \
    runShellCommandAndReturnOutputAsListWithChangedDir, grabPipeOutputChagedDir, grabIpAddress, runProcess
from common.operation.constants import SegmentsName, RegexPattern, Versions, AkoType, AppName, Env
from common.lib.nsxt_client import NsxtClient
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
deploy_app = Blueprint("deploy_app", __name__, static_folder="deployApp")


@deploy_app.route('/vsphere/deployApp', methods=['POST'])
def deployKaurdApp():
    env = None
    try:
        env = request.headers['Env']
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Bad Request",
            "ERROR_CODE": "400"
        }
        current_app.logger.error("No env headers passed")
        return jsonify(d), 400
    if env is None:
        d = {
            "responseType": "ERROR",
            "msg": "Bad Request",
            "ERROR_CODE": "400"
        }
        current_app.logger.error("No env headers found")
        return jsonify(d), 400
    if env == Env.VMC:
        pass
    elif env == Env.VSPHERE or env == Env.VCF:
        pass
    else:
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env type",
            "ERROR_CODE": "400"
        }
        current_app.logger.error("Wrong env type")
        return jsonify(d), 500
    connect = connectToWorkLoadCluster(env)
    if connect[1] != 200:
        d = {
            "responseType": "ERROR",
            "msg": "Failed connect to workload " + str(connect[0]),
            "ERROR_CODE": 500
        }
        current_app.logger.error("Failed connect to workload " + str(connect[0]))
        return jsonify(d), 500
    deploy = depployKaurd()
    if deploy[1] != 200:
        d = {
            "responseType": "ERROR",
            "msg": "Failed deploy kaurd " + str(deploy[0]),
            "ERROR_CODE": 500
        }
        current_app.logger.error("Failed deploy kaurd " + str(deploy[0]))
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Succesfully deployed kaurd " ,
        "ERROR_CODE": 200
    }
    current_app.logger.info("Succesfully deployed kaurd")
    return jsonify(d), 200


@deploy_app.route('/deployApp', methods=['POST'])
def deployApp():
    isAllSegmentAlreadyCreated = True
    try:
        if current_app.config['access_token'] is None:
            current_app.logger.info("Access token not found")
        if current_app.config['ORG_ID'] is None:
            current_app.logger.info("ORG_ID not found")
        if current_app.config['SDDC_ID'] is None:
            current_app.logger.info("SDDC_ID not found")
        if current_app.config['NSX_REVERSE_PROXY_URL'] is None:
            current_app.logger.info("NSX_REVERSE_PROXY_URL not found")
        if current_app.config['VC_IP'] is None:
            current_app.logger.info("Vc ip not found")
        if current_app.config['VC_PASSWORD'] is None:
            current_app.logger.info("Vc cred not found")
        if current_app.config['VC_USER'] is None:
            current_app.logger.info("Vc user not found")
    except:
        d = {
            "responseType": "ERROR",
            "msg": "Un-Authorized",
            "ERROR_CODE": 401
        }
        current_app.logger.error("Un-Authorized")
        return jsonify(d), 401
    shared_cluster_name = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
        'tkgSharedClusterName']
    current_app.logger.info("Connect to shared cluster")
    commands_shared = ["tanzu", "cluster", "kubeconfig", "get", shared_cluster_name, "--admin"]
    kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
    if kubeContextCommand_shared is None:
        current_app.logger.error("Failed to get switch to shared cluster context command")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get switch to shared cluster context command",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
    status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
    if status[1] != 0:
        current_app.logger.error("Failed to  switch to shared cluster context " + str(status[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get switch  shared cluster context " + str(status[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    podRunninng_ako_main = ["kubectl", "get", "svc", "-A"]
    podRunninng_ako_grep = ["grep", "envoy"]
    command_status_ako = grabIpAddress(podRunninng_ako_main, podRunninng_ako_grep, RegexPattern.IP_ADDRESS)
    if command_status_ako is None:
        current_app.logger.error("Failed to grab ip address ")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to grab ip address ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    headers = {
        "Content-Type": "application/json",
        "csp-auth-token": current_app.config['access_token']
    }
    listOfDnat = getListOfDnat(headers)
    if not NsxtClient.find_object(listOfDnat, "Ext-Harbor_automation"):
        body = {
            "action": "DNAT",
            "destination_network": "52.11.108.133",
            "service": "/infra/services/HTTPS",
            "translated_network": str(command_status_ako),
            "translated_ports": "443",
            "logging": False,
            "enabled": True,
            "scope": ["/infra/labels/cgw-public"],
            "firewall_match": "MATCH_INTERNAL_ADDRESS",
            "display_name": "Ext-Harbor_automation"
        }
        url = current_app.config[
                  'NSX_REVERSE_PROXY_URL'] + "orgs/" + current_app.config['ORG_ID'] + "/sddcs/" + current_app.config[
                  'SDDC_ID'] + "/policy/api/v1/infra/tier-1s/cgw/nat/USER/nat-rules/Ext-Harbor_automation"
        response = createExt(body, url, "external harbor")
        if response[1] != 200:
            return response[0]
    listOfGroups = NsxtClient(current_app.config).list_groups(gateway_id='cgw')
    if not NsxtClient.find_object(listOfGroups, "Shared-Service-Ingress-IP_automation"):
        body = {
            "display_name": "Shared-Service-Ingress-IP_automation",
            "expression": [
                {
                    "resource_type": "IPAddressExpression",
                    "ip_addresses": [
                        str(command_status_ako)
                    ]
                }
            ]
        }
        url = current_app.config[
                  'NSX_REVERSE_PROXY_URL'] + "orgs/" + current_app.config['ORG_ID'] + "/sddcs/" + current_app.config[
                  'SDDC_ID'] + "/policy/api/v1/infra/domains/cgw/groups/Shared-Service-Ingress-IP_automation"
        response = createExt(body, url, "external harbor group")
        if response[1] != 200:
            return response[0]
    listOfGroups = NsxtClient(current_app.config).list_gateway_firewall_rules(gw_id='cgw')
    if not NsxtClient.find_object(listOfGroups, "Ext-Harbor_automation"):
        body = {
            "action": "ALLOW",
            "display_name": "Ext-Harbor_automation",
            "logged": False,
            "source_groups": [
                "ANY"
            ],
            "destination_groups": [
                "/infra/domains/cgw/groups/Shared-Service-Ingress-IP_automation"
            ],
            "services": [
                "/infra/services/HTTPS"
            ],
            "scope": [
                "/infra/labels/cgw-all"
            ]
        }
        url = current_app.config[
                  'NSX_REVERSE_PROXY_URL'] + "orgs/" + current_app.config['ORG_ID'] + "/sddcs/" + current_app.config[
                  'SDDC_ID'] + "/policy/api/v1/infra/domains/cgw/gateway-policies/default/rules/Ext-Harbor_automation"
        response = createExt(body, url, "harbor firewall")
        if response[1] != 200:
            return response[0]
    connect = connectToWorkLoadCluster()
    if connect[1] != 200:
        d = {
            "responseType": "ERROR",
            "msg": "Failed connect to workload " + str(connect[0]),
            "ERROR_CODE": 500
        }
        current_app.logger.error("Failed connect to workload " + str(connect[0]))
        return jsonify(d), 500
    deploy = deployNginxAndGetIp()
    if deploy[1] != 200:
        d = {
            "responseType": "ERROR",
            "msg": "Failed deploy ngnix " + str(deploy[0]),
            "ERROR_CODE": 500
        }
        current_app.logger.error("Failed deploy ngnix " + str(deploy[0]))
        return jsonify(d), 500

    listOfDnat = getListOfDnat(headers)
    if not NsxtClient.find_object(listOfDnat, "Ext-Ngnx_automation"):
        body = {
            "action": "DNAT",
            "destination_network": "34.223.122.111",
            "service": "/infra/services/HTTP",
            "translated_network": deploy[0],
            "translated_ports": "80",
            "logging": False,
            "enabled": True,
            "scope": ["/infra/labels/cgw-public"],
            "firewall_match": "MATCH_INTERNAL_ADDRESS",
            "display_name": "Ext-Ngnx_automation"
        }
        url = current_app.config['NSX_REVERSE_PROXY_URL'] + "orgs/" + current_app.config['ORG_ID'] + "/sddcs/" + \
              current_app.config['SDDC_ID'] + "/policy/api/v1/infra/tier-1s/cgw/nat/USER/nat-rules/Ext-Ngnx_automation"
        response = createExt(body, url, "Ngnx Dnat")
        if response[1] != 200:
            return response[0]
    listOfGroups = NsxtClient(current_app.config).list_groups(gateway_id='cgw')
    if not NsxtClient.find_object(listOfGroups, "ngnx-App_automation"):
        body = {
            "display_name": "ngnx-App_automation",
            "expression": [
                {
                    "resource_type": "IPAddressExpression",
                    "ip_addresses": [
                        deploy[0]
                    ]
                }
            ]
        }
        url = current_app.config['NSX_REVERSE_PROXY_URL'] + "orgs/" + current_app.config['ORG_ID'] + "/sddcs/" + \
              current_app.config['SDDC_ID'] + "/policy/api/v1/infra/domains/cgw/groups/ngnx-App_automation"
        response = createExt(body, url, "Ngnx group")
        if response[1] != 200:
            return response[0]
    listOfGroups = NsxtClient(current_app.config).list_gateway_firewall_rules(gw_id='cgw')
    if not NsxtClient.find_object(listOfGroups, "Ext-DemoApp"):
        body = {
            "action": "ALLOW",
            "display_name": "Ext-DemoApp",
            "logged": False,
            "source_groups": [
                "ANY"
            ],
            "destination_groups": [
                "/infra/domains/cgw/groups/ngnx-App_automation"
            ],
            "services": [
                "/infra/services/HTTP"
            ],
            "scope": [
                "/infra/labels/cgw-all"
            ]
        }
        url = current_app.config['NSX_REVERSE_PROXY_URL'] + "orgs/" + current_app.config['ORG_ID'] + "/sddcs/" + \
              current_app.config[
                  'SDDC_ID'] + "/policy/api/v1/infra/domains/cgw/gateway-policies/default/rules/Ext-Ngnx_automation"
        response = createExt(body, url, "EXt gatway policy")
        if response[1] != 200:
            return response[0]
    d = {
        "responseType": "SUCCESS",
        "msg": "Sucessfully deployed Ngnx",
        "ERROR_CODE": 200
    }
    current_app.logger.info("Sucessfully deployed Ngnx")
    return jsonify(d), 200


def createExt(body, url, type):
    headers = {
        "Content-Type": "application/json",
        "csp-auth-token": current_app.config['access_token']
    }
    body_modified = json.dumps(body, indent=4)
    response_sddc = requests.request("PUT", url, headers=headers, data=body_modified, verify=False)
    if response_sddc.status_code != 200:
        d = {
            "responseType": "ERROR",
            "msg": response_sddc.text,
            "ERROR_CODE": response_sddc.status_code
        }
        current_app.logger.error("Failed to create  " + type + " " + response_sddc.text)
        return jsonify(d), response_sddc.status_code
    d = {
        "responseType": "SUCCESS",
        "msg": response_sddc.text,
        "ERROR_CODE": response_sddc.status_code
    }
    current_app.logger.info("Successfully created " + type)
    return jsonify(d), response_sddc.status_code


def pushImageToHarbor():
    str_enc = str(request.get_json(force=True)['componentSpec']['harborSpec']['harborPasswordBase64'])
    base64_bytes = str_enc.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password = enc_bytes.decode('ascii').rstrip("\n")
    harborPassword = password
    host = request.get_json(force=True)['componentSpec']['harborSpec']['harborFqdn']
    docker_login = ["docker", "login", host, "-u", "admin", "-p", harborPassword]
    helm_command = ["helm", "repo", "add", "bitnami", "https://charts.bitnami.com/bitnami"]
    docker_pull = ["docker", "pull", "bitnami/nginx"]
    docker_tag = ["docker", "tag", "bitnami/nginx:latest harbor.tanzu.cc/library/nginx:latest"]
    docker_push = ["docker", "push", "harbor.tanzu.cc/library/nginx:latest"]
    try:
        runProcess(docker_login)
        runProcess(helm_command)
        runProcess(docker_pull)
        runProcess(docker_tag)
        runProcess(docker_push)
    except Exception as e:
        return str(e), 500
    return "SUCCEES", 200


def connectToWorkLoadCluster(env):
    if env == Env.VMC:
        workload_cluster_name = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
            'tkgWorkloadClusterName']
    else:
        workload_cluster_name = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterName']
    current_app.logger.info("Connect to workload cluster")
    commands_shared = ["tanzu", "cluster", "kubeconfig", "get", workload_cluster_name, "--admin"]
    kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
    if kubeContextCommand_shared is None:
        current_app.logger.error("Failed to get switch to workload cluster context command")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get switch to workload cluster context command",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
    status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
    if status[1] != 0:
        current_app.logger.error("Failed to switch to workload cluster context " + str(status[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to switch to workload cluster context " + str(status[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Switch to workload cluster context ",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def depployKaurd():
    apply_kaurd = ["kubectl", "run", "--restart=Always", "--image=gcr.io/kuar-demo/kuard-amd64:blue", "kuard"]

    app = runShellCommandAndReturnOutput(apply_kaurd)
    if app[1] != 0:
        current_app.logger.error("Failed to apply kaurd " + str(app[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to apply ngnx " + str(app[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    apply_kaurd_expose = ["kubectl", "expose", "pod", "kuard", "--type=LoadBalancer", "--port=80", "--target-port=8080"]

    app = runShellCommandAndReturnOutput(apply_kaurd_expose)
    if app[1] != 0:
        current_app.logger.error("Failed to apply kaurd expose " + str(app[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to apply kaurd expose  " + str(app[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Applied and exposed kaurd  ",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def deployNginxAndGetIp():
    apply_nginx = ["kubectl", "apply", "-f" "deployApp/nginx.yaml"]

    app = runShellCommandAndReturnOutput(apply_nginx)
    if app[1] != 0:
        current_app.logger.error("Failed to apply ngnx " + str(app[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to apply ngnx " + str(app[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if not waitTillPodsRunning():
        current_app.logger.error("Ngnix is not running")
        d = {
            "responseType": "ERROR",
            "msg": "Ngnix is not running",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    get_ngnx_ip_1 = ["kubectl", "get", "svc"]
    get_ngnx_ip_2 = ["grep", "mynginx1-service"]
    command_status_ako = grabIpAddress(get_ngnx_ip_1, get_ngnx_ip_2, RegexPattern.IP_ADDRESS)
    if command_status_ako is None:
        current_app.logger.error("Failed to grab ip address ")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to grab ip address ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    else:
        current_app.logger.info("Ngnix is up and running")
        return command_status_ako, 200


def getListOfDnat(headers):
    payload = {}
    firewall_rule_CGW_url = current_app.config['NSX_REVERSE_PROXY_URL'] \
                            + "orgs/" + current_app.config[
                                'ORG_ID'] + "/sddcs/" + current_app.config[
                                'SDDC_ID'] + "/policy/api/v1/infra/tier-1s/cgw/nat/USER/nat-rules/"

    firewall_rule_CGW = requests.request("GET", firewall_rule_CGW_url, headers=headers,
                                         data=payload,
                                         verify=False)
    if firewall_rule_CGW.status_code != 200:
        d = {
            "responseType": "ERROR",
            "msg": firewall_rule_CGW.json(),
            "ERROR_CODE": firewall_rule_CGW.status_code
        }
        current_app.logger.error(firewall_rule_CGW.json())
        return jsonify(d), firewall_rule_CGW.status_code
    return firewall_rule_CGW.json()["results"]


def waitTillPodsRunning():
    count = 0
    while True and count < 30:
        ensure_pods_running = ["kubectl", "get", "pods"]
        status = runShellCommandAndReturnOutputAsList(ensure_pods_running)
        if status[1] != 0:
            return False
        if not verifyPodsAreRunning("mynginx1", status[0], RegexPattern.RUNNING):
            count = count + 1
            time.sleep(10)
            current_app.logger.info("waited " + str(count * 10) + "s")
        else:
            return True
    return False
