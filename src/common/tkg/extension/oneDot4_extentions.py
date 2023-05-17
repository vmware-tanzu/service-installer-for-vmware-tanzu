# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import os
import time
from pathlib import Path

from flask import current_app, jsonify, request

from common.common_utilities import (
    checkAirGappedIsEnabled,
    checkFluentBitInstalled,
    checkRepositoryAdded,
    checkToEnabled,
    deploy_fluent_bit,
    envCheck,
    getManagementCluster,
    getVersionOfPackage,
    installCertManagerAndContour,
    loadBomFile,
    preChecks,
    switchToContext,
    verifyCluster,
)
from common.operation.constants import AppName, Extentions, Paths, RegexPattern, Repo, Tkg_Extention_names
from common.operation.ShellHelper import (
    runProcess,
    runShellCommandAndReturnOutput,
    runShellCommandAndReturnOutputAsList,
    verifyPodsAreRunning,
)
from common.tkg.extension.oneDot3_extentions import getRepo

from .extentions import deploy_extentions, extentions_types


class deploy_Dot4_ext(deploy_extentions):
    def deploy(self, extention_name):
        dot4 = extention_types_dot4_impl()
        if str(extention_name).__contains__("Fluent"):
            status = dot4.fluent_bit(extention_name)
            return status[0], status[1]
        elif str(extention_name) == Tkg_Extention_names.GRAFANA:
            status = dot4.grafana()
            return status[0], status[1]
        elif str(extention_name) == Tkg_Extention_names.LOGGING:
            status = dot4.logging()
            return status[0], status[1]
        elif str(extention_name) == Tkg_Extention_names.PROMETHEUS:
            status = dot4.prometheus()
            return status[0], status[1]


class extention_types_dot4_impl(extentions_types):
    def fluent_bit(self, fluent_bit_type):
        env = envCheck()
        env = env[0]
        status_ = checkRepositoryAdded(env)
        if status_[1] != 200:
            current_app.logger.error(str(status_[0].json["msg"]))
            d = {"responseType": "ERROR", "msg": str(status_[0].json["msg"]), "STATUS_CODE": 500}
            return jsonify(d), 500
        fluent_bit_response = deploy_extension_fluent(fluent_bit_type)
        if fluent_bit_response[1] != 200:
            current_app.logger.error(fluent_bit_response[0].json["msg"])
            d = {"responseType": "ERROR", "msg": fluent_bit_response[0].json["msg"], "STATUS_CODE": 500}
            return jsonify(d), 500
        else:
            current_app.logger.info("Successfully deployed Fluent-bit Syslog")
            d = {"responseType": "SUCCESS", "msg": "Successfully deployed Fluent-bit Syslog", "STATUS_CODE": 200}
            return jsonify(d), 200

    def grafana(self):
        monitoring = monitoringDeployment(Tkg_Extention_names.GRAFANA)
        if monitoring[1] != 200:
            current_app.logger.error(monitoring[0].json["msg"])
            d = {"responseType": "ERROR", "msg": monitoring[0].json["msg"], "STATUS_CODE": 500}
            return jsonify(d), 500
        else:
            current_app.logger.info("Successfully deployed Grafana")
            d = {"responseType": "SUCCESS", "msg": "Successfully deployed Grafana", "STATUS_CODE": 200}
            return jsonify(d), 200

    def prometheus(self):
        monitoring = monitoringDeployment(Tkg_Extention_names.PROMETHEUS)
        if monitoring[1] != 200:
            current_app.logger.error(monitoring[0].json["msg"])
            d = {"responseType": "ERROR", "msg": monitoring[0].json["msg"], "STATUS_CODE": 500}
            return jsonify(d), 500
        else:
            current_app.logger.info("Successfully deployed Promethus")
            d = {"responseType": "SUCCESS", "msg": "Successfully deployed Promethus", "STATUS_CODE": 200}
            return jsonify(d), 200

    def logging(self):
        current_app.logger.info("Successfully deployed Fluent-bit Logging")
        d = {"responseType": "SUCCESS", "msg": "Successfully deployed Fluent-bit Logging", "STATUS_CODE": 200}
        return jsonify(d), 200


def captureVersion(extention):
    command = ["tanzu", "package", "available", "list", extention.lower() + ".tanzu.vmware.com", "-A"]
    get_version = runShellCommandAndReturnOutput(command)
    mcs = get_version[0].split("\n")
    for mc in mcs:
        if not str(mc).__contains__("Retrieving"):
            if str(mc).__contains__(extention.lower()):
                return str(mc).split(" ")[4].strip()

    return None


def generateYamlFile(extention, version, certKey_Path, cert_Path, fqdn, secret, yaml_file_name):
    extention = extention.lower()
    get_repo = [
        "kubectl",
        "-n",
        "tkg-system",
        "get",
        "packages",
        extention + ".tanzu.vmware.com." + version,
        "-o",
        "jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}'",
    ]

    get_repo_state = runShellCommandAndReturnOutput(get_repo)
    if get_repo_state[1] != 0:
        current_app.logger.error("Failed to get extention yaml copy " + str(get_repo_state[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get extention yaml copy " + str(get_repo_state[0]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    generate_file = [
        "imgpkg",
        "pull",
        "-b",
        get_repo_state[0].replace("'", "").strip(),
        "-o",
        "/tmp/" + extention + "-package",
    ]
    generate_file_state = runShellCommandAndReturnOutputAsList(generate_file)
    if generate_file_state[1] != 0:
        current_app.logger.error("Failed to generate extension yaml copy " + str(generate_file_state[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to generate extension yaml copy " + str(generate_file_state[0]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    command_yaml_copy = ["cp", "/tmp/" + extention + "-package/config/values.yaml", yaml_file_name]

    copy_state = runShellCommandAndReturnOutputAsList(command_yaml_copy)
    if copy_state[1] != 0:
        current_app.logger.error("Failed to copy extension yaml " + str(copy_state[0]))
        d = {"responseType": "ERROR", "msg": "Failed to copy extension yaml " + str(copy_state[0]), "STATUS_CODE": 500}
        return jsonify(d), 500

    if not os.path.exists(yaml_file_name):
        current_app.logger.error("Failed to copy extension yaml " + str(copy_state[0]))
        d = {"responseType": "ERROR", "msg": "Failed to copy extension yaml " + str(copy_state[0]), "STATUS_CODE": 500}
        return jsonify(d), 500

    # modify yaml file, add fqdn etc..

    if extention == "grafana":
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
            current_app.logger.error("Failed to change  cert " + str(state_harbor_change_host_password_cert[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to change cert " + str(state_harbor_change_host_password_cert[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
    command = ["./common/injectValue.sh", yaml_file_name, "inject_ingress_fqdn", fqdn]
    runShellCommandAndReturnOutputAsList(command)
    command2 = ["./common/injectValue.sh", yaml_file_name, "remove"]
    runShellCommandAndReturnOutputAsList(command2)

    d = {"responseType": "SUCCESS", "msg": "Yaml file for extension deployment created", "STATUS_CODE": 200}
    return jsonify(d), 200


def monitoringDeployment(monitoringType):
    try:
        enable = request.get_json(force=True)["tanzuExtensions"]["monitoring"]["enableLoggingExtension"]
        if enable == "true":
            pre = preChecks()
            if pre[1] != 200:
                current_app.logger.error(pre[0].json["msg"])
                d = {"responseType": "ERROR", "msg": pre[0].json["msg"], "STATUS_CODE": 500}
                return jsonify(d), 500
            env = envCheck()
            if env[1] != 200:
                current_app.logger.error("Wrong env provided " + env[0])
                d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
                return jsonify(d), 500
            env = env[0]
            if checkToEnabled(env):
                current_app.logger.info("Tanzu observability is enabled, skipping prometheus and grafana deployment")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Tanzu observability is enabled, skipping prometheus and grafana deployment",
                    "STATUS_CODE": 200,
                }
                return jsonify(d), 200
            if checkAirGappedIsEnabled(env):
                repo_address = str(
                    request.get_json(force=True)["envSpec"]["customRepositorySpec"]["tkgCustomImageRepository"]
                )
            else:
                repo_address = Repo.PUBLIC_REPO
            cluster = str(request.get_json(force=True)["tanzuExtensions"]["tkgClustersName"])
            listOfClusters = cluster.split(",")
            for listOfCluster in listOfClusters:
                if not verifyCluster(listOfCluster):
                    current_app.logger.info("Cluster " + listOfCluster + " is not deployed and not running")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "Cluster " + listOfCluster + " is not deployed and not running",
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                mgmt = getManagementCluster()
                if mgmt is None:
                    current_app.logger.error("Failed to get management cluster")
                    d = {"responseType": "ERROR", "msg": "Failed to get management cluster", "STATUS_CODE": 500}
                    return jsonify(d), 500
                if str(mgmt).strip() == listOfCluster.strip():
                    current_app.logger.info("Currently " + monitoringType + " is not supported on management cluster")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Currently " + monitoringType + " is not supported on management cluster",
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                else:
                    switch = switchToContext(str(listOfCluster).strip(), env)
                    if switch[1] != 200:
                        current_app.logger.info(switch[0].json["msg"])
                        d = {"responseType": "ERROR", "msg": switch[0].json["msg"], "STATUS_CODE": 500}
                        return jsonify(d), 500
                load_bom = loadBomFile()
                if load_bom is None:
                    current_app.logger.error("Failed to load the bom data ")
                    d = {"responseType": "ERROR", "msg": "Failed to load the bom data", "STATUS_CODE": 500}
                    return jsonify(d), 500
                repo = getRepo(env)
                repository = repo[1]
                os.system("chmod +x ./common/injectValue.sh")
            cert_Path = ""
            if monitoringType == Tkg_Extention_names.PROMETHEUS:
                password = None
                extention = Tkg_Extention_names.PROMETHEUS
                # bom_map = getBomMap(load_bom, Tkg_Extention_names.PROMETHEUS)
                appName = AppName.PROMETHUS
                namespace = "tanzu-prometheus-monitoring"
                extra_ns = "tanzu-prometheus-monitoring"
                clusterPath = Paths.CLUSTER_PATH + cluster
                yamlFile = clusterPath + "/prometheus-data-values.yaml"
                service = "all"
                cert_ext_status = installCertManagerAndContour(env, str(listOfCluster).strip(), repo_address, service)
                if cert_ext_status[1] != 200:
                    current_app.logger.error(cert_ext_status[0].json["msg"])
                    d = {"responseType": "ERROR", "msg": cert_ext_status[0].json["msg"], "STATUS_CODE": 500}
                    return jsonify(d), 500
                cert_Path = request.get_json(force=True)["tanzuExtensions"]["monitoring"]["prometheusCertPath"]
                fqdn = request.get_json(force=True)["tanzuExtensions"]["monitoring"]["prometheusFqdn"]
                certKey_Path = request.get_json(force=True)["tanzuExtensions"]["monitoring"]["prometheusCertKeyPath"]
            elif monitoringType == Tkg_Extention_names.GRAFANA:
                password = request.get_json(force=True)["tanzuExtensions"]["monitoring"]["grafanaPasswordBase64"]
                extention = Tkg_Extention_names.GRAFANA
                clusterPath = Paths.CLUSTER_PATH + cluster
                yamlFile = clusterPath + "/grafana-data-values.yaml"
                appName = AppName.GRAFANA
                namespace = "tanzu-grafana-dashboards"
                extra_ns = "tanzu-grafana-dashboards"
                command = [
                    "./common/injectValue.sh",
                    Extentions.GRAFANA_LOCATION + "/grafana-extension.yaml",
                    "fluent_bit",
                    repository + "/" + Extentions.APP_EXTENTION,
                ]
                runShellCommandAndReturnOutputAsList(command)
                # bom_map = getBomMap(load_bom, Tkg_Extention_names.GRAFANA)
                cert_Path = request.get_json(force=True)["tanzuExtensions"]["monitoring"]["grafanaCertPath"]
                fqdn = request.get_json(force=True)["tanzuExtensions"]["monitoring"]["grafanaFqdn"]
                certKey_Path = request.get_json(force=True)["tanzuExtensions"]["monitoring"]["grafanaCertKeyPath"]

            extention_validate_command = ["kubectl", "get", "app", appName, "-n", namespace]

            command_fluent_bit = runShellCommandAndReturnOutputAsList(extention_validate_command)
            if not verifyPodsAreRunning(appName, command_fluent_bit[0], RegexPattern.RECONCILE_SUCCEEDED):
                version = getVersionOfPackage(extention.lower() + ".tanzu.vmware.com")
                current_app.logger.info(f"Deploying {extention} {version}")
                if version is None:
                    current_app.logger.error("Failed to capture the available Prometheus version")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to capture the available Prometheus version",
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                file_status = generateYamlFile(extention, version, certKey_Path, cert_Path, fqdn, password, yamlFile)
                if file_status[1] == 500:
                    current_app.logger.error(yamlFile + " generation failed " + str(file_status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "yamlFile generation failed " + str(file_status[0]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                # Changed for glasgow
                verify_ns = ["kubectl", "get", "ns"]
                out = runShellCommandAndReturnOutputAsList(verify_ns)
                for item in out[0]:
                    if namespace in item:
                        break
                else:
                    create_ns_cmd = ["kubectl", "create", "ns", namespace]
                    runProcess(create_ns_cmd)

                out = runShellCommandAndReturnOutputAsList(verify_ns)
                for item in out[0]:
                    if extra_ns in item:
                        break
                else:
                    create_ns_cmd = ["kubectl", "create", "ns", extra_ns]
                    runProcess(create_ns_cmd)

                deply_extension_command = [
                    "tanzu",
                    "package",
                    "install",
                    extention.lower(),
                    "--package",
                    extention.lower() + ".tanzu.vmware.com",
                    "--version",
                    version,
                    "--values-file",
                    yamlFile,
                    "--namespace",
                    extra_ns,
                ]
                state_extention_apply = runShellCommandAndReturnOutputAsList(deply_extension_command)
                if state_extention_apply[1] != 0:
                    current_app.logger.error(
                        extention + " install command failed. Checking for reconciliation status..."
                    )

                found = False
                count = 0
                command_ext_bit = runShellCommandAndReturnOutputAsList(extention_validate_command)
                if verifyPodsAreRunning(appName, command_ext_bit[0], RegexPattern.RECONCILE_SUCCEEDED):
                    found = True
                    current_app.logger.info(appName + " deployed successfully")

                while (
                    not verifyPodsAreRunning(appName, command_ext_bit[0], RegexPattern.RECONCILE_SUCCEEDED)
                    and count < 20
                ):
                    command_ext_bit = runShellCommandAndReturnOutputAsList(extention_validate_command)
                    if verifyPodsAreRunning(appName, command_ext_bit[0], RegexPattern.RECONCILE_SUCCEEDED):
                        found = True
                        break
                    count = count + 1
                    time.sleep(30)
                    current_app.logger.info("Waited for  " + str(count * 30) + "s, retrying.")
                if not found:
                    current_app.logger.error("Extension is still not deployed " + str(count * 30))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Extension is still not deployed " + str(count * 30),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                else:
                    current_app.logger.info(appName + " is deployed")
                    d = {"responseType": "SUCCESS", "msg": appName + " is deployed", "STATUS_CODE": 200}
                    return jsonify(d), 200
            else:
                current_app.logger.info(appName + " is already running")
                d = {"responseType": "SUCCESS", "msg": appName + " is already running", "STATUS_CODE": 200}
                return jsonify(d), 200
        else:
            current_app.logger.info("Monitoring extension deployment is not enabled")
            d = {"responseType": "SUCCESS", "msg": "Monitoring extension deployment is not enabled", "STATUS_CODE": 200}
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.info("Failed to deploy monitoring " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to deploy monitoring " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500


def deploy_extension_fluent(fluent_bit_endpoint):
    try:
        is_already_installed = checkFluentBitInstalled()
        if not is_already_installed[0]:
            env = envCheck()
            if env[1] != 200:
                current_app.logger.error("Wrong env provided " + env[0])
                d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
                return jsonify(d), 500
            env = env[0]
            cluster = str(request.get_json(force=True)["tanzuExtensions"]["tkgClustersName"])
            listOfClusters = cluster.split(",")
            for listOfCluster in listOfClusters:
                if not verifyCluster(listOfCluster):
                    current_app.logger.info("Cluster " + listOfCluster + " is not deployed and not running")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "Cluster " + listOfCluster + " is not deployed and not running",
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                mgmt = getManagementCluster()
                if mgmt is None:
                    current_app.logger.error("Failed to get management cluster")
                    d = {"responseType": "ERROR", "msg": "Failed to get management cluster", "STATUS_CODE": 500}
                    return jsonify(d), 500
                if str(mgmt).strip() == listOfCluster.strip():
                    current_app.logger.info(
                        "Currently fluent-bit " + fluent_bit_endpoint + "is not supported on " "management cluster"
                    )
                    d = {
                        "responseType": "ERROR",
                        "msg": "Currently fluent-bit "
                        + fluent_bit_endpoint
                        + " is not supported on management cluster",
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                else:
                    switch = switchToContext(str(listOfCluster).strip(), env)
                    if switch[1] != 200:
                        current_app.logger.info(switch[0].json["msg"])
                        d = {"responseType": "ERROR", "msg": switch[0].json["msg"], "STATUS_CODE": 500}
                        return jsonify(d), 500
                response = deploy_fluent_bit(fluent_bit_endpoint, cluster)
                if response[1] != 200:
                    current_app.logger.error(response[0].json["msg"])
                    d = {"responseType": "ERROR", "msg": response[0].json["msg"], "STATUS_CODE": 500}
                    return jsonify(d), 500
            current_app.logger.info("Fluent-bit with endpoint - " + fluent_bit_endpoint + " installed successfully")
            d = {"responseType": "SUCCESS", "msg": "Fluent-bit deployed successfully", "STATUS_CODE": 200}
            return jsonify(d), 200
        else:
            current_app.logger.info("Fluent-bit is already deployed and its status is - " + is_already_installed[1])
            d = {
                "responseType": "SUCCESS",
                "msg": "Fluent-bit is already deployed and its status is - " + is_already_installed[1],
                "STATUS_CODE": 200,
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Exception occurred while deploying Fluent-bit - " + str(e))
        d = {"responseType": "ERROR", "msg": "Exception occurred while deploying fluent-bit", "STATUS_CODE": 500}
        return jsonify(d), 500
