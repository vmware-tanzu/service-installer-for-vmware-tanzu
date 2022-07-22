from .extentions import extentions_types, deploy_extentions
from common.operation.constants import Tkg_Extention_names, Repo, RegexPattern, Extentions, Env, AppName
from common.common_utilities import switchToContext, loadBomFile, checkAirGappedIsEnabled, preChecks, envCheck, \
    waitForProcess, installCertManagerAndContour, deployExtention, getManagementCluster, verifyCluster, \
    switchToManagementContext
from common.operation.ShellHelper import runShellCommandAndReturnOutput, grabKubectlCommand, grabIpAddress, \
    verifyPodsAreRunning, grabPipeOutput, runShellCommandAndReturnOutputAsList, \
    runShellCommandAndReturnOutputAsListWithChangedDir, grabPipeOutputChagedDir
from flask import current_app, jsonify, request
from tqdm import tqdm
import time
import ruamel
import os
from pathlib import Path


class deploy_Dot3_ext(deploy_extentions):
    def deploy(self, extention_name):
        try:
            dot3 = extention_types_dot3_impl()
            if str(extention_name).__contains__("Fluent"):
                status = dot3.fluent_bit(extention_name)
                return status[0], status[1]
            elif str(extention_name) == Tkg_Extention_names.GRAFANA:
                status = dot3.grafana()
                return status[0], status[1]
            elif str(extention_name) == Tkg_Extention_names.LOGGING:
                status = dot3.logging()
                return status[0], status[1]
            elif str(extention_name) == Tkg_Extention_names.PROMETHEUS:
                status = dot3.prometheus()
                return status[0], status[1]
            else:
                current_app.logger.info("Un supported extention type " + extention_name)
                d = {
                    "responseType": "ERROR",
                    "msg": "Un supported extention type " + extention_name,
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        except Exception as e:
            current_app.logger.info("Failed to deploy extension " + extention_name + " " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy extension " + extention_name + " " + str(e),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500


class extention_types_dot3_impl(extentions_types):
    def fluent_bit(self, fluent_bit_type):
        fluent = deployFluentBit(fluent_bit_type)
        if fluent[1] != 200:
            current_app.logger.error(fluent[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": fluent[0].json['msg'],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Successfully deployed fluent bit " + fluent_bit_type)
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully deployed fluent bit " + fluent_bit_type,
            "ERROR_CODE": 200
        }
        return jsonify(d), 200

    def grafana(self):
        monitoring = monitoringDeployment(Tkg_Extention_names.GRAFANA)
        if monitoring[1] != 200:
            current_app.logger.error(monitoring[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": monitoring[0].json['msg'],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Successfully deployed Grafana")
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully deployed Grafana",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200

    def prometheus(self):
        monitoring = monitoringDeployment(Tkg_Extention_names.PROMETHEUS)
        if monitoring[1] != 200:
            current_app.logger.error(monitoring[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": monitoring[0].json['msg'],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Successfully deployed promethus")
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully deployed promethus",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200

    def logging(self):
        current_app.logger.info("Successfully deployed logging")
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully deployed logging",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200


def createFluentBitHttpFile(repoAddress, name_from_bom, tag_from_bom, management_cluster, cluster, http_end_point,
                            http_port, uri_, header, file_location):
    os.system("rm -rf " + file_location)
    data = dict(
        logging=dict(image=dict(repository=repoAddress, name=name_from_bom, tag=tag_from_bom)),
        tkg=dict(
            instance_name=management_cluster,
            cluster_name=cluster
        ),
        fluent_bit=dict(
            output_plugin='http',
            http=dict(
                host=http_end_point,
                port=http_port,
                uri=uri_,
                header_key_value=header,
                format='json'
            )
        )
    )
    with open(file_location, 'w') as outfile:
        outfile.write("#@data/values\n")
        outfile.write("#@overlay/match-child-defaults missing_ok=True\n")
        outfile.write("---\n")
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=3)
        yaml.dump(data, outfile)


def createFluentBitSyslogFile(repoAddress, name_from_bom, tag_from_bom, management_cluster, cluster, host_,
                              port_, mode_, format_, file_location):
    os.system("rm -rf " + file_location)
    data = dict(
        logging=dict(image=dict(repository=repoAddress, name=name_from_bom, tag=tag_from_bom)),
        tkg=dict(
            instance_name=management_cluster,
            cluster_name=cluster
        ),
        fluent_bit=dict(
            output_plugin='syslog',
            syslog=dict(
                host=host_,
                port=port_,
                mode=mode_,
                format=format_
            )
        )
    )
    with open(file_location, 'w') as outfile:
        outfile.write("#@data/values\n")
        outfile.write("#@overlay/match-child-defaults missing_ok=True\n")
        outfile.write("---\n")
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=3)
        yaml.dump(data, outfile)


def createFluentBitElasticFile(repoAddress, name_from_bom, tag_from_bom, management_cluster, cluster, host_,
                               port_, file_location):
    os.system("rm -rf " + file_location)
    data = dict(
        logging=dict(image=dict(repository=repoAddress, name=name_from_bom, tag=tag_from_bom)),
        tkg=dict(
            instance_name=management_cluster,
            cluster_name=cluster
        ),
        fluent_bit=dict(
            output_plugin='elasticsearch',
            elasticsearch=dict(
                host=host_,
                port=port_
            )
        )
    )
    with open(file_location, 'w') as outfile:
        outfile.write("#@data/values\n")
        outfile.write("#@overlay/match-child-defaults missing_ok=True\n")
        outfile.write("---\n")
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=3)
        yaml.dump(data, outfile)


def createFluentBitKafkaFile(repoAddress, name_from_bom, tag_from_bom, management_cluster, cluster,
                             broker_service_name_,
                             topic_name_, file_location):
    os.system("rm -rf " + file_location)
    data = dict(
        logging=dict(image=dict(repository=repoAddress, name=name_from_bom, tag=tag_from_bom)),
        tkg=dict(
            instance_name=management_cluster,
            cluster_name=cluster
        ),
        fluent_bit=dict(
            output_plugin='kafka',
            kafka=dict(
                broker_service_name=broker_service_name_,
                topic_name=topic_name_
            )
        )
    )
    with open(file_location, 'w') as outfile:
        outfile.write("#@data/values\n")
        outfile.write("#@overlay/match-child-defaults missing_ok=True\n")
        outfile.write("---\n")
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=3)
        yaml.dump(data, outfile)


def createFluentBitSplunkFile(repoAddress, name_from_bom, tag_from_bom, management_cluster, cluster,
                              host_,
                              port_, token_, file_location):
    os.system("rm -rf " + file_location)
    data = dict(
        logging=dict(image=dict(repository=repoAddress, name=name_from_bom, tag=tag_from_bom)),
        tkg=dict(
            instance_name=management_cluster,
            cluster_name=cluster
        ),
        fluent_bit=dict(
            output_plugin='splunk',
            splunk=dict(
                host=host_,
                port=port_,
                token=token_
            )
        )
    )
    with open(file_location, 'w') as outfile:
        outfile.write("#@data/values\n")
        outfile.write("#@overlay/match-child-defaults missing_ok=True\n")
        outfile.write("---\n")
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=3)
        yaml.dump(data, outfile)


def getRepo(env):
    try:
        if checkAirGappedIsEnabled(env):
            repo_address = str(request.get_json(force=True)['envSpec']['customRepositorySpec'][
                                   'tkgCustomImageRepository'])
        else:
            repo_address = Repo.PUBLIC_REPO
        if repo_address.endswith("/"):
            repo_address = repo_address.rstrip("/")
        repo_address = repo_address.replace("https://", "").replace("http://", "")
        return "SUCCESS", repo_address
    except Exception as e:
        return "ERROR", str(e)


def deployFluentBit(fluentBitType):
    pre = preChecks()
    if pre[1] != 200:
        current_app.logger.error(pre[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": pre[0].json['msg'],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Failed to env check")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to env check",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    cluster = str(
        request.get_json(force=True)['tanzuExtensions']['tkgClustersName'])
    listOfClusters = cluster.split(",")
    for listOfCluster in listOfClusters:
        if not verifyCluster(listOfCluster):
            current_app.logger.error("Cluster " + listOfCluster + " is not deployed and not running")
            d = {
                "responseType": "ERROR",
                "msg": "Cluster " + listOfCluster + " is not deployed and not running",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        mgmt = getManagementCluster()
        if mgmt is None:
            current_app.logger.error("Failed to get management cluster")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get management cluster",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if str(mgmt).strip() == listOfCluster.strip():
            current_app.logger.info("Currently "+fluentBitType+" is not supported on management cluster")
            d = {
                "responseType": "ERROR",
                "msg": "Currently "+fluentBitType+" is not supported on management cluster",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            switch = switchToContext(str(listOfCluster).strip(), env)
            if switch[1] != 200:
                current_app.logger.info(switch[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": switch[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        load_bom = loadBomFile()
        if load_bom is None:
            current_app.logger.error("Failed to load the bom data ")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to load the bom data",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        fluent_bit_validate_command = ["kubectl", "get", "app", AppName.FLUENT_BIT, "-n", "tanzu-system-logging"]
        command_fluent_bit = runShellCommandAndReturnOutputAsList(fluent_bit_validate_command)
        if not verifyPodsAreRunning(AppName.FLUENT_BIT, command_fluent_bit[0], RegexPattern.RECONCILE_SUCCEEDED):
            current_app.logger.info("Deploying fluent-bit " + fluentBitType)
            command = ["kubectl", "apply", "-f", "namespace-role.yaml"]
            state = runShellCommandAndReturnOutputAsListWithChangedDir(command,
                                                                       Extentions.FLUENT_BIT_LOCATION)
            if state[1] != 0:
                for i in tqdm(range(120), desc="Waiting for tanzu-system-logging name space available …",
                              ascii=False,
                              ncols=75):
                    time.sleep(1)
                state = runShellCommandAndReturnOutputAsListWithChangedDir(command,
                                                                           Extentions.FLUENT_BIT_LOCATION)
                if state[1] != 0:
                    current_app.logger.error("Failed to apply fluent-bit http " + str(state))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to apply fluent-bit http " + str(state),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500

            else:
                current_app.logger.info(state[0])

            repo = getRepo(env)
            management_cluster = getManagementCluster()
            if management_cluster is None:
                current_app.logger.error("Failed to get management cluster")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get management cluster",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            if repo[0] == "ERROR":
                current_app.logger.error("Failed to get repository from input file" + str(repo[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to repository from input file" + str(repo[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            repository = repo[1]
            select = fluentBitTypeSelector(fluentBitType, repository, load_bom, management_cluster, listOfCluster)
            if select[1] != 200:
                current_app.logger.error(select[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": select[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            command = ["./common/injectValue.sh", Extentions.FLUENT_BIT_LOCATION + "/fluent-bit-extension.yaml",
                       "fluent_bit", repository + "/" + Extentions.APP_EXTENTION]
            runShellCommandAndReturnOutputAsList(command)
            command_fluent_apply = ["kubectl", "apply", "-f", "fluent-bit-extension.yaml"]
            state_fluent_apply = runShellCommandAndReturnOutputAsListWithChangedDir(
                command_fluent_apply,
                Extentions.FLUENT_BIT_LOCATION)
            if state_fluent_apply[1] == 500:
                current_app.logger.error(
                    "Failed to apply " + str(state_fluent_apply[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply " + str(state_fluent_apply[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500

            listCommand = ["kubectl", "get", "app", AppName.FLUENT_BIT, "-n", "tanzu-system-logging"]
            st = waitForProcess(listCommand, AppName.FLUENT_BIT)
            if st[1] != 200:
                return st[0], st[1]
            else:
                current_app.logger.info(
                    "Fluent-bit " + fluentBitType + " deployed, and is up and running on cluster " + listOfCluster)
        else:
            current_app.logger.info(
                "Fluent-bit " + fluentBitType + "is already up and running on cluster " + listOfCluster)
    d = {
        "responseType": "SUCCESS",
        "msg": "Fluent-bit extentions deployed successfully",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def fluentBitTypeSelector(fluentBitType, repoAddress, bom, managementCluster, clusterName):
    try:
        fluent_bit_name = bom['components']['fluent-bit'][0]['images']['fluentBitImage']['imagePath']
        fluent_bit_tag = bom['components']['fluent-bit'][0]['images']['fluentBitImage']['tag']
        file_location = ""
        if fluentBitType == Tkg_Extention_names.FLUENT_BIT_HTTP:
            file_location = Extentions.FLUENT_BIT_LOCATION + "/http/fluent-bit-data-values.yaml"
            nameFromBom = fluent_bit_name
            tagFromBom = fluent_bit_tag
            httpEndPoint = str(request.get_json(force=True)['tanzuExtensions']['logging']['httpEndpoint'][
                                   'httpEndpointAddress'])
            httpPort = str(
                request.get_json(force=True)['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointPort'])
            uri = str(
                request.get_json(force=True)['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointUri'])
            header = str(request.get_json(force=True)['tanzuExtensions']['logging']['httpEndpoint'][
                             'httpEndpointHeaderKeyValue'])
            createFluentBitHttpFile(repoAddress, nameFromBom, tagFromBom, managementCluster, clusterName, httpEndPoint,
                                    httpPort, uri, header, file_location)
        elif fluentBitType == Tkg_Extention_names.FLUENT_BIT_KAFKA:
            file_location = Extentions.FLUENT_BIT_LOCATION + "/kafka/fluent-bit-data-values.yaml"
            nameFromBom = fluent_bit_name
            tagFromBom = fluent_bit_tag
            brokerServiceName = str(request.get_json(force=True)['tanzuExtensions']['logging']['kafkaEndpoint'][
                                        'kafkaBrokerServiceName'])
            topicName = str(
                request.get_json(force=True)['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaTopicName'])
            createFluentBitKafkaFile(repoAddress, nameFromBom, tagFromBom, managementCluster, clusterName,
                                     brokerServiceName, topicName, file_location)
        elif fluentBitType == Tkg_Extention_names.FLUENT_BIT_ELASTIC:
            file_location = Extentions.FLUENT_BIT_LOCATION + "/elasticsearch/fluent-bit-data-values.yaml"
            nameFromBom = fluent_bit_name
            tagFromBom = fluent_bit_tag
            host = str(request.get_json(force=True)['tanzuExtensions']['logging']['elasticSearchEndpoint'][
                           'elasticSearchEndpointAddress'])
            port = str(request.get_json(force=True)['tanzuExtensions']['logging']['elasticSearchEndpoint'][
                           'elasticSearchEndpointPort'])
            createFluentBitElasticFile(repoAddress, nameFromBom, tagFromBom, managementCluster, clusterName, host, port,
                                       file_location)
        elif fluentBitType == Tkg_Extention_names.FLUENT_BIT_SYSLOG:
            file_location = Extentions.FLUENT_BIT_LOCATION + "/syslog/fluent-bit-data-values.yaml"
            nameFromBom = fluent_bit_name
            tagFromBom = fluent_bit_tag
            host = str(request.get_json(force=True)['tanzuExtensions']['logging']['syslogEndpoint'][
                           'syslogEndpointAddress'])
            port = str(request.get_json(force=True)['tanzuExtensions']['logging']['syslogEndpoint'][
                           'syslogEndpointPort'])
            mode = str(request.get_json(force=True)['tanzuExtensions']['logging']['syslogEndpoint'][
                           'syslogEndpoint_mode'])
            format_ = str(request.get_json(force=True)['tanzuExtensions']['logging']['syslogEndpoint'][
                              'syslogEndpointFormat'])
            createFluentBitSyslogFile(repoAddress, nameFromBom, tagFromBom, managementCluster, clusterName, host, port,
                                      mode, format_, file_location)
        elif fluentBitType == Tkg_Extention_names.FLUENT_BIT_SPLUNK:
            file_location = Extentions.FLUENT_BIT_LOCATION + "/splunk/fluent-bit-data-values.yaml"
            nameFromBom = fluent_bit_name
            tagFromBom = fluent_bit_tag
            host = str(request.get_json(force=True)['tanzuExtensions']['logging']['splunkEndpoint'][
                           'splunkEndpointAddress'])
            port = str(request.get_json(force=True)['tanzuExtensions']['logging']['splunkEndpoint'][
                           'splunkEndpointPort'])
            token = str(request.get_json(force=True)['tanzuExtensions']['logging']['splunkEndpoint'][
                            'splunkEndpointToken'])
            createFluentBitSplunkFile(repoAddress, nameFromBom, tagFromBom, managementCluster, clusterName, host, port,
                                      token, file_location)
        secret = createSecret(file_location, "fluent-bit-data-values", "tanzu-system-logging")
        if secret[1] != 200:
            current_app.logger.error(secret[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": secret[0].json['msg'],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Created secrets  for " + fluentBitType,
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Fluent bit " + fluentBitType + " failed " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Fluent bit " + fluentBitType + " failed " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def createSecret(filePath, data, namespace):
    fluent_bit_secret_command = ["kubectl", "create", "secret", "generic", data,
                                 "--from-file=values.yaml=" + filePath, "-n", namespace]
    command_fluent_bit = runShellCommandAndReturnOutputAsList(fluent_bit_secret_command)
    if command_fluent_bit[1] != 0:
        current_app.logger.error("Failed to get repository from input file" + str(command_fluent_bit[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to repository from input file" + str(command_fluent_bit[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info("Successfully created secret " + filePath)
    d = {
        "responseType": "ERROR",
        "msg": "Successfully created secret " + filePath,
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def generateYamlWithoutCert(virtual_host, repo_address, bom_map, extentions_types, file_location, adminPassword):
    if extentions_types == Tkg_Extention_names.PROMETHEUS:
        repo_address = repo_address + "/prometheus"
        data = dict(
            monitoring=dict(ingress=dict(enabled='true', virtual_host_fqdn=virtual_host),
                            prometheus_server=dict(
                                image=dict(repository=repo_address, name=bom_map['prometheus_server_name'],
                                           tag=bom_map['prometheus_server_tag']))
                            , alertmanager=dict(image=dict(repository=repo_address, name=bom_map['alertmanager_name'],
                                                           tag=bom_map['alertmanager_tag'])),
                            kube_state_metrics=dict(
                                image=dict(repository=repo_address, name=bom_map['kube_state_metrics_name'],
                                           tag=bom_map['kube_state_metrics_tag'])),
                            node_exporter=dict(image=dict(repository=repo_address, name=bom_map['node_exporter_name'],
                                                          tag=bom_map['node_exporter_tag'])),
                            pushgateway=dict(image=dict(repository=repo_address, name=bom_map['pushgateway_name'],
                                                        tag=bom_map['pushgateway_tag'])),
                            cadvisor=dict(image=dict(repository=repo_address, name=bom_map['cadvisor_name'],
                                                     tag=bom_map['cadvisor_tag'])),
                            prometheus_server_configmap_reload=dict(
                                image=dict(repository=repo_address,
                                           name=bom_map['prometheus_server_configmap_reload_name'],
                                           tag=bom_map['prometheus_server_configmap_reload_tag'])),
                            prometheus_server_init_container=dict(image=dict(repository=repo_address))))
    if extentions_types == Tkg_Extention_names.GRAFANA:
        repo_address = repo_address + "/grafana"
        data = dict(
            monitoring=dict(grafana=dict(ingress=dict(enabled='true', virtual_host_fqdn=virtual_host),
                                         image=dict(repository=repo_address, name=bom_map['image_name'],
                                                    tag=bom_map['image_tag']),
                                         secret=dict(admin_password=adminPassword))
                            , grafana_init_container=dict(
                    image=dict(repository=repo_address, name=bom_map['grafana_init_container_name'],
                               tag=bom_map['grafana_init_container_tag'])),
                            grafana_sc_dashboard=dict(
                                image=dict(repository=repo_address, name=bom_map['grafana_sc_dashboard_name'],
                                           tag=bom_map['grafana_sc_dashboard_tag']))))

    with open(file_location, 'w') as outfile:
        outfile.write("#@data/values\n")
        outfile.write("#@overlay/match-child-defaults missing_ok=True\n")
        outfile.write("---\n")
        yaml1 = ruamel.yaml.YAML()
        yaml1.indent(mapping=2, sequence=4, offset=3)
        yaml1.dump(data, outfile)


def getImageName(server_image):
    return server_image[server_image.rindex("/") + 1:len(server_image)]


def monitoringDeployment(monitoringType):
    try:
        enable = request.get_json(force=True)['tanzuExtensions']['monitoring']['enableLoggingExtension']
        if enable == "true":
            pre = preChecks()
            if pre[1] != 200:
                current_app.logger.error(pre[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": pre[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
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
            if checkAirGappedIsEnabled(env):
                repo_address = str(
                    request.get_json(force=True)['envSpec']['customRepositorySpec'][
                        'tkgCustomImageRepository'])
            else:
                repo_address = Repo.PUBLIC_REPO
            cluster = str(
                request.get_json(force=True)['tanzuExtensions']['tkgClustersName'])
            listOfClusters = cluster.split(",")
            for listOfCluster in listOfClusters:
                if not verifyCluster(listOfCluster):
                    current_app.logger.info("Cluster " + listOfCluster + " is not deployed and not running")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "Cluster " + listOfCluster + " is not deployed and not running",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                mgmt = getManagementCluster()
                if mgmt is None:
                    current_app.logger.error("Failed to get management cluster")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get management cluster",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                if str(mgmt).strip() == listOfCluster.strip():
                    current_app.logger.info("Currently "+monitoringType+" is not supported on management cluster")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Currently "+monitoringType+" is not supported on management cluster",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                else:
                    switch = switchToContext(str(listOfCluster).strip(), env)
                    if switch[1] != 200:
                        current_app.logger.info(switch[0].json['msg'])
                        d = {
                            "responseType": "ERROR",
                            "msg": switch[0].json['msg'],
                            "ERROR_CODE": 500
                        }
                        return jsonify(d), 500
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
                if monitoringType == Tkg_Extention_names.PROMETHEUS:
                    password = None
                    extention = Tkg_Extention_names.PROMETHEUS
                    extention_yaml = "prometheus-extension.yaml"
                    secret_name = "prometheus-data-values"
                    command = ["./common/injectValue.sh",Extentions.PROMETHUS_LOCATION + "/prometheus-extension.yaml","fluent_bit", repository
                               + "/" + Extentions.APP_EXTENTION]
                    runShellCommandAndReturnOutputAsList(command)
                    app_location = Extentions.PROMETHUS_LOCATION
                    file_location = Extentions.PROMETHUS_LOCATION + "/prometheus-data-values.yaml"
                    bom_map = getBomMap(load_bom, Tkg_Extention_names.PROMETHEUS)
                    appName = AppName.PROMETHUS
                    service = "all"
                    cert_ext_status = installCertManagerAndContour(env,str(listOfCluster).strip(), repo_address, service)
                    if cert_ext_status[1] != 200:
                        current_app.logger.error(cert_ext_status[0].json['msg'])
                        d = {
                            "responseType": "ERROR",
                            "msg": cert_ext_status[0].json['msg'],
                            "ERROR_CODE": 500
                        }
                        return jsonify(d), 500
                    cert_Path = request.get_json(force=True)['tanzuExtensions']['monitoring'][
                        'prometheusCertPath']
                    fqdn = request.get_json(force=True)['tanzuExtensions']['monitoring'][
                        'prometheusFqdn']
                    certKey_Path = request.get_json(force=True)['tanzuExtensions']['monitoring'][
                        'prometheusCertKeyPath']
                elif monitoringType == Tkg_Extention_names.GRAFANA:
                    password = request.get_json(force=True)['tanzuExtensions']['monitoring']['grafanaPasswordBase64']
                    extention = Tkg_Extention_names.GRAFANA
                    secret_name = "grafana-data-values"
                    extention_yaml = "grafana-extension.yaml"
                    app_location = Extentions.GRAFANA_LOCATION
                    file_location = Extentions.GRAFANA_LOCATION + "/grafana-data-values.yaml"
                    appName = AppName.GRAFANA
                    command = ["./common/injectValue.sh",Extentions.GRAFANA_LOCATION + "/grafana-extension.yaml","fluent_bit",repository + "/" + Extentions.APP_EXTENTION]
                    runShellCommandAndReturnOutputAsList(command)
                    bom_map = getBomMap(load_bom, Tkg_Extention_names.GRAFANA)
                    cert_Path = request.get_json(force=True)['tanzuExtensions']['monitoring']['grafanaCertPath']
                    fqdn = request.get_json(force=True)['tanzuExtensions']['monitoring']['grafanaFqdn']
                    certKey_Path = request.get_json(force=True)['tanzuExtensions']['monitoring'][
                        'grafanaCertKeyPath']
                fluent_bit_validate_command = ["kubectl", "get", "app", appName, "-n",
                                               "tanzu-system-monitoring"]

                command_fluent_bit = runShellCommandAndReturnOutputAsList(fluent_bit_validate_command)
                if not verifyPodsAreRunning(appName, command_fluent_bit[0],
                                            RegexPattern.RECONCILE_SUCCEEDED):
                    generateYamlWithoutCert(fqdn, repository, bom_map,extention,file_location, password)
                    if cert_Path and certKey_Path:
                        promethus_cert = Path(cert_Path).read_text()
                        promethus_cert_key = Path(certKey_Path).read_text()
                        if monitoringType == Tkg_Extention_names.PROMETHEUS:
                            inject_commad = "inject_cert_promethus"
                        elif monitoringType == Tkg_Extention_names.GRAFANA:
                            inject_commad = "inject_cert_grafana"
                        command_harbor_change_host_password_cert = ["sh", "./common/injectValue.sh",
                                                                    file_location ,
                                                                    inject_commad, promethus_cert, promethus_cert_key]
                        state_harbor_change_host_password_cert = runShellCommandAndReturnOutput(command_harbor_change_host_password_cert)
                        if state_harbor_change_host_password_cert[1] == 500:
                            current_app.logger.error(
                                "Failed to change  cert " + str(state_harbor_change_host_password_cert[0]))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Failed to change cert " + str(state_harbor_change_host_password_cert[0]),
                                "ERROR_CODE": 500
                            }
                            return jsonify(d), 500
                    current_app.logger.info("Deploying " + extention)
                    command = ["kubectl", "apply", "-f", "namespace-role.yaml"]
                    state = runShellCommandAndReturnOutputAsListWithChangedDir(command,
                                                                               app_location)
                    if state[1] != 0:
                        for i in tqdm(range(120), desc="Waiting for tanzu-system-monitoring name space available …",
                                      ascii=False, ncols=75):
                            time.sleep(1)
                        state = runShellCommandAndReturnOutputAsListWithChangedDir(command,
                                                                                   app_location)
                        if state[1] != 0:
                            current_app.logger.error("Failed to apply  " + appName + " " + str(state))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Failed to apply " + appName + " " + str(state),
                                "ERROR_CODE": 500
                            }
                            return jsonify(d), 500

                    else:
                        current_app.logger.info(state[0])
                    secret = createSecret(file_location, secret_name, "tanzu-system-monitoring")
                    if secret[1] != 200:
                        current_app.logger.error(secret[0].json['msg'])
                        d = {
                            "responseType": "ERROR",
                            "msg": secret[0].json['msg'],
                            "ERROR_CODE": 500
                        }
                        return jsonify(d), 500
                    state_harbor_apply = deployExtention(extention_yaml, appName,
                                                         "tanzu-system-monitoring",
                                                         app_location)
                    if state_harbor_apply[1] == 500:
                        current_app.logger.error(str(state_harbor_apply[0].json['msg']))
                        d = {
                            "responseType": "ERROR",
                            "msg": str(state_harbor_apply[0].json['msg']),
                            "ERROR_CODE": 500
                        }
                        return jsonify(d), 500
                    current_app.logger.info("Successfully deployed " + appName + " on cluster " + listOfCluster)
                else:
                    current_app.logger.info(appName + " is already running on cluster " + listOfCluster)
            current_app.logger.info("Successfully deployed " + appName + " on all  clusters " + str(listOfClusters))
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully deployed " + appName + " on all  clusters " + str(listOfClusters),
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
        else:
            current_app.logger.info("Monitoring extention deployment is not enabled")
            d = {
                "responseType": "SUCCESS",
                "msg": "Monitoring extention deployment is not enabled",
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
