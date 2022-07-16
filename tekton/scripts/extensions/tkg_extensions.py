
#!/usr/local/bin/python3

#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
from pathlib import Path
import time
import json
from util.logger_helper import LoggerHelper, log
import os
from pathlib import Path
from tqdm import tqdm
import time
import json
from ruamel import yaml

#from model.extensions import extensions_types, deploy_extensions
from constants.constants import Tkg_Extention_names, Repo, RegexPattern, Extentions, AppName, Paths 
import json, requests
from util.common_utils import getVersionOfPackage, switchToContext, loadBomFile, \
     checkAirGappedIsEnabled, installCertManagerAndContour, getManagementCluster, verifyCluster, \
     checkToEnabled, checkFluentBitInstalled, deploy_fluent_bit
from util.ShellHelper import runShellCommandAndReturnOutputAsList, \
    verifyPodsAreRunning, runShellCommandAndReturnOutput \
    
#from exts.tkg_extensions import getBomMap, generateYamlWithoutCert, getRepo
from util.logger_helper import LoggerHelper, log

logger = LoggerHelper.get_logger(Path(__file__).stem)


class deploy_tkg_extensions():
    def __init__(self, extension_name, jsonspec):
        self.extension_name = extension_name
        self.jsonspec = jsonspec
        logger.info("Deploying extentions: {}".format(self.extension_name))

    def deploy(self):       

        if str(self.extension_name).__contains__("Fluent"):
            status = self.fluent_bit(self.extension_name)
            return status[0], status[1]
        elif str(self.extension_name) == Tkg_Extention_names.GRAFANA:
            status = self.grafana()
            return status[0], status[1]
        elif str(self.extension_name) == Tkg_Extention_names.LOGGING:
            status = self.logging()
            return status[0], status[1]
        elif str(self.extension_name) == Tkg_Extention_names.PROMETHEUS:
            status = self.prometheus()
            return status[0], status[1]

    def fluent_bit(self, fluent_bit_type):
        fluent_bit_response = deploy_extension_fluent(fluent_bit_type, self.jsonspec)
        if fluent_bit_response[1] != 200:
            logger.error(fluent_bit_response[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": fluent_bit_response[0].json['msg'],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        else:
            logger.info("Successfully deployed fluent bit syslog")
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully deployed fluent bit syslog",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200

    def grafana(self):
        monitoring = monitoringDeployment(Tkg_Extention_names.GRAFANA, self.jsonspec)
        if monitoring[1] != 200:
            logger.error(monitoring[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": monitoring[0].json['msg'],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        else:
            logger.info("Successfully deployed GRAFANA")
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully deployed GRAFANA",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200

    def prometheus(self):
        monitoring = monitoringDeployment(Tkg_Extention_names.PROMETHEUS, self.jsonspec)
        if monitoring[1] != 200:
            logger.error(monitoring[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": monitoring[0].json['msg'],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        else:
            logger.info("Successfully deployed promethus")
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully deployed promethus",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200

    def logging(self):
        logger.info("Successfully deployed fluent bit logging")
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully deployed fluent bit logging",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

    

def getImageName(server_image):
    return server_image[server_image.rindex("/") + 1:len(server_image)]

def getRepo(env, jsonspec):
    try:
        if checkAirGappedIsEnabled(env, jsonspec):
            repo_address = str(jsonspec['envSpec']['customRepositorySpec'][
                                   'tkgCustomImageRepository'])
        else:
            repo_address = Repo.PUBLIC_REPO
        if repo_address.endswith("/"):
            repo_address = repo_address.rstrip("/")
        repo_address = repo_address.replace("https://", "").replace("http://", "")
        return "SUCCESS", repo_address
    except Exception as e:
        return "ERROR", str(e)

def getBomMap(load_bom, monitorinType):
    bom_map = {}
    if monitorinType == Tkg_Extention_names.PROMETHEUS:
        image = load_bom['components']['prometheus'][0]['images']['prometheusImage']['imagePath']
        bom_map['prometheus_server_name'] = getImageName(image)
        bom_map['prometheus_server_tag'] = \
            load_bom['components']['prometheus'][0]['images']['prometheusImage']['tag']
        image = load_bom['components']['alertmanager'][0]['images']['alertmanagerImage']['imagePath']
        bom_map['alertmanager_name'] = getImageName(image)
        bom_map['alertmanager_tag'] = \
            load_bom['components']['alertmanager'][0]['images']['alertmanagerImage']['tag']
        image = load_bom['components']['kube-state-metrics'][0]['images']['kubeStateMetricsImage'][
            'imagePath']
        bom_map['kube_state_metrics_name'] = getImageName(image)
        bom_map['kube_state_metrics_tag'] = \
            load_bom['components']['kube-state-metrics'][0]['images']['kubeStateMetricsImage']['tag']
        image = \
            load_bom['components']['prometheus_node_exporter'][0]['images'][
                'prometheusNodeExporterImage'][
                'imagePath']
        bom_map['node_exporter_name'] = getImageName(image)
        bom_map['node_exporter_tag'] = \
            load_bom['components']['prometheus_node_exporter'][0]['images'][
                'prometheusNodeExporterImage'][
                'tag']
        image = load_bom['components']['pushgateway'][0]['images']['pushgatewayImage']['imagePath']
        bom_map['pushgateway_name'] = getImageName(image)
        bom_map['pushgateway_tag'] = \
            load_bom['components']['pushgateway'][0]['images']['pushgatewayImage']['tag']
        image = load_bom['components']['cadvisor'][0]['images']['cadvisorImage']['imagePath']
        bom_map['cadvisor_name'] = getImageName(image)
        bom_map['cadvisor_tag'] = load_bom['components']['cadvisor'][0]['images']['cadvisorImage'][
            'tag']
        image = load_bom['components']['configmap-reload'][0]['images']['configmapReloadImage'][
            'imagePath']
        bom_map['prometheus_server_configmap_reload_name'] = getImageName(image)
        bom_map['prometheus_server_configmap_reload_tag'] = \
            load_bom['components']['configmap-reload'][0]['images']['configmapReloadImage']['tag']
    elif monitorinType == Tkg_Extention_names.GRAFANA:
        image = load_bom['components']['grafana'][0]['images']['grafanaImage']['imagePath']
        bom_map['image_name'] = getImageName(image)
        bom_map['image_tag'] = \
            load_bom['components']['grafana'][0]['images']['grafanaImage']['tag']
        image = load_bom['components']['k8s-sidecar'][0]['images']['k8sSidecarImage']['imagePath']
        bom_map['grafana_init_container_name'] = getImageName(image)
        bom_map['grafana_init_container_tag'] = \
            load_bom['components']['k8s-sidecar'][0]['images']['k8sSidecarImage']['tag']
        bom_map['grafana_sc_dashboard_name'] = getImageName(image)
        bom_map['grafana_sc_dashboard_tag'] = \
            load_bom['components']['k8s-sidecar'][0]['images']['k8sSidecarImage']['tag']

    return bom_map


def captureVersion(extention):
    command = ["tanzu", "package", "available", "list", extention.lower() + ".tanzu.vmware.com",
               "-A"]
    get_version = runShellCommandAndReturnOutput(command)
    mcs = get_version[0].split("\n")
    for mc in mcs:
        if not str(mc).__contains__("Retrieving"):
            if str(mc).__contains__(extention.lower()):
                return str(mc).split(" ")[4].strip()

    return None


def generateYamlFile(extention, version, certKey_Path, cert_Path, fqdn, secret, yaml_file_name):
    extention = extention.lower()
    get_repo = ["kubectl", "-n", "tanzu-package-repo-global", "get", "packages",
                extention + ".tanzu.vmware.com." + version, "-o",
                "jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}'"]

    get_repo_state = runShellCommandAndReturnOutput(get_repo)
    if get_repo_state[1] != 0:
        logger.error("Failed to extention yaml copy " + str(get_repo_state[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to extention yaml copy " + str(get_repo_state[0]),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500

    generate_file = ["imgpkg", "pull", "-b", get_repo_state[0].replace("'", "").strip(), "-o",
                     "/tmp/" + extention + "-package"]
    generate_file_state = runShellCommandAndReturnOutputAsList(generate_file)
    if generate_file_state[1] != 0:
        logger.error("Failed to generate extension yaml copy " + str(generate_file_state[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to generate extension yaml copy " + str(generate_file_state[0]),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500

    command_yaml_copy = ["cp", "/tmp/" + extention + "-package/config/values.yaml",
                         yaml_file_name]

    copy_state = runShellCommandAndReturnOutputAsList(command_yaml_copy)
    if copy_state[1] != 0:
        logger.error("Failed to copy extension yaml " + str(copy_state[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to copy extension yaml " + str(copy_state[0]),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500

    # modify yaml file, add fqdn etc..

    if extention == 'grafana':
        command = ["./common/injectValue.sh", yaml_file_name, "inject_secret", secret, "tanzu-system-dashboards"]
    else:
        command = ["./common/injectValue.sh", yaml_file_name, "inject_ingress", "true"]
    runShellCommandAndReturnOutputAsList(command)
    if cert_Path and certKey_Path:
        cert = Path(cert_Path).read_text()
        cert_key = Path(certKey_Path).read_text()
        inject_cert_key = ["sh", "./common/injectValue.sh", yaml_file_name, "inject_cert_dot4", cert, cert_key]
        state_harbor_change_host_password_cert = runShellCommandAndReturnOutput(inject_cert_key)
        if state_harbor_change_host_password_cert[1] == 500:
            logger.error(
                "Failed to change  cert " + str(state_harbor_change_host_password_cert[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to change cert " + str(state_harbor_change_host_password_cert[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
    command = ["./common/injectValue.sh", yaml_file_name, "inject_ingress_fqdn", fqdn]
    runShellCommandAndReturnOutputAsList(command)
    command2 = ["./common/injectValue.sh", yaml_file_name, "remove"]
    runShellCommandAndReturnOutputAsList(command2)

    d = {
        "responseType": "SUCCESS",
        "msg": "Yaml file for extension deployment created",
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200


def monitoringDeployment(monitoringType, jsonspec):
    try:
        enable = jsonspec['tanzuExtensions']['monitoring']['enableLoggingExtension']
        if enable == "true":
            """
            Env check commented and hardcoded the env variable with value vpshere

            pre = preChecks()
            if pre[1] != 200:
                logger.error(pre[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": pre[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            

            env = envCheck()
            if env[1] != 200:
                logger.error("Wrong env provided " + env[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "Wrong env provided " + env[0],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            """
            env = "vsphere"
            if checkToEnabled(env, jsonspec):
                logger.info("Tanzu observability is enabled, skipping prometheus and grafana deployment")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Tanzu observability is enabled, skipping prometheus and grafana deployment",
                    "ERROR_CODE": 200
                }
                return json.dumps(d), 200
            if checkAirGappedIsEnabled(env, jsonspec):
                repo_address = str(
                    jsonspec['envSpec']['customRepositorySpec'][
                        'tkgCustomImageRepository'])
            else:
                repo_address = Repo.PUBLIC_REPO
            cluster = str(
                jsonspec['tanzuExtensions']['tkgClustersName'])
            listOfClusters = cluster.split(",")
            for listOfCluster in listOfClusters:
                if not verifyCluster(listOfCluster):
                    logger.info("Cluster " + listOfCluster + " is not deployed and not running")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "Cluster " + listOfCluster + " is not deployed and not running",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                mgmt = getManagementCluster()
                if mgmt is None:
                    logger.error("Failed to get management cluster")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get management cluster",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                if str(mgmt).strip() == listOfCluster.strip():
                    logger.info("Currently " + monitoringType + " is not supported on management cluster")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Currently " + monitoringType + " is not supported on management cluster",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                else:
                    switch = switchToContext(str(listOfCluster).strip(), env)
                    if switch[1] != 200:
                        logger.info(switch[0].json['msg'])
                        d = {
                            "responseType": "ERROR",
                            "msg": switch[0].json['msg'],
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                load_bom = loadBomFile()
                if load_bom is None:
                    logger.error("Failed to load the bom data ")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to load the bom data",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                repo = getRepo(env, jsonspec)
                repository = repo[1]
                os.system("chmod +x ./common/injectValue.sh")
            if monitoringType == Tkg_Extention_names.PROMETHEUS:
                password = None
                extention = Tkg_Extention_names.PROMETHEUS
                bom_map = getBomMap(load_bom, Tkg_Extention_names.PROMETHEUS)
                appName = AppName.PROMETHEUS
                namespace = "package-tanzu-system-monitoring"
                yamlFile = Paths.CLUSTER_PATH + cluster + "/prometheus-data-values.yaml"
                service = "all"
                cert_ext_status = installCertManagerAndContour(env, str(listOfCluster).strip(), repo_address, service, jsonspec)
                if cert_ext_status[1] != 200:
                    logger.error(cert_ext_status[0].json['msg'])
                    d = {
                        "responseType": "ERROR",
                        "msg": cert_ext_status[0].json['msg'],
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                cert_Path = jsonspec['tanzuExtensions']['monitoring'][
                    'prometheusCertPath']
                fqdn = jsonspec['tanzuExtensions']['monitoring'][
                    'prometheusFqdn']
                certKey_Path = jsonspec['tanzuExtensions']['monitoring'][
                    'prometheusCertKeyPath']
            elif monitoringType == Tkg_Extention_names.GRAFANA:
                password = jsonspec['tanzuExtensions']['monitoring']['grafanaPasswordBase64']
                extention = Tkg_Extention_names.GRAFANA
                secret_name = "grafana-data-values"
                extention_yaml = "grafana-extension.yaml"
                yamlFile = Paths.CLUSTER_PATH + cluster + "/grafana-data-values.yaml"
                appName = AppName.GRAFANA
                namespace = "package-tanzu-system-dashboards"
                command = ["./common/injectValue.sh", Extentions.GRAFANA_LOCATION + "/grafana-extension.yaml",
                           "fluent_bit", repository + "/" + Extentions.APP_EXTENTION]
                runShellCommandAndReturnOutputAsList(command)
                bom_map = getBomMap(load_bom, Tkg_Extention_names.GRAFANA)
                cert_Path = jsonspec['tanzuExtensions']['monitoring']['grafanaCertPath']
                fqdn = jsonspec['tanzuExtensions']['monitoring']['grafanaFqdn']
                certKey_Path = jsonspec['tanzuExtensions']['monitoring'][
                    'grafanaCertKeyPath']

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

                deply_extension_command = ["tanzu", "package", "install", extention.lower(), "--package-name",
                                           extention.lower() + ".tanzu.vmware.com", "--version", version,
                                           "--values-file", yamlFile, "--namespace", namespace, "--create-namespace"]
                state_extention_apply = runShellCommandAndReturnOutputAsList(deply_extension_command)
                if state_extention_apply[1] != 0:
                    logger.error(
                        extention + " install command failed. Checking for reconciliation status...")

                found = False
                count = 0
                command_ext_bit = runShellCommandAndReturnOutputAsList(extention_validate_command)
                if verifyPodsAreRunning(appName, command_ext_bit[0], RegexPattern.RECONCILE_SUCCEEDED):
                    found = True
                    logger.info(appName + " deployed successfully")

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
                    logger.error("Extension is still not deployed " + str(count * 30))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Extension is still not deployed " + str(count * 30),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                else:
                    logger.info(appName + " is deployed")
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


def deploy_extension_fluent(fluent_bit_endpoint, jsonspec):
    try:
        is_already_installed = checkFluentBitInstalled()
        if not is_already_installed[0]:
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
            env = "vsphere"
            cluster = str(jsonspec['tanzuExtensions']['tkgClustersName'])
            listOfClusters = cluster.split(",")
            for listOfCluster in listOfClusters:
                if not verifyCluster(listOfCluster):
                    logger.info("Cluster " + listOfCluster + " is not deployed and not running")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "Cluster " + listOfCluster + " is not deployed and not running",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                mgmt = getManagementCluster()
                if mgmt is None:
                    logger.error("Failed to get management cluster")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get management cluster",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                if str(mgmt).strip() == listOfCluster.strip():
                    logger.info("Currently fluent-bit " + fluent_bit_endpoint + "is not supported on "
                                                                                            "management cluster")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Currently fluent-bit " + fluent_bit_endpoint + " is not supported on management cluster",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                else:
                    switch = switchToContext(str(listOfCluster).strip(), env)
                    if switch[1] != 200:
                        logger.info(switch[0].json['msg'])
                        d = {
                            "responseType": "ERROR",
                            "msg": switch[0].json['msg'],
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                response = deploy_fluent_bit(fluent_bit_endpoint, cluster, jsonspec)
                if response[1] != 200:
                    logger.error(response[0].json['msg'])
                    d = {
                        "responseType": "ERROR",
                        "msg": response[0].json['msg'],
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
            logger.info("Fluent-bit with endpoint - " + fluent_bit_endpoint + " installed successfully")
            d = {
                "responseType": "SUCCESS",
                "msg": "Fluent-bit deployed successfully",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        else:
            logger.info("Fluent-bit is already deployed and its status is - " + is_already_installed[1])
            d = {
                "responseType": "SUCCESS",
                "msg": "Fluent-bit is already deployed and its status is - " + is_already_installed[1],
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
    except Exception as e:
        logger.error("Exception occurred while deploying fluent-bit - " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while deploying fluent-bit",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500
