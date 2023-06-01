from python_terraform import *
import os
import base64


def init(env, file):
    tf = Terraform(working_dir='/opt/vmware/arcas/src/vcd/aviConfig', var_file=file)
    return_code, stdout, stderr = tf.init(capture_output=False)
    print(return_code)
    print(stdout)
    print(stderr)


def _vcd_avi_configuration(env, file):
    with open(file, "r") as outfile:
        data = outfile.read()
    with open("/opt/vmware/arcas/src/vcd/aviConfig/vcd_vsphere.tfvars.json", "w") as outfile:
        outfile.write(data)
    init(env, file)
    write_temp_json_file(file)
    os.environ['TF_LOG'] = "DEBUG"
    os.environ['TF_LOG_PATH'] = "/var/log/server/arcas.log"
    tf = Terraform(working_dir='/opt/vmware/arcas/src/vcd/aviConfig', var_file="vcd_vsphere.tfvars.json")
    return_code, stdout, stderr = tf.apply(capture_output=False, skip_plan=True)
    print(return_code)
    print(stdout)
    print(stderr)


def seperateNetmaskAndIp(cidr):
    return str(cidr).split("/")


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
    with open("/opt/vmware/arcas/src/vcd/aviConfig/vcd.json", 'w') as f:
        json.dump(data, f)
