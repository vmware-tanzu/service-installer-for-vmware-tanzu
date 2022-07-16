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

__version__ = get_distribution('arcas').version

pro = None
t1 = None
stopThread = False

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
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
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
        # print(response.json()['ERROR_CODE'])
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
            print("Avi configuration failed " + str(response.json()))
            safe_exit()
        else:
            print("AVI_Configuration: AVI configured Successfully")
    except Exception as e:
        print("Avi configuration failed " + str(e))
        safe_exit()


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
    else:
        print("Wrong env type, please specify vmc or vsphere")
        safe_exit()
    try:
        url = "http://localhost:5000/api/tanzu/precheck"
        response = requests.request("POST", url, headers=headers, data=open(file, 'rb'), verify=False)

        if response.json()['ERROR_CODE'] != 200:
            print("Precheck failed " + str(response.json()))
            safe_exit()
        else:
            print("Session: " + str(response.json()['msg']))
    except Exception as e:
        print("Precheck failed " + str(e))
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
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
            print("Deploy extensions failed" + str(response.json()))
            safe_exit()
        else:
            print("Deploy_Extensions: Deployed extensions Successfully")
    except Exception as e:
        print("Deploy extensions failed" + str(e))
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
        # print(response.json()['ERROR_CODE'])
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
            print("Create workload cluster failed " + str(response.json()))
            safe_exit()
        else:
            print("Create_Workload_Cluster: Created workload cluster Successfully")
    except Exception as e:
        print("Create workload cluster failed " + str(e))
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
        if response.json()['ERROR_CODE'] != 200:
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
        if response.json()['ERROR_CODE'] != 200:
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
    vds = "For vSphere-VDS:"
    vmc = "For vmc:"
    vcf = "For vSphere-NSXT:"
    tkgs = "For Tanzu with vSphere(VDS):"
    availaible = "Available Flags:"
    enable_wcp = "Enable WCP:"
    tkgs_ns_wrk = "Create Namespace and Workload Cluster: "
    verbose = "--verbose"
    verbose_text = "Log Verbosity"
    cleanup_flag = "--cleanup"
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
    print(f"{tkgs.rjust(30)}")
    print(f"{enable_wcp.rjust(25)}")
    print(
        f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vsphere'.rjust(8)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}")
    print("["f"{avi_config}""]" "["f"{config_wcp}""]" "["f"{enable_WCP}""]".rjust(75))
    print(f"{tkgs_ns_wrk.rjust(53)}")
    print(
        f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vsphere'.rjust(8)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}")
    print("["f"{create_name_space}""]" "["f"{create_workload_cluster}""]" "["f"{deploy_extention}""]".rjust(94))
    print("\n")
    print("Cleanup:")
    print(f"{vds.rjust(20)}"f"{l.rjust(20)}"f"{env.rjust(6)}"f"{'vsphere'.rjust(8)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}"f"{cleanup_flag.rjust(10)}")
    print(f"{vcf.rjust(21)}"f"{l.rjust(19)}"f"{env.rjust(6)}"f"{'vcf'.rjust(5)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}"f"{cleanup_flag.rjust(10)}")
    print(f"{vmc.rjust(12)}"f"{l.rjust(28)}"f"{env.rjust(6)}"f"{'vmc'.rjust(5)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}"f"{cleanup_flag.rjust(10)}")
    print(f"{tkgs.rjust(30)}"f"{l.rjust(10)}"f"{env.rjust(6)}"f"{'vsphere'.rjust(8)}"f"{file.rjust(7)}"f"{file_path_text.rjust(21)}"f"{cleanup_flag.rjust(10)}")
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
    print(f"{verbose.rjust(16)}"f"{verbose_text.rjust(38)}")


def main():
    global pro, t1
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, 'hvave:',
                                   ["help", "version", "env=", "file=",
                                    "vmc_pre_configuration","vcf_pre_configuration", "avi_configuration", "shared_service_configuration",

                                    "workload_preconfig", "workload_deploy", "deployapp", "tkg_mgmt_configuration",
                                    "all", "session", "precheck", "deploy_extensions", "avi_wcp_configuration",
                                    "enable_wcp", "create_supervisor_namespace", "create_workload_cluster", "verbose",
                                    "cleanup"])
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
        if opt in ("-vv", "--verbose"):
            t1 = threading.Thread(target=add_verbosity, name='t1')
            t1.start()
            break
    for opt, arg in opts:
        if opt in ("-r", "--cleanup"):
            userPrompt_for_cleanup(env, file)
            safe_exit()
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
