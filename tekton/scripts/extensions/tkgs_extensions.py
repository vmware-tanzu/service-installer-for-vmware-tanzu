import base64
import os
import time
import ruamel
import json
import requests
from pathlib import Path
from util.logger_helper import LoggerHelper, log
from util.ShellHelper import runShellCommandAndReturnOutputAsList, \
    runShellCommandAndReturnOutputAsListWithChangedDir, verifyPodsAreRunning, runShellCommandAndReturnOutput, \
    grabPipeOutput

from constants.constants import Tkgs_Extension_Details, RegexPattern, Tkg_Extention_names, Repo, Extentions, \
    AppName, Paths
from util.common_utils import getVersionOfPackage,\
     checkToEnabled, installExtentionFor14, checkRepositoryAdded, \
    checkTmcEnabled, waitForGrepProcessWithoutChangeDir, connect_to_workload, isClusterRunning, \
     deploy_fluent_bit, checkFluentBitInstalled, fluent_bit_enabled, getClusterID, configureKubectl, createClusterFolder


from util.extensions_helper import checkTanzuExtensionEnabled, checkPromethusEnabled
from .tkg_extensions import generateYamlFile, getRepo

from util.shared_config import certChanging

from util.logger_helper import LoggerHelper, log

logger = LoggerHelper.get_logger(Path(__file__).stem)

def deploy_tkgs_extensions(jsonspec):
    try:
        if checkTanzuExtensionEnabled(jsonspec):
            """
            Env check commented and hardcoded the env variable with value vpshere
            env = envCheck()
            if env[1] != 200:
                logger.error("Wrong env provided " + env[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "Wrong env provided " + env[0],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            env = env[0]
            """
            #env="vpshere"
            vcenter_ip = jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
            vcenter_username = jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
            str_enc = str(jsonspec['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            password = enc_bytes.decode('ascii').rstrip("\n")
            cluster = jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]

            # Code added to configure KubeCtl
            url_ = "https://" + vcenter_ip + "/"
            sess = requests.post(url_ + "rest/com/vmware/cis/session", auth=(vcenter_username, password), verify=False)
            if sess.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to fetch session ID for vCenter - " + vcenter_ip,
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            else:
                session_id = sess.json()['value']
            header = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "vmware-api-session-id": session_id
            }
            id = getClusterID(vcenter_ip, vcenter_username, password, cluster, jsonspec)
            if id[1] != 200:
                return None, id[0]
            clusterip_resp = requests.get(url_ + "api/vcenter/namespace-management/clusters/" + str(id[0]),
                                          verify=False,
                                          headers=header)
            if clusterip_resp.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to fetch API server cluster endpoint - " + vcenter_ip,
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

            cluster_endpoint = clusterip_resp.json()["api_server_cluster_endpoint"]

            configure_kubectl = configureKubectl(cluster_endpoint)
            if configure_kubectl[1] != 200:
                return configure_kubectl[0], 500
            ####################

            status = tkgsExtensionsPrecheck(vcenter_ip, vcenter_username, password, cluster, jsonspec)
            if status[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Required Pre-checks required before TKGs extensions deployment FAILED",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

            logger.info("Pre-checks required before TKGs extensions deployment PASSED")
            workload_cluster = jsonspec['tanzuExtensions']['tkgClustersName']
            deploy_ext = deploy_extensions(workload_cluster, jsonspec)
            #deploy_ext = json.loads(deploy_ext[0]), deploy_ext[1]
            if deploy_ext[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": deploy_ext[1],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            d = {
                "responseType": "SUCCESS",
                "msg": "Extensions deployed successfully",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        else:
            logger.info("Extensions are not enabled")
            d = {
                "responseType": "SUCCESS",
                "msg": "Extensions are not enabled",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
    except Exception as e:
        logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while deploying extensions",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500


def tkgsExtensionsPrecheck(vcenter_ip, vcenter_username, password, cluster, jsonspec):
    # Creating cluster folder
    workload_name = jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterName']
    if not createClusterFolder(workload_name):
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create directory: " + Paths.CLUSTER_PATH + workload_name,
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500
    logger.info("The yml files will be located at: " + Paths.CLUSTER_PATH + workload_name)
    ###################

    workload_cluster = jsonspec['tanzuExtensions']['tkgClustersName']

    workload_status = isClusterRunning(vcenter_ip, vcenter_username, password, cluster, workload_cluster, jsonspec)
    #workload_status = json.loads(workload_status[0]), workload_status[1]
    if workload_status[1] != 200:
        return None, workload_status[0]

    #logger.info(workload_status[0]['msg'])

    connect = connect_to_workload(vcenter_ip, vcenter_username, password, cluster, workload_cluster, jsonspec)
    if connect[0] is None:
        logger.error(connect[1])
        return None, connect[1]

    logger.info(connect[1])

    rolebinding_result = createClusterRoleBinding()
    if rolebinding_result[0] is None:
        logger.error(rolebinding_result[1])
        return None, rolebinding_result[1]

    logger.info(rolebinding_result[1])

    if not checkTmcEnabled(jsonspec):
        kapp_status = kappConfiguration()
        if kapp_status[0] is None:
            logger.error(kapp_status[1])
            return None, kapp_status[1]
        logger.info(kapp_status[1])

    package_repo = configurePackagesRepository(jsonspec)
    if package_repo[0] is None:
        logger.error(package_repo[1])
        return None, package_repo[1]

    logger.info(package_repo[1])

    return "SUCCESS", "Pre-checks to start TKGs extensions PASSED"


def createClusterRoleBinding():
    try:
        check_status = checkClusterRoleStatus()
        if check_status[0]:
            return "SUCCESS", check_status[1]
        else:
            logger.info("Creating Cluster Role Binding...")
            output = generateRoleYaml()
            if output[0] is None:
                return None, output[1]
            command = ["kubectl", "apply", "-f", Tkgs_Extension_Details.ROLE_NAME+".yaml"]
            output = runShellCommandAndReturnOutputAsList(command)
            if output[1] != 0:
                return None, "ClusterRoleBinding creation failed"
            status = checkClusterRoleStatus()
            if status[0]:
                return "SUCCESS", status[1]
            else:
                return None, "cluster Role binding not completed"
    except Exception as e:
        logger.error("Exception occurred while creating cluster role binding")
        logger.error(str(e))
        return None, "Exception occurred while creating cluster role binding"


def generateRoleYaml():
    try:
        data = dict(kind="ClusterRoleBinding", apiVersion="rbac.authorization.k8s.io/v1",
                    metadata=dict(name=Tkgs_Extension_Details.ROLE_NAME),
                    roleRef=dict(kind="ClusterRole", name="psp:vmware-system-privileged", apiGroup="rbac.authorization.k8s.io"),
                    subjects=[dict(kind="Group", apiGroup="rbac.authorization.k8s.io", name="system:authenticated")])
        with open(Tkgs_Extension_Details.ROLE_NAME+".yaml", 'w') as outfile:
            yaml1 = ruamel.yaml.YAML()
            yaml1.dump(data, outfile)
        return "SUCCESS", "Cluster Role Binding yaml created successfully"
    except Exception as e:
        return None, "Exception occurred while generating yaml file for Cluster Role Binding"


def checkClusterRoleStatus():
    try:
        command = ["kubectl", "get", "clusterrolebinding"]
        grepCommand = ["grep", Tkgs_Extension_Details.ROLE_NAME]
        output = grabPipeOutput(command, grepCommand)
        if output[1] == 0:
            if output[0].__contains__("arcas-automation-authenticated-user-privileged-binding") \
                    and output[0].__contains__("ClusterRole/psp:vmware-system-privileged"):
                return True, "Cluster Role Binding is already created"
            else:
                return False, "Cluster Role Binding is not yet created !"
        else:
            return False, "Cluster Role Binding is not yet created !"
    except Exception as e:
        logger.error("Exception occurred while checking cluster role binding status")
        logger.error(str(e))
        return False, "Exception occurred while checking cluster role binding status"


def kappConfiguration():
    if not isKappRunning():
        logger.info("kapp-controller is not deployed... deploying it now")
        pod_security = isSecurityPodRunning()
        if pod_security[0]:
            logger.info(pod_security[1])
        else:
            logger.info("kapp Controller Pod Security Policy is not yet created")
            create_policy = createPodSecurity()
            if create_policy[0] is None:
                return None, create_policy[1]
        kapp_command = ["kubectl", "apply", "-f", Paths.KAPP_CTRL_FILE]
        output = runShellCommandAndReturnOutputAsList(kapp_command)
        if output[1] != 0:
            return None, "Command to deploy kapp-controller failed!"

        count = 0
        run_status = False
        while count < 120:
            if isKappRunning():
                run_status = True
                break
            time.sleep(5)
            logger.info("Waited for " + str(count * 5) + "s for kapp-controller, retrying...")
            count = count + 1

        if run_status:
            return "SUCCESS", "kapp-controller installed successfully"
        else:
            logger.error("kapp-controller is not up even after 10 minutes wait...")
            return None, "Failed to deploy kapp-controller"
    else:
        return "SUCCESS", "kapp-controller is already deployed"


def isSecurityPodRunning():
    try:
        command = ["kubectl", "get", "psp"]
        grepCommand = ["grep", "tanzu-system-kapp-ctrl-restricted"]
        output = grabPipeOutput(command, grepCommand)
        if output[1] == 0:
            if output[0].__contains__("tanzu-system-kapp-ctrl-restricted"):
                return True, "kapp Controller Pod Security Policy is created"
        return False, "kapp Controller Pod Security Policy is not yet created."
    except Exception as e:
        logger.info("Exception occurred while checking kapp Controller Pod Security Policy status")
        logger.error(str(e))
        return False, "Exception occurred while checking kapp Controller Pod Security Policy status"


def createPodSecurity():
    logger.info("Creating kapp Controller Pod Security Policy....")
    command = ["kubectl", "apply", "-f", Paths.POD_SECURITY_KAPP_CTRL_FILE]
    output = runShellCommandAndReturnOutputAsList(command)
    if output[1] != 0:
        return None, "kapp Controller Pod Security Policy creation failed"
    pod_security = isSecurityPodRunning()
    if not pod_security[0]:
        return None, pod_security[1]
    return "SUCCESS", "kapp Controller Pod Security Policy created"


def isKappRunning():
    command = ["kubectl", "get", "pods", "-n", "tkg-system"]
    grepCommand = ["grep", "kapp-controller"]
    output = grabPipeOutput(command, grepCommand)
    if not verifyPodsAreRunning("kapp-controller", output[0], RegexPattern.RUNNING):
        return False
    else:
        return True


def isRepoConfigured():
    command = ["tanzu", "package", "repository", "list", "-n", "tanzu-package-repo-global"]
    repo_output = runShellCommandAndReturnOutputAsList(command)
    if repo_output[1] != 0:
        return False, "Command to fetch standard package repository details failed"
    if not verifyPodsAreRunning("tanzu-standard", repo_output[0], RegexPattern.RECONCILE_SUCCEEDED):
        repo_string = Tkgs_Extension_Details.PACKAGE_REPO_URL.split(":")[0]
        for line in repo_output[0]:
            if line.__contains__(repo_string) and line.__contains__("tanzu-standard"):
                logger.warn("Standard Package Repository is already added but "
                                        "it's not in Reconcile Succeed status")
                return False
    else:
        return True

    return False


def configurePackagesRepository(jsonspec):
    if checkTmcEnabled(jsonspec):
        logger.info("TMC is enabled and standard package repository installation should be done by TMC")
        logger.info("Checking Standard Package Repository status...")
        command = ["tanzu", "package", "repository", "list", "-n", "tanzu-package-repo-global"]
        repo_output = runShellCommandAndReturnOutputAsList(command)
        if repo_output[1] != 0:
            logger.error(repo_output[0])
            return None, "Command to fetch standard package repository details failed"
        for i in repo_output[0]:
            if str(i).__contains__("tanzu-standard"):
                if str(i).__contains__(RegexPattern.RECONCILE_SUCCEEDED):
                    return True, "Standard Package Repository is in Reconcile succeeded status"
                else:
                    return None, "Standard Package Repository is not in Reconcile succeeded status"
        return None, "Standard Package Repository installation not found"
    else:
        if not isRepoConfigured():
            logger.info("Installing Standard Package Repository...")
            deploy_command = ["tanzu", "package", "repository", "add", "tanzu-standard", "--url",
                              Tkgs_Extension_Details.PACKAGE_REPO_URL, "-n", "tanzu-package-repo-global"]
            repo_output = runShellCommandAndReturnOutputAsList(deploy_command)
            if repo_output[1] != 0:
                return None, "Command to add standard package repository failed"

            count = 0
            run_status = False
            while count < 120:
                if isRepoConfigured():
                    run_status = True
                    break
                time.sleep(5)
                logger.info("Waited for " + str(count * 5) + "s for package repository, retrying...")
                count = count + 1

            if run_status:
                return "SUCCESS", "Standard Package Repository installed successfully"
            else:
                logger.error("Standard Package Repository is not up even after 10 minutes wait...")
                return None, "Failed to deploy Standard Package Repository"
        else:
            return "SUCCESS", "Standard Package Repository is already deployed!"


def deploy_extensions(cluster_name, jsonspec):
    try:
        listOfExtention = []
        service = "all"
        repo_address = Repo.PUBLIC_REPO
        checkHarborEnabled = jsonspec['tanzuExtensions']['harborSpec']['enableHarborExtension']

        if checkPromethusEnabled(jsonspec):
            listOfExtention.append(Tkg_Extention_names.PROMETHEUS)
            listOfExtention.append(Tkg_Extention_names.GRAFANA)

        status = tkgsCertManagerandContour(cluster_name, service, jsonspec)
        #status = json.loads(status[0]), status[1]
        if status[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy extension" + str(status[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if str(checkHarborEnabled).lower() == "true":
            logger.info("Installing harbor...")
            str_enc = str(jsonspec['tanzuExtensions']['harborSpec']['harborPasswordBase64'])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            password = enc_bytes.decode('ascii').rstrip("\n")
            harborPassword = password
            host = jsonspec['tanzuExtensions']['harborSpec']['harborFqdn']
            harborCertPath = jsonspec['tanzuExtensions']['harborSpec']['harborCertPath']
            harborCertKeyPath = jsonspec['tanzuExtensions']['harborSpec']['harborCertKeyPath']
            if not host or not harborPassword:
                logger.error("Harbor FQDN and password are mandatory for harbor deployment."
                                         " Please provide both the details")
                d = {
                    "responseType": "ERROR",
                    "msg": "Harbor FQDN and password are mandatory for harbor deployment. Please provide both the "
                           "details",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            state = installHarborTkgs(harborCertPath, harborCertKeyPath, harborPassword, host, cluster_name)
            #state = json.loads(state[0]), state[1]
            if state[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": state[0],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            else:
                logger.info(state[0])

        #to_enable = jsonspec["envSpec"]["saasEndpoints"]["tanzuObservabilityDetails"]["tanzuObservabilityAvailability"]
        if checkToEnabled(jsonspec):
            logger.info("Tanzu observability is enabled, skipping prometheus and grafana deployment")
            '''d = {
                "responseType": "ERROR",
                "msg": "Tanzu observability is enabled, skipping prometheus and grafana deployment",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200'''
        else:
            if len(listOfExtention) == 0:
                logger.info("Prometheus and Grafana are deactivated")
                '''d = {
                    "responseType": "SUCCESS",
                    "msg": "Prometheus and Grafana are deactivated",
                    "ERROR_CODE": 200
                }
                return json.dumps(d), 200'''
            else:
                for extension_name in listOfExtention:
                    monitor_status = deploy_monitoring_extentions(extension_name, cluster_name, jsonspec)
                    monitor_status = json.loads(monitor_status[0]), monitor_status[1]
                    if monitor_status[1] != 200:
                        logger.error(monitor_status[0])
                        d = {
                            "responseType": "ERROR",
                            "msg": monitor_status[0],
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                    logger.info("Extension - " + extension_name + " deployed successfully")

        is_enabled = fluent_bit_enabled(jsonspec)
        if is_enabled[0]:
            is_deployed = checkFluentBitInstalled()
            if not is_deployed[0]:
                end_point = is_enabled[1]
                workload_cluster = jsonspec['tanzuExtensions']['tkgClustersName']
                response = deploy_fluent_bit(end_point, workload_cluster, jsonspec)
                response = json.loads(response[0]), response[1]
                if response[1] != 200:
                    logger.error(response[0])
                    d = {
                        "responseType": "ERROR",
                        "msg": response[0],
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                logger.info("Fluent-bit deployed successfully")
            else:
                logger.info("Fluent-bit is already deployed and its status is - " + is_deployed[1])
        else:
            logger.info("Fluent-bit deployment is not enabled. Hence, skipping it.")

        d = {
            "responseType": "SUCCESS",
            "msg": "Extensions deployed successfully",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

    except Exception as e:
        logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while deploying extensions",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500


def tkgsCertManagerandContour(cluster_name, service_name, jsonspec):
    try:
        status_ = checkRepositoryAdded(jsonspec)
        #status_ = json.loads(status_[0]), status_[1]
        if status_[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": str(status_[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        install = installExtentionFor14(service_name, cluster_name, jsonspec)
        if install[1] != 200:
            return install[0], install[1]
        logger.info("Configured cert-manager and contour successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Configured cert-manager and contour extensions successfully",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200
    except Exception as e:
        logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while installing Cert-manager and Contour",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500


def deploy_monitoring_extentions(monitoringType, clusterName, jsonspec):
    try:
        repo = getRepo(jsonspec)
        repository = repo[1]
        os.system(f"chmod +x {Paths.INJECT_VALUE_SH}")
        enable = jsonspec['tanzuExtensions']['monitoring']['enableLoggingExtension']
        extention = ""
        appName = ""
        namespace = ""
        certKey_Path = ""
        fqdn = ""
        cert_Path = ""
        password = ""
        yamlFile = ""
        if enable.lower() == "true":
            if monitoringType == Tkg_Extention_names.PROMETHEUS:
                password = None
                extention = Tkg_Extention_names.PROMETHEUS
                appName = AppName.PROMETHUS
                namespace = "package-tanzu-system-monitoring"
                yamlFile = Paths.CLUSTER_PATH + clusterName + "/prometheus-data-values.yaml"
                service = "all"
                cert_Path = jsonspec['tanzuExtensions']['monitoring'][
                    'prometheusCertPath']
                fqdn = jsonspec['tanzuExtensions']['monitoring'][
                    'prometheusFqdn']
                certKey_Path = jsonspec['tanzuExtensions']['monitoring'][
                    'prometheusCertKeyPath']
            elif monitoringType == Tkg_Extention_names.GRAFANA:
                password = jsonspec['tanzuExtensions']['monitoring']['grafanaPasswordBase64']
                if not password:
                    logger.error("Password for grafana is mandatory, please add and re-run deployment")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Password for grafana is mandatory, please add and re-run deployment",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                extention = Tkg_Extention_names.GRAFANA
                yamlFile = Paths.CLUSTER_PATH + clusterName + "/grafana-data-values.yaml"
                appName = AppName.GRAFANA
                namespace = "package-tanzu-system-dashboards"
                command = [f"{Paths.INJECT_VALUE_SH}", Extentions.GRAFANA_LOCATION + "/grafana-extension.yaml", "fluent_bit",
                           repository + "/" + Extentions.APP_EXTENTION]
                runShellCommandAndReturnOutputAsList(command)
                cert_Path = jsonspec['tanzuExtensions']['monitoring']['grafanaCertPath']
                fqdn = jsonspec['tanzuExtensions']['monitoring']['grafanaFqdn']
                certKey_Path = jsonspec['tanzuExtensions']['monitoring'][
                    'grafanaCertKeyPath']

            if not fqdn:
                logger.error("FQDN for " + extention + " is mandatory, please add and re-run deployment")
                d = {
                    "responseType": "ERROR",
                    "msg": "FQDN for " + extention + " is mandatory, please add and re-run deployment",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

            extention_validate_command = ["kubectl", "get", "app", appName, "-n", namespace]

            command_fluent_bit = runShellCommandAndReturnOutputAsList(extention_validate_command)
            if not verifyPodsAreRunning(appName, command_fluent_bit[0],
                                        RegexPattern.RECONCILE_SUCCEEDED):
                logger.info("Deploying " + extention)
                version = getVersionOfPackage(extention.lower() + ".tanzu.vmware.com")
                if version is None:
                    logger.error("Failed Capture the available Prometheus version")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Capture the available Prometheus version",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                file_status = generateYamlFile(extention, version, certKey_Path, cert_Path, fqdn, password, yamlFile)
                if file_status[1] == 500:
                    logger.error(yamlFile + " generation failed " + str(file_status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": yamlFile + " generation failed " + str(file_status[0]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500

                update_sc_response = updateStorageClass(yamlFile, extention)
                if update_sc_response[1] != 200:
                    d = {
                        "responseType": "ERROR",
                        "msg": update_sc_response[0],
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500

                logger.info("Initiated " + extention + " deployment")
                deply_extension_command = ["tanzu", "package", "install", extention.lower(), "--package-name",
                                           extention.lower() + ".tanzu.vmware.com", "--version", version,
                                           "--values-file", yamlFile, "--namespace", namespace, "--create-namespace"]
                state_extention_apply = runShellCommandAndReturnOutputAsList(deply_extension_command)
                if state_extention_apply[1] != 0:
                    logger.error(extention + "install command failed. Checking for reconciliation "
                                                         "status...")

                found = False
                count = 0
                command_ext_bit = runShellCommandAndReturnOutputAsList(extention_validate_command)
                if verifyPodsAreRunning(appName, command_ext_bit[0], RegexPattern.RECONCILE_SUCCEEDED):
                    found = True

                while not verifyPodsAreRunning(appName, command_ext_bit[0],
                                               RegexPattern.RECONCILE_SUCCEEDED) and count < 20:
                    command_ext_bit = runShellCommandAndReturnOutputAsList(extention_validate_command)
                    if verifyPodsAreRunning(appName, command_ext_bit[0], RegexPattern.RECONCILE_SUCCEEDED):
                        found = True
                        break
                    count = count + 1
                    time.sleep(30)
                    logger.info("Waited for  " + str(count * 30) + "s, retrying.")
                if not found:
                    logger.error(extention + " Extension is still not deployed " + str(count * 30))
                    d = {
                        "responseType": "ERROR",
                        "msg": extention + " Extension is still not deployed " + str(count * 30),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                else:
                    d = {
                        "responseType": "SUCCESS",
                        "msg": appName + " is deployed",
                        "ERROR_CODE": 200
                    }
                    return json.dumps(d), 200
            else:
                logger.info(appName + " is already running")
                d = {
                    "responseType": "SUCCESS",
                    "msg": appName + " is already running",
                    "ERROR_CODE": 200
                }
                return json.dumps(d), 200
        else:
            logger.info("Monitoring extension deployment is not enabled")
            d = {
                "responseType": "SUCCESS",
                "msg": "Monitoring extension deployment is not enabled",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200

    except Exception as e:
        logger.info("Failed to  deploy monitoring " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  deploy monitoring " + str(e),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500


def updateStorageClass(yamlFile, extension):
    try:
        sc = None
        get_sc_command = ["kubectl", "get", "sc"]
        get_sc_output = runShellCommandAndReturnOutputAsList(get_sc_command)
        if get_sc_output[1] != 0:
            logger.error("Command to get storage class name failed.")
            d = {
                "responseType": "ERROR",
                "msg": "Command to get storage class name failed.",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        else:
            for item in range(len(get_sc_output[0])):
                if get_sc_output[0][item].split()[1] == "(default)":
                    sc = get_sc_output[0][item].split()[0]
                    break

        if sc is None:
            logger.error("Failed to obtain storage class name for cluster")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to obtain storage class name for cluster",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        logger.info("Default Storage Class for workload cluster - " + sc)
        logger.info("Update " + extension + " data files with storage class")
        if extension == Tkg_Extention_names.PROMETHEUS:
            inject_sc = ["sh", Paths.INJECT_VALUE_SH, yamlFile, "inject_sc_prometheus", sc]
        elif extension == Tkg_Extention_names.GRAFANA:
            inject_sc = ["sh", Paths.INJECT_VALUE_SH, yamlFile, "inject_sc_grafana", sc]
        elif extension == AppName.HARBOR:
            inject_sc = ["sh", Paths.INJECT_VALUE_SH, yamlFile, "inject_sc_harbor", sc]
        else:
            logger.error("Wrong extension name provided for updating storage class name - " + extension)
            d = {
                "responseType": "ERROR",
                "msg": "Wrong extension name provided for updating storage class name - " + extension,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        inject_sc_response = runShellCommandAndReturnOutput(inject_sc)
        if inject_sc_response[1] == 500:
            logger.error("Failed to update storage class name " + str(inject_sc_response[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to update storage class name " + str(inject_sc_response[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        else:
            logger.info(inject_sc_response[0])
            d = {
                "responseType": "SUCCESS",
                "msg": extension + " yaml file updated successfully",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
    except Exception as e:
        logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while update data file for extensions",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500


def installHarborTkgs(harborCertPath, harborCertKeyPath, harborPassword, host, clusterName):
    main_command = ["tanzu", "package", "installed", "list", "-A"]
    sub_command = ["grep", AppName.HARBOR]
    out = grabPipeOutput(main_command, sub_command)
    if not (verifyPodsAreRunning(AppName.HARBOR, out[0], RegexPattern.RECONCILE_SUCCEEDED)
            or verifyPodsAreRunning(AppName.HARBOR, out[0], RegexPattern.RECONCILE_FAILED)):
        timer = 0
        logger.info("Validating contour and cert-manager is running")
        command = ["tanzu", "package", "installed", "list", "-A"]
        status = runShellCommandAndReturnOutputAsList(command)
        verify_contour = False
        verify_cert_manager = False
        while timer < 600:
            if verify_contour or verifyPodsAreRunning(AppName.CONTOUR, status[0], RegexPattern.RECONCILE_SUCCEEDED):
                logger.info("Contour is running")
                verify_contour = True
            if verify_cert_manager or verifyPodsAreRunning(AppName.CERT_MANAGER, status[0], RegexPattern.RECONCILE_SUCCEEDED):
                verify_cert_manager = True
                logger.info("Cert Manager is running")

            if verify_contour and verify_cert_manager:
                break
            else:
                timer = timer + 30
                time.sleep(30)
                status = runShellCommandAndReturnOutputAsList(command)
                logger.info("Waited for " + str(timer) + "s, retrying for contour and cert manager to be "
                                                                     "running")
        if not verify_contour:
            logger.error("Contour is not running")
            d = {
                "responseType": "ERROR",
                "msg": "Contour is not running ",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if not verify_cert_manager:
            logger.error("Cert manager is not running")
            d = {
                "responseType": "ERROR",
                "msg": "Cert manager is not running ",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        state = getVersionOfPackage("harbor.tanzu.vmware.com")
        if state is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get Version of package contour.tanzu.vmware.com",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        logger.info("Deploying harbor - " + state)
        get_url_command = ["kubectl", "-n", "tanzu-package-repo-global", "get", "packages",
                           "harbor.tanzu.vmware.com." + state, "-o",
                           "jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}'"]
        logger.info("Getting harbor url")
        status = runShellCommandAndReturnOutputAsList(get_url_command)
        if status[1] != 0:
            logger.error("Failed to get harbor image url " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get harbor image url " + str(status[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        logger.info("Got harbor url " + str(status[0][0]).replace("'", ""))
        pull = ["imgpkg", "pull", "-b", str(status[0][0]).replace("'", ""), "-o", "/tmp/harbor-package"]
        status = runShellCommandAndReturnOutputAsList(pull)
        if status[1] != 0:
            logger.error("Failed to pull harbor packages " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get harbor image url " + str(status[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        os.system("rm -rf " + Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml")
        os.system("cp /tmp/harbor-package/config/values.yaml " + Paths.CLUSTER_PATH + clusterName +"/harbor-data"
                                                                                                   "-values.yaml")
        command_harbor_genrate_psswd = ["sh", "/tmp/harbor-package/config/scripts/generate-passwords.sh",
                                        Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml"]
        state_harbor_genrate_psswd = runShellCommandAndReturnOutputAsList(command_harbor_genrate_psswd)
        if state_harbor_genrate_psswd[1] == 500:
            logger.error("Failed to generate password " + str(state_harbor_genrate_psswd[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to generate password " + str(state_harbor_genrate_psswd[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        cer = certChanging(harborCertPath, harborCertKeyPath, harborPassword, host,clusterName)
        #cer = json.loads(cer[0]), cer[1]
        if cer[1] != 200:
            logger.error(cer[0])
            d = {
                "responseType": "ERROR",
                "msg": cer[0],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        os.system(f"chmod +x {Paths.INJECT_VALUE_SH}")

        update_sc_resp = updateStorageClass(Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml", AppName.HARBOR)
        update_sc_resp = json.loads(update_sc_resp[0]), update_sc_resp[1]
        if update_sc_resp[1] != 200:
            logger.error(update_sc_resp[0])
            d = {
                "responseType": "ERROR",
                "msg": update_sc_resp[0],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        else:
            logger.info(update_sc_resp[0])

        command = ["sh", Paths.INJECT_VALUE_SH, Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml", "remove"]
        runShellCommandAndReturnOutputAsList(command)

        logger.info("Initiated harbor deployment")
        command = ["tanzu", "package", "install", "harbor", "--package-name", "harbor.tanzu.vmware.com", "--version",
                   state, "--values-file", Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml", "--namespace", "package-tanzu-system-registry",
                   "--create-namespace"]
        runShellCommandAndReturnOutputAsList(command)

        logger.info("Waiting for harbor installation to complete...")
        running = False
        reconcile_failed = False
        count = 0

        while count < 60:
            cert_state = grabPipeOutput(main_command, sub_command)
            if verifyPodsAreRunning(AppName.HARBOR, cert_state[0], RegexPattern.RECONCILE_SUCCEEDED):
                running = True
                break
            elif verifyPodsAreRunning(AppName.HARBOR, cert_state[0], RegexPattern.RECONCILE_FAILED):
                reconcile_failed = True
                break
            time.sleep(30)
            count = count + 1
            logger.info("Waited for  " + str(count * 30) + "s, retrying.")

        if running:
            d = {
                "responseType": "SUCCESS",
                "msg": "Deployed harbor successfully",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        elif reconcile_failed:
            logger.info("Harbor deployment reconcile failed")
            logger.info("Applying overlay and re-checking...")
            overlay_status = tkgsOverlay()
            if overlay_status[0] is None:
                logger.error(overlay_status[1])
                d = {
                    "responseType": "ERROR",
                    "msg": overlay_status[1],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
        else:
            logger.info("Harbor status did not change. Waited for " + str(count * 30) + "s")
            logger.info("Applying overlay and re-checking...")

        logger.info("Waiting for harbor installation to complete post pods re-creation...")
        state = waitForGrepProcessWithoutChangeDir(main_command, sub_command, AppName.HARBOR,
                                                   RegexPattern.RECONCILE_SUCCEEDED)
        #state = json.loads(state[0]), state[1]
        if state[1] != 200:
            logger.info("Harbor Deployment Failed.")
            d = {
                "responseType": "ERROR",
                "msg": state[0],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        logger.info("Deployed harbor successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Deployed harbor successfully",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200
    else:
        logger.info("Harbor is already deployed and it's status is - " + out[0].split()[3] + " " +
                                out[0].split()[4])
        d = {
            "responseType": "SUCCESS",
            "msg": "Harbor is already deployed and it's status is - " + out[0].split()[3] + " " +
                   out[0].split()[4],
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200


def tkgsOverlay():
    try:
        os.system(f"chmod +x {Paths.TKGS_OVERLAY} {Paths.FIX_FS_GRP}")
        apply = ["sh", Paths.TKGS_OVERLAY]
        apply_state = runShellCommandAndReturnOutput(apply)
        if apply_state[1] != 0:
            logger.error("Failed to create secrets " + str(apply_state[0]))
            return None, "Failed to create secrets " + str(apply_state[0])
        logger.info(apply_state[0])

        time.sleep(10)

        apply_command = ["kubectl", "-n", "package-tanzu-system-registry", "annotate", "packageinstalls", "harbor",
                         "ext.packaging.carvel.dev/ytt-paths-from-secret-name.1=harbor-database-redis-trivy-jobservice-registry-image-overlay"]

        patch_status = runShellCommandAndReturnOutput(apply_command)
        if patch_status[1] != 0:
            logger.error(patch_status[0])
            return None, "Command for applying harbor secret failed"
        else:
            logger.info(patch_status[0])

        logger.info("Waiting for 30s before deleting pods...")
        time.sleep(30)

        logger.info("Deleting pods")
        delete_command = ["kubectl", "delete", "pods", "--all", "-n", "package-tanzu-system-registry"]
        delete_status = runShellCommandAndReturnOutputAsList(delete_command)
        if delete_status[1] != 0:
            return None, "Command for deleting existing harbor pods failed."
        else:
            logger.info(delete_status[0])

        return "SUCCESS", "Secrets created successfully"
    except Exception as e:
        logger.error(str(e))
        return None, "Exception occurred while applying harbor secrets"
