import base64
import os
import time
import ruamel
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList, \
    runShellCommandAndReturnOutputAsListWithChangedDir, verifyPodsAreRunning, runShellCommandAndReturnOutput, \
    grabPipeOutput
from flask import current_app, jsonify, request
from common.operation.constants import Tkgs_Extension_Details, RegexPattern, Tkg_Extention_names, Repo, Extentions, \
    AppName, Paths
from common.common_utilities import getVersionOfPackage, loadBomFile, checkAirGappedIsEnabled, preChecks, envCheck, \
    waitForProcess, installCertManagerAndContour, deployExtention, getManagementCluster, verifyCluster, \
    switchToManagementContext, checkToEnabled, checkPromethusEnabled, installExtentionFor14, checkRepositoryAdded, loadBomFile, \
    checkTmcEnabled, waitForGrepProcessWithoutChangeDir, getClusterID, connect_to_workload, isWcpEnabled, isClusterRunning, \
    checkTanzuExtentionEnabled, fluent_bit_enabled, deploy_fluent_bit, checkFluentBitInstalled
from .oneDot4_extentions import generateYamlFile
from .oneDot3_extentions import getBomMap, getRepo
from vmc.sharedConfig.shared_config import certChanging


def deploy_tkgs_extensions():
    try:
        if checkTanzuExtentionEnabled():
            env = envCheck()
            if env[1] != 200:
                current_app.logger.error("Wrong env provided " + env[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "Wrong env provided " + env[0],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            env = env[0]
            vcenter_ip = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
            vcenter_username = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
            str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            password = enc_bytes.decode('ascii').rstrip("\n")
            cluster = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]

            status = tkgsExtensionsPrecheck(vcenter_ip, vcenter_username, password, cluster, env)
            if status[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Required Pre-checks required before TKGs extensions deployment FAILED",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500

            current_app.logger.info("Pre-checks required before TKGs extensions deployment PASSED")
            workload_cluster = request.get_json(force=True)['tanzuExtensions']['tkgClustersName']
            deploy_ext = deploy_extensions(env, workload_cluster)
            if deploy_ext[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": deploy_ext[1],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500

            current_app.logger.info(deploy_ext[0].json['msg'])

            d = {
                "responseType": "SUCCESS",
                "msg": "Extensions deployed successfully",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
        else:
            current_app.logger.info("Extensions are not enabled")
            d = {
                "responseType": "SUCCESS",
                "msg": "Extensions are not enabled",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while deploying extensions",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def tkgsExtensionsPrecheck(vcenter_ip, vcenter_username, password, cluster, env):

    workload_cluster = request.get_json(force=True)['tanzuExtensions']['tkgClustersName']

    workload_status = isClusterRunning(vcenter_ip, vcenter_username, password, cluster, workload_cluster)
    if workload_status[1] != 200:
        return None, workload_status[0].json['msg']

    current_app.logger.info(workload_status[0].json['msg'])

    connect = connect_to_workload(vcenter_ip, vcenter_username, password, cluster, workload_cluster)
    if connect[0] is None:
        current_app.logger.error(connect[1])
        return None, connect[1]

    current_app.logger.info(connect[1])

    rolebinding_result = createClusterRoleBinding()
    if rolebinding_result[0] is None:
        current_app.logger.error(rolebinding_result[1])
        return None, rolebinding_result[1]

    current_app.logger.info(rolebinding_result[1])

    if not checkTmcEnabled(env):
        kapp_status = kappConfiguration()
        if kapp_status[0] is None:
            current_app.logger.error(kapp_status[1])
            return None, kapp_status[1]
        current_app.logger.info(kapp_status[1])

    package_repo = configurePackagesRepository(env)
    if package_repo[0] is None:
        current_app.logger.error(package_repo[1])
        return None, package_repo[1]

    current_app.logger.info(package_repo[1])

    return "SUCCESS", "Pre-checks to start TKGs extensions PASSED"


def createClusterRoleBinding():
    try:
        check_status = checkClusterRoleStatus()
        if check_status[0]:
            return "SUCCESS", check_status[1]
        else:
            current_app.logger.info("Creating Cluster Role Binding...")
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
        current_app.logger.error("Exception occurred while creating cluster role binding")
        current_app.logger.error(str(e))
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
        current_app.logger.error("Exception occurred while checking cluster role binding status")
        current_app.logger.error(str(e))
        return False, "Exception occurred while checking cluster role binding status"


def kappConfiguration():
    if not isKappRunning():
        current_app.logger.info("kapp-controller is not deployed... deploying it now")
        pod_security = isSecurityPodRunning()
        if pod_security[0]:
            current_app.logger.info(pod_security[1])
        else:
            current_app.logger.info("kapp Controller Pod Security Policy is not yet created")
            create_policy = createPodSecurity()
            if create_policy[0] is None:
                return None, create_policy[1]
        kapp_command = ["kubectl", "apply", "-f", "kapp-controller.yaml"]
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
            current_app.logger.info("Waited for " + str(count * 5) + "s for kapp-controller, retrying...")
            count = count + 1

        if run_status:
            return "SUCCESS", "kapp-controller installed successfully"
        else:
            current_app.logger.error("kapp-controller is not up even after 10 minutes wait...")
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
        current_app.logger.info("Exception occurred while checking kapp Controller Pod Security Policy status")
        current_app.logger.error(str(e))
        return False, "Exception occurred while checking kapp Controller Pod Security Policy status"


def createPodSecurity():
    current_app.logger.info("Creating kapp Controller Pod Security Policy....")
    command = ["kubectl", "apply", "-f", "tanzu-system-kapp-ctrl-restricted.yaml"]
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
                current_app.logger.warn("Standard Package Repository is already added but "
                                        "it's not in Reconcile Succeed status")
                return False
    else:
        return True

    return False


def configurePackagesRepository(env):
    if checkTmcEnabled(env):
        current_app.logger.info("TMC is enabled and standard package repository installation should be done by TMC")
        current_app.logger.info("Checking Standard Package Repository status...")
        command = ["tanzu", "package", "repository", "list", "-n", "tanzu-package-repo-global"]
        repo_output = runShellCommandAndReturnOutputAsList(command)
        if repo_output[1] != 0:
            current_app.logger.error(repo_output[0])
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
            current_app.logger.info("Installing Standard Package Repository...")
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
                current_app.logger.info("Waited for " + str(count * 5) + "s for package repository, retrying...")
                count = count + 1

            if run_status:
                return "SUCCESS", "Standard Package Repository installed successfully"
            else:
                current_app.logger.error("Standard Package Repository is not up even after 10 minutes wait...")
                return None, "Failed to deploy Standard Package Repository"
        else:
            return "SUCCESS", "Standard Package Repository is already deployed!"


def deploy_extensions(env, cluster_name):
    try:
        listOfExtention = []
        service = "all"
        repo_address = Repo.PUBLIC_REPO
        checkHarborEnabled = request.get_json(force=True)['tanzuExtensions']['harborSpec']['enableHarborExtension']

        if checkPromethusEnabled():
            listOfExtention.append(Tkg_Extention_names.PROMETHEUS)
            listOfExtention.append(Tkg_Extention_names.GRAFANA)

        status = tkgsCertManagerandContour(env, cluster_name, service)
        if status[1] != 200:
            current_app.logger.info("Failed to deploy extension "+str(status[0].json['msg']))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy extension" + str(status[0].json['msg']),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if str(checkHarborEnabled).lower() == "true":
            current_app.logger.info("Installing harbor...")
            str_enc = str(request.get_json(force=True)['tanzuExtensions']['harborSpec']['harborPasswordBase64'])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            password = enc_bytes.decode('ascii').rstrip("\n")
            harborPassword = password
            host = request.get_json(force=True)['tanzuExtensions']['harborSpec']['harborFqdn']
            harborCertPath = request.get_json(force=True)['tanzuExtensions']['harborSpec']['harborCertPath']
            harborCertKeyPath = request.get_json(force=True)['tanzuExtensions']['harborSpec']['harborCertKeyPath']
            if not host or not harborPassword:
                current_app.logger.error("Harbor FQDN and password are mandatory for harbor deployment."
                                         " Please provide both the details")
                d = {
                    "responseType": "ERROR",
                    "msg": "Harbor FQDN and password are mandatory for harbor deployment. Please provide both the "
                           "details",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            state = installHarborTkgs(harborCertPath, harborCertKeyPath, harborPassword, host, cluster_name, env)
            if state[1] != 200:
                current_app.logger.error(state[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": state[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            else:
                current_app.logger.info(state[0].json['msg'])

        if checkToEnabled(env):
            current_app.logger.info("Tanzu observability is enabled, skipping prometheus and grafana deployment")
            '''d = {
                "responseType": "ERROR",
                "msg": "Tanzu observability is enabled, skipping prometheus and grafana deployment",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200'''
        else:
            if len(listOfExtention) == 0:
                current_app.logger.info("Prometheus and Grafana are disabled")
                '''d = {
                    "responseType": "SUCCESS",
                    "msg": "Prometheus and Grafana are disabled",
                    "ERROR_CODE": 200
                }
                return jsonify(d), 200'''
            else:
                for extension_name in listOfExtention:
                    monitor_status = deploy_monitoring_extentions(env, extension_name, cluster_name)
                    if monitor_status[1] != 200:
                        current_app.logger.error(monitor_status[0].json['msg'])
                        d = {
                            "responseType": "ERROR",
                            "msg": monitor_status[0].json['msg'],
                            "ERROR_CODE": 500
                        }
                        return jsonify(d), 500
                    current_app.logger.info("Extension - " + extension_name + " deployed successfully")

        is_enabled = fluent_bit_enabled(env)
        if is_enabled[0]:
            is_deployed = checkFluentBitInstalled()
            if not is_deployed[0]:
                end_point = is_enabled[1]
                workload_cluster = request.get_json(force=True)['tanzuExtensions']['tkgClustersName']
                response = deploy_fluent_bit(end_point, workload_cluster)
                if response[1] != 200:
                    current_app.logger.error(response[0].json['msg'])
                    d = {
                        "responseType": "ERROR",
                        "msg": response[0].json['msg'],
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                current_app.logger.info("Fluent-bit deployed successfully")
            else:
                current_app.logger.info("Fluent-bit is already deployed and its status is - " + is_deployed[1])
        else:
            current_app.logger.info("Fluent-bit deployment is not enabled. Hence, skipping it.")

        d = {
            "responseType": "SUCCESS",
            "msg": "Extensions deployed successfully",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while deploying extensions",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def tkgsCertManagerandContour(env, cluster_name, service_name):
    try:
        status_ = checkRepositoryAdded(env)
        if status_[1] != 200:
            current_app.logger.error(str(status_[0].json['msg']))
            d = {
                "responseType": "ERROR",
                "msg": str(status_[0].json['msg']),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        install = installExtentionFor14(service_name, cluster_name, env)
        if install[1] != 200:
            return install[0], install[1]
        current_app.logger.info("Configured cert-manager and contour successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Configured cert-manager and contour extensions successfully",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while installing Cert-manager and Contour",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def deploy_monitoring_extentions(env, monitoringType, clusterName):
    try:
        load_bom = loadBomFile()
        if load_bom is None:
            current_app.logger.error("Failed to load the bom data ")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to load the bom data",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        repo = getRepo(env)
        repository = repo[1]
        os.system("chmod +x ./common/injectValue.sh")
        enable = request.get_json(force=True)['tanzuExtensions']['monitoring']['enableLoggingExtension']
        if enable.lower() == "true":
            if monitoringType == Tkg_Extention_names.PROMETHEUS:
                password = None
                extention = Tkg_Extention_names.PROMETHEUS
                bom_map = getBomMap(load_bom, Tkg_Extention_names.PROMETHEUS)
                appName = AppName.PROMETHUS
                namespace = "package-tanzu-system-monitoring"
                yamlFile = "./prometheus-data-values.yaml"
                service = "all"
                cert_Path = request.get_json(force=True)['tanzuExtensions']['monitoring'][
                    'prometheusCertPath']
                fqdn = request.get_json(force=True)['tanzuExtensions']['monitoring'][
                    'prometheusFqdn']
                certKey_Path = request.get_json(force=True)['tanzuExtensions']['monitoring'][
                    'prometheusCertKeyPath']
            elif monitoringType == Tkg_Extention_names.GRAFANA:
                password = request.get_json(force=True)['tanzuExtensions']['monitoring']['grafanaPasswordBase64']
                if not password:
                    current_app.logger.error("Password for grafana is mandatory, please add and re-run deployment")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Password for grafana is mandatory, please add and re-run deployment",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                extention = Tkg_Extention_names.GRAFANA
                yamlFile = Paths.CLUSTER_PATH + clusterName + "/grafana-data-values.yaml"
                appName = AppName.GRAFANA
                namespace = "package-tanzu-system-dashboards"
                command = ["./common/injectValue.sh", Extentions.GRAFANA_LOCATION + "/grafana-extension.yaml", "fluent_bit",
                           repository + "/" + Extentions.APP_EXTENTION]
                runShellCommandAndReturnOutputAsList(command)
                bom_map = getBomMap(load_bom, Tkg_Extention_names.GRAFANA)
                cert_Path = request.get_json(force=True)['tanzuExtensions']['monitoring']['grafanaCertPath']
                fqdn = request.get_json(force=True)['tanzuExtensions']['monitoring']['grafanaFqdn']
                certKey_Path = request.get_json(force=True)['tanzuExtensions']['monitoring'][
                    'grafanaCertKeyPath']

            if not fqdn:
                current_app.logger.error("FQDN for " + extention + " is mandatory, please add and re-run deployment")
                d = {
                    "responseType": "ERROR",
                    "msg": "FQDN for " + extention + " is mandatory, please add and re-run deployment",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500

            extention_validate_command = ["kubectl", "get", "app", appName, "-n", namespace]

            command_fluent_bit = runShellCommandAndReturnOutputAsList(extention_validate_command)
            if not verifyPodsAreRunning(appName, command_fluent_bit[0],
                                        RegexPattern.RECONCILE_SUCCEEDED):
                current_app.logger.info("Deploying " + extention)
                version = getVersionOfPackage(extention.lower() + ".tanzu.vmware.com")
                if version is None:
                    current_app.logger.error("Failed Capture the available Prometheus version")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Capture the available Prometheus version",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                file_status = generateYamlFile(extention, version, certKey_Path, cert_Path, fqdn, password, yamlFile)
                if file_status[1] == 500:
                    current_app.logger.error(yamlFile + " generation failed " + str(file_status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": yamlFile + " generation failed " + str(file_status[0]),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500

                update_sc_response = updateStorageClass(yamlFile, extention)
                if update_sc_response[1] != 200:
                    d = {
                        "responseType": "ERROR",
                        "msg": update_sc_response[0].json['msg'],
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500

                current_app.logger.info("Initiated " + extention + " deployment")
                deply_extension_command = ["tanzu", "package", "install", extention.lower(), "--package-name",
                                           extention.lower() + ".tanzu.vmware.com", "--version", version,
                                           "--values-file", yamlFile, "--namespace", namespace, "--create-namespace"]
                state_extention_apply = runShellCommandAndReturnOutputAsList(deply_extension_command)
                if state_extention_apply[1] != 0:
                    current_app.logger.error(extention + "install command failed. Checking for reconciliation "
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
                    current_app.logger.info("Waited for  " + str(count * 30) + "s, retrying.")
                if not found:
                    current_app.logger.error(extention + " Extension is still not deployed " + str(count * 30))
                    d = {
                        "responseType": "ERROR",
                        "msg": extention + " Extension is still not deployed " + str(count * 30),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                else:
                    d = {
                        "responseType": "SUCCESS",
                        "msg": appName + " is deployed",
                        "ERROR_CODE": 200
                    }
                    return jsonify(d), 200
            else:
                current_app.logger.info(appName + " is already running")
                d = {
                    "responseType": "SUCCESS",
                    "msg": appName + " is already running",
                    "ERROR_CODE": 200
                }
                return jsonify(d), 200
        else:
            current_app.logger.info("Monitoring extension deployment is not enabled")
            d = {
                "responseType": "SUCCESS",
                "msg": "Monitoring extension deployment is not enabled",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200

    except Exception as e:
        current_app.logger.info("Failed to  deploy monitoring " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to  deploy monitoring " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def updateStorageClass(yamlFile, extension):
    try:
        sc = None
        get_sc_command = ["kubectl", "get", "sc"]
        get_sc_output = runShellCommandAndReturnOutputAsList(get_sc_command)
        if get_sc_output[1] != 0:
            current_app.logger.error("Command to get storage class name failed.")
            d = {
                "responseType": "ERROR",
                "msg": "Command to get storage class name failed.",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            for item in range(len(get_sc_output[0])):
                if get_sc_output[0][item].split()[1] == "(default)":
                    sc = get_sc_output[0][item].split()[0]
                    break

        if sc is None:
            current_app.logger.error("Failed to obtain storage class name for cluster")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to obtain storage class name for cluster",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        current_app.logger.info("Default Storage Class for workload cluster - " + sc)
        current_app.logger.info("Update " + extension + " data files with storage class")
        if extension == Tkg_Extention_names.PROMETHEUS:
            inject_sc = ["sh", "./common/injectValue.sh", yamlFile, "inject_sc_prometheus", sc]
        elif extension == Tkg_Extention_names.GRAFANA:
            inject_sc = ["sh", "./common/injectValue.sh", yamlFile, "inject_sc_grafana", sc]
        elif extension == AppName.HARBOR:
            inject_sc = ["sh", "./common/injectValue.sh", yamlFile, "inject_sc_harbor", sc]
        else:
            current_app.logger.error("Wrong extension name provided for updating storage class name - " + extension)
            d = {
                "responseType": "ERROR",
                "msg": "Wrong extension name provided for updating storage class name - " + extension,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        inject_sc_response = runShellCommandAndReturnOutput(inject_sc)
        if inject_sc_response[1] == 500:
            current_app.logger.error("Failed to update storage class name " + str(inject_sc_response[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to update storage class name " + str(inject_sc_response[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info(inject_sc_response[0])
            d = {
                "responseType": "SUCCESS",
                "msg": extension + " yaml file updated successfully",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while update data file for extensions",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def installHarborTkgs(harborCertPath, harborCertKeyPath, harborPassword, host, clusterName, env):
    main_command = ["tanzu", "package", "installed", "list", "-A"]
    sub_command = ["grep", AppName.HARBOR]
    out = grabPipeOutput(main_command, sub_command)
    if not (verifyPodsAreRunning(AppName.HARBOR, out[0], RegexPattern.RECONCILE_SUCCEEDED)
            or verifyPodsAreRunning(AppName.HARBOR, out[0], RegexPattern.RECONCILE_FAILED)):
        timer = 0
        current_app.logger.info("Validating contour and cert-manager is running")
        command = ["tanzu", "package", "installed", "list", "-A"]
        status = runShellCommandAndReturnOutputAsList(command)
        verify_contour = False
        verify_cert_manager = False
        while timer < 600:
            if verify_contour or verifyPodsAreRunning(AppName.CONTOUR, status[0], RegexPattern.RECONCILE_SUCCEEDED):
                current_app.logger.info("Contour is running")
                verify_contour = True
            if verify_cert_manager or verifyPodsAreRunning(AppName.CERT_MANAGER, status[0], RegexPattern.RECONCILE_SUCCEEDED):
                verify_cert_manager = True
                current_app.logger.info("Cert Manager is running")

            if verify_contour and verify_cert_manager:
                break
            else:
                timer = timer + 30
                time.sleep(30)
                status = runShellCommandAndReturnOutputAsList(command)
                current_app.logger.info("Waited for " + str(timer) + "s, retrying for contour and cert manager to be "
                                                                     "running")
        if not verify_contour:
            current_app.logger.error("Contour is not running")
            d = {
                "responseType": "ERROR",
                "msg": "Contour is not running ",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if not verify_cert_manager:
            current_app.logger.error("Cert manager is not running")
            d = {
                "responseType": "ERROR",
                "msg": "Cert manager is not running ",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        state = getVersionOfPackage("harbor.tanzu.vmware.com")
        if state is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get Version of package contour.tanzu.vmware.com",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Deploying harbor - " + state)
        get_url_command = ["kubectl", "-n", "tanzu-package-repo-global", "get", "packages",
                           "harbor.tanzu.vmware.com." + state, "-o",
                           "jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}'"]
        current_app.logger.info("Getting harbor url")
        status = runShellCommandAndReturnOutputAsList(get_url_command)
        if status[1] != 0:
            current_app.logger.error("Failed to get harbor image url " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get harbor image url " + str(status[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Got harbor url " + str(status[0][0]).replace("'", ""))
        pull = ["imgpkg", "pull", "-b", str(status[0][0]).replace("'", ""), "-o", "/tmp/harbor-package"]
        status = runShellCommandAndReturnOutputAsList(pull)
        if status[1] != 0:
            current_app.logger.error("Failed to pull harbor packages " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get harbor image url " + str(status[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        os.system("rm -rf " + Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml")
        os.system("cp /tmp/harbor-package/config/values.yaml " + Paths.CLUSTER_PATH + clusterName +"/harbor-data"
                                                                                                   "-values.yaml")
        command_harbor_genrate_psswd = ["sh", "/tmp/harbor-package/config/scripts/generate-passwords.sh",
                                        Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml"]
        state_harbor_genrate_psswd = runShellCommandAndReturnOutputAsList(command_harbor_genrate_psswd)
        if state_harbor_genrate_psswd[1] == 500:
            current_app.logger.error("Failed to generate password " + str(state_harbor_genrate_psswd[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to generate password " + str(state_harbor_genrate_psswd[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        cer = certChanging(harborCertPath, harborCertKeyPath, harborPassword, host,clusterName)
        if cer[1] != 200:
            current_app.logger.error(cer[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": cer[0].json['msg'],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        os.system("chmod +x common/injectValue.sh")

        update_sc_resp = updateStorageClass(Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml", AppName.HARBOR)
        if update_sc_resp[1] != 200:
            current_app.logger.error(update_sc_resp[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": update_sc_resp[0].json['msg'],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info(update_sc_resp[0].json["msg"])

        command = ["sh", "./common/injectValue.sh", Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml", "remove"]
        runShellCommandAndReturnOutputAsList(command)

        current_app.logger.info("Initiated harbor deployment")
        command = ["tanzu", "package", "install", "harbor", "--package-name", "harbor.tanzu.vmware.com", "--version",
                   state, "--values-file", Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml", "--namespace", "package-tanzu-system-registry",
                   "--create-namespace"]
        runShellCommandAndReturnOutputAsList(command)

        current_app.logger.info("Waiting for harbor installation to complete...")
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
            current_app.logger.info("Waited for  " + str(count * 30) + "s, retrying.")

        if running:
            d = {
                "responseType": "SUCCESS",
                "msg": "Deployed harbor successfully",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
        elif reconcile_failed:
            current_app.logger.info("Harbor deployment reconcile failed")
            current_app.logger.info("Applying overlay and re-checking...")
            overlay_status = tkgsOverlay()
            if overlay_status[0] is None:
                current_app.logger.error(overlay_status[1])
                d = {
                    "responseType": "ERROR",
                    "msg": overlay_status[1],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        else:
            current_app.logger.info("Harbor status did not change. Waited for " + str(count * 30) + "s")
            current_app.logger.info("Applying overlay and re-checking...")

        current_app.logger.info("Waiting for harbor installation to complete post pods re-creation...")
        state = waitForGrepProcessWithoutChangeDir(main_command, sub_command, AppName.HARBOR,
                                                   RegexPattern.RECONCILE_SUCCEEDED)
        if state[1] != 200:
            current_app.logger.info("Harbor Deployment Failed.")
            d = {
                "responseType": "ERROR",
                "msg": state[0].json['msg'],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        current_app.logger.info("Deployed harbor successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Deployed harbor successfully",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    else:
        current_app.logger.info("Harbor is already deployed and it's status is - " + out[0].split()[3] + " " +
                                out[0].split()[4])
        d = {
            "responseType": "SUCCESS",
            "msg": "Harbor is already deployed and it's status is - " + out[0].split()[3] + " " +
                   out[0].split()[4],
            "ERROR_CODE": 200
        }
        return jsonify(d), 200


def tkgsOverlay():
    try:
        os.system("chmod +x tkgs_apply_overlay.sh fix-fsgroup-overlay.yaml")
        apply = ["sh", "./tkgs_apply_overlay.sh"]
        apply_state = runShellCommandAndReturnOutput(apply)
        if apply_state[1] != 0:
            current_app.logger.error("Failed to create secrets " + str(apply_state[0]))
            return None, "Failed to create secrets " + str(apply_state[0])
        current_app.logger.info(apply_state[0])

        time.sleep(10)

        apply_command = ["kubectl", "-n", "package-tanzu-system-registry", "annotate", "packageinstalls", "harbor",
                         "ext.packaging.carvel.dev/ytt-paths-from-secret-name.1=harbor-database-redis-trivy-jobservice-registry-image-overlay"]

        patch_status = runShellCommandAndReturnOutput(apply_command)
        if patch_status[1] != 0:
            current_app.logger.error(patch_status[0])
            return None, "Command for applying harbor secret failed"
        else:
            current_app.logger.info(patch_status[0])

        current_app.logger.info("Waiting for 30s before deleting pods...")
        time.sleep(30)

        current_app.logger.info("Deleting pods")
        delete_command = ["kubectl", "delete", "pods", "--all", "-n", "package-tanzu-system-registry"]
        delete_status = runShellCommandAndReturnOutputAsList(delete_command)
        if delete_status[1] != 0:
            return None, "Command for deleting existing harbor pods failed."
        else:
            current_app.logger.info(delete_status[0])

        return "SUCCESS", "Secrets created successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while applying harbor secrets"
