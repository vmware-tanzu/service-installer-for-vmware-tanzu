# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import getopt
import sys
import requests
import json
import subprocess
from pathlib import Path
from pkg_resources import get_distribution
import os
import signal
import threading
import time
import base64
from src.vcd.aviConfig.avi_nsx_cloud import nsx_cloud_creation, getCloudSate, isAviHaEnabled
from src.common.operation.constants import CseMarketPlace
from python_terraform import *

__version__ = get_distribution('arcas').version

pro = None
t1 = None
stopThread = False
cat_dict = {}


def version():
    print("version: v" + __version__)


def vmc_pre_configuration(env, file):
    print("Vmc_Pre_Configuration: Configuring vmc pre configuration")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vmc":
            url = "http://localhost:5000/api/tanzu/vmc/envconfig"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Only vmc env type is supported for vmc configuration.")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("VMC pre configuration failed " + str(response.json()))
            safe_exit()
        else:
            print("Vmc_Pre_Configuration: Configuring vmc pre configuration successfully")
    except Exception as e:
        print("VMC pre configuration failed " + str(e))
        safe_exit()


def vcf_pre_configuration(env, file):
    print("Vcf_Pre_Configuration: Configuring vcf pre configuration")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vcf":
            url = "http://localhost:5000/api/tanzu/vsphere/alb/vcf_pre_config"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Only vcf env type is supported for vcf configuration.")
            sys.exit(1)
        if response.json()['STATUS_CODE'] != 200:
            print("VCF pre configuration failed " + str(response.json()))
            sys.exit(1)
        else:
            print("VCF_Pre_Configuration: Configuring vcf pre configuration successfully")
    except Exception as e:
        print("VCF pre configuration failed " + str(e))
        sys.exit(1)


def all(env, file):
    print("Configuring tkgm...")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        url = "http://localhost:5000/api/tanzu/vmc/tkgm"
        response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        # print(response.json()['STATUS_CODE'])
        if response.json()['STATUS_CODE'] != 200:
            print("Tkm configuration failed " + str(response.json()))
            safe_exit()
        else:
            print(str(response.json()['msg']))
    except Exception as e:
        print("Tkm configuration failed " + str(e))
        safe_exit()


def avi_wcp_configuration(env, file):
    print("AVI_Configuration: Configuring wcp")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vsphere":
            url = "http://localhost:5000/api/tanzu/vsphere/tkgmgmt/alb/config"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Wrong env type, please specify vmc or vsphere")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("Avi wcp configuration failed " + str(response.json()))
            safe_exit()
        else:
            print("AVI_Configuration: Configured wcp Successfully")
    except Exception as e:
        print("Avi wcp configuration failed " + str(e))
        safe_exit()


def enable_wcp(env, file):
    print("Enable_Wcp: Enabling  WCP")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vsphere":
            url = "http://localhost:5000/api/tanzu/vsphere/enablewcp"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Wrong env type, please specify vmc or vsphere")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("Enable WCP configuration failed " + str(response.json()))
            safe_exit()
        else:
            print("Enable_Wcp: Enabled  WCP Successfully")
    except Exception as e:
        print("Enable WCP configuration failed " + str(e))
        safe_exit()


def avi_configuration(env, file):
    print("AVI_Configuration: Configuring AVI")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vmc":
            url = "http://localhost:5000/api/tanzu/vmc/alb"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        elif env == "vsphere" or env == "vcf":
            url = "http://localhost:5000/api/tanzu/vsphere/alb"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Wrong env type, please specify vmc or vsphere")
            safe_exit()
            return "Failed"
        if response.json()['STATUS_CODE'] != 200:
            print("Avi configuration failed " + str(response.json()))
            safe_exit()
            return "Failed"
        else:
            print("AVI_Configuration: AVI configured Successfully")
            return "SUCCESS"
    except Exception as e:
        print("Avi configuration failed " + str(e))
        safe_exit()
        return "Failed"


def precheck_env(env, file):
    print("Session: Performing prechecks")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    if env == "vmc":
        pass
    elif env == "vsphere":
        pass
    elif env == "vcf":
        pass
    elif env == "vcd":
        import sys

        """class Logger(object):
            def __init__(self):
                self.terminal = sys.stdout
                self.log = open("/var/log/server/arcas..log", "a")

            def write(self, message):
                self.terminal.write(message)
                self.log.write(message)

            def flush(self):
                # this flush method is needed for python 3 compatibility.
                # this handles the flush command by doing nothing.
                # you might want to specify some extra behavior here.
                pass

        sys.stdout = Logger()"""
        pass
    else:
        print("Wrong env type, please specify vmc or vsphere")
        safe_exit()
    if env == "vcd":
        headers1 = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Env': 'vsphere'
        }
        with open(file, "r") as file_read:
            data = json.load(file_read)
        isDeploy = data['envSpec']['aviCtrlDeploySpec']['deployAvi']
        if isDeploy == "true":
            write_temp_json_file(file)
            url = "http://localhost:5000/api/tanzu/vmc/env/session"
            file1 = "/opt/vmware/arcas/src/vcd/vcd_avi.json"
            requests.request("POST", url, headers=headers1, data=open(file1, 'rb'), verify=False)
        avi_var_file = "/opt/vmware/arcas/src/vcd/avi.json"
        isAviDeploy = data['envSpec']['aviCtrlDeploySpec']['deployAvi']
        if isAviDeploy == "false":
            avi_fqdn = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterFqdn']
            ip = avi_fqdn
        else:
            avi_fqdn = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Fqdn']
            if isAviHaEnabled(data):
                aviClusterFqdn = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterFqdn']
                ip = aviClusterFqdn
            else:
                ip = avi_fqdn
        out = {
            "aviFqdn": ip
        }
        with open(avi_var_file, "w") as file_out:
            file_out.write(json.dumps(out, indent=4))

        net_file = "/opt/vmware/arcas/src/vcd/net.json"

        out_net = {
            "create_t1_gtw": "true",
            "create_vcd_rtd_net": "true"
        }
        with open(net_file, "w") as file_out:
            file_out.write(json.dumps(out_net, indent=4))
        create_files(env, data, file)
        url = "http://localhost:5000/api/tanzu/getNsxManager"
        response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        if response.json()['STATUS_CODE'] != 200:
            print("Precheck failed " + str(response.json()))
            safe_exit()
    try:
        if env == "vcd":
            url = "http://localhost:5000/api/tanzu/vcdprecheck"
        else:
            url = "http://localhost:5000/api/tanzu/precheck"
        response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)

        if response.json()['STATUS_CODE'] != 200:
            print("Precheck failed " + str(response.json()))
            safe_exit()
        else:
            print("Session: " + str(response.json()['msg']))
    except Exception as e:
        print("Pre-check failed " + str(e))
        safe_exit()


def managemnet_configuration(env, file):
    print("TKG_Mgmt_Configuration: Configuring TKG Management Cluster")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vmc":
            url = "http://localhost:5000/api/tanzu/vmc/tkgmgmt"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        elif env == "vsphere" or env == "vcf":
            url = "http://localhost:5000/api/tanzu/vsphere/tkgmgmt"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Wrong env type, please specify vmc or vsphre")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("Management configuration failed " + str(response.json()))
            safe_exit()
        else:
            print("TKG_Mgmt_Configuration: TKG Management cluster deployed and configured Successfully")
    except Exception as e:
        print("Management configuration failed " + str(e))
        safe_exit()


def deployapp(env, file):
    print("Deploying sample app....")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vmc":
            url = "http://localhost:5000/deployApp"
        elif env == "vsphere" or env == "vcf":
            url = "http://localhost:5000/vsphere/deployApp"
        else:
            print("Wrong env type, please specify vmc or vsphere")
            safe_exit()
        response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        if response.json()['STATUS_CODE'] != 200:
            print("Deploy app: " + str(response.json()))
            safe_exit()
        else:
            print(str(response.json()['msg']))
    except Exception as e:
        print("Deploy app failed " + str(e))
        safe_exit()


def shared_service_configuration(env, file):
    print("Shared_Service_Configuration: Configuring TKG Shared Services Cluster")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vmc":
            url = "http://localhost:5000/api/tanzu/vmc/tkgsharedsvc"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        elif env == "vsphere" or env == "vcf":
            url = "http://localhost:5000/api/tanzu/vsphere/tkgsharedsvc"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Wrong env type, please specify vmc or vsphre")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("Shared service configuration failed : " + str(response.json()))
            safe_exit()
        else:
            print("Shared_Service_Configuration: TKG Shared Services Cluster deployed and configured Successfully")
    except Exception as e:
        print("Shared service configuration failed : " + str(e))
        safe_exit()


def deploy_extentions(env, file):
    print("Deploy_Extentions: Deploying extensions")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vmc":
            url = "http://localhost:5000/api/tanzu/extentions"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        elif env == "vsphere" or env == "vcf":
            url = "http://localhost:5000/api/tanzu/extentions"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Wrong env type, please specify vmc or vsphere or vcf")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("Deploy extensions failed" + str(response.json()))
            safe_exit()
        else:
            print("Deploy_Extensions: Deployed extensions Successfully")
    except Exception as e:
        print("Deploy extensions failed" + str(e))
        safe_exit()


def vcd_avi_configuration(env, file):
    if env == "vcd":
        env = "vsphere"
        file1 = file
        with open(file1, "r") as file_read:
            read = file_read.read()
        with open("/opt/vmware/arcas/src/vcd/tf-input.json", "w") as file_write:
            file_write.write(read)
        with open("/opt/vmware/arcas/src/vcd/tf-input.json", "r") as out:
            data1 = json.load(out)
        isDeploy = data1['envSpec']['aviCtrlDeploySpec']['deployAvi']
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Env': env
        }
        if str(isDeploy).lower() == "true":
            file1 = "/opt/vmware/arcas/src/vcd/vcd_avi.json"
            avi_configuration(env, file1)
        else:
            print("INFO: Performing validations")
        isImportAviToVcd = get_state_form_vcd(file, env, "avi")
        if isImportAviToVcd == "true":
            url = "http://localhost:5000/api/tanzu/upload_avi_cert"
            res = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
            if res.json()['STATUS_CODE'] != 200:
                print("Upload cert failed " + str(res.json()))
                safe_exit()
            else:
                print("INFO:  Upload cert  Successfully")
            out = {
                "import_ctrl": "true",
                "import_cloud": "false",
                "import_seg": "false"
            }
            with open("/opt/vmware/arcas/src/vcd/vars.tfvars.json", "w") as file_out:
                file_out.write(json.dumps(out, indent=4))
            os.environ['TF_LOG'] = "DEBUG"
            os.environ['TF_LOG_PATH'] = "/var/log/server/arcas.log"
            tf = Terraform(working_dir='/opt/vmware/arcas/src/vcd')
            return_code, stdout, stderr = tf.init(capture_output=False)
            return_code, stdout, stderr = tf.apply(target='module.nsx-alb-res', capture_output=False, skip_plan=True,
                                                   auto_approve=True)
            if return_code != 0:
                print(stderr)
                sys.exit(1)
        else:
            out = {
                "import_ctrl": "false",
                "import_cloud": "false",
                "import_seg": "false"
            }
            print("INFO: Avi imported to Vcd")


def get_state_form_vcd(file, env, type):
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    cloud_state = getCloudSate(file)
    if type == "cloud":
        url = "http://localhost:5000/api/tanzu/listCloudVcd"
    elif type == "avi":
        url = "http://localhost:5000/api/tanzu/listAviVcd"
    elif type == "seg":
        url = "http://localhost:5000/api/tanzu/listSegVcd"
    elif type == "org":
        url = "http://localhost:5000/api/tanzu/listOrgVcd"
    elif type == "org_vdc":
        url = "http://localhost:5000/api/tanzu/listOrgVdc"
    elif type == "networks":
        url = "http://localhost:5000/api/tanzu/listNetworksOrg"
    else:
        print("ERROR: Wrong type")
        url = ""
        safe_exit()

    response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
    if response.status_code != 200:
        print("ERROR: Failed get list " + str(response.text))
        safe_exit()
    present = False
    with open(file, "r") as out:
        data1 = json.load(out)
    if type == "cloud":
        name = data1['envSpec']['aviNsxCloudSpec']['nsxtCloudVcdDisplayName']
        res = response.json()["NSXT_CLOUD_VCD_LIST"]
    elif type == "avi":
        name = data1['envSpec']['aviCtrlDeploySpec']['aviVcdDisplayName']
        res = response.json()["AVI_VCD_LIST"]
    elif type == "seg":
        name = data1['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['serviceEngineGroupVcdDisplayName']
        res = response.json()["SEG_VDC_LIST"]
    elif type == "org":
        name = data1['envSpec']['cseSpec']['svcOrgSpec']['svcOrgName']
        res = response.json()["ORG_LIST_VCD"]
    elif type == "org_vdc":
        name = data1['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcName']
        res = response.json()["ORG_LIST_VCD"]
    elif type == "networks":
        name = data1['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['networkName']
        res = response.json()["NETWORKS_LIST"]
    else:
        res = ""
        name = ""
        print("ERROR: Wrong type")
        safe_exit()
    for cloud in res:
        if cloud.strip() == name.strip():
            present = True
            break
    if type == "cloud":
        if cloud_state != "FOUND":
            print("ERROR:  Cloud not found in avi")
            safe_exit()
    if present:
        import_cloud = "false"
    else:
        import_cloud = "true"
    return import_cloud


def avi_cloud_configuration(file, env):
    status = nsx_cloud_creation(file, True)
    if status[0] != "SUCCESS":
        safe_exit()
    with open(file, "r") as file_read:
        read = file_read.read()
    with open("/opt/vmware/arcas/src/vcd/tf-input.json", "w") as file_write:
        file_write.write(read)
    with open("/opt/vmware/arcas/src/vcd/tf-input.json", "r") as out1:
        data1 = json.load(out1)
    isDeployCloud = data1['envSpec']['aviNsxCloudSpec']['configureAviNsxtCloud']
    isImported = get_state_form_vcd(file, env, "cloud")
    with open("/opt/vmware/arcas/src/vcd/vars.tfvars.json", "r") as out1:
        data2 = json.load(out1)
    out = {
        "import_ctrl": data2["import_ctrl"],
        "import_cloud": isImported,
        "import_seg": "false"
    }
    with open("/opt/vmware/arcas/src/vcd/vars.tfvars.json", "w") as file_out:
        file_out.write(json.dumps(out, indent=4))
    if str(isDeployCloud).lower() == "true":
        print("INFO:  Validating Nsxt cloud Imported")
        if isImported == "true":
            os.environ['TF_LOG'] = "DEBUG"
            os.environ['TF_LOG_PATH'] = "/var/log/server/arcas.log"
            tf = Terraform(working_dir='/opt/vmware/arcas/src/vcd',
                           var_file="/opt/vmware/arcas/src/vcd/vars.tfvars.json")
            return_code, stdout, stderr = tf.init(capture_output=False)
            return_code, stdout, stderr = tf.apply(target='module.nsx-alb-res', capture_output=False, skip_plan=True,
                                                   auto_approve=True)
            if return_code != 0:
                print(stderr)
                safe_exit()
        else:
            print("INFO: Nsx cloud  is alreeady imported to  vcd")
    else:
        print("INFO:  User opted not to deploy cloud, validating it is present vcd")
        isImported = get_state_form_vcd(file, env, "cloud")
        if isImported == "false":
            print("INFO: Cloud already  imported to vcd")
        else:
            print("ERROR: Cloud not  imported to vcd")


def vcd_org_configuration(file, env):
    with open(file, "r") as file_read:
        read = file_read.read()
    status = nsx_cloud_creation(file, True)
    if status[0] != "SUCCESS":
        safe_exit()
    with open("/opt/vmware/arcas/src/vcd/tf-input.json", "w") as file_write:
        file_write.write(read)
    os.environ['TF_LOG'] = "DEBUG"
    os.environ['TF_LOG_PATH'] = "/var/log/server/arcas.log"
    tf = Terraform(working_dir='/opt/vmware/arcas/src/vcd', var_file="/opt/vmware/arcas/src/vcd/vars.tfvars.json")
    return_code, stdout, stderr = tf.init(capture_output=False)
    isImportAvi_org_ToVcd = get_state_form_vcd(file, env, "org")
    if isImportAvi_org_ToVcd == "true":
        return_code, stdout, stderr = tf.apply(target='module.org', capture_output=False, skip_plan=True,
                                               auto_approve=True)
        if return_code != 0:
            print(stderr)
            safe_exit()
    else:
        print("INFO: Org  is already imported")
    isImportAvi_org_Vcd = get_state_form_vcd(file, env, "org_vdc")
    if isImportAvi_org_Vcd == "true":
        return_code, stdout, stderr = tf.apply(target='module.org-vdc', capture_output=False, skip_plan=True,
                                               auto_approve=True)
        if return_code != 0:
            print(stderr)
            safe_exit()
    else:
        print("INFO: Org  vcd is already imported")

    isImportAvi_seg_ToVcd = get_state_form_vcd(file, env, "seg")
    if isImportAvi_seg_ToVcd == "true":
        with open("/opt/vmware/arcas/src/vcd/vars.tfvars.json", "r") as out1:
            data2 = json.load(out1)
        out = {
            "import_ctrl": data2["import_ctrl"],
            "import_cloud": data2["import_cloud"],
            "import_seg": isImportAvi_seg_ToVcd
        }
        with open("/opt/vmware/arcas/src/vcd/vars.tfvars.json", "w") as file_out:
            file_out.write(json.dumps(out, indent=4))
        return_code, stdout, stderr = tf.apply(target='module.nsx-alb-res', capture_output=False, skip_plan=True,
                                               auto_approve=True)
        if return_code != 0:
            print(stderr)
            safe_exit()
    else:
        print("INFO: Org  Seg is already imported")

    # check gateway and network is present
    net_file = "/opt/vmware/arcas/src/vcd/net.json"
    isImport_network_ToVcd = get_state_form_vcd(file, env, "networks")
    if isImport_network_ToVcd == "false":
        print("INFO: ORG Network is already created")

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    url = "http://localhost:5000/api/tanzu/listTier1Vcd"
    res = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
    if res.json()['STATUS_CODE'] != 200:
        isimport_edge = "true"
    else:
        isimport_edge = "false"
        print("INFO: Tier-1 gateway is already created")

    out_net = {
        "create_t1_gtw": isimport_edge,
        "create_vcd_rtd_net": isImport_network_ToVcd
    }
    with open(net_file, "w") as file_out:
        file_out.write(json.dumps(out_net, indent=4))

    if isimport_edge == "true":
        return_code, stdout, stderr = tf.apply(target='module.networks', capture_output=False, skip_plan=True,
                                               auto_approve=True)
        if return_code != 0:
            print(stderr)
            safe_exit()


def vcd_cse_server_configuration(file, env):
    with open(file, "r") as file_read:
        read = file_read.read()
    with open(file) as f:
        data = json.load(f)
    with open("/opt/vmware/arcas/src/vcd/tf-input.json", "w") as file_write:
        file_write.write(read)
    os.environ['TF_LOG'] = "DEBUG"
    os.environ['TF_LOG_PATH'] = "/var/log/server/arcas.log"
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    tf = Terraform(working_dir='/opt/vmware/arcas/src/vcd')
    return_code, stdout, stderr = tf.init(capture_output=False)
    if cat_dict["cse"] == "true" or cat_dict["k8s"] == "true":
        return_code, stdout, stderr = tf.apply(target='module.catalog', capture_output=False, skip_plan=True,
                                           auto_approve=True)
        if return_code != 0:
            print(stderr)
            safe_exit()
    else:
        print("INFO : Catalogs are already created")
    cse_upload_url = "http://localhost:5000/api/tanzu/upload_cse_catalog"
    response_cse = requests.request("POST", cse_upload_url, headers=headers, data=open(file, 'rb'), verify=False)
    cse_catalog = CseMarketPlace.CSE_OVA_NAME
    if response_cse.json()["STATUS_CODE"] != 200:
        print("ERROR: Failed " + str(response_cse.text))
        safe_exit()
    k8s_upload_url = "http://localhost:5000/api/tanzu/upload_k_catalog"
    response_ks8 = requests.request("POST", k8s_upload_url, headers=headers, data=open(file, 'rb'), verify=False)
    if response_ks8.json()["STATUS_CODE"] != 200:
        print("ERROR: Failed " + str(response_ks8.text))
        safe_exit()

    cse_server_config_file_path = "/opt/vmware/arcas/src/vcd/cse_server.json"
    out = {
        "token": "temp",
        "template_name": cse_catalog
    }
    with open(cse_server_config_file_path, "w") as file_out:
        file_out.write(json.dumps(out, indent=4))

    config_cse_plugin_url = "http://localhost:5000/api/tanzu/configure_cse_plugin"
    response_config_cse_plugin = requests.request("POST", config_cse_plugin_url, headers=headers, data=open(file, 'rb'),
                                                  verify=False)
    if response_config_cse_plugin.json()["STATUS_CODE"] != 200:
        print("ERROR: Failed " + str(response_config_cse_plugin.text))
        safe_exit()
    return_code, stdout, stderr = tf.apply(target='module.cse-config', capture_output=False, skip_plan=True,
                                           auto_approve=True)
    if return_code != 0:
        print(stderr)
        safe_exit()
    create_server_config_url = "http://localhost:5000/api/tanzu/create_server_config_cse"
    response_cse_server_config = requests.request("POST", create_server_config_url, headers=headers,
                                                  data=open(file, 'rb'), verify=False)
    if response_cse_server_config.json()["STATUS_CODE"] != 200:
        print("ERROR: Failed " + str(response_cse_server_config.text))
        safe_exit()

    access_token_url = "http://localhost:5000/api/tanzu/get_access_token_vapp"
    response_access_token = requests.request("POST", access_token_url, headers=headers, data=open(file, 'rb'),
                                             verify=False)
    if response_access_token.json()["STATUS_CODE"] != 200:
        print("ERROR: Failed " + str(response_access_token.text))
        safe_exit()

    cse_server_config_file_path = "/opt/vmware/arcas/src/vcd/cse_server.json"
    out = {
        "token": response_access_token.json()["token"],
        "template_name": cse_catalog
    }
    print("INFO: Waiting for 5m for upload to complete")
    time.sleep(300)
    with open(cse_server_config_file_path, "w") as file_out:
        file_out.write(json.dumps(out, indent=4))
    return_code, stdout, stderr = tf.apply(target='module.vapp', capture_output=False, skip_plan=True,
                                           auto_approve=True)
    if return_code != 0:
        print(stderr)
        safe_exit()


def create_files(env, data, file):
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    list_catalog_url = "http://localhost:5000/api/tanzu/listCatalogVcd"
    cse_catalog = data['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgCatalogSpec']['cseOvaCatalogName']
    response_catalog = requests.request("POST", list_catalog_url, headers=headers, data=open(file, 'rb'), verify=False)
    create_k8s_catalog = "false"
    create_catalog = "false"
    if response_catalog.json()["STATUS_CODE"] != 200:
        if str(response_catalog.json()['msg']).__contains__("List is empty"):
            create_catalog = "true"
            create_k8s_catalog = "true"
            pass
        elif str(response_catalog.json()['msg']).__contains__("Organization not found in VCD"):
            create_catalog = "true"
            create_k8s_catalog = "true"
        else:
            print("ERROR: Failed " + str(response_catalog.text))
            safe_exit()
    elif str(response_catalog.json()['msg']).__contains__("List is empty"):
        create_catalog = "true"
        create_k8s_catalog = "true"
    else:
        cat_list = response_catalog.json()['CATALOG_LIST']
        found = False
        if cat_list is not None:
            for cat in cat_list:
                if cat == cse_catalog:
                    found = True
                    create_catalog = "true"
                    break
        else:
            create_catalog = "true"
        if found:
            create_catalog = "false"
    cse_config_file_path = "/opt/vmware/arcas/src/vcd/cseconfig.json"
    out = {
        "create_catalog": create_catalog,
        "upload_ova": "false",
        "catalog_item_name": cse_catalog,
        "ova_path": "/tmp/cse.ova"
    }
    with open(cse_config_file_path, "w") as file_out:
        file_out.write(json.dumps(out, indent=4))
    k8s_config_file_path = "/opt/vmware/arcas/src/vcd/kconfig.json"
    k8_catalog = data['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgCatalogSpec']['k8sTemplatCatalogName']
    if create_k8s_catalog == "true":
        pass
    else:
        found_ = False
        if cat_list is not None:
            for cat in cat_list:
                if cat == k8s_config_file_path:
                    found_ = True
                    create_k8s_catalog = "true"
                    break
        else:
            create_k8s_catalog = "true"
        if found_:
            create_k8s_catalog = "false"
    out = {
        "create_catalog_k8s": create_k8s_catalog,
        "upload_ova_k8s": "false",
        "catalog_item_name_k8s": k8_catalog,
        "ova_path_k8s": "/tmp/k8s.ova"
    }
    with open(k8s_config_file_path, "w") as file_out:
        file_out.write(json.dumps(out, indent=4))

    cse_server_config_file_path = "/opt/vmware/arcas/src/vcd/cse_server.json"
    out = {
        "token": "temp_value",
        "template_name": "temp"
    }

    cat_dict["cse"] = create_k8s_catalog
    cat_dict["k8s"] = k8_catalog
    with open(cse_server_config_file_path, "w") as file_out:
        file_out.write(json.dumps(out, indent=4))


def write_temp_json_file(file):
    with open(file) as f:
        data = json.load(f)

    str_enc = str(data['envSpec']['aviCtrlDeploySpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
    base64_bytes = str_enc.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
    sample_string_bytes = VC_PASSWORD.encode("ascii")

    base64_bytes = base64.b64encode(sample_string_bytes)
    base64_string = base64_bytes.decode("ascii")
    vc_adrdress = data['envSpec']['aviCtrlDeploySpec']['vcenterDetails']["vcenterAddress"]
    vc_user = data['envSpec']['aviCtrlDeploySpec']['vcenterDetails']["vcenterSsoUser"]
    vc_datacenter = data['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterDatacenter']
    vc_cluster = data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["vcenterCluster"]

    vc_data_store = data['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterDatastore']
    if not data['envSpec']['aviCtrlDeploySpec']['vcenterDetails']["contentLibraryName"]:
        lib = "TanzuAutomation-Lib"
    else:
        lib = data['envSpec']['aviCtrlDeploySpec']['vcenterDetails']["contentLibraryName"]

    if not data['envSpec']['aviCtrlDeploySpec']['vcenterDetails']["aviOvaName"]:
        VC_AVI_OVA_NAME = "avi-controller"
    else:
        VC_AVI_OVA_NAME = data['envSpec']['aviCtrlDeploySpec']['vcenterDetails']["aviOvaName"]

    if not data['envSpec']['aviCtrlDeploySpec']['vcenterDetails']["resourcePoolName"]:
        res = ""
    else:
        res = data['envSpec']['aviCtrlDeploySpec']['vcenterDetails']["resourcePoolName"]
    if not data['envSpec']['marketplaceSpec']['refreshToken']:
        refreshToken = ""
    else:
        refreshToken = data['envSpec']['marketplaceSpec']['refreshToken']
    dns = data['envSpec']['infraComponents']['dnsServersIp']
    searchDomains = data['envSpec']['infraComponents']['searchDomains']
    ntpServers = data['envSpec']['infraComponents']['ntpServers']
    net = data['envSpec']['aviCtrlDeploySpec']['aviMgmtNetwork']['aviMgmtNetworkGatewayCidr']
    mgmt_pg = data['envSpec']['aviCtrlDeploySpec']['aviMgmtNetwork']['aviMgmtNetworkName']

    enable_avi_ha = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['enableAviHa']
    ctrl1_ip = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController01Ip"]
    ctrl1_fqdn = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController01Fqdn"]
    if enable_avi_ha == "true":
        ctrl2_ip = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController02Ip"]
        ctrl2_fqdn = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController02Fqdn"]
        ctrl3_ip = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController03Ip"]
        ctrl3_fqdn = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController03Fqdn"]
        aviClusterIp = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviClusterIp"]
        aviClusterFqdn = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviClusterFqdn"]
    else:
        ctrl2_ip = ""
        ctrl2_fqdn = ""
        ctrl3_ip = ""
        ctrl3_fqdn = ""
        aviClusterIp = ""
        aviClusterFqdn = ""
    str_enc_avi = str(data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviPasswordBase64'])
    base64_bytes_avi = str_enc_avi.encode('ascii')
    enc_bytes_avi = base64.b64decode(base64_bytes_avi)
    password_avi = enc_bytes_avi.decode('ascii').rstrip("\n")

    sample_string_bytes = password_avi.encode("ascii")

    base64_bytes = base64.b64encode(sample_string_bytes)
    base64_password_avi = base64_bytes.decode("ascii")

    str_enc_avi = str(data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviBackupPassphraseBase64'])
    base64_bytes_avi = str_enc_avi.encode('ascii')
    enc_bytes_avi = base64.b64decode(base64_bytes_avi)
    password_avi_back = enc_bytes_avi.decode('ascii').rstrip("\n")
    sample_string_bytes = password_avi_back.encode("ascii")

    base64_bytes = base64.b64encode(sample_string_bytes)
    base64_string_back = base64_bytes.decode("ascii")
    aviSize = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviSize']
    if not data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviCertPath']:
        cert = ""
    else:
        cert = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviCertPath']
    if not data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviCertKeyPath']:
        cert_key = ""
    else:
        cert_key = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviCertKeyPath']

    data = dict(envSpec=dict(
        vcenterDetails=dict(vcenterAddress=vc_adrdress, vcenterSsoUser=vc_user, vcenterSsoPasswordBase64=base64_string,
                            vcenterDatacenter=vc_datacenter, vcenterCluster=vc_cluster, vcenterDatastore=vc_data_store,
                            contentLibraryName=lib, aviOvaName=VC_AVI_OVA_NAME, resourcePoolName=res),
        marketplaceSpec=dict(refreshToken=refreshToken),
        infraComponents=dict(dnsServersIp=dns, searchDomains=searchDomains, ntpServers=ntpServers)),
        tkgComponentSpec=dict(aviMgmtNetwork=dict(aviMgmtNetworkName=mgmt_pg, aviMgmtNetworkGatewayCidr=net),
                              aviComponents=dict(aviPasswordBase64=base64_password_avi,
                                                 aviBackupPassphraseBase64=base64_string_back,
                                                 enableAviHa=enable_avi_ha, aviController01Ip=ctrl1_ip,
                                                 aviController01Fqdn=ctrl1_fqdn, aviController02Ip=ctrl2_ip,
                                                 aviController02Fqdn=ctrl2_fqdn, aviController03Ip=ctrl3_ip,
                                                 aviController03Fqdn=ctrl3_fqdn, aviClusterIp=aviClusterIp,
                                                 aviClusterFqdn=aviClusterFqdn, aviSize=aviSize,
                                                 aviCertPath=cert, aviCertKeyPath=cert_key),
                              tkgMgmtComponents=dict(tkgMgmtDeploymentType="prod")))
    with open("/opt/vmware/arcas/src/vcd/vcd_avi.json", 'w') as f:
        json.dump(data, f)


def load_tanzu_image_to_harbor(repo_name, tkg_binaries):
    print("Load_Tanzu_Image: Load Tanzu Images to Harbor")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    try:
        url = "http://localhost:5000/api/tanzu/harbor"
        response = requests.request("POST", url, headers=headers,
                                    json={'repo_name': repo_name, 'tkg_binaries': tkg_binaries},
                                    verify=False)
        if response.json()['STATUS_CODE'] != 200:
            print("Load Tanzu Images to Harbor failed " + str(response.json()))
            safe_exit()
        else:
            print("Load_Tanzu_Image: Load Tanzu Images to Harbor Successfully")
    except Exception as e:
        print("Load Tanzu Images to Harbor failed " + str(e))
        safe_exit()


def session(env, file):
    print("Session: Capturing Environment Details")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    url = "http://localhost:5000/api/tanzu/vmc/env/session"
    try:
        if env == "vmc":
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        elif env == "vsphere" or env == "vcf":
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Un recognised env " + env + "provided")
            safe_exit()
        # print(response.json()['STATUS_CODE'])
        if response.json()['STATUS_CODE'] != 200:
            print("Failed to get session" + str(response.json()))
            safe_exit()
        else:
            print("Session: " + str(response.json()['msg']))
    except Exception as e:
        print("Failed to get session" + str(e))
        safe_exit()


def workload_deploy(env, file):
    print("Workload_Deploy: Configuring TKG Workload Cluster")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vmc":
            url = "http://localhost:5000/api/tanzu/vmc/workload/config"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        elif env == "vsphere" or env == "vcf":
            url = "http://localhost:5000/api/tanzu/vsphere/workload/config"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Un recognised env " + env + "provided")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("Workload deploy failed " + str(response.json()))
            safe_exit()
        else:
            print("Workload_Deploy: TKG Workload Cluster deployed and configured Successfully")
    except Exception as e:
        print("Workload deploy failed " + str(e))
        safe_exit()


def workload_preconfig(env, file):
    print("Workload_Preconfig: Configuring AVI objects for TKG Workload Clusters")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vmc":
            url = "http://localhost:5000/api/tanzu/vmc/workload/network-config"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        elif env == "vsphere" or env == "vcf":
            url = "http://localhost:5000/api/tanzu/vsphere/workload/network-config"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Un recognised env " + env + "provided")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("Workload pre configuration failed " + str(response.json()))
            safe_exit()
        else:
            print("Workload_Preconfig: AVI objects for TKG Workload Clusters Configured Successfully")
    except Exception as e:
        print("Workload pre configuration failed " + str(e))
        safe_exit()


def create_supervisor_namespace(env, file):
    print("Supervisor_Name_Space: Creating supervisor name space")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vsphere":
            url = "http://localhost:5000/api/tanzu/vsphere/workload/createnamespace"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Un recognised env " + env + "provided")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("Supervisor name space creation failed " + str(response.json()))
            safe_exit()
        else:
            print("Supervisor_Name_Space: Created supervisor name space Successfully")
    except Exception as e:
        print("supervisor name space creation failed " + str(e))
        safe_exit()


def create_workload_cluster(env, file):
    print("Create_Workload_Cluster: Creating workload cluster")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vsphere":
            url = "http://localhost:5000/api/tanzu/vsphere/workload/createworkload"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Un recognised env " + env + "provided")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("Create workload cluster failed " + str(response.json()))
            safe_exit()
        else:
            print("Create_Workload_Cluster: Created workload cluster Successfully")
    except Exception as e:
        print("Create workload cluster failed " + str(e))
        safe_exit()


def userPrompt_for_wcp_shutdown(env, file):
    print("ESXi username and password is required for the Gracefully shutting down WCP")
    msg = """\n
    Please provide username to connect to ESXi hosts: """
    user_response = input(msg)
    user_response = user_response.strip()
    esxi_user = user_response
    msg = """\n
    Please provide password to connect to ESXi hosts: """
    user_response = input(msg)
    user_response = user_response.strip()
    esxi_password = user_response
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env,
        'User': esxi_user,
        'Password': esxi_password
    }
    print(headers)
    try:
        if env == 'vsphere':
            url = "http://localhost:5000/api/tanzu/wcp-shutdown"
            print(url)
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
            print(response.json())
        else:
            print("Un recognised env " + env + "provided")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("WCP shutdown failed: " + str(response.json()))
            safe_exit()
    except Exception as e:
        print("WCP shutdown failed: " + str(e))
        safe_exit()


def userPrompt_for_wcp_bringup(env, file):
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env,
    }
    try:
        if env == 'vsphere':
            url = "http://localhost:5000/api/tanzu/wcp-bringup"
            print(url)
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
            print(response.json())
        else:
            print("Un recognised env " + env + "provided")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("WCP shutdown failed: " + str(response.json()))
            safe_exit()
    except Exception as e:
        print("WCP shutdown failed: " + str(e))
        safe_exit()


def userPrompt_for_cleanup(env, file):
    print("Fetching deployed components from environment")
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Env': env
    }
    try:
        if env == "vsphere" or env == "vmc" or env == "vcf":
            url = "http://localhost:5000/api/tanzu/cleanup-prompt"
            response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        else:
            print("Un recognised env " + env + "provided")
            safe_exit()
        if response.json()['STATUS_CODE'] != 200:
            print("Cleanup failed: " + str(response.json()))
            safe_exit()
        workload_clusters = response.json()["WORKLOAD_CLUSTERS"]
        management_clusters = response.json()["MANAGEMENT_CLUSTERS"]
        content_libraries = response.json()["CONTENT_LIBRARY"]
        kubernetes_templates = response.json()["KUBERNETES_TEMPLATES"]
        avi_vms = response.json()["AVI_VMS"]
        resource_pools = response.json()["RESOURCE_POOLS"]
        namespaces = response.json()["NAMESPACES"]
        supervisor_cluster = response.json()["SUPERVISOR_CLUSTER"]
        if env == "vcf" or env == "vmc":
            network_segments = response.json()["NETWORK_SEGMENTS"]

        msg = """\n
    Skip cleanup of Content Libraries and Downloaded Kubernetes OVAs from vcenter env (Y/N) ? : """

        user_response = input(msg)
        user_response = user_response.strip()
        if user_response.lower() == 'y' or user_response.lower() == "yes":
            retain = True
            print("Content-libraries and Kubernetes OVA will not be removed...")
        elif user_response.lower() == 'n' or user_response.lower() == "no":
            retain = False
            print("Proceeding with complete cleanup...")
        else:
            print("Invalid response")
            safe_exit()

        msg = """\n\n
Below resources from environment will be Cleaned-up.
        """

        if management_clusters:
            msg = msg + """\n
    Management Clusters: %s """ % management_clusters
        if supervisor_cluster:
            msg = msg + """\n
    For vSphere on Tanzu, cleanup is performed by disabling Workload Control Plane (WCP) on cluster\n
    %s """ % supervisor_cluster
        if namespaces:
            msg = msg + """\n
    Namespaces: %s """ % namespaces
        if workload_clusters:
            msg = msg + """\n
    Workload Clusters: %s """ % workload_clusters
        if content_libraries and not retain:
            msg = msg + """\n
    Content Libraries: %s """ % content_libraries
        if kubernetes_templates and not retain:
            msg = msg + """\n
    Kubernetes Template VMs: %s """ % kubernetes_templates
        if avi_vms:
            msg = msg + """\n
    NSX Load Balancer VMs: %s """ % avi_vms
        if resource_pools:
            msg = msg + """\n
    Resource Pools: %s """ % resource_pools
        if env == "vcf" or env == "vmc":
            if network_segments:
                msg = msg + """\n
    Network Segments: %s """ % network_segments

        msg = msg + """\n
Please confirm if you wish to continue with cleanup (Y/N) ? : """

        user_response = input(msg)
        user_response = user_response.strip()
        if user_response.lower() == 'y' or user_response.lower() == "yes":
            print("Proceeding with cleanup...")
        elif user_response.lower() == 'n' or user_response.lower() == "no":
            print("Aborted Cleanup based on user response")
            safe_exit()
        else:
            print("Invalid response")
            safe_exit()
        headers.update({"Retain": str(retain)})
        url = "http://localhost:5000/api/tanzu/cleanup-env"
        response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)
        if response.json()['STATUS_CODE'] != 200:
            print("Cleanup failed " + str(response.json()))
            safe_exit()
        else:
            print("Session: " + str(response.json()['msg']))
            safe_exit()

    except Exception as e:
        print("Cleanup failed: " + str(e))
        safe_exit()


def add_verbosity():
    global pro
    log_file = "/opt/vmware/arcas/src/arcas_server.log"
    pro = subprocess.Popen(["tail", "-n0", "-f", log_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for output in pro.stdout:
        if (pro.poll() is not None) or (len(output) == 0) or stopThread:
            os.kill(pro.pid, SIGINT(2))
            break
        output = output.rstrip()
        output = output.decode("utf-8")
        print(f"{output}")
    print("\n")


def is_json_valid(input_file):
    try:
        with open(input_file, 'r') as openfile:
            json.load(openfile)
    except ValueError as e:
        return False
    return True


def get_harbor_preloading_status(repo_name):
    try:
        file_size = 100  # fake file size
        uploaded_size = 0
        url = f"http://localhost:5000/api/tanzu/harbor_pre_load_status?repo_name={repo_name}"
        while uploaded_size < file_size:
            response = requests.request("GET", url, verify=False)
            if response.json()['STATUS_CODE'] != 200:
                print("Failed to get status of harbor preloading " + str(response.json()))
                safe_exit()
            uploaded_size = int(response.json()['percentage'])
            updateProgressBar(uploaded_size, file_size)
            time.sleep(10)
    except Exception as e:
        print("Failed to get status of harbor preloading " + str(e))
        safe_exit()


# Progress bar
def updateProgressBar(size_uploaded, size_file, size_bar=50):
    perc_uploaded = round(size_uploaded / size_file * 100)
    progress = round(perc_uploaded / 100 * size_bar)
    status_bar = f"Harbor preload status : {'▒' * progress}{' ' * (size_bar - progress)}"
    print(f"\r{status_bar} | {perc_uploaded}%", end='')


def usage():
    l = "arcas"
    version = "--version"
    version_text = "Version Information"
    help_ = "--help"
    help_text = "Help for Arcas"
    env = "--env"
    file = "--file"
    file_path = "Path to Input File"
    file_path_text = "<path_to_input_file>"
    env_type = "IaaS Platform, 'vmc' or 'vsphere' or 'vcf'"
    vmc_config = "--vmc_pre_configuration"
    vcf_config = "--vcf_pre_configuration"
    vmc_text = "Creates segments, Firewalls rules, Inventory Groups and Services"
    avi_config = "--avi_configuration"
    avi_config_text = "Deploy and Configure AVI"
    shared = "--shared_service_configuration"
    shared_text = "Configure ALB Components and Deploy TKG Shared Service Cluster and Labelling"
    workload_pre = "--workload_preconfig"
    workload_pre_text = "Configure ALB for TKG Workload Cluster"
    workload_dep = "--workload_deploy"
    workload_dep_text = "Deploy Workload Cluster and Add AKO Labels"
    tkg_mgmt = "--tkg_mgmt_configuration"
    tkg_mgmt_text = "Configure ALB Components and Deploy TKG Management Cluster"
    deploy_extention = "--deploy_extensions"
    deployApp_text = "Deploy extensions"
    config_wcp = "--avi_wcp_configuration"
    config_wcp_text = "Configure avi cloud for wcp"
    create_name_space = "--create_supervisor_namespace"
    create_name_space_text = "Create supervisor namespace"
    create_workload_cluster = "--create_workload_cluster"
    create_workload_cluster_text = "Create workload cluster"
    enable_WCP = "--enable_wcp"
    enable_WCP_text = "Enable WCP"
    wcp_shutdown = "--wcp_shutdown"
    wcp_shutdown_text = "Gracefully shutdown WCP: "
    wcp_bringup = "--wcp_bringup"
    wcp_bringup_text = "Bring back up the WCP cluster: "

    vds = "For vSphere-VDS:"
    vmc = "For vmc:"
    vcf = "For vSphere-NSXT:"
    tkgs = "For Tanzu with vSphere(VDS):"
    vcd = "For Vcd:"
    availaible = "Available Flags:"
    enable_wcp = "Enable WCP:"
    tkgs_ns_wrk = "Create Namespace and Workload Cluster: "
    verbose = "--verbose"
    load_harbor = "--load_tanzu_image_to_harbor"
    repo_name = "--repo_name"
    repo_name_text = "Harbor repository name"
    tkg_binaries_path = "--tkg_binaries_path"
    tkg_binaries_path_text = "Absolute path for TKG binaries"
    load_harbor_status = "--get_harbor_preloading_status"
    load_harbor_text = "Load tanzu image to harbor"
    load_harbor_status_text = "Load tanzu image to harbor status"
    verbose_text = "Log Verbosity"
    cleanup_flag = "--cleanup"
    precheck_skip = "--skip_precheck"
    vcd_avi = "--vcd_avi_configuration"
    vcd_avi_cloud = "--avi_cloud_configuration"
    vcd_cse_server_config = "--cse_server_configuration"
    vcd_org_config = "--vcd_org_configuration"
    precheck_skip_text = "Skip preflight checks for the environment. Recommended only for test purpose."

    print("Usage:")
    print(f"{vds.rjust(20)}")
    print(
        f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vsphere'.rjust(8)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}")
    print("["f"{avi_config}""]" "["f"{tkg_mgmt}""]".rjust(62))
    print("["f"{shared}""]" "["f"{workload_pre}""]" "["f"{workload_dep}""]" "["f"{deploy_extention}""]".rjust(109))
    print(f"{vmc.rjust(12)}")
    print(
        f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vmc'.rjust(5)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}")
    print("["f"{vmc_config}""]" "["f"{avi_config}""]" "["f"{tkg_mgmt}""]".rjust(87))
    print("["f"{shared}""]" "["f"{workload_pre}""]" "["f"{workload_dep}""]" "["f"{deploy_extention}""]".rjust(109))
    print(f"{vcf.rjust(21)}")
    print(
        f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vcf'.rjust(5)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}")
    print("["f"{vcf_config}""]" "["f"{avi_config}""]" "["f"{tkg_mgmt}""]".rjust(87))
    print("["f"{shared}""]" "["f"{workload_pre}""]" "["f"{workload_dep}""]" "["f"{deploy_extention}""]".rjust(109))
    print(f"{tkgs.rjust(32)}")
    print(f"{enable_wcp.rjust(25)}")
    print(
        f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vsphere'.rjust(8)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}")
    print("["f"{avi_config}""]" "["f"{config_wcp}""]" "["f"{enable_WCP}""]".rjust(75))
    print(f"{tkgs_ns_wrk.rjust(53)}")
    print(
        f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vsphere'.rjust(8)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}")
    print("["f"{create_name_space}""]" "["f"{create_workload_cluster}""]" "["f"{deploy_extention}""]".rjust(94))
    print(f"{wcp_shutdown_text.rjust(39)}")
    print(
        f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vsphere'.rjust(8)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}")
    print("["f"{wcp_shutdown}""]".rjust(31))
    print(f"{wcp_bringup_text.rjust(45)}")
    print(
        f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vsphere'.rjust(8)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}")
    print("["f"{wcp_bringup}""]".rjust(30))
    print(f"{vcd.rjust(13)}")
    print(
        f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vcd'.rjust(4)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}")
    print("["f"{vcd_avi}""]" "["f"{vcd_avi_cloud}""]" "["f"{vcd_org_config}""]".rjust(92))
    print("["f"{vcd_cse_server_config}""]".rjust(43))
    print("\n")
    print("Cleanup:")
    print(
        f"{vds.rjust(20)}"f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vsphere'.rjust(8)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}"f"{cleanup_flag.rjust(10)}")
    print(
        f"{vcf.rjust(21)}"f"{l.rjust(19)}"f"{env.rjust(6)}"f"{'vcf'.rjust(5)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}"f"{cleanup_flag.rjust(10)}")
    print(
        f"{vmc.rjust(12)}"f"{l.rjust(28)}"f"{env.rjust(6)}"f"{'vmc'.rjust(5)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}"f"{cleanup_flag.rjust(10)}")
    print(
        f"{tkgs.rjust(32)}"f"{l.rjust(8)}"f"{env.rjust(6)}"f"{'vsphere'.rjust(8)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}"f"{cleanup_flag.rjust(10)}")
    print("<path_to_input_file>: File used for deployment")
    print("\n")
    print(availaible)
    print("Mandatory Flags:".rjust(20))
    print(f"{env.rjust(12)}"f"{env_type.rjust(71)}")
    print(f"{file.rjust(13)}"f"{file_path.rjust(46)}")
    print("\n")
    print("vSphere-NSXT Specific Flag:".rjust(31))
    print(f"{vcf_config.rjust(30)}"f"{vmc_text.rjust(75)}")
    print("VMC Specific Flag:".rjust(22))
    print(f"{vmc_config.rjust(30)}"f"{vmc_text.rjust(75)}")
    print("TKGs Specific Flag:".rjust(23))
    print(f"{config_wcp.rjust(30)}"f"{config_wcp_text.rjust(38)}")
    print(f"{create_name_space.rjust(36)}"f"{create_name_space_text.rjust(32)}")
    print(f"{create_workload_cluster.rjust(32)}"f"{create_workload_cluster_text.rjust(32)}")
    print(f"{enable_WCP.rjust(19)}"f"{enable_WCP_text.rjust(32)}")
    print("\n")
    print("Configuration Flags:".rjust(24))
    print(f"{avi_config.rjust(26)}"f"{avi_config_text.rjust(39)}")
    print(f"{tkg_mgmt.rjust(31)}"f"{tkg_mgmt_text.rjust(68)}")
    print(f"{shared.rjust(37)}"f"{shared_text.rjust(80)}")
    print(f"{workload_pre.rjust(27)}"f"{workload_pre_text.rjust(52)}")
    print(f"{workload_dep.rjust(24)}"f"{workload_dep_text.rjust(59)}")
    print(f"{deploy_extention.rjust(26)}"f"{deployApp_text.rjust(32)}")
    print(f"{help_.rjust(13)}"f"{help_text.rjust(42)}")
    print(f"{version.rjust(16)}"f"{version_text.rjust(44)}")
    print(f"{precheck_skip.rjust(22)}"f"{precheck_skip_text.rjust(96)}")
    print(f"{verbose.rjust(16)}"f"{verbose_text.rjust(38)}")
    print(f"{load_harbor.rjust(35)}"f"{load_harbor_text.rjust(32)}")
    print(f"{load_harbor_status.rjust(37)}"f"{load_harbor_status_text.rjust(37)}")
    print(f"{repo_name.rjust(18)}"f"{repo_name_text.rjust(44)}")
    print(f"{tkg_binaries_path.rjust(26)}"f"{tkg_binaries_path_text.rjust(45)}")


def main():
    global pro, t1
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, 'hvave:',
                                   ["help", "version", "env=", "file=",
                                    "vmc_pre_configuration", "vcf_pre_configuration", "avi_configuration",
                                    "shared_service_configuration", "load_tanzu_image_to_harbor", "repo_name=",
                                    "tkg_binaries_path=",
                                    "get_harbor_preloading_status", "vcd_avi_configuration", "avi_cloud_configuration",
                                    "vcd_org_configuration", "cse_server_configuration",

                                    "workload_preconfig", "workload_deploy", "deployapp", "tkg_mgmt_configuration",
                                    "all", "session", "precheck", "deploy_extensions", "avi_wcp_configuration",
                                    "enable_wcp", "create_supervisor_namespace", "create_workload_cluster", "verbose",
                                    "cleanup", "wcp_shutdown", "wcp_bringup", "skip_precheck"])

        for opt, arg in opts:
            if opt in ("-vv", "--verbose"):
                t1 = threading.Thread(target=add_verbosity, name='t1')
                t1.start()
                break
        repo_name = None
        tkg_binaries_path = None
        for opt, arg in opts:
            if opt in ("-r", "--repo_name"):
                repo_name = arg
            elif opt in ("-t", "--tkg_binaries_path"):
                tkg_binaries_path = arg
        for opt, arg in opts:
            if opt in ("-j", "--load_tanzu_image_to_harbor"):
                if repo_name is None:
                    print("--repo_name parameter is not passed, please specify repo_name for harbor image to upload")
                    sys.exit()
                elif tkg_binaries_path is None:
                    print("--tkg_binaries_path parameter is not passed, please specify local tkg_binaries_path to "
                          "upload on harbor")
                    sys.exit()
                # repo name to upload docker image
                load_tanzu_image_to_harbor(repo_name, tkg_binaries_path)
                safe_exit()
        for opt, arg in opts:
            if opt in ("-n", "--get_harbor_preloading_status"):
                if repo_name is None:
                    print("--repo_name parameter is not passed, please specify --repo_name for harbor image upload "
                          "status check")
                    sys.exit()
                get_harbor_preloading_status(repo_name)
                safe_exit()
        li = []
        for opt, arg in opts:
            li.append(opt)
            if opt in ("-h", "--help"):
                usage()
                sys.exit()
            elif opt in ("-v", "--version"):
                version()
                sys.exit()
        res = [ele for ele in li if (ele in "--env")]
        if not res:
            print("env parameter is not passed, please specify --env <env type> , vmc or vsphere.")
            sys.exit()
        res1 = [ele for ele in li if (ele in "--file")]
        if not res1:
            print("--file parameter is not passed, please specify --file in json format")
            sys.exit()
    except getopt.GetoptError as e:
        print(e)
        usage()
        sys.exit(2)
    env = None
    for opt, arg in opts:
        if opt in ("-e", "--env"):
            env = arg
            break
    file = None
    for opt, arg in opts:
        if opt in ("-e", "--file"):
            file = arg
            break
    if env is None:
        print("env argument is not passed, please specify --env <env type> , vmc or vsphere.")
        sys.exit()
    if file is None:
        print("File argument is not passed, please specify --file <json file path>")
        sys.exit()
    my_file = Path(file)
    if not my_file.exists():
        print(file + " file doesn't exist")
        sys.exit()
    if not is_json_valid(file):
        print(file + " is not a valid json file")
        sys.exit()
    for opt, arg in opts:
        if opt in ("-r", "--cleanup"):
            userPrompt_for_cleanup(env, file)
            safe_exit()

    for opt, arg in opts:
        if opt in ("-ws", "--wcp_shutdown"):
            userPrompt_for_wcp_shutdown(env, file)
            safe_exit()

    for opt, arg in opts:
        if opt in ("-wb", "--wcp_bringup"):
            userPrompt_for_wcp_bringup(env, file)
            safe_exit()

    skip = False
    for opt, arg in opts:
        if opt in ("-sp", "--skip_precheck"):
            skip = True

    with open("/tmp/skipPrecheck.txt", 'w') as fi:
        fi.write(str(skip))

    precheck_env(env, file)

    for opt, arg in opts:
        if opt in ("-c", "--vcf_pre_configuration"):
            vcf_pre_configuration(env, file)
        if opt in ("-v", "--vmc_pre_configuration"):
            vmc_pre_configuration(env, file)
        if opt in ("-a", "--avi_configuration"):
            avi_configuration(env, file)
        if opt in ("-s", "--shared_service_configuration"):
            shared_service_configuration(env, file)
        if opt in ("-w", "--workload_preconfig"):
            workload_preconfig(env, file)
        if opt in ("-x", "--workload_deploy"):
            workload_deploy(env, file)
        if opt in ("-m", "--tkg_mgmt_configuration"):
            managemnet_configuration(env, file)
        if opt in ("-l", "--all"):
            all(env, file)
        if opt in ("-d", "--deployapp"):
            deployapp(env, file)
        if opt in ("-s", "--session"):
            session(env, file)
        if opt in ("-e", "--deploy_extensions"):
            deploy_extentions(env, file)
        if opt in ("-p", "--avi_wcp_configuration"):
            avi_wcp_configuration(env, file)
        if opt in ("-y", "--enable_wcp"):
            enable_wcp(env, file)
        if opt in ("-f", "--create_supervisor_namespace"):
            create_supervisor_namespace(env, file)
        if opt in ("-g", "--create_workload_cluster"):
            create_workload_cluster(env, file)
        if opt in ("-vvf", "--vcd_avi_configuration"):
            vcd_avi_configuration(env, file)
        if opt in ("-nn", "--avi_cloud_configuration"):
            avi_cloud_configuration(file, env)
        if opt in ("-pj", "--vcd_org_configuration"):
            vcd_org_configuration(file, env)
        if opt in ("-rn", "--cse_server_configuration"):
            vcd_cse_server_configuration(file, env)
    safe_exit()


def safe_exit():
    if not (pro is None):
        os.kill(pro.pid, signal.SIGTERM)
    if not (t1 is None):
        stopThread = True
        try:
            sys.exit(1)
        except Exception as e:
            print(e)
    sys.exit(1)


if __name__ == "__main__":
    usage()
