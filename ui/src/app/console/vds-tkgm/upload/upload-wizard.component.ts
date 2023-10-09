/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { Component, OnInit, ViewChild } from '@angular/core';
import { Router } from '@angular/router';

// Third party imports
import { Subscription } from 'rxjs';

// App imports
import { DataService } from 'src/app/shared/service/data.service';
import { VMCDataService } from 'src/app/shared/service/vmc-data.service';
import { VsphereTkgsService } from 'src/app/shared/service/vsphere-tkgs-data.service';
import { VCDDataService } from 'src/app/shared/service/vcd-data.service';
import { FormMetaDataStore } from 'src/app/views/landing/wizard/shared/FormMetaDataStore';
import { PROVIDERS, Providers } from 'src/app/shared/constants/app.constants';
import { APP_ROUTES, Routes } from 'src/app/shared/constants/routes.constants';
import { AppDataService } from 'src/app/shared/service/app-data.service';
import { BrandingObj } from 'src/app/shared/service/branding.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { id } from '@cds/core/internal';

@Component({
    selector: 'app-upload',
    templateUrl: './upload-wizard.component.html',
    styleUrls: ['./upload-wizard.component.scss'],
})
export class UploadWizardComponent implements OnInit {

    @ViewChild('attachments') public attachment: any;
    public APP_ROUTES: Routes = APP_ROUTES;
    public PROVIDERS: Providers = PROVIDERS;

    public displayWizard = false;
    public fileName: string;
    public fileUploaded = false;
    public file: File;
    public inputFile;

    public clusterType: string;
    public provider: string;
    public infraType: string;
    public landingPageContent: BrandingObj;
    public loading = false;

    public readFile = false;
    errorNotification = '';
    public noupload = true;
    showLoginLoader = false;

    tkgsStage: string;
    tkgsStageType = ['Enable Workload control plane', 'Namespace and Workload cluster']
    public subscription: Subscription;
    constructor(
        public apiClient: APIClient, private router: Router,
        private appDataService: AppDataService,
        private dataService: DataService,
        private vmcDataService: VMCDataService,
        private vsphereTkgsDataService: VsphereTkgsService,
        private vcdDataService: VCDDataService,

    ) {
        this.appDataService.getProviderType().asObservable().subscribe((data) => this.provider = data);
        this.appDataService.getInfraType().asObservable().subscribe((data) => this.infraType = data);
    }

    public ngOnInit() {
    }

    /**
     * @method navigate
     * @desc helper method to trigger router navigation to specified route
     * @param route - the route to navigate to
     */
    public navigate(route: string): void {
        this.apiClient.redirectedToHome = true;
        this.router.navigate([route]);
    }

    public readInputJsonFile() {
        if (this.fileName !== '' && this.fileUploaded) {
            const reader = new FileReader();
            reader.readAsText(this.file, 'UTF-8');
            // tslint:disable-next-line:only-arrow-functions
            reader.onload = async function(evt) {
                if (typeof evt.target.result === 'string') {
                    const readInput = await (JSON.parse(evt.target.result));
                    await console.log(' ');
                    return readInput;
                }
            };
            // tslint:disable-ne xt-line:only-arrow-functions
            reader.onerror = function(evt) {
                console.log('Error Reading Input File');
            };
        } else {
        }
        // Give an Error here
        return;
    }

    public processTkgsProxyParam(input) {
        const http_proxy = input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['httpProxy'];
        const https_proxy = input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['httpsProxy'];
        if (http_proxy === https_proxy) {
            const stripUser = http_proxy.substr(7);
            if (stripUser.includes('@')) {
                const username = stripUser.substring(0, stripUser.indexOf(':'));
                const password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                const url = 'http://' + stripUser.substr(stripUser.indexOf('@') + 1);
                this.vsphereTkgsDataService.changeTkgsHttpProxyUrl(url);
                this.vsphereTkgsDataService.changeTkgsHttpsProxyUrl(url);
                this.vsphereTkgsDataService.changeTkgsHttpProxyUsername(username);
                this.vsphereTkgsDataService.changeTkgsHttpsProxyUsername(username);
                this.vsphereTkgsDataService.changeTkgsHttpProxyPassword(password);
                this.vsphereTkgsDataService.changeTkgsHttpsProxyPassword(password);
            } else {
                this.vsphereTkgsDataService.changeTkgsHttpProxyUrl(http_proxy);
                this.vsphereTkgsDataService.changeTkgsHttpProxyUrl(https_proxy);
            }
            this.vsphereTkgsDataService.changeTkgsIsSameAsHttp(true);
        } else {
            const httpStripUser = http_proxy.substr(7);
            this.vsphereTkgsDataService.changeTkgsIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                const username = httpStripUser.substring(0, httpStripUser.indexOf(':'));
                this.vsphereTkgsDataService.changeTkgsHttpProxyUsername(username);
                const password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@'));
                this.vsphereTkgsDataService.changeTkgsHttpProxyPassword(password);
                const url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substr(httpStripUser.indexOf('@') + 1);
                this.vsphereTkgsDataService.changeTkgsHttpProxyUrl(url);
            } else {
                this.vsphereTkgsDataService.changeTkgsHttpProxyUrl(http_proxy);
            }
            const httpsStripUser = https_proxy.substr(8);
            if (httpsStripUser.includes('@')) {
                const username = httpsStripUser.substring(0, httpsStripUser.indexOf(':'));
                this.vsphereTkgsDataService.changeTkgsHttpsProxyUsername(username);
                const password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@'));
                this.vsphereTkgsDataService.changeTkgsHttpsProxyPassword(password);
                const url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substr(httpsStripUser.indexOf('@') + 1);
                this.vsphereTkgsDataService.changeTkgsHttpsProxyUrl(url);
            } else {
                this.vsphereTkgsDataService.changeTkgsHttpsProxyUrl(https_proxy);
            }
        }
    }

    public processArcasProxyParam(input) {
        const http_proxy = input['envSpec']['proxySpec']['arcasVm']['httpProxy'];
        const https_proxy = input['envSpec']['proxySpec']['arcasVm']['httpsProxy'];
        if (http_proxy === https_proxy) {
            const stripUser = http_proxy.substr(7);
            if (stripUser.includes('@')) {
                const username = stripUser.substring(0, stripUser.indexOf(':'));
                const password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                const url = 'http://' + stripUser.substr(stripUser.indexOf('@') + 1);
                this.dataService.changeArcasHttpProxyUrl(url);
                this.dataService.changeArcasHttpsProxyUrl(url);
                this.dataService.changeArcasHttpProxyUsername(username);
                this.dataService.changeArcasHttpsProxyUsername(username);
                this.dataService.changeArcasHttpProxyPassword(password);
                this.dataService.changeArcasHttpsProxyPassword(password);
            } else {
                this.dataService.changeArcasHttpProxyUrl(http_proxy);
                this.dataService.changeArcasHttpsProxyUrl(https_proxy);
            }
            this.dataService.changeArcasIsSameAsHttp(true);
        } else {
            const httpStripUser = http_proxy.substr(7);
            this.dataService.changeArcasIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                const username = httpStripUser.substring(0, httpStripUser.indexOf(':'));
                this.dataService.changeArcasHttpProxyUsername(username);
                const password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@'));
                this.dataService.changeArcasHttpProxyPassword(password);
                const url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substr(httpStripUser.indexOf('@') + 1);
                this.dataService.changeArcasHttpProxyUrl(url);
            } else {
                this.dataService.changeArcasHttpProxyUrl(http_proxy);
            }
            const httpsStripUser = https_proxy.substr(8);
            if (httpsStripUser.includes('@')) {
                const username = httpsStripUser.substring(0, httpsStripUser.indexOf(':'));
                this.dataService.changeArcasHttpsProxyUsername(username);
                const password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@'));
                this.dataService.changeArcasHttpsProxyPassword(password);
                const url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substr(httpsStripUser.indexOf('@') + 1);
                this.dataService.changeArcasHttpsProxyUrl(url);
            } else {
                this.dataService.changeArcasHttpsProxyUrl(https_proxy);
            }
        }
    }

    processMgmtProxyParam(input) {
        const http_proxy = input['envSpec']['proxySpec']['tkgMgmt']['httpProxy'];
        const https_proxy = input['envSpec']['proxySpec']['tkgMgmt']['httpsProxy'];
        if (http_proxy === https_proxy) {
            const stripUser = http_proxy.substr(7);
            if (stripUser.includes('@')) {
                const username = stripUser.substring(0, stripUser.indexOf(':'));
                const password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                const url = 'http://' + stripUser.substr(stripUser.indexOf('@') + 1);
                this.dataService.changeMgmtHttpProxyUrl(url);
                this.dataService.changeMgmtHttpsProxyUrl(url);
                this.dataService.changeMgmtHttpProxyUsername(username);
                this.dataService.changeMgmtHttpsProxyUsername(username);
                this.dataService.changeMgmtHttpProxyPassword(password);
                this.dataService.changeMgmtHttpsProxyPassword(password);
            } else {
                this.dataService.changeMgmtHttpProxyUrl(http_proxy);
                this.dataService.changeMgmtHttpsProxyUrl(https_proxy);
            }
            this.dataService.changeMgmtIsSameAsHttp(true);
        } else {
            const httpStripUser = http_proxy.substr(7);
            this.dataService.changeMgmtIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                const username = httpStripUser.substring(0, httpStripUser.indexOf(':') );
                this.dataService.changeMgmtHttpProxyUsername(username);
                const password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@') );
                this.dataService.changeMgmtHttpProxyPassword(password);
                const url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substr(httpStripUser.indexOf('@') + 1);
                this.dataService.changeMgmtHttpProxyUrl(url);
            } else {
                this.dataService.changeMgmtHttpProxyUrl(http_proxy);
            }
            const httpsStripUser = https_proxy.substr(8);
            if (httpsStripUser.includes('@')) {
                const username = httpsStripUser.substring(0, httpsStripUser.indexOf(':') );
                this.dataService.changeMgmtHttpsProxyUsername(username);
                const password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@') );
                this.dataService.changeMgmtHttpsProxyPassword(password);
                const url = https_proxy.substring(0, https_proxy.indexOf(':')) +
                    '://' + httpsStripUser.substr(httpsStripUser.indexOf('@') + 1);
                this.dataService.changeMgmtHttpsProxyUrl(url);
            } else {
                this.dataService.changeMgmtHttpsProxyUrl(https_proxy);
            }
        }
    }

    public processSharedProxyParam(input) {
        const http_proxy = input['envSpec']['proxySpec']['tkgSharedservice']['httpProxy'];
        const https_proxy = input['envSpec']['proxySpec']['tkgSharedservice']['httpsProxy'];
        if (http_proxy === https_proxy) {
            const stripUser = http_proxy.substring(7);
            if (stripUser.includes('@')) {
                const username = stripUser.substring(0, stripUser.indexOf(':'));
                const password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                const url = 'http://' + stripUser.substring(stripUser.indexOf('@') + 1);
                this.dataService.changeSharedHttpProxyUrl(url);
                this.dataService.changeSharedHttpsProxyUrl(url);
                this.dataService.changeSharedHttpProxyUsername(username);
                this.dataService.changeSharedHttpsProxyUsername(username);
                this.dataService.changeSharedHttpProxyPassword(password);
                this.dataService.changeSharedHttpsProxyPassword(password);
            } else {
                this.dataService.changeSharedHttpProxyUrl(http_proxy);
                this.dataService.changeSharedHttpsProxyUrl(https_proxy);
            }
            this.dataService.changeSharedIsSameAsHttp(true);
        } else {
            const httpStripUser = http_proxy.substring(7);
            this.dataService.changeSharedIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                const username = httpStripUser.substring(0, httpStripUser.indexOf(':') );
                this.dataService.changeSharedHttpProxyUsername(username);
                const password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@') );
                this.dataService.changeSharedHttpProxyPassword(password);
                const url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substring(httpStripUser.indexOf('@') + 1);
                this.dataService.changeSharedHttpProxyUrl(url);
            } else {
                this.dataService.changeSharedHttpProxyUrl(http_proxy);
            }
            const httpsStripUser = https_proxy.substring(8);
            if (httpsStripUser.includes('@')) {
                const username = httpsStripUser.substring(0, httpsStripUser.indexOf(':') );
                this.dataService.changeSharedHttpsProxyUsername(username);
                const password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@') );
                this.dataService.changeSharedHttpsProxyPassword(password);
                // tslint:disable-next-line:max-line-length
                const url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substring(httpsStripUser.indexOf('@') + 1);
                this.dataService.changeSharedHttpsProxyUrl(url);
            } else {
                this.dataService.changeSharedHttpsProxyUrl(https_proxy);
            }
        }
    }

    public processWrkProxyParam(input) {
        const http_proxy = input['envSpec']['proxySpec']['tkgWorkload']['httpProxy'];
        const https_proxy = input['envSpec']['proxySpec']['tkgWorkload']['httpsProxy'];
        if (http_proxy === https_proxy) {
            const stripUser = http_proxy.substring(7);
            if (stripUser.includes('@')) {
                const username = stripUser.substring(0, stripUser.indexOf(':'));
                const password = stripUser.substring(stripUser.indexOf(':') + 1, stripUser.indexOf('@'));
                const url = 'http://' + stripUser.substring(stripUser.indexOf('@') + 1);
                this.dataService.changeWrkHttpProxyUrl(url);
                this.dataService.changeWrkHttpsProxyUrl(url);
                this.dataService.changeWrkHttpProxyUsername(username);
                this.dataService.changeWrkHttpsProxyUsername(username);
                this.dataService.changeWrkHttpProxyPassword(password);
                this.dataService.changeWrkHttpsProxyPassword(password);
            } else {
                this.dataService.changeWrkHttpProxyUrl(http_proxy);
                this.dataService.changeWrkHttpsProxyUrl(https_proxy);
            }
            this.dataService.changeWrkIsSameAsHttp(true);
        } else {
            const httpStripUser = http_proxy.substring(7);
            this.dataService.changeWrkIsSameAsHttp(false);
            if (httpStripUser.includes('@')) {
                const username = httpStripUser.substring(0, httpStripUser.indexOf(':') );
                this.dataService.changeWrkHttpProxyUsername(username);
                const password = httpStripUser.substring(httpStripUser.indexOf(':') + 1, httpStripUser.indexOf('@') );
                this.dataService.changeWrkHttpProxyPassword(password);
                const url = http_proxy.substring(0, http_proxy.indexOf(':')) + '://' + httpStripUser.substring(httpStripUser.indexOf('@') + 1);
                this.dataService.changeWrkHttpProxyUrl(url);
            } else {
                this.dataService.changeWrkHttpProxyUrl(http_proxy);
            }
            const httpsStripUser = https_proxy.substring(8);
            if (httpsStripUser.includes('@')) {
                const username = httpsStripUser.substring(0, httpsStripUser.indexOf(':') );
                this.dataService.changeWrkHttpsProxyUsername(username);
                const password = httpsStripUser.substring(httpsStripUser.indexOf(':') + 1, httpsStripUser.indexOf('@') );
                this.dataService.changeWrkHttpsProxyPassword(password);
                // tslint:disable-next-line:max-line-length
                const url = https_proxy.substring(0, https_proxy.indexOf(':')) + '://' + httpsStripUser.substring(httpsStripUser.indexOf('@') + 1);
                this.dataService.changeWrkHttpsProxyUrl(url);
            } else {
                this.dataService.changeWrkHttpsProxyUrl(https_proxy);
            }
        }
    }

    public processEnableMonitoring(input, dataServiceObj) {
        if (input['tanzuExtensions'].hasOwnProperty('monitoring')) {
            if (input['tanzuExtensions']['monitoring'].hasOwnProperty('enableLoggingExtension')) {
                if (input['tanzuExtensions']['monitoring']['enableLoggingExtension'] === 'true') {
                    dataServiceObj.changeEnableMonitoringExtension(true);
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('prometheusFqdn')) {
                        dataServiceObj.changePrometheusFqdn(input['tanzuExtensions']['monitoring']['prometheusFqdn']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('prometheusCertPath')) {
                        dataServiceObj.changePrometheusCertPath(input['tanzuExtensions']['monitoring']['prometheusCertPath']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('prometheusCertKeyPath')) {
                        dataServiceObj.changePrometheusCertkeyPath(input['tanzuExtensions']['monitoring']['prometheusCertKeyPath']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaFqdn')) {
                        dataServiceObj.changeGrafanaFqdn(input['tanzuExtensions']['monitoring']['grafanaFqdn']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaPasswordBase64')) {
                        dataServiceObj.changeGrafanaPassword(atob(input['tanzuExtensions']['monitoring']['grafanaPasswordBase64']));
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaCertPath')) {
                        dataServiceObj.changeGrafanaCertPath(input['tanzuExtensions']['monitoring']['grafanaCertPath']);
                    }
                    if (input['tanzuExtensions']['monitoring'].hasOwnProperty('grafanaCertKeyPath')) {
                        dataServiceObj.changeGrafanaCertKeyPath(input['tanzuExtensions']['monitoring']['grafanaCertKeyPath']);
                    }
                } else {
                    dataServiceObj.changeEnableMonitoringExtension(false);
                }
            }
        }

    }

    public processEnableLogging(input, dataServiceObj) {
        if (input['tanzuExtensions'].hasOwnProperty('logging')) {
            if (input['tanzuExtensions']['logging'].hasOwnProperty('syslogEndpoint') &&
                input['tanzuExtensions']['logging'].hasOwnProperty('httpEndpoint') &&
                input['tanzuExtensions']['logging'].hasOwnProperty('kafkaEndpoint')) {
                if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('enableSyslogEndpoint') &&
                    input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('enableHttpEndpoint') &&
                    input['tanzuExtensions']['logging']['kafkaEndpoint'].hasOwnProperty('enableKafkaEndpoint')) {
                    if (input['tanzuExtensions']['logging']['syslogEndpoint']['enableSyslogEndpoint'] === 'true') {
                        dataServiceObj.changeEnableLoggingExtension(true);
                        dataServiceObj.changeLoggingEndpoint('Syslog');
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointAddress')) {
                            dataServiceObj.changeSyslogAddress(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointAddress']);
                        }
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointPort')) {
                            dataServiceObj.changeSyslogPort(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointPort']);
                        }
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointMode')) {
                            dataServiceObj.changeSyslogMode(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointMode']);
                        }
                        if (input['tanzuExtensions']['logging']['syslogEndpoint'].hasOwnProperty('syslogEndpointFormat')) {
                            dataServiceObj.changeSyslogFormat(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointFormat']);
                        }
                    } else if (input['tanzuExtensions']['logging']['httpEndpoint']['enableHttpEndpoint'] === 'true') {
                        dataServiceObj.changeEnableLoggingExtension(true);
                        dataServiceObj.changeLoggingEndpoint('HTTP');
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointAddress')) {
                            dataServiceObj.changeHttpAddress(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointAddress']);
                        }
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointPort')) {
                            dataServiceObj.changeHttpPort(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointPort']);
                        }
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointUri')) {
                            dataServiceObj.changeHttpUri(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointUri']);
                        }
                        if (input['tanzuExtensions']['logging']['httpEndpoint'].hasOwnProperty('httpEndpointHeaderKeyValue')) {
                            dataServiceObj.changeHttpHeaderKey(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointHeaderKeyValue']);
                        }
                    } else if (input['tanzuExtensions']['logging']['kafkaEndpoint']['enableKafkaEndpoint'] === 'true') {
                        dataServiceObj.changeEnableLoggingExtension(true);
                        dataServiceObj.changeLoggingEndpoint('Kafka');
                        if (input['tanzuExtensions']['logging']['kafkaEndpoint'].hasOwnProperty('kafkaBrokerServiceName')) {
                            dataServiceObj.changeKafkaServiceName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaBrokerServiceName']);
                        }
                        if (input['tanzuExtensions']['logging']['kafkaEndpoint'].hasOwnProperty('kafkaTopicName')) {
                            dataServiceObj.changeKafkaTopicName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaTopicName']);
                        }
                    } else {
                        dataServiceObj.changeEnableLoggingExtension(false);
                    }
                }
            }
        }
    }

    public processVmcEnableMonitoring(input) {
        if (input['tanzuExtensions']['monitoring']['enableLoggingExtension'] === 'true') {
            this.vmcDataService.changeEnableMonitoringExtension(true);
            this.vmcDataService.changePrometheusFqdn(input['tanzuExtensions']['monitoring']['prometheusFqdn']);
            this.vmcDataService.changePrometheusCertPath(input['tanzuExtensions']['monitoring']['prometheusCertPath']);
            this.vmcDataService.changePrometheusCertkeyPath(input['tanzuExtensions']['monitoring']['prometheusCertKeyPath']);
            this.vmcDataService.changeGrafanaFqdn(input['tanzuExtensions']['monitoring']['grafanaFqdn']);
            this.vmcDataService.changeGrafanaPassword(atob(input['tanzuExtensions']['monitoring']['grafanaPasswordBase64']));
            this.vmcDataService.changeGrafanaCertPath(input['tanzuExtensions']['monitoring']['grafanaCertPath']);
            this.vmcDataService.changeGrafanaCertKeyPath(input['tanzuExtensions']['monitoring']['grafanaCertKeyPath']);
        } else {
            this.vmcDataService.changeEnableMonitoringExtension(false);
        }
    }

    public processVmcEnableLogging(input) {
        if (input['tanzuExtensions']['logging']['syslogEndpoint']['enableSyslogEndpoint'] === 'true') {
            this.vmcDataService.changeEnableLoggingExtension(true);
            this.vmcDataService.changeLoggingEndpoint('Syslog');
            this.vmcDataService.changeSyslogAddress(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointAddress']);
            this.vmcDataService.changeSyslogPort(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointPort']);
            this.vmcDataService.changeSyslogMode(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointMode']);
            this.vmcDataService.changeSyslogFormat(input['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointFormat']);
        } else if (input['tanzuExtensions']['logging']['httpEndpoint']['enableHttpEndpoint'] === 'true') {
            this.vmcDataService.changeEnableLoggingExtension(true);
            this.vmcDataService.changeLoggingEndpoint('HTTP');
            this.vmcDataService.changeHttpAddress(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointAddress']);
            this.vmcDataService.changeHttpPort(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointPort']);
            this.vmcDataService.changeHttpUri(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointUri']);
            this.vmcDataService.changeHttpHeaderKey(input['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointHeaderKeyValue']);
        } else if (input['tanzuExtensions']['logging']['elasticSearchEndpoint']['enableElasticSearchEndpoint'] === 'true') {
            this.vmcDataService.changeEnableLoggingExtension(true);
            this.vmcDataService.changeLoggingEndpoint('Elastic Search');
            this.vmcDataService.changeElasticSearchAddress(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['elasticSearchEndpointAddress']);
            this.vmcDataService.changeElasticSearchPort(input['tanzuExtensions']['logging']['elasticSearchEndpoint']['elasticSearchEndpointPort']);
        } else if (input['tanzuExtensions']['logging']['kafkaEndpoint']['enableKafkaEndpoint'] === 'true') {
            this.vmcDataService.changeEnableLoggingExtension(true);
            this.vmcDataService.changeLoggingEndpoint('Kafka');
            this.vmcDataService.changeKafkaServiceName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaBrokerServiceName']);
            this.vmcDataService.changeKafkaTopicName(input['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaTopicName']);
        } else if (input['tanzuExtensions']['logging']['splunkEndpoint']['enableSplunkEndpoint'] === 'true') {
            this.vmcDataService.changeEnableLoggingExtension(true);
            this.vmcDataService.changeLoggingEndpoint('Splunk');
            this.vmcDataService.changeSplunkAddress(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointAddress']);
            this.vmcDataService.changeSplunkPort(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointPort']);
            this.vmcDataService.changeSplunkToken(input['tanzuExtensions']['logging']['splunkEndpoint']['splunkEndpointToken']);
        }
    }

    public setVmcParamsFromInputJSON(input) {
        if (input) {
            this.vmcDataService.changeInputFileStatus(true);
            // Dumy Component
            const dns = input['envVariablesSpec']['dnsServersIp'];
            const ntp = input['envVariablesSpec']['ntpServersIp'];
            this.vmcDataService.changeDnsServer(dns);
            this.vmcDataService.changeNtpServer(ntp);
            // Iaas Provider
            this.vmcDataService.changeSddcToken(input['envSpec']['sddcRefreshToken']);
            this.vmcDataService.changeOrgName(input['envSpec']['orgName']);
            this.vmcDataService.changeSddcName(input['envSpec']['sddcName']);
            this.vmcDataService.changeDatacenter(input['envSpec']['sddcDatacenter']);
            this.vmcDataService.changeCluster(input['envSpec']['sddcCluster']);
            this.vmcDataService.changeDatastore(input['envSpec']['sddcDatastore']);
            // Tanzu SaaS Endpoints
            if (input['saasEndpoints']['tmcDetails']['tmcAvailability'] === 'true') {
                this.vmcDataService.changeEnableTMC(true);
                this.vmcDataService.changeApiToken(input['saasEndpoints']['tmcDetails']['tmcRefreshToken']);
            } else {
                this.vmcDataService.changeEnableTMC(false);
            }
            if (input['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityAvailability'] === 'true') {
                this.vmcDataService.changeEnableTO(true);
                this.vmcDataService.changeTOUrl(input['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityUrl']);
                this.vmcDataService.changeTOApiToken(input['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityRefreshToken']);
            } else {
                this.vmcDataService.changeEnableTO(false);
            }
            // AVI Component
            this.vmcDataService.changeAviPassword(atob(input['componentSpec']['aviComponentSpec']['aviPasswordBase64']));
            this.vmcDataService.changeAviBackupPassword(atob(input['componentSpec']['aviComponentSpec']['aviBackupPassPhraseBase64']));
            this.vmcDataService.changeAviGateway(input['componentSpec']['aviMgmtNetworkSpec']['aviMgmtGatewayCidr']);
            this.vmcDataService.changeAviDhcpStart(input['componentSpec']['aviMgmtNetworkSpec']['aviMgmtDhcpStartRange']);
            this.vmcDataService.changeAviDhcpEnd(input['componentSpec']['aviMgmtNetworkSpec']['aviMgmtDhcpEndRange']);
            this.vmcDataService.changeAviClusterVipNetworkName(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipNetworkName']);
            this.vmcDataService.changeAviClusterVipGatewayIp(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipNetworkGatewayCidr']);
            this.vmcDataService.changeAviClusterVipStartIp(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipDhcpStartRange']);
            this.vmcDataService.changeAviClusterVipEndIp(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipDhcpEndRange']);
            this.vmcDataService.changeAviClusterVipSeStartIp(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipIpStartRange']);
            this.vmcDataService.changeAviClusterVipSeEndIp(input['componentSpec']['aviClusterVipNetwork']['aviClusterVipIpEndRange']);
            // TKG Mgmt Data Network
            this.vmcDataService.changeTkgMgmtDataGateway(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataGatewayCidr']);
            this.vmcDataService.changeTkgMgmtDataDhcpStart(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataDhcpStartRange']);
            this.vmcDataService.changeTkgMgmtDataDhcpEnd(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataDhcpEndRange']);
            this.vmcDataService.changeTkgMgmtDataServiceStart(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataServiceStartRange']);
            this.vmcDataService.changeTkgMgmtDataServiceEnd(input['componentSpec']['tkgMgmtDataNetworkSpec']['tkgMgmtDataServiceEndRange']);
            // TKG Mgmt Cluster Settings
            this.vmcDataService.changeMgmtClusterName(input['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterName']);
            this.vmcDataService.changeMgmtDeploymentType(input['componentSpec']['tkgMgmtSpec']['tkgMgmtDeploymentType']);
            this.vmcDataService.changeMgmtDeploymentSize(input['componentSpec']['tkgMgmtSpec']['tkgMgmtSize']);
            this.vmcDataService.changeMgmtSegment(input['componentSpec']['tkgMgmtSpec']['tkgMgmtNetworkName']);
            this.vmcDataService.changeMgmtGateway(input['componentSpec']['tkgMgmtSpec']['tkgMgmtGatewayCidr']);
            // Shared Service Cluster Settings
            this.vmcDataService.changeSharedDeploymentType(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceDeploymentType']);
            this.vmcDataService.changeSharedDeploymentSize(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceSize']);
            this.vmcDataService.changeSharedClusterName(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedClusterName']);
            this.vmcDataService.changeSharedWorkerNodeCount(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceWorkerMachineCount']);
            this.vmcDataService.changeSharedGateway(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedGatewayCidr']);
            this.vmcDataService.changeSharedDhcpStart(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedDhcpStartRange']);
            this.vmcDataService.changeSharedDhcpEnd(input['componentSpec']['tkgSharedServiceSpec']['tkgSharedDhcpEndRange']);
            this.vmcDataService.changeEnableHarbor(true);
            this.vmcDataService.changeHarborFqdn(input['componentSpec']['harborSpec']['harborFqdn']);
            this.vmcDataService.changeHarborPassword(atob(input['componentSpec']['harborSpec']['harborPasswordBase64']));
            this.vmcDataService.changeHarborCertPath(input['componentSpec']['harborSpec']['harborCertPath']);
            this.vmcDataService.changeHarborCertKey(input['componentSpec']['harborSpec']['harborCertKeyPath']);
            // TKG Workload Data Network Settings
            this.vmcDataService.changeTkgWrkDataGateway(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataGatewayCidr']);
            this.vmcDataService.changeTkgWrkDataDhcpStart(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataDhcpStartRange']);
            this.vmcDataService.changeTkgWrkDataDhcpEnd(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataDhcpEndRange']);
            this.vmcDataService.changeTkgWrkDataServiceStart(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataServiceStartRange']);
            this.vmcDataService.changeTkgWrkDataServiceEnd(input['componentSpec']['tkgWorkloadDataNetworkSpec']['tkgWorkloadDataServiceEndRange']);
            // Workload Cluster Settings
            this.vmcDataService.changeWrkDeploymentType(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDeploymentType']);
            this.vmcDataService.changeWrkDeploymentSize(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadSize']);
            this.vmcDataService.changeWrkWorkerNodeCount(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadWorkerMachineCount']);
            this.vmcDataService.changeWrkClusterName(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterName']);
            this.vmcDataService.changeWrkGateway(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadGatewayCidr']);
            this.vmcDataService.changeWrkDhcpStart(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDhcpStartRange']);
            this.vmcDataService.changeWrkDhcpEnd(input['componentSpec']['tkgWorkloadSpec']['tkgWorkloadDhcpEndRange']);
            // Extension
            if (input['tanzuExtensions']['tanzuExtensions'] === 'true') {
                this.vmcDataService.changeEnableTanzuExtension(true);
            } else {
                this.vmcDataService.changeEnableTanzuExtension(false);
            }
            if (input['tanzuExtensions']['enableExtensions'] === 'true') {
                this.vmcDataService.changeTkgClusters(input['tanzuExtensions']['tkgClustersName']);
                this.processVmcEnableLogging(input);
                this.processVmcEnableMonitoring(input);
            } else {
                this.vmcDataService.changeEnableLoggingExtension(false);
                this.vmcDataService.changeEnableMonitoringExtension(false);
            }
            this.errorNotification = '';
        } else {
            this.errorNotification = 'Error Occurred while reading ' + this.fileName + ' file';
        }
    }

    public setParamsFromInputJSONForVCD(input) {
        if(input) {
            this.vcdDataService.changeInputFileStatus(true);
            if(input.hasOwnProperty('envSpec')) {

                if (input['envSpec'].hasOwnProperty('marketplaceSpec')) {
                    if (input['envSpec']['marketplaceSpec'].hasOwnProperty('refreshToken')) {
                        if (input['envSpec']['marketplaceSpec']['refreshToken'] !== '') {
                            this.vcdDataService.changeIsMarketplace(true);
                        } else this.vcdDataService.changeIsMarketplace(false);
                        this.vcdDataService.changeMarketplaceRefreshToken(input['envSpec']['marketplaceSpec']['refreshToken']);
                    } else this.vcdDataService.changeIsMarketplace(false);
                } else this.vcdDataService.changeIsMarketplace(false);

                if(input['envSpec'].hasOwnProperty('infraComponents')) {
                    if (input['envSpec']['infraComponents'].hasOwnProperty('dnsServersIp')) {
                        this.vcdDataService.changeDnsServer(input['envSpec']['infraComponents']['dnsServersIp']);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('searchDomains')) {
                        this.vcdDataService.changeSearchDomain(input['envSpec']['infraComponents']['searchDomains']);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('ntpServers')) {
                        this.vcdDataService.changeNtpServer(input['envSpec']['infraComponents']['ntpServers']);
                    }
                }

                if(input['envSpec'].hasOwnProperty('ceipParticipation')) {
                    if(input['envSpec']['ceipParticipation'] === 'true') {
                        this.vcdDataService.changeCeipParticipation(true);
                    }
                    else this.vcdDataService.changeCeipParticipation(false);
                } else this.vcdDataService.changeCeipParticipation(false);

                if(input['envSpec'].hasOwnProperty('vcdSpec')) {
                    if(input['envSpec']['vcdSpec'].hasOwnProperty('vcdComponentSpec')) {
                        if(input['envSpec']['vcdSpec']['vcdComponentSpec'].hasOwnProperty('vcdAddress')) {
                            this.vcdDataService.changeVcdAddress(input['envSpec']['vcdSpec']['vcdComponentSpec']['vcdAddress']);
                        }
                        if(input['envSpec']['vcdSpec']['vcdComponentSpec'].hasOwnProperty('vcdSysAdminUserName')) {
                            this.vcdDataService.changeVcdUsername(input['envSpec']['vcdSpec']['vcdComponentSpec']['vcdSysAdminUserName']);
                        }
                        if(input['envSpec']['vcdSpec']['vcdComponentSpec'].hasOwnProperty('vcdSysAdminPassword')) {
                            this.vcdDataService.changeVcdPassword(atob(input['envSpec']['vcdSpec']['vcdComponentSpec']['vcdSysAdminPassword']));
                        }
                    }
                }
                if(input['envSpec'].hasOwnProperty('aviCtrlDeploySpec')) {
                    if(input['envSpec']['aviCtrlDeploySpec'].hasOwnProperty('deployAvi')) {
                        if(input['envSpec']['aviCtrlDeploySpec']['deployAvi'] === 'true') {
                            this.vcdDataService.aviGreenfield = true;
                            this.vcdDataService.configureAviNsxtCloud = true;
                            this.vcdDataService.createSeGroup = true;
                            this.vcdDataService.changeDeployAvi(true);
                        } else {
                            this.vcdDataService.aviGreenfield = false;
                            this.vcdDataService.changeDeployAvi(false);
                        }
                    }
                    if(input['envSpec']['aviCtrlDeploySpec'].hasOwnProperty('vcenterDetails')) {
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterAddress')) {
                            this.vcdDataService.changeVCAddress(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterAddress']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterSsoUser')) {
                            this.vcdDataService.changeVCUser(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterSsoUser']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterSsoPasswordBase64')) {
                            this.vcdDataService.changeVCPass(atob(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterSsoPasswordBase64']));
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterDatacenter')) {
                            this.vcdDataService.changeDatacenter(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterDatacenter']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterCluster')) {
                            this.vcdDataService.changeCluster(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterCluster']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('vcenterDatastore')) {
                            this.vcdDataService.changeDatastore(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterDatastore']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('resourcePoolName')) {
                            this.vcdDataService.changeResourcePool(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['resourcePoolName']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('contentLibraryName')) {
                            this.vcdDataService.changeContentLib(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['contentLibraryName']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails'].hasOwnProperty('aviOvaName')) {
                            this.vcdDataService.changeOvaImage(input['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['aviOvaName']);
                        }
                    }
                    if(input['envSpec']['aviCtrlDeploySpec'].hasOwnProperty('aviMgmtNetwork')) {
                        if(input['envSpec']['aviCtrlDeploySpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkName')) {
                            this.vcdDataService.changeAviMgmtNetworkName(input['envSpec']['aviCtrlDeploySpec']['aviMgmtNetwork']['aviMgmtNetworkName']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkGatewayCidr')) {
                            this.vcdDataService.changeAviMgmtNetworkGatewayCidr(input['envSpec']['aviCtrlDeploySpec']['aviMgmtNetwork']['aviMgmtNetworkGatewayCidr']);
                        }
                    }
                    if(input['envSpec']['aviCtrlDeploySpec'].hasOwnProperty('aviComponentsSpec')) {
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviUsername')) {
                            this.vcdDataService.changeAviUsername(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviUsername']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviPasswordBase64')) {
                            this.vcdDataService.changeAviPasswordBase64(atob(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviPasswordBase64']));
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviBackupPassphraseBase64')) {
                            this.vcdDataService.changeAviBackupPasswordBase64(atob(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviBackupPassphraseBase64']));
                        }

                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('enableAviHa')) {
                            if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['enableAviHa'] === 'true') {
                                this.vcdDataService.changeEnableAviHa(true);
                            } else this.vcdDataService.changeEnableAviHa(false);
                        } else this.vcdDataService.changeEnableAviHa(false);

                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController01Ip')) {
                            this.vcdDataService.changeAviController01Ip(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Ip']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController01Fqdn')) {
                            this.vcdDataService.changeAviController01Fqdn(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Fqdn']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController02Ip')) {
                            this.vcdDataService.changeAviController02Ip(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController02Ip']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController02Fqdn')) {
                            this.vcdDataService.changeAviController02Fqdn(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController02Fqdn']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController03Ip')) {
                            this.vcdDataService.changeAviController03Ip(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController03Ip']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviController03Fqdn')) {
                            this.vcdDataService.changeAviController03Fqdn(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController03Fqdn']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviClusterIp')) {
                            this.vcdDataService.changeAviClusterIp(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterIp']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviClusterFqdn')) {
                            this.vcdDataService.changeAviClusterFqdn(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterFqdn']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviSize')) {
                            this.vcdDataService.changeAviSize(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviSize']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviCertPath')) {
                            this.vcdDataService.changeAviCertPath(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviCertPath']);
                        }
                        if(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec'].hasOwnProperty('aviCertKeyPath')) {
                            this.vcdDataService.changeAviCertKeyPath(input['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviCertKeyPath']);
                        }
                    }
                    if(input['envSpec']['aviCtrlDeploySpec'].hasOwnProperty('aviVcdDisplayName')) {
                        this.vcdDataService.changeAviVcdDisplayName(input['envSpec']['aviCtrlDeploySpec']['aviVcdDisplayName']);
                    }
                }
                if(input['envSpec'].hasOwnProperty('aviNsxCloudSpec')) {
                    if (input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('configureAviNsxtCloud')) {
                        if(input['envSpec']['aviNsxCloudSpec']['configureAviNsxtCloud'] === 'true'){
                            this.vcdDataService.configureAviNsxtCloud = true;
                            this.vcdDataService.createSeGroup = true;
                            this.vcdDataService.changeConfigureNsxtCloud(true);
                        } else {
                            this.vcdDataService.changeConfigureNsxtCloud(false);
                            this.vcdDataService.configureAviNsxtCloud = false;
                        }
                    } else{
                        this.vcdDataService.changeConfigureNsxtCloud(false);
                        this.vcdDataService.configureAviNsxtCloud = false;
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('nsxDetails')) {
                        if(input['envSpec']['aviNsxCloudSpec']['nsxDetails'].hasOwnProperty('nsxtAddress')) {
                            this.vcdDataService.changeNsxtAddress(input['envSpec']['aviNsxCloudSpec']['nsxDetails']['nsxtAddress']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['nsxDetails'].hasOwnProperty('nsxtUser')) {
                            this.vcdDataService.changeNsxtUser(input['envSpec']['aviNsxCloudSpec']['nsxDetails']['nsxtUser']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['nsxDetails'].hasOwnProperty('nsxtUserPasswordBase64')) {
                            this.vcdDataService.changeNsxtUserPasswordBase64(atob(input['envSpec']['aviNsxCloudSpec']['nsxDetails']['nsxtUserPasswordBase64']));
                        }
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('aviNsxCloudName')) {
                        this.vcdDataService.changeAviNsxCloudName(input['envSpec']['aviNsxCloudSpec']['aviNsxCloudName']);
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('nsxtCloudVcdDisplayName')) {
                        this.vcdDataService.changeNsxtCloudVcdDisplayName(input['envSpec']['aviNsxCloudSpec']['nsxtCloudVcdDisplayName']);
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('vcenterDetails')) {
                        if(input['envSpec']['aviNsxCloudSpec']['vcenterDetails'].hasOwnProperty('vcenterAddress')) {
                            this.vcdDataService.changeVcenterAddressCloud(input['envSpec']['aviNsxCloudSpec']['vcenterDetails']['vcenterAddress']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoUser')) {
                            this.vcdDataService.changeVcenterSsoUserCloud(input['envSpec']['aviNsxCloudSpec']['vcenterDetails']['vcenterSsoUser']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoPasswordBase64')) {
                            this.vcdDataService.changeVcenterSsoPasswordBase64Cloud(atob(input['envSpec']['aviNsxCloudSpec']['vcenterDetails']['vcenterSsoPasswordBase64']));
                        }
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('aviSeTier1Details')) {
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeTier1Details'].hasOwnProperty('nsxtTier1SeMgmtNetworkName')){
                            this.vcdDataService.changeNsxtTier1SeMgmtNetworkName(input['envSpec']['aviNsxCloudSpec']['aviSeTier1Details']['nsxtTier1SeMgmtNetworkName']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeTier1Details'].hasOwnProperty('nsxtOverlay')){
                            this.vcdDataService.changeNsxtOverlay(input['envSpec']['aviNsxCloudSpec']['aviSeTier1Details']['nsxtOverlay']);
                        }
                    }

                    if(input['envSpec']['aviNsxCloudSpec'].hasOwnProperty('aviSeMgmtNetwork')) {
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork'].hasOwnProperty('aviSeMgmtNetworkName')) {
                            this.vcdDataService.changeAviSeMgmtNetworkName(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkName']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork'].hasOwnProperty('aviSeMgmtNetworkGatewayCidr')) {
                            this.vcdDataService.changeAviSeMgmtNetworkGatewayCidr(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkGatewayCidr']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork'].hasOwnProperty('aviSeMgmtNetworkDhcpStartRange')) {
                            this.vcdDataService.changeAviSeMgmtNetworkDhcpStartRange(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkDhcpStartRange']);
                        }
                        if(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork'].hasOwnProperty('aviSeMgmtNetworkDhcpEndRange')) {
                            this.vcdDataService.changeAviSeMgmtNetworkDhcpEndRange(input['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkDhcpEndRange']);
                        }
                    }
                }

                if(input['envSpec'].hasOwnProperty('cseSpec')) {
                    if(input['envSpec']['cseSpec'].hasOwnProperty('svcOrgSpec')) {
                        if(input['envSpec']['cseSpec']['svcOrgSpec'].hasOwnProperty('svcOrgName')) {
                            this.vcdDataService.changeSvcOrgName(input['envSpec']['cseSpec']['svcOrgSpec']['svcOrgName']);
                        }
                        if(input['envSpec']['cseSpec']['svcOrgSpec'].hasOwnProperty('svcOrgFullName')) {
                            this.vcdDataService.changeSvcOrgFullName(input['envSpec']['cseSpec']['svcOrgSpec']['svcOrgFullName']);
                        }
                    }
                    if(input['envSpec']['cseSpec'].hasOwnProperty('svcOrgVdcSpec')) {
                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('svcOrgVdcName')) {
                            this.vcdDataService.changeSvcOrgVdcName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcName']);
                        }
                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('svcOrgVdcResourceSpec')) {
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('providerVDC')) {
                                this.vcdDataService.changeProviderVDC(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['providerVDC']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('cpuAllocation')) {
                                this.vcdDataService.changeCpuAllocation(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['cpuAllocation']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('cpuGuaranteed')) {
                                this.vcdDataService.changeCpuGuaranteed(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['cpuGuaranteed']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('memoryAllocation')) {
                                this.vcdDataService.changeMemoryAllocation(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['memoryAllocation']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('memoryGuaranteed')) {
                                this.vcdDataService.changeMemoryGuaranteed(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['memoryGuaranteed']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('vcpuSpeed')) {
                                this.vcdDataService.changeVcpuSpeed(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['vcpuSpeed']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('isElastic')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['isElastic'] === true) {
                                    this.vcdDataService.changeIsElastic(true);
                                }
                                else this.vcdDataService.changeIsElastic(false);
                            } else this.vcdDataService.changeIsElastic(false);

                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('includeMemoryOverhead')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['includeMemoryOverhead'] === 'true') {
                                    this.vcdDataService.changeIncludeMemoryOverhead(true);
                                } else this.vcdDataService.changeIncludeMemoryOverhead(false);
                            } else this.vcdDataService.changeIncludeMemoryOverhead(false);

                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('vmQuota')) {
                                this.vcdDataService.changeVmQuota(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['vmQuota']);
                            }
                            //STORAGE POLICY
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('storagePolicySpec')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['storagePolicySpec'].hasOwnProperty('storagePolicies')) {
                                    const storagePolicy: Map<string, string> = new Map<string, string>();
                                    let policyName;
                                    let policyLimit;
                                    let inputVal = input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['storagePolicySpec']['storagePolicies'];
                                    for(const spec in inputVal) {
                                        if(inputVal[spec].hasOwnProperty('storagePolicy') && inputVal[spec].hasOwnProperty('storageLimit')) {
                                            policyName = inputVal[spec]['storagePolicy'];
                                            policyLimit = inputVal[spec]['storageLimit'];
                                            storagePolicy.set(policyName, policyLimit);
                                        } else if (inputVal[spec].hasOwnProperty('storagePolicy')) {
                                            policyName = inputVal[spec]['storagePolicy'];
                                            storagePolicy.set(policyName, "");
                                        }
                                    }
                                    this.vcdDataService.changeStorageSpec(storagePolicy);
                                }

                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['storagePolicySpec'].hasOwnProperty('defaultStoragePolicy')) {
                                    this.vcdDataService.changeDefaultStoragePolicy(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['storagePolicySpec']['defaultStoragePolicy']);
                                }
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('thinProvisioning')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['thinProvisioning'] === 'true') {
                                    this.vcdDataService.changeThinProvisioning(true);
                                } else this.vcdDataService.changeThinProvisioning(false);
                            } else this.vcdDataService.changeThinProvisioning(false);
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('fastProvisioning')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['fastProvisioning'] === 'true') {
                                    this.vcdDataService.changeFastProvisioning(true);
                                } else this.vcdDataService.changeFastProvisioning(false);
                            } else this.vcdDataService.changeFastProvisioning(false);
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('networkPoolName')) {
                                this.vcdDataService.changeNetworkPoolName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['networkPoolName']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec'].hasOwnProperty('networkQuota')) {
                                this.vcdDataService.changeNetworkQuota(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcResourceSpec']['networkQuota']);
                            }
                        }

                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('serviceEngineGroup')) {
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup'].hasOwnProperty('createSeGroup')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['createSeGroup'] === 'true' || this.vcdDataService.aviGreenfield || this.vcdDataService.configureAviNsxtCloud) {
                                    this.vcdDataService.changeImportSEG(true);
                                    this.vcdDataService.createSeGroup = true;
                                } else{
                                    this.vcdDataService.createSeGroup = false;
                                    this.vcdDataService.changeImportSEG(false);
                                }
                            } else {
                                this.vcdDataService.changeImportSEG(false);
                                this.vcdDataService.createSeGroup = false;
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup'].hasOwnProperty('serviceEngineGroupName')) {
                                this.vcdDataService.changeServiceEngineGroupname(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['serviceEngineGroupName']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup'].hasOwnProperty('serviceEngineGroupVcdDisplayName')) {
                                this.vcdDataService.changeServiceEngineGroupVcdDisplayName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['serviceEngineGroupVcdDisplayName']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup'].hasOwnProperty('reservationType')) {
                                this.vcdDataService.changeReservationType(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['reservationType']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup'].hasOwnProperty('vcenterPlacementDetails')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails'].hasOwnProperty('vcenterDatacenter')) {
                                    this.vcdDataService.changeVcenterDatacenterCloud(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails']['vcenterDatacenter']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails'].hasOwnProperty('vcenterCluster')) {
                                    this.vcdDataService.changeVcenterClusterCloud(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails']['vcenterCluster']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails'].hasOwnProperty('vcenterDatastore')) {
                                    this.vcdDataService.changeVcenterDatastoreCloud(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails']['vcenterDatastore']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails'].hasOwnProperty('vcenterContentSeLibrary')) {
                                    this.vcdDataService.changeVcenterContentSeLibrary(input['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['vcenterPlacementDetails']['vcenterContentSeLibrary']);
                                }
                            }
                        }

                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('svcOrgVdcGatewaySpec')) {
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec'].hasOwnProperty('tier0GatewaySpec')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('importTier0')) {
                                    if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['importTier0'] === 'true') {
                                        this.vcdDataService.changeImportTier0(true);
                                        this.vcdDataService.importTier0Nsxt = true;
                                    } else {
                                        this.vcdDataService.changeImportTier0(false);
                                        this.vcdDataService.importTier0Nsxt = false;
                                    }
                                } else {
                                    this.vcdDataService.changeImportTier0(false);
                                    this.vcdDataService.importTier0Nsxt = false;
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('tier0Router')) {
                                    this.vcdDataService.changeTier0Router(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['tier0Router']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('tier0GatewayName')) {
                                    this.vcdDataService.changeTier0GatewayName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['tier0GatewayName']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('extNetGatewayCIDR')) {
                                    this.vcdDataService.changeExtNetgatewayCIDR(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['extNetGatewayCIDR']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('extNetStartIP')) {
                                    this.vcdDataService.changeExtNetStartIP(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['extNetStartIP']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec'].hasOwnProperty('extNetEndIP')) {
                                    this.vcdDataService.changeExtNetEndIP(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier0GatewaySpec']['extNetEndIP']);
                                }
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec'].hasOwnProperty('tier1GatewaySpec')) {
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec'].hasOwnProperty('tier1GatewayName')) {
                                    this.vcdDataService.changeTier1Gatewayname(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec']['tier1GatewayName']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec'].hasOwnProperty('isDedicated')) {
                                    if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec']['isDedicated'] === 'true') {
                                        this.vcdDataService.changeIsDedicated(true);
                                    } else this.vcdDataService.changeIsDedicated(false);
                                } else this.vcdDataService.changeIsDedicated(false);
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec'].hasOwnProperty('primaryIp')) {
                                    this.vcdDataService.changePrimaryIp(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec']['primaryIp']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec'].hasOwnProperty('ipAllocationStartIP')) {
                                    this.vcdDataService.changeIpAllocationStartIP(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec']['ipAllocationStartIP']);
                                }
                                if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec'].hasOwnProperty('ipAllocationEndIP')) {
                                    this.vcdDataService.changeIpAllocationEndIP(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcGatewaySpec']['tier1GatewaySpec']['ipAllocationEndIP']);
                                }
                            }
                        }
                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('svcOrgVdcNetworkSpec')) {
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('networkName')) {
                                this.vcdDataService.changeNetworkName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['networkName']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('gatewayCIDR')) {
                                this.vcdDataService.changeGatewayCIDR(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['gatewayCIDR']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('staticIpPoolStartAddress')) {
                                this.vcdDataService.changeStaticIpPoolstartAddress(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['staticIpPoolStartAddress']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('staticIpPoolEndAddress')) {
                                this.vcdDataService.changeStaticIpPoolendAddress(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['staticIpPoolEndAddress']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('primaryDNS')) {
                                this.vcdDataService.changePrimaryDNS(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['primaryDNS']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('secondaryDNS')) {
                                this.vcdDataService.changeSecondaryDNS(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['secondaryDNS']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec'].hasOwnProperty('dnsSuffix')) {
                                this.vcdDataService.changeDnsSuffix(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgVdcNetworkSpec']['dnsSuffix']);
                            }
                        }
                        if(input['envSpec']['cseSpec']['svcOrgVdcSpec'].hasOwnProperty('svcOrgCatalogSpec')) {
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgCatalogSpec'].hasOwnProperty('cseOvaCatalogName')) {
                                this.vcdDataService.changeCseOvaCatalogName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgCatalogSpec']['cseOvaCatalogName']);
                            }
                            if(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgCatalogSpec'].hasOwnProperty('k8sTemplatCatalogName')) {
                                this.vcdDataService.changeK8sTemplatCatalogName(input['envSpec']['cseSpec']['svcOrgVdcSpec']['svcOrgCatalogSpec']['k8sTemplatCatalogName']);
                            }
                        }
                    }
                    if(input['envSpec']['cseSpec'].hasOwnProperty('cseServerDeploySpec')){
                        if(input['envSpec']['cseSpec']['cseServerDeploySpec'].hasOwnProperty('vAppName')){
                            this.vcdDataService.changeVappName(input['envSpec']['cseSpec']['cseServerDeploySpec']['vAppName']);
                        }
                        if(input['envSpec']['cseSpec']['cseServerDeploySpec'].hasOwnProperty('customCseProperties')){
                            if(input['envSpec']['cseSpec']['cseServerDeploySpec']['customCseProperties'].hasOwnProperty('cseSvcAccountName')) {
                                this.vcdDataService.changeCseSvcAccountName(input['envSpec']['cseSpec']['cseServerDeploySpec']['customCseProperties']['cseSvcAccountName']);
                            }
                            if(input['envSpec']['cseSpec']['cseServerDeploySpec']['customCseProperties'].hasOwnProperty('cseSvcAccountPasswordBase64')) {
                                this.vcdDataService.changeCseSvcAccountPasswordBase64(atob(input['envSpec']['cseSpec']['cseServerDeploySpec']['customCseProperties']['cseSvcAccountPasswordBase64']));
                            }
                        }
                    }
                }
            }
        }
    }

    public setParamsFromInputJSON(input) {
        if (input) {
            this.dataService.changeInputFileStatus(true);
            let missingKeys;
            // Dumy Component
            if (input.hasOwnProperty('envSpec')) {
                if (input['envSpec'].hasOwnProperty('infraComponents')) {
                    if (input['envSpec']['infraComponents'].hasOwnProperty('dnsServersIp')) {
                        const dns = input['envSpec']['infraComponents']['dnsServersIp'];
                        this.dataService.changeDnsServer(dns);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('ntpServers')) {
                        const ntp = input['envSpec']['infraComponents']['ntpServers'];
                        this.dataService.changeNtpServer(ntp);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('searchDomains')) {
                        const searchDomain = input['envSpec']['infraComponents']['searchDomains'];
                        this.dataService.changeSearchDomain(searchDomain);
                    }
                }
                if (input['envSpec'].hasOwnProperty('proxySpec')) {
                    if (input['envSpec']['proxySpec'].hasOwnProperty('arcasVm')) {
                        if (input['envSpec']['proxySpec']['arcasVm'].hasOwnProperty('enableProxy')) {
                            if (input['envSpec']['proxySpec']['arcasVm']['enableProxy'] === 'true') {
                                this.dataService.changeArcasEnableProxy(true);
                                if (input['envSpec']['proxySpec']['arcasVm'].hasOwnProperty('httpProxy') &&
                                    input['envSpec']['proxySpec']['arcasVm'].hasOwnProperty('httpsProxy')) {
                                        this.processArcasProxyParam(input);
                                    }
                                if (input['envSpec']['proxySpec']['arcasVm'].hasOwnProperty('noProxy')) {
                                    this.dataService.changeArcasNoProxy(
                                        input['envSpec']['proxySpec']['arcasVm']['noProxy']);
                                }
                                if(input['envSpec']['proxySpec']['arcasVm'].hasOwnProperty('proxyCert')) {
                                    this.dataService.changeArcasProxyCert(
                                        input['envSpec']['proxySpec']['arcasVm']['proxyCert']);
                                }
                            } else {
                                this.dataService.changeArcasEnableProxy(false);
                            }
                        }
                    }
                    if (input['envSpec']['proxySpec'].hasOwnProperty('tkgMgmt')) {
                        if (input['envSpec']['proxySpec']['tkgMgmt'].hasOwnProperty('enableProxy')) {
                            if (input['envSpec']['proxySpec']['tkgMgmt']['enableProxy'] === 'true') {
                                this.dataService.changeMgmtEnableProxy(true);
                                if (input['envSpec']['proxySpec']['tkgMgmt'].hasOwnProperty('httpProxy') &&
                                    input['envSpec']['proxySpec']['tkgMgmt'].hasOwnProperty('httpsProxy')) {
                                        this.processMgmtProxyParam(input);
                                    }
                                if (input['envSpec']['proxySpec']['tkgMgmt'].hasOwnProperty('noProxy')) {
                                    this.dataService.changeMgmtNoProxy(
                                        input['envSpec']['proxySpec']['tkgMgmt']['noProxy']);
                                }
                                if(input['envSpec']['proxySpec']['tkgMgmt'].hasOwnProperty('proxyCert')) {
                                    this.dataService.changeMgmtProxyCert(
                                        input['envSpec']['proxySpec']['tkgMgmt']['proxyCert']);
                                }
                            } else {
                                this.dataService.changeMgmtEnableProxy(false);
                            }
                        }
                    }
                    if (input['envSpec']['proxySpec'].hasOwnProperty('tkgSharedservice')) {
                        if (input['envSpec']['proxySpec']['tkgSharedservice'].hasOwnProperty('enableProxy')) {
                            if (input['envSpec']['proxySpec']['tkgSharedservice']['enableProxy'] === 'true') {
                                this.dataService.changeSharedEnableProxy(true);
                                if (input['envSpec']['proxySpec']['tkgSharedservice'].hasOwnProperty('httpProxy') &&
                                    input['envSpec']['proxySpec']['tkgSharedservice'].hasOwnProperty('httpsProxy')) {
                                    this.processSharedProxyParam(input);
                                }
                                if (input['envSpec']['proxySpec']['tkgSharedservice'].hasOwnProperty('noProxy')) {
                                    this.dataService.changeSharedNoProxy(
                                        input['envSpec']['proxySpec']['tkgSharedservice']['noProxy']);
                                }
                                if(input['envSpec']['proxySpec']['tkgSharedservice'].hasOwnProperty('proxyCert')) {
                                    this.dataService.changeSharedProxyCert(
                                        input['envSpec']['proxySpec']['tkgSharedservice']['proxyCert']);
                                }
                            } else {
                                this.dataService.changeSharedEnableProxy(false);
                            }
                        }
                    }
                    if (input['envSpec']['proxySpec'].hasOwnProperty('tkgWorkload')) {
                        if (input['envSpec']['proxySpec']['tkgWorkload'].hasOwnProperty('enableProxy')) {
                            if (input['envSpec']['proxySpec']['tkgWorkload']['enableProxy'] === 'true') {
                                this.dataService.changeWrkEnableProxy(true);
                                if (input['envSpec']['proxySpec']['tkgWorkload'].hasOwnProperty('httpProxy') &&
                                    input['envSpec']['proxySpec']['tkgWorkload'].hasOwnProperty('httpsProxy')) {
                                        this.processWrkProxyParam(input);
                                    }
                                if (input['envSpec']['proxySpec']['tkgWorkload'].hasOwnProperty('noProxy')) {
                                    this.dataService.changeWrkNoProxy(
                                        input['envSpec']['proxySpec']['tkgWorkload']['noProxy']);
                                }
                                if(input['envSpec']['proxySpec']['tkgWorkload'].hasOwnProperty('proxyCert')) {
                                    this.dataService.changeWrkProxyCert(
                                        input['envSpec']['proxySpec']['tkgWorkload']['proxyCert']);
                                }
                            } else {
                                this.dataService.changeWrkEnableProxy(false);
                            }
                        }
                    }
                }
                if (input['envSpec'].hasOwnProperty('vcenterDetails')) {
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterAddress')) {
                        this.dataService.changeVCAddress(
                            input['envSpec']['vcenterDetails']['vcenterAddress']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoUser')) {
                        this.dataService.changeVCUser(
                            input['envSpec']['vcenterDetails']['vcenterSsoUser']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoPasswordBase64')) {
                        this.dataService.changeVCPass(
                            atob(input['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']));
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterDatastore')) {
                        this.dataService.changeDatastore(
                            input['envSpec']['vcenterDetails']['vcenterDatastore']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterCluster')) {
                        this.dataService.changeCluster(
                            input['envSpec']['vcenterDetails']['vcenterCluster']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterDatacenter')) {
                        this.dataService.changeDatacenter(
                            input['envSpec']['vcenterDetails']['vcenterDatacenter']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('contentLibraryName')) {
                        if (input['envSpec']['vcenterDetails']['contentLibraryName'] !== '') {
                            this.dataService.changeIsCustomerConnect(false);
                        }
                        this.dataService.changeContentLib(
                            input['envSpec']['vcenterDetails']['contentLibraryName']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('aviOvaName')) {
                        if (input['envSpec']['vcenterDetails']['aviOvaName'] !== '') {
                            this.dataService.changeIsCustomerConnect(false);
                        }
                        this.dataService.changeOvaImage(
                            input['envSpec']['vcenterDetails']['aviOvaName']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('resourcePoolName')) {
                        this.dataService.changeResourcePool(
                            input['envSpec']['vcenterDetails']['resourcePoolName']);
                    }
                }
                if (input['envSpec'].hasOwnProperty('marketplaceSpec')) {
                    if (input['envSpec']['marketplaceSpec'].hasOwnProperty('refreshToken')) {
                        if (input['envSpec']['vcenterDetails']['aviOvaName'] === '' &&
                            input['envSpec']['vcenterDetails']['contentLibraryName'] === '') {
                            if (input['envSpec']['marketplaceSpec']['refreshToken'] !== '') {
                                this.dataService.changeIsMarketplace(true);
                            }
                        }
                        this.dataService.changeMarketplaceRefreshToken(
                            input['envSpec']['marketplaceSpec']['refreshToken']);
                    }
                }

                if (input['envSpec'].hasOwnProperty('compliantSpec')) {
                    if (input['envSpec']['compliantSpec'].hasOwnProperty('compliantDeployment')) {
                        input['envSpec']['compliantSpec']['compliantDeployment'] = 'false';
                        if(input['envSpec']['compliantSpec']['compliantDeployment'] === 'true') {
                            this.dataService.changeCompliantDeployment(true);
                        } else this.dataService.changeCompliantDeployment(false);
                    } else this.dataService.changeCompliantDeployment(false);
                } else this.dataService.changeCompliantDeployment(false);

                if(input['envSpec'].hasOwnProperty('ceipParticipation')) {
                    if(input['envSpec']['ceipParticipation'] === 'true') {
                        this.dataService.changeCeipParticipation(true);
                    } else {
                        this.dataService.changeCeipParticipation(false);
                    }
                } else {
                    this.dataService.changeCeipParticipation(false);
                }
                if (input['envSpec'].hasOwnProperty('saasEndpoints')) {
                    if (input['envSpec']['saasEndpoints'].hasOwnProperty('tmcDetails')) {
                        if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcAvailability')) {
                            if (input['envSpec']['saasEndpoints']['tmcDetails']['tmcAvailability'] === 'true') {
                                this.dataService.changeEnableTMC(true);
                                this.apiClient.tmcEnabled = true;
                                if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcRefreshToken')) {
                                    this.dataService.changeApiToken(
                                        input['envSpec']['saasEndpoints']['tmcDetails']['tmcRefreshToken']);
                                }
                                if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcInstanceURL')) {
                                    this.dataService.changeInstanceUrl(input['envSpec']['saasEndpoints']['tmcDetails']['tmcInstanceURL']);
                                }
                                if (input['envSpec']['saasEndpoints'].hasOwnProperty('tanzuObservabilityDetails')) {
                                    if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityAvailability')) {
                                        if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityAvailability'] === 'true') {
                                            this.dataService.changeEnableTO(true);
                                            this.apiClient.toEnabled = true;
                                            if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityUrl')) {
                                                this.dataService.changeTOUrl(
                                                    input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityUrl']);
                                            }
                                            if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityRefreshToken')) {
                                                this.dataService.changeTOApiToken(
                                                    input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityRefreshToken']);
                                            }
                                        } else {
                                            this.apiClient.toEnabled = false;
                                            this.dataService.changeEnableTO(false);
                                        }
                                    }
                                } else {
                                    this.apiClient.toEnabled = false;
                                    this.dataService.changeEnableTO(false);
                                }
                            } else {
                                this.apiClient.tmcEnabled = false;
                                this.dataService.changeEnableTMC(false);
                                this.apiClient.toEnabled = false;
                                this.dataService.changeEnableTO(false);
                                this.dataService.changeEnableTSM(false);
                            }
                        } else {
                            this.apiClient.tmcEnabled = false;
                            this.dataService.changeEnableTMC(false);
                            this.apiClient.toEnabled = false;
                            this.dataService.changeEnableTO(false);
                            this.dataService.changeEnableTSM(false);
                        }
                    }
                }
                if (input['envSpec'].hasOwnProperty('customRepositorySpec')) {
                    if (input['envSpec']['customRepositorySpec'].hasOwnProperty('tkgCustomImageRepository')) {
                        if (input['envSpec']['customRepositorySpec']['tkgCustomImageRepository'] !== '') {
                            this.dataService.changeEnableRepoSettings(true);
                            this.dataService.changeRepoImage(
                                input['envSpec']['customRepositorySpec']['tkgCustomImageRepository']);
                            if (input['envSpec']['customRepositorySpec'].hasOwnProperty('tkgCustomImageRepositoryPublicCaCert')) {
                                if (input['envSpec']['customRepositorySpec']['tkgCustomImageRepositoryPublicCaCert'] === 'true') {
                                    this.dataService.changeCaCert(true);
                                } else {
                                    this.dataService.changeCaCert(false);
                                }
                            }
                        } else {
                            this.dataService.changeEnableRepoSettings(false);
                        }
                    }
                }
            }
            if (input.hasOwnProperty('tkgComponentSpec')) {
                if (input['tkgComponentSpec'].hasOwnProperty('aviComponents')) {
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController01Fqdn')) {
                        this.dataService.changeAviFqdn(
                            input['tkgComponentSpec']['aviComponents']['aviController01Fqdn']);
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController01Ip')) {
                        this.dataService.changeAviIp(
                            input['tkgComponentSpec']['aviComponents']['aviController01Ip']);
                    }
                    if(input['tkgComponentSpec']['aviComponents'].hasOwnProperty('modeOfDeployment')) {
                        let mode = input['tkgComponentSpec']['aviComponents']['modeOfDeployment'];
                        if(mode.toLowerCase() === 'non-orchestrated') this.dataService.changeModeOfDeployment('non-orchestrated');
                        else this.dataService.changeModeOfDeployment('orchestrated');
                    } else {
                        this.dataService.changeModeOfDeployment('orchestrated');

                    }
                    if(input['tkgComponentSpec']['aviComponents'].hasOwnProperty('typeOfLicense')) {
                        let mode = input['tkgComponentSpec']['aviComponents']['typeOfLicense'];
                        if(mode.toLowerCase() === 'essentials') {
                            this.dataService.changeTypeOfLicense('essentials');
                            this.apiClient.isEnterpriseLicense = false;
                        }
                        else {
                            this.dataService.changeTypeOfLicense('enterprise');
                            this.apiClient.isEnterpriseLicense = true;
                        }
                    } else {
                        this.dataService.changeTypeOfLicense('enterprise');
                        this.apiClient.isEnterpriseLicense = true;
                    }

                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('enableAviHa')) {
                        if(input['tkgComponentSpec']['aviComponents']['enableAviHa'] === 'true') {
                            this.dataService.changeEnableAviHA(true);
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController02Fqdn')) {
                                this.dataService.changeAviFqdn02(
                                    input['tkgComponentSpec']['aviComponents']['aviController02Fqdn']);
                            }
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController02Ip')) {
                                this.dataService.changeAviIp02(
                                    input['tkgComponentSpec']['aviComponents']['aviController02Ip']);
                            }
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController03Fqdn')) {
                                this.dataService.changeAviFqdn03(
                                    input['tkgComponentSpec']['aviComponents']['aviController03Fqdn']);
                            }
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviController03Ip')) {
                                this.dataService.changeAviIp03(
                                    input['tkgComponentSpec']['aviComponents']['aviController03Ip']);
                            }
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviClusterIp')) {
                                this.dataService.changeAviClusterIp(
                                    input['tkgComponentSpec']['aviComponents']['aviClusterIp']);
                            }
                            if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviClusterFqdn')) {
                                this.dataService.changeAviClusterFqdn(
                                    input['tkgComponentSpec']['aviComponents']['aviClusterFqdn']);
                            }
                        } else {
                            this.dataService.changeEnableAviHA(false);
                        }
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviSize')) {
                        this.dataService.changeAviSize(input['tkgComponentSpec']['aviComponents']['aviSize']);
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviCertPath')) {
                        this.dataService.changeAviCertPath(input['tkgComponentSpec']['aviComponents']['aviCertPath']);
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviCertKeyPath')) {
                        this.dataService.changeAviCertKeyPath(input['tkgComponentSpec']['aviComponents']['aviCertKeyPath']);
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviPasswordBase64')) {
                        this.dataService.changeAviPassword(
                            atob(input['tkgComponentSpec']['aviComponents']['aviPasswordBase64']));
                    }
                    if (input['tkgComponentSpec']['aviComponents'].hasOwnProperty('aviBackupPassphraseBase64')) {
                        this.dataService.changeAviBackupPassword(
                            atob(input['tkgComponentSpec']['aviComponents']['aviBackupPassphraseBase64']));
                    }
                }
                if(input['tkgComponentSpec'].hasOwnProperty('identityManagementSpec')){
                    if (input['tkgComponentSpec']['identityManagementSpec'].hasOwnProperty('identityManagementType')){
                        if (input['tkgComponentSpec']['identityManagementSpec']['identityManagementType'] === 'oidc'){
                            this.dataService.changeIdentityManagementType('oidc');
                            this.dataService.changeEnableIdentityManagement(true);
                            this.apiClient.enableIdentityManagement = true;
                            if (input['tkgComponentSpec']['identityManagementSpec'].hasOwnProperty('oidcSpec')) {
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcIssuerUrl')) {
                                    this.dataService.changeOidcIssuerUrl(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcIssuerUrl']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcClientId')) {
                                    this.dataService.changeOidcClientId(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcClientId']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcClientSecret')) {
                                    this.dataService.changeOidcClientSecret(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcClientSecret']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcScopes')) {
                                    this.dataService.changeOidcScopes(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcScopes']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcUsernameClaim')) {
                                    this.dataService.changeOidcUsernameClaim(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcUsernameClaim']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['oidcSpec'].hasOwnProperty('oidcGroupsClaim')) {
                                    this.dataService.changeOidcGroupClaim(
                                        input['tkgComponentSpec']['identityManagementSpec']['oidcSpec']['oidcGroupsClaim']);
                                }
                            }
                        } else if (input['tkgComponentSpec']['identityManagementSpec']['identityManagementType'] === 'ldap') {
                            this.dataService.changeIdentityManagementType('ldap');
                            this.dataService.changeEnableIdentityManagement(true);
                            this.apiClient.enableIdentityManagement = true;
                            if (input['tkgComponentSpec']['identityManagementSpec'].hasOwnProperty('ldapSpec')) {
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapEndpointIp')) {
                                    this.dataService.changeLdapEndpointIp(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapEndpointIp']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapEndpointPort')) {
                                    this.dataService.changeLdapEndpointPort(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapEndpointPort']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapBindPWBase64')) {
                                    this.dataService.changeLdapBindPw(
                                        atob(input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapBindPWBase64']));
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapBindDN')) {
                                    this.dataService.changeLdapBindDN(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapBindDN']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapUserSearchBaseDN')) {
                                    this.dataService.changeLdapUserSearchBaseDN(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapUserSearchBaseDN']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapUserSearchFilter')) {
                                    this.dataService.changeLdapUserSearchFilter(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapUserSearchFilter']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapUserSearchUsername')) {
                                    this.dataService.changeLdapUserSearchUsername(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapUserSearchUsername']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchBaseDN')) {
                                    this.dataService.changeLdapGroupSearchBaseDN(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchBaseDN']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchFilter')) {
                                    this.dataService.changeLdapGroupSearchFilter(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchFilter']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchUserAttr')) {
                                    this.dataService.changeLdapGroupSearchUserAttr(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchUserAttr']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchGroupAttr')) {
                                    this.dataService.changeLdapGroupSearchGroupAttr(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchGroupAttr']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapGroupSearchNameAttr')) {
                                    this.dataService.changeLdapGroupSearchNameAttr(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapGroupSearchNameAttr']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapRootCAData')) {
                                    this.dataService.changeLdapRootCAData(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapRootCAData']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapTestUserName')) {
                                    this.dataService.changeLdapTestUserName(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapTestUserName']);
                                }
                                if (input['tkgComponentSpec']['identityManagementSpec']['ldapSpec'].hasOwnProperty('ldapTestGroupName')) {
                                    this.dataService.changeLdapTestGroupName(
                                        input['tkgComponentSpec']['identityManagementSpec']['ldapSpec']['ldapTestGroupName']);
                                }
                            }

                        }
                        else {
                            this.dataService.changeEnableIdentityManagement(false);
                            this.apiClient.enableIdentityManagement = false;
                        }
                    } else {
                        this.dataService.changeEnableIdentityManagement(false);
                        this.apiClient.enableIdentityManagement = false;
                    }
                } else {
                    this.dataService.changeEnableIdentityManagement(false);
                    this.apiClient.enableIdentityManagement = false;
                }
                if (input['tkgComponentSpec'].hasOwnProperty('aviMgmtNetwork')) {
                    if (input['tkgComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkName')) {
                        this.dataService.changeAviSegment(
                            input['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName']);
                    }
                    if (input['tkgComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkGatewayCidr')) {
                        this.dataService.changeAviGateway(
                            input['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkGatewayCidr']);
                    }
                    if (input['tkgComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtServiceIpStartRange')) {
                        this.dataService.changeAviDhcpStart(
                            input['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtServiceIpStartRange']);
                    }
                    if (input['tkgComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtServiceIpEndRange')) {
                        this.dataService.changeAviDhcpEnd(
                            input['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtServiceIpEndRange']);
                    }
                }
                if (input['tkgComponentSpec'].hasOwnProperty('tkgClusterVipNetwork')) {
                    if (input['tkgComponentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipNetworkName')) {
                        this.dataService.changeAviClusterVipNetworkName(
                            input['tkgComponentSpec']['tkgClusterVipNetwork']['tkgClusterVipNetworkName']);
                    }
                    if (input['tkgComponentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipNetworkGatewayCidr')) {
                        this.dataService.changeAviClusterVipGatewayIp(
                            input['tkgComponentSpec']['tkgClusterVipNetwork']['tkgClusterVipNetworkGatewayCidr']);
                    }
                    if (input['tkgComponentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipIpStartRange')) {
                        this.dataService.changeAviClusterVipStartIp(
                            input['tkgComponentSpec']['tkgClusterVipNetwork']['tkgClusterVipIpStartRange']);
                    }
                    if (input['tkgComponentSpec']['tkgClusterVipNetwork'].hasOwnProperty('tkgClusterVipIpEndRange')) {
                        this.dataService.changeAviClusterVipEndIp(
                            input['tkgComponentSpec']['tkgClusterVipNetwork']['tkgClusterVipIpEndRange']);
                    }
                }
                if (input['tkgComponentSpec'].hasOwnProperty('tkgMgmtComponents')) {
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtSize')) {
                        this.dataService.changeMgmtDeploymentSize(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtSize']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtDeploymentType')) {
                        this.dataService.changeMgmtDeploymentType(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtDeploymentType']);
                    }
                    if(input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtCpuSize')) {
                        this.dataService.changeMgmtCpu(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtCpuSize']);
                    }
                    if(input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtMemorySize')) {
                        this.dataService.changeMgmtMemory(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtMemorySize']);
                    }
                    if(input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtStorageSize')) {
                        this.dataService.changeMgmtStorage(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtStorageSize']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtClusterName')) {
                        this.dataService.changeMgmtClusterName(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterName']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtGatewayCidr')) {
                        this.dataService.changeMgmtGateway(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtGatewayCidr']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtNetworkName')) {
                        this.dataService.changeMgmtSegment(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtNetworkName']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtClusterCidr')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterCidr'] !== '') {
                            this.dataService.changeMgmtClusterCidr(
                                input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterCidr']);
                        }
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtServiceCidr')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtServiceCidr'] !== '') {
                            this.dataService.changeMgmtServiceCidr(
                                input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtServiceCidr']);
                        }
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtBaseOs')) {
                        this.dataService.changeMgmtBaseImage(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtBaseOs']);
                    }
                    if (this.apiClient.enableIdentityManagement) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtRbacUserRoleSpec')) {
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('clusterAdminUsers')) {
                                this.dataService.changeMgmtClusterAdminUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec']['clusterAdminUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('adminUsers')) {
                                this.dataService.changeMgmtAdminUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec']['adminUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('editUsers')) {
                                this.dataService.changeMgmtEditUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec']['editUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'].hasOwnProperty('viewUsers')) {
                                this.dataService.changeMgmtViewUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec']['viewUsers']);
                            }
                        }
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgMgmtClusterGroupName')) {
                        this.dataService.changeMgmtClusterGroupName(input['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterGroupName']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceSize')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceSize'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.dataService.changeSharedDeploymentSize(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceSize']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceDeploymentType')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceDeploymentType'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.dataService.changeSharedDeploymentType(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceDeploymentType']);
                    }
                    if(input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceCpuSize')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceCpuSize'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.dataService.changeSharedCpu(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceCpuSize']);
                    }
                    if(input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceMemorySize')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceMemorySize'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.dataService.changeSharedMemory(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceMemorySize']);
                    }
                    if(input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceStorageSize')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceStorageSize'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.dataService.changeSharedStorage(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceStorageSize']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceClusterName')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceClusterName'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.dataService.changeSharedClusterName(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceClusterName']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceWorkerMachineCount')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceWorkerMachineCount'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.dataService.changeSharedWorkerNodeCount(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceWorkerMachineCount']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceClusterCidr')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceClusterCidr'] !== '') {
                            this.dataService.changeSharedClusterCidr(
                                input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceClusterCidr']);
                        }
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceServiceCidr')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceServiceCidr'] !== '') {
                            this.dataService.changeSharedServiceCidr(
                                input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceServiceCidr']);
                        }
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceBaseOs')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceBaseOs'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.dataService.changeSharedBaseImage(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceBaseOs']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceKubeVersion')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceKubeVersion'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.dataService.changeSharedBaseImageVersion(
                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceKubeVersion']);
                    }

                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceEnableAviL7')) {
                        if(input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceEnableAviL7'] === 'true') {
                            if(this.apiClient.isEnterpriseLicense) {
                                this.dataService.changeEnableAviL7Shared(true);
                            } else this.dataService.changeEnableAviL7Shared(false);
                        } else this.dataService.changeEnableAviL7Shared(false);
                    } else this.dataService.changeEnableAviL7Shared(false);

                    if(input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgCustomCertsPath')) {
                        if(input['tkgComponentSpec']['tkgMgmtComponents']['tkgCustomCertsPath'] !== "" &&
                        input['tkgComponentSpec']['tkgMgmtComponents']['tkgCustomCertsPath'] !== null) {
                            this.dataService.changeTkgCustomCert(input['tkgComponentSpec']['tkgMgmtComponents']['tkgCustomCertsPath']);
                        }
                    }
                    if (this.apiClient.enableIdentityManagement) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceRbacUserRoleSpec')) {
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('clusterAdminUsers')) {
                                if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec']['clusterAdminUsers'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.dataService.changeSharedClusterAdminUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec']['clusterAdminUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('adminUsers')) {
                                if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec']['adminUsers'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.dataService.changeSharedAdminUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec']['adminUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('editUsers')) {
                                if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec']['editUsers'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.dataService.changeSharedEditUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec']['editUsers']);
                            }
                            if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec'].hasOwnProperty('viewUsers')) {
                                if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec']['viewUsers'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.dataService.changeSharedViewUsers(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceRbacUserRoleSpec']['viewUsers']);
                            }
                        }
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceClusterGroupName')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceClusterGroupName'] !== ""){
                            this.apiClient.sharedServicesClusterSettings = true;
                        }
                        this.dataService.changeSharedClusterGroupName(input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceClusterGroupName']);
                    }
                    if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedserviceEnableDataProtection')) {
                        if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceEnableDataProtection'] === 'true' && this.apiClient.tmcEnabled) {
                            this.dataService.changeSharedEnableDataProtection(true);
                            this.apiClient.sharedDataProtectonEnabled = true;
                            if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedClusterCredential')) {
                                if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterCredential'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.dataService.changeSharedDataProtectionCreds(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterCredential']);
                            }
                            if (input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedClusterBackupLocation')) {
                                if (input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterBackupLocation'] !== ""){
                                    this.apiClient.sharedServicesClusterSettings = true;
                                }
                                this.dataService.changeSharedDataProtectionTargetLocation(
                                    input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterBackupLocation']);
                            }
                        } else{
                            this.apiClient.sharedDataProtectonEnabled = false;
                            this.dataService.changeSharedEnableDataProtection(false);
                        }
                    } else {
                        this.apiClient.sharedDataProtectonEnabled = false;
                        this.dataService.changeSharedEnableDataProtection(false);
                    }
                    if(!this.apiClient.tmcEnabled) {
                        if(input['tkgComponentSpec']['tkgMgmtComponents'].hasOwnProperty('tkgSharedClusterVeleroDataProtection')) {
                            if(input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection'].hasOwnProperty('enableVelero')) {
                                if(input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection']['enableVelero'] === 'true') {
                                    this.dataService.changeSharedEnableVelero(true);
                                    if(input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection'].hasOwnProperty('username')) {
                                        this.dataService.changeSharedVeleroUsername(
                                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection']['username']);
                                    }
                                    if(input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection'].hasOwnProperty('passwordBase64')) {
                                        this.dataService.changeSharedVeleroPassword(
                                            atob(input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection']['passwordBase64']));
                                    }
                                    if(input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection'].hasOwnProperty('bucketName')) {
                                        this.dataService.changeSharedVeleroBucketName(
                                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection']['bucketName']);
                                    }
                                    if(input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection'].hasOwnProperty('backupRegion')) {
                                        this.dataService.changeSharedVeleroRegion(
                                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection']['backupRegion']);
                                    }
                                    if(input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection'].hasOwnProperty('backupS3Url')) {
                                        this.dataService.changeSharedVeleroS3Url(
                                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection']['backupS3Url']);
                                    }
                                    if(input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection'].hasOwnProperty('backupPublicUrl')) {
                                        this.dataService.changeSharedVeleroPublicUrl(
                                            input['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedClusterVeleroDataProtection']['backupPublicUrl']);
                                    }
                                } else {
                                    this.dataService.changeSharedEnableVelero(false);
                                }
                            } else {
                                this.dataService.changeSharedEnableVelero(false);
                            }
                        } else {
                            this.dataService.changeSharedEnableVelero(false)
                        }
                    } else {
                        this.dataService.changeSharedEnableVelero(false);
                    }
                }
            }
            if (input.hasOwnProperty('tkgMgmtDataNetwork')) {
                if (input['tkgMgmtDataNetwork'].hasOwnProperty('tkgMgmtDataNetworkGatewayCidr')) {
                    this.dataService.changeTkgMgmtDataGateway(
                        input['tkgMgmtDataNetwork']['tkgMgmtDataNetworkGatewayCidr']);
                }
                if (input['tkgMgmtDataNetwork'].hasOwnProperty('tkgMgmtDataNetworkName')) {
                    this.dataService.changeTkgMgmtDataSegment(
                        input['tkgMgmtDataNetwork']['tkgMgmtDataNetworkName']);
                }
                if (input['tkgMgmtDataNetwork'].hasOwnProperty('tkgMgmtAviServiceIpStartRange')) {
                    this.dataService.changeTkgMgmtDataDhcpStart(
                        input['tkgMgmtDataNetwork']['tkgMgmtAviServiceIpStartRange']);
                }
                if (input['tkgMgmtDataNetwork'].hasOwnProperty('tkgMgmtAviServiceIpEndRange')) {
                    this.dataService.changeTkgMgmtDataDhcpEnd(
                        input['tkgMgmtDataNetwork']['tkgMgmtAviServiceIpEndRange']);
                }
            }
            if (input.hasOwnProperty('tkgWorkloadDataNetwork')) {
                if (input['tkgWorkloadDataNetwork'].hasOwnProperty('tkgWorkloadDataNetworkName')) {
                    if (input['tkgWorkloadDataNetwork']['tkgWorkloadDataNetworkName'] !== ""){
                        this.apiClient.workloadDataSettings = true;
                    }
                    this.dataService.changeTkgWrkDataSegment(
                        input['tkgWorkloadDataNetwork']['tkgWorkloadDataNetworkName']);
                }
                if (input['tkgWorkloadDataNetwork'].hasOwnProperty('tkgWorkloadDataNetworkGatewayCidr')) {
                    if (input['tkgWorkloadDataNetwork']['tkgWorkloadDataNetworkGatewayCidr'] !== ""){
                        this.apiClient.workloadDataSettings = true;
                    }
                    this.dataService.changeTkgWrkDataGateway(
                        input['tkgWorkloadDataNetwork']['tkgWorkloadDataNetworkGatewayCidr']);
                }
                if (input['tkgWorkloadDataNetwork'].hasOwnProperty('tkgWorkloadAviServiceIpStartRange')) {
                    if (input['tkgWorkloadDataNetwork']['tkgWorkloadAviServiceIpStartRange'] !== ""){
                        this.apiClient.workloadDataSettings = true;
                    }
                    this.dataService.changeTkgWrkDataDhcpStart(
                        input['tkgWorkloadDataNetwork']['tkgWorkloadAviServiceIpStartRange']);
                }
                if (input['tkgWorkloadDataNetwork'].hasOwnProperty('tkgWorkloadAviServiceIpEndRange')) {
                    if (input['tkgWorkloadDataNetwork']['tkgWorkloadAviServiceIpEndRange'] !== ""){
                        this.apiClient.workloadDataSettings = true;
                    }
                    this.dataService.changeTkgWrkDataDhcpEnd(
                        input['tkgWorkloadDataNetwork']['tkgWorkloadAviServiceIpEndRange']);
                }
            }
            if (input.hasOwnProperty('tkgWorkloadComponents')) {
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadDeploymentType')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadDeploymentType'] !== ""){
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkDeploymentType(
                        input['tkgWorkloadComponents']['tkgWorkloadDeploymentType']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadSize')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadSize'] !== "") {
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkDeploymentSize(
                        input['tkgWorkloadComponents']['tkgWorkloadSize']);
                }
                if(input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadCpuSize')){
                    if (input['tkgWorkloadComponents']['tkgWorkloadCpuSize'] !== ""){
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkCpu(input['tkgWorkloadComponents']['tkgWorkloadCpuSize']);
                }
                if(input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadMemorySize')){
                    if (input['tkgWorkloadComponents']['tkgWorkloadMemorySize'] !== "") {
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkMemory(input['tkgWorkloadComponents']['tkgWorkloadMemorySize']);
                }
                if(input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadStorageSize')){
                    if (input['tkgWorkloadComponents']['tkgWorkloadStorageSize'] !== "") {
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkStorage(input['tkgWorkloadComponents']['tkgWorkloadStorageSize']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadClusterName')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadClusterName'] !== "") {
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkClusterName(
                        input['tkgWorkloadComponents']['tkgWorkloadClusterName']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadWorkerMachineCount')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadWorkerMachineCount'] !== "") {
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkWorkerNodeCount(
                        input['tkgWorkloadComponents']['tkgWorkloadWorkerMachineCount']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadNetworkName')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadNetworkName'] !== "") {
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkSegment(
                        input['tkgWorkloadComponents']['tkgWorkloadNetworkName']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadGatewayCidr')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadGatewayCidr'] !== ""){
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkGateway(
                        input['tkgWorkloadComponents']['tkgWorkloadGatewayCidr']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadClusterCidr')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadClusterCidr'] !== '') {
                        this.dataService.changeWrkClusterCidr(
                            input['tkgWorkloadComponents']['tkgWorkloadClusterCidr']);
                    }
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadServiceCidr')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadServiceCidr'] !== '') {
                        this.dataService.changeWrkServiceCidr(
                            input['tkgWorkloadComponents']['tkgWorkloadServiceCidr']);
                    }
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadBaseOs')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadBaseOs'] !== ""){
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkBaseImage(
                        input['tkgWorkloadComponents']['tkgWorkloadBaseOs']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadKubeVersion')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadKubeVersion'] !== ""){
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkBaseImageVersion(
                        input['tkgWorkloadComponents']['tkgWorkloadKubeVersion']);
                }

                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadEnableAviL7')) {
                    if(input['tkgWorkloadComponents']['tkgWorkloadEnableAviL7'] === 'true') {
                        if(this.apiClient.isEnterpriseLicense) {
                                this.dataService.changeEnableAviL7Workload(true);
                        } else this.dataService.changeEnableAviL7Workload(false);
                    } else this.dataService.changeEnableAviL7Workload(false);
                } else this.dataService.changeEnableAviL7Workload(false);

                if (this.apiClient.enableIdentityManagement) {
                    if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadRbacUserRoleSpec')) {
                        if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('clusterAdminUsers')) {
                            if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['clusterAdminUsers'] !== ""){
                                this.apiClient.workloadClusterSettings = true;
                            }
                            this.dataService.changeWrkClusterAdminUsers(
                                input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['clusterAdminUsers']);
                        }
                        if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('adminUsers')) {
                            if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['adminUsers'] !== ""){
                                this.apiClient.workloadClusterSettings = true;
                            }
                            this.dataService.changeWrkAdminUsers(
                                input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['adminUsers']);
                        }
                        if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('editUsers')) {
                            if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['editUsers'] !== ""){
                                this.apiClient.workloadClusterSettings = true;
                            }
                            this.dataService.changeWrkEditUsers(
                                input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['editUsers']);
                        }
                        if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec'].hasOwnProperty('viewUsers')) {
                            if (input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['viewUsers'] !== ""){
                                this.apiClient.workloadClusterSettings = true;
                            }
                            this.dataService.changeWrkViewUsers(
                                input['tkgWorkloadComponents']['tkgWorkloadRbacUserRoleSpec']['viewUsers']);
                        }
                    }
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadClusterGroupName')) {
                    if (input['tkgWorkloadComponents']['tkgWorkloadClusterGroupName'] !== ""){
                        this.apiClient.workloadClusterSettings = true;
                    }
                    this.dataService.changeWrkClusterGroupName(input['tkgWorkloadComponents']['tkgWorkloadClusterGroupName']);
                }
                if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadEnableDataProtection')) {
                    if(input['tkgWorkloadComponents']['tkgWorkloadEnableDataProtection'] === 'true' && this.apiClient.tmcEnabled) {
                        this.dataService.changeWrkEnableDataProtection(true);
                        this.apiClient.wrkDataProtectionEnabled = true;
                        if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadClusterCredential')) {
                            if (input['tkgWorkloadComponents']['tkgWorkloadClusterCredential'] !== ""){
                                this.apiClient.workloadClusterSettings = true;
                            }
                            this.dataService.changeWrkDataProtectionCreds(
                                input['tkgWorkloadComponents']['tkgWorkloadClusterCredential']);
                        }
                        if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadClusterBackupLocation')) {
                            if (input['tkgWorkloadComponents']['tkgWorkloadClusterBackupLocation'] !== ""){
                                this.apiClient.workloadClusterSettings = true;
                            }
                            this.dataService.changeWrkDataProtectionTargetLocation(
                                input['tkgWorkloadComponents']['tkgWorkloadClusterBackupLocation']);
                        }
                    } else {
                        this.dataService.changeWrkEnableDataProtection(false);
                        this.apiClient.wrkDataProtectionEnabled = false;
                    }
                } else {
                    this.dataService.changeWrkEnableDataProtection(false);
                    this.apiClient.wrkDataProtectionEnabled = false;
                }
                if(!this.apiClient.tmcEnabled) {
                    if(input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadClusterVeleroDataProtection')) {
                        if(input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('enableVelero')) {
                            if(input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection']['enableVelero'] === 'true') {
                                this.dataService.changeWrkEnableVelero(true);
                            }
                        } else {
                            this.dataService.changeWrkEnableVelero(false);
                        }
                        if(input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('username')) {
                            this.dataService.changeWrkVeleroUsername(
                                input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection']['username']);
                        }
                        if(input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('passwordBase64')) {
                            this.dataService.changeWrkVeleroPassword(
                                atob(input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection']['passwordBase64']));
                        }
                        if(input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('bucketName')) {
                            this.dataService.changeWrkVeleroBucketName(
                                input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection']['bucketName']);
                        }
                        if(input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('backupRegion')) {
                            this.dataService.changeWrkVeleroRegion(
                                input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection']['backupRegion']);
                        }
                        if(input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('backupS3Url')) {
                            this.dataService.changeWrkVeleroS3Url(
                                input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection']['backupS3Url']);
                        }
                        if(input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('backupPublicUrl')) {
                            this.dataService.changeWrkVeleroPublicUrl(
                                input['tkgWorkloadComponents']['tkgWorkloadClusterVeleroDataProtection']['backupPublicUrl']);
                        }
                    } else {
                        this.dataService.changeWrkEnableVelero(false);
                    }
                } else {
                    this.dataService.changeWrkEnableVelero(false);
                }
                let tmcEnabled;
                this.dataService.currentEnableTMC.subscribe(enableTmc => tmcEnabled = enableTmc);
                if (tmcEnabled) {
                    if (input['tkgWorkloadComponents'].hasOwnProperty('tkgWorkloadTsmIntegration')) {
                        if (input['tkgWorkloadComponents']['tkgWorkloadTsmIntegration'] === 'true') {
                            this.dataService.changeEnableTSM(true);
                            if (input['tkgWorkloadComponents'].hasOwnProperty('namespaceExclusions')) {
                                if (input['tkgWorkloadComponents']['namespaceExclusions'].hasOwnProperty('exactName')) {
                                    if (input['tkgWorkloadComponents']['namespaceExclusions']['exactName'] !== ""){
                                        this.apiClient.workloadClusterSettings = true;
                                    }
                                    this.dataService.changeTsmExactNamespaceExclusion(input['tkgWorkloadComponents']['namespaceExclusions']['exactName']);
                                }
                                if (input['tkgWorkloadComponents']['namespaceExclusions'].hasOwnProperty('startsWith')) {
                                    if (input['tkgWorkloadComponents']['namespaceExclusions']['startsWith'] !== ""){
                                        this.apiClient.workloadClusterSettings = true;
                                    }
                                    this.dataService.changeTsmStartsWithNamespaceExclusion(input['tkgWorkloadComponents']['namespaceExclusions']['startsWith']);
                                }
                            }
                        } else {
                            this.dataService.changeEnableTSM(false);
                        }
                    } else {
                        this.dataService.changeEnableTSM(false);
                    }
                }
            }
            if (input.hasOwnProperty('harborSpec')) {
                this.dataService.changeEnableHarbor(true);
                if (input['harborSpec'].hasOwnProperty('harborFqdn')) {
                    this.dataService.changeHarborFqdn(
                        input['harborSpec']['harborFqdn']);
                }
                if (input['harborSpec'].hasOwnProperty('harborPasswordBase64')) {
                    this.dataService.changeHarborPassword(
                        atob(input['harborSpec']['harborPasswordBase64']));
                }
                if (input['harborSpec'].hasOwnProperty('harborCertPath')) {
                    this.dataService.changeHarborCertPath(
                        input['harborSpec']['harborCertPath']);
                }
                if (input['harborSpec'].hasOwnProperty('harborCertKeyPath')) {
                    this.dataService.changeHarborCertKey(
                        input['harborSpec']['harborCertKeyPath']);
                }
            }
            if (input.hasOwnProperty('tanzuExtensions')) {
                if (input['tanzuExtensions'].hasOwnProperty('enableExtensions')) {
                    if (input['tanzuExtensions']['enableExtensions'] === 'true') {
                        this.dataService.changeEnableTanzuExtension(true);
                        if (input['tanzuExtensions'].hasOwnProperty('tkgClustersName')) {
                            this.dataService.changeTkgClusters(input['tanzuExtensions']['tkgClustersName']);
                            this.processEnableLogging(input, this.dataService);
                            this.processEnableMonitoring(input, this.dataService);
                        }
                    } else {
                        this.dataService.changeEnableTanzuExtension(false);
                        this.dataService.changeEnableLoggingExtension(false);
                        this.dataService.changeEnableMonitoringExtension(false);
                    }
                } else {
                    this.dataService.changeEnableTanzuExtension(false);
                    this.dataService.changeEnableLoggingExtension(false);
                    this.dataService.changeEnableMonitoringExtension(false);
                }
            }
        }
    }

    public setParamsFromInputJSONTkgs(input) {
        if (input) {
            this.vsphereTkgsDataService.changeInputFileStatus(true);
            // Dumy Component
            if (input.hasOwnProperty('envSpec')) {
                if (input['envSpec'].hasOwnProperty('infraComponents')) {
                    if (input['envSpec']['infraComponents'].hasOwnProperty('dnsServersIp')) {
                        const dns = input['envSpec']['infraComponents']['dnsServersIp'];
                        this.vsphereTkgsDataService.changeDnsServer(dns);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('ntpServers')) {
                        const ntp = input['envSpec']['infraComponents']['ntpServers'];
                        this.vsphereTkgsDataService.changeNtpServer(ntp);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('searchDomains')) {
                        const searchDomain = input['envSpec']['infraComponents'].searchDomains;
                        this.vsphereTkgsDataService.changeSearchDomain(searchDomain);
                    }
                }
                if (input['envSpec'].hasOwnProperty('vcenterDetails')) {
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterAddress')) {
                        this.vsphereTkgsDataService.changeVCAddress(input['envSpec']['vcenterDetails']['vcenterAddress']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoUser')) {
                        this.vsphereTkgsDataService.changeVCUser(input['envSpec']['vcenterDetails']['vcenterSsoUser']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoPasswordBase64')) {
                        this.vsphereTkgsDataService.changeVCPass(atob(input['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']));
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterDatastore')) {
                        this.vsphereTkgsDataService.changeDatastore(input['envSpec']['vcenterDetails']['vcenterDatastore']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterCluster')) {
                        this.vsphereTkgsDataService.changeCluster(input['envSpec']['vcenterDetails']['vcenterCluster']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterDatacenter')) {
                        this.vsphereTkgsDataService.changeDatacenter(input['envSpec']['vcenterDetails']['vcenterDatacenter']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('contentLibraryName')) {
                        if (input['envSpec']['vcenterDetails']['contentLibraryName'] !== '') {
                            this.vsphereTkgsDataService.changeIsMarketplace(false);
                        }
                        this.vsphereTkgsDataService.changeContentLib(
                            input['envSpec']['vcenterDetails']['contentLibraryName']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('aviOvaName')) {
                        if (input['envSpec']['vcenterDetails']['aviOvaName'] !== '') {
                            this.vsphereTkgsDataService.changeIsMarketplace(false);
                        }
                        this.vsphereTkgsDataService.changeOvaImage(
                            input['envSpec']['vcenterDetails']['aviOvaName']);
                    }
                }
                if (input['envSpec'].hasOwnProperty('marketplaceSpec')) {
                    if (input['envSpec']['marketplaceSpec'].hasOwnProperty('refreshToken')) {
                        if (input['envSpec']['vcenterDetails']['aviOvaName'] === '' &&
                            input['envSpec']['vcenterDetails']['contentLibraryName'] === '') {
                            if (input['envSpec']['marketplaceSpec']['refreshToken'] !== '') {
                                this.vsphereTkgsDataService.changeIsMarketplace(true);
                            }
                        }
                        this.vsphereTkgsDataService.changeMarketplaceRefreshToken(
                            input['envSpec']['marketplaceSpec']['refreshToken']);
                    }
                }
                if (input['envSpec'].hasOwnProperty('saasEndpoints')) {
                    if (input['envSpec']['saasEndpoints'].hasOwnProperty('tmcDetails')) {
                        if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcAvailability')) {
                            if (input['envSpec']['saasEndpoints']['tmcDetails']['tmcAvailability'] === 'true') {
                                this.vsphereTkgsDataService.changeEnableTMC(true);
                                this.apiClient.tmcEnabled = true;

                                if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcRefreshToken')) {
                                    this.vsphereTkgsDataService.changeApiToken(
                                        input['envSpec']['saasEndpoints']['tmcDetails']['tmcRefreshToken']);
                                }
                                if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcSupervisorClusterName')) {
                                    this.vsphereTkgsDataService.changeSupervisorClusterName(
                                        input['envSpec']['saasEndpoints']['tmcDetails']['tmcSupervisorClusterName']);
                                }

                                if (input['envSpec']['saasEndpoints'].hasOwnProperty('tanzuObservabilityDetails')) {
                                    if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityAvailability')) {
                                        if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityAvailability'] === 'true') {
                                            this.vsphereTkgsDataService.changeEnableTO(true);
                                            this.apiClient.toEnabled = true;
                                            if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityUrl')) {
                                                this.vsphereTkgsDataService.changeTOUrl(
                                                    input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityUrl']);
                                            }
                                            if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityRefreshToken')) {
                                                this.vsphereTkgsDataService.changeTOApiToken(
                                                    input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityRefreshToken']);
                                            }
                                        } else {
                                            this.apiClient.toEnabled = false;
                                            this.vsphereTkgsDataService.changeEnableTO(false);
                                        }
                                    } else {
                                        this.apiClient.toEnabled = false;
                                        this.vsphereTkgsDataService.changeEnableTO(false);
                                    }
                                } else {
                                    this.apiClient.toEnabled = false;
                                    this.vsphereTkgsDataService.changeEnableTO(false);
                                }

                            } else {
                                this.vsphereTkgsDataService.changeEnableTMC(false);
                                this.apiClient.tmcEnabled = false;
                                this.apiClient.toEnabled = false;
                                this.vsphereTkgsDataService.changeEnableTO(false);
                                this.vsphereTkgsDataService.changeEnableTSM(false);
                            }
                        } else {
                            this.vsphereTkgsDataService.changeEnableTMC(false);
                            this.apiClient.tmcEnabled = false;
                            this.apiClient.toEnabled = false;
                            this.vsphereTkgsDataService.changeEnableTO(false);
                            this.vsphereTkgsDataService.changeEnableTSM(false);
                        }
                    }
                }
            }
            if (input.hasOwnProperty('tkgsComponentSpec')) {
                if (input['tkgsComponentSpec'].hasOwnProperty('controlPlaneSize')) {
                    this.vsphereTkgsDataService.changeControlPlaneSize(
                        input['tkgsComponentSpec']['controlPlaneSize']);
                }

                if (input['tkgsComponentSpec'].hasOwnProperty('aviComponents')) {
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController01Fqdn')) {
                        this.vsphereTkgsDataService.changeAviFqdn(
                            input['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']);
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController01Ip')) {
                        this.vsphereTkgsDataService.changeAviIp(
                            input['tkgsComponentSpec']['aviComponents']['aviController01Ip']);
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviPasswordBase64')) {
                        this.vsphereTkgsDataService.changeAviPassword(
                            atob(input['tkgsComponentSpec']['aviComponents']['aviPasswordBase64']));
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviBackupPassphraseBase64')) {
                        this.vsphereTkgsDataService.changeAviBackupPassword(
                            atob(input['tkgsComponentSpec']['aviComponents']['aviBackupPassphraseBase64']));
                    }
                    if(input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('typeOfLicense')) {
                        let mode = input['tkgsComponentSpec']['aviComponents']['typeOfLicense'];
                        if(mode.toLowerCase() === 'essentials') this.vsphereTkgsDataService.changeTypeOfLicense('essentials');
                        else this.vsphereTkgsDataService.changeTypeOfLicense('enterprise');
                    } else {
                        this.vsphereTkgsDataService.changeTypeOfLicense('enterprise');
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('enableAviHa')) {
                        if(input['tkgsComponentSpec']['aviComponents']['enableAviHa'] === 'true') {
                            this.vsphereTkgsDataService.changeEnableAviHA(true);
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController02Fqdn')) {
                                this.vsphereTkgsDataService.changeAviFqdn02(
                                    input['tkgsComponentSpec']['aviComponents']['aviController02Fqdn']);
                            }
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController02Ip')) {
                                this.vsphereTkgsDataService.changeAviIp02(
                                    input['tkgsComponentSpec']['aviComponents']['aviController02Ip']);
                            }
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController03Fqdn')) {
                                this.vsphereTkgsDataService.changeAviFqdn03(
                                    input['tkgsComponentSpec']['aviComponents']['aviController03Fqdn']);
                            }
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController03Ip')) {
                                this.vsphereTkgsDataService.changeAviIp03(
                                    input['tkgsComponentSpec']['aviComponents']['aviController03Ip']);
                            }
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviClusterIp')) {
                                this.vsphereTkgsDataService.changeAviClusterIp(
                                    input['tkgsComponentSpec']['aviComponents']['aviClusterIp']);
                            }
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviClusterFqdn')) {
                                this.vsphereTkgsDataService.changeAviClusterFqdn(
                                    input['tkgsComponentSpec']['aviComponents']['aviClusterFqdn']);
                            }
                        } else {
                            this.vsphereTkgsDataService.changeEnableAviHA(false);
                        }
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviSize')) {
                        this.vsphereTkgsDataService.changeAviSize(input['tkgsComponentSpec']['aviComponents']['aviSize']);
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviCertPath')) {
                        this.vsphereTkgsDataService.changeAviCertPath(input['tkgsComponentSpec']['aviComponents']['aviCertPath']);
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviCertKeyPath')) {
                        this.vsphereTkgsDataService.changeAviCertKeyPath(input['tkgsComponentSpec']['aviComponents']['aviCertKeyPath']);
                    }
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('aviMgmtNetwork')) {
                    if (input['tkgsComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkName')) {
                        this.vsphereTkgsDataService.changeAviSegment(
                            input['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName']);
                    }
                    if (input['tkgsComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkGatewayCidr')) {
                        this.vsphereTkgsDataService.changeAviGateway(
                            input['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkGatewayCidr']);
                    }
                    if (input['tkgsComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtServiceIpStartRange')) {
                        this.vsphereTkgsDataService.changeAviDhcpStart(
                            input['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtServiceIpStartRange']);
                    }
                    if (input['tkgsComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtServiceIpEndRange')) {
                        this.vsphereTkgsDataService.changeAviDhcpEnd(
                            input['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtServiceIpEndRange']);
                    }
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('tkgsVipNetwork')) {
                    if (input['tkgsComponentSpec']['tkgsVipNetwork'].hasOwnProperty('tkgsVipNetworkName')) {
                        this.vsphereTkgsDataService.changeAviClusterVipNetworkName(
                            input['tkgsComponentSpec']['tkgsVipNetwork']['tkgsVipNetworkName']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVipNetwork'].hasOwnProperty('tkgsVipNetworkGatewayCidr')) {
                        this.vsphereTkgsDataService.changeAviClusterVipGatewayIp(
                            input['tkgsComponentSpec']['tkgsVipNetwork']['tkgsVipNetworkGatewayCidr']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVipNetwork'].hasOwnProperty('tkgsVipIpStartRange')) {
                        this.vsphereTkgsDataService.changeAviClusterVipStartIp(
                            input['tkgsComponentSpec']['tkgsVipNetwork']['tkgsVipIpStartRange']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVipNetwork'].hasOwnProperty('tkgsVipIpEndRange')) {
                        this.vsphereTkgsDataService.changeAviClusterVipEndIp(
                            input['tkgsComponentSpec']['tkgsVipNetwork']['tkgsVipIpEndRange']);
                    }
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('tkgsMgmtNetworkSpec')) {
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkGatewayCidr')) {
                        this.vsphereTkgsDataService.changeMgmtGateway(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkGatewayCidr']);
                    }
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkName')) {
                        this.vsphereTkgsDataService.changeMgmtSegment(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkName']);
                    }
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkStartingIp')) {
                        this.vsphereTkgsDataService.changeMgmtStartIp(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkStartingIp']);
                    }
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkDnsServer')) {
                        this.vsphereTkgsDataService.changeMgmtDns(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkDnsServer']);
                    }
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkSearchDomains')) {
                        this.vsphereTkgsDataService.changeMgmtSearchDomain(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkSearchDomains']);
                    }
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkNtp')) {
                        this.vsphereTkgsDataService.changeMgmtNtp(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkNtp']);
                    }
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('tkgsPrimaryWorkloadNetwork')) {
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsPrimaryWorkloadNetworkGatewayCidr')) {
                        this.vsphereTkgsDataService.changeWrkGateway(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsPrimaryWorkloadNetworkGatewayCidr']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsPrimaryWorkloadNetworkName')) {
                        this.vsphereTkgsDataService.changeWrkSegment(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsPrimaryWorkloadNetworkName']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsPrimaryWorkloadNetworkStartRange')) {
                        this.vsphereTkgsDataService.changeWrkStartIp(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsPrimaryWorkloadNetworkStartRange']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsPrimaryWorkloadNetworkEndRange')) {
                        this.vsphereTkgsDataService.changeWrkEndIp(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsPrimaryWorkloadNetworkEndRange']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsWorkloadDnsServer')) {
                        this.vsphereTkgsDataService.changeWrkDns(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsWorkloadDnsServer']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsWorkloadServiceCidr')) {
                        if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsWorkloadServiceCidr'] !== '') {
                            this.vsphereTkgsDataService.changeWrkServiceCidr(
                                input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsWorkloadServiceCidr']);
                        }
                    }
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('tkgsStoragePolicySpec')) {
                    if (input['tkgsComponentSpec']['tkgsStoragePolicySpec'].hasOwnProperty('masterStoragePolicy')) {
                        this.vsphereTkgsDataService.changeMasterStoragePolicy(
                            input['tkgsComponentSpec']['tkgsStoragePolicySpec']['masterStoragePolicy']);
                    }
                    if (input['tkgsComponentSpec']['tkgsStoragePolicySpec'].hasOwnProperty('ephemeralStoragePolicy')) {
                        this.vsphereTkgsDataService.changeEphemeralStoragePolicy(
                            input['tkgsComponentSpec']['tkgsStoragePolicySpec']['ephemeralStoragePolicy']);
                    }
                    if (input['tkgsComponentSpec']['tkgsStoragePolicySpec'].hasOwnProperty('imageStoragePolicy')) {
                        this.vsphereTkgsDataService.changeImageStoragePolicy(
                            input['tkgsComponentSpec']['tkgsStoragePolicySpec']['imageStoragePolicy']);
                    }
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('tkgsVsphereNamespaceSpec')) {
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceName')) {
                        this.vsphereTkgsDataService.changeNamespaceName(
                            input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceName']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceDescription')) {
                        this.vsphereTkgsDataService.changeNamespaceDescription(
                            input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceDescription']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceWorkloadNetwork')) {
                        this.vsphereTkgsDataService.changeNamespaceSegment(
                            input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceWorkloadNetwork']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceContentLibrary')) {
                        this.vsphereTkgsDataService.changeNamespaceContentLib(
                            input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceContentLibrary']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceVmClasses')) {
                        this.vsphereTkgsDataService.changeNamespaceVmClass(
                            input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceVmClasses']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceResourceSpec')) {
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec'].hasOwnProperty('cpuLimit')) {
                            this.vsphereTkgsDataService.changeCpuLimit(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec']['cpuLimit']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec'].hasOwnProperty('memoryLimit')) {
                            this.vsphereTkgsDataService.changeMemLimit(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec']['memoryLimit']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec'].hasOwnProperty('storageRequestLimit')) {
                            this.vsphereTkgsDataService.changeStorageLimit(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec']['storageRequestLimit']);
                        }
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceStorageSpec')) {
                        // tslint:disable-next-line:max-line-length
                        const storagePolicy: Map<string, string> = new Map<string, string>();
                        let policyName;
                        let policyLimit;
                        let inputVal = input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceStorageSpec'];
                        // tslint:disable-next-line:max-line-length
                        for(const spec in inputVal) {
                            if (inputVal[spec].hasOwnProperty('storagePolicy') &&
                                inputVal[spec].hasOwnProperty('storageLimit')) {
                                policyName = inputVal[spec]['storagePolicy'];
                                policyLimit = inputVal[spec]['storageLimit'];
                                storagePolicy.set(policyName, policyLimit);
                            } else if (inputVal[spec].hasOwnProperty('storagePolicy')) {
                                policyName = inputVal[spec]['storagePolicy'];
                                storagePolicy.set(policyName, "");
                            }
                        }
                        this.vsphereTkgsDataService.changeStorageSpec(storagePolicy);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereWorkloadClusterSpec')) {
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgsVsphereNamespaceName')) {
                            this.vsphereTkgsDataService.changeWrkNamespaceName(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgsVsphereWorkloadClusterName')) {
                            this.vsphereTkgsDataService.changeWrkClusterName(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterName']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('allowedStorageClasses')) {
                            this.vsphereTkgsDataService.changeAllowedStorageClass(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['allowedStorageClasses']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('defaultStorageClass')) {
                            this.vsphereTkgsDataService.changeDefaultStorageClass(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['defaultStorageClass']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('nodeStorageClass')) {
                            this.vsphereTkgsDataService.changeNodeStorageClass(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['nodeStorageClass']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('serviceCidrBlocks')) {
                            if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['serviceCidrBlocks'] !== '') {
                                this.vsphereTkgsDataService.changeServiceCidr(
                                    input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['serviceCidrBlocks']);
                            }
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('podCidrBlocks')) {
                            if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['podCidrBlocks'] !== '') {
                                this.vsphereTkgsDataService.changePodCidr(
                                    input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['podCidrBlocks']);
                            }
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('controlPlaneVmClass')) {
                            this.vsphereTkgsDataService.changeControlPlaneVmClass(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['controlPlaneVmClass']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('workerVmClass')) {
                            this.vsphereTkgsDataService.changeWorkerVmClass(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['workerVmClass']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('workerNodeCount')) {
                            this.vsphereTkgsDataService.changeWrkWorkerNodeCount(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['workerNodeCount']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('enableControlPlaneHa')) {
                            if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['enableControlPlaneHa'] === 'true') {
                                this.vsphereTkgsDataService.changeEnableHA(true);
                            } else {
                                this.vsphereTkgsDataService.changeEnableHA(false);
                            }
                        }
                        let tmcEnabled;
                        this.vsphereTkgsDataService.currentEnableTMC.subscribe(enableTmc => tmcEnabled = enableTmc);
                        if (tmcEnabled) {
                            if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgWorkloadTsmIntegration')) {
                                if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadTsmIntegration'] === 'true') {
                                    this.vsphereTkgsDataService.changeEnableTSM(true);
                                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('namespaceExclusions')) {
                                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['namespaceExclusions'].hasOwnProperty('exactName')) {
                                            this.vsphereTkgsDataService.changeTsmExactNamespaceExclusion(
                                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['namespaceExclusions']['exactName']);
                                        }
                                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['namespaceExclusions'].hasOwnProperty('startsWith')) {
                                            this.vsphereTkgsDataService.changeTsmStartsWithNamespaceExclusion(
                                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['namespaceExclusions']['startsWith']);
                                        }
                                    }
                                } else {
                                    this.vsphereTkgsDataService.changeEnableTSM(false);
                                }
                            } else {
                                this.vsphereTkgsDataService.changeEnableTSM(false);
                            }
                        } else {
                            this.vsphereTkgsDataService.changeEnableTSM(false);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('controlPlaneVolumes')) {
                            // tslint:disable-next-line:max-line-length
                            const tkgsVolumes: Map<string, string> = new Map<string, string>();
                            let volumeName;
                            let volumeMount;
                            let volumeCapacity;
                            let inputVal = input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['controlPlaneVolumes'];
                            // tslint:disable-next-line:max-line-length
                            for(const spec in inputVal) {
                                if (inputVal[spec].hasOwnProperty('name') &&
                                    inputVal[spec].hasOwnProperty('mountPath') &&
                                    inputVal[spec].hasOwnProperty('storage')) {

                                    volumeName = inputVal[spec]['name'];
                                    volumeMount = inputVal[spec]['mountPath'];
                                    volumeCapacity = inputVal[spec]['storage'];
                                    let mountCap = volumeMount + ":" + volumeCapacity;
                                    tkgsVolumes.set(volumeName, mountCap);
                                }
                            }
                            this.apiClient.tkgsControlPlaneVolumes = tkgsVolumes;
                            this.vsphereTkgsDataService.changeTkgsControlVolumes(tkgsVolumes);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('workerVolumes')) {
                            // tslint:disable-next-line:max-line-length
                            const tkgsVolumes: Map<string, string> = new Map<string, string>();
                            let volumeName;
                            let volumeMount;
                            let volumeCapacity;
                            let inputVal = input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['workerVolumes'];
                            // tslint:disable-next-line:max-line-length
                            for(const spec in inputVal) {
                                if (inputVal[spec].hasOwnProperty('name') &&
                                    inputVal[spec].hasOwnProperty('mountPath') &&
                                    inputVal[spec].hasOwnProperty('storage')) {

                                    volumeName = inputVal[spec]['name'];
                                    volumeMount = inputVal[spec]['mountPath'];
                                    volumeCapacity = inputVal[spec]['storage'];
                                    let mountCap = volumeMount + ":" + volumeCapacity;
                                    tkgsVolumes.set(volumeName, mountCap);
                                }
                            }
                            this.apiClient.tkgsWorkerVolumes = tkgsVolumes;
                            this.vsphereTkgsDataService.changeTkgsWorkerVolumes(tkgsVolumes);
                        }
                    }
                }
            }
            if (input.hasOwnProperty('tanzuExtensions')) {
                if (input['tanzuExtensions'].hasOwnProperty('enableExtensions')) {
                    if (input['tanzuExtensions']['enableExtensions'] === 'true') {
                        this.vsphereTkgsDataService.changeEnableTanzuExtension(true);
                        if (input['tanzuExtensions'].hasOwnProperty('tkgClustersName')) {
                            this.vsphereTkgsDataService.changeTkgClusters(input['tanzuExtensions']['tkgClustersName']);
                            this.processEnableLogging(input, this.vsphereTkgsDataService);
                            this.processEnableMonitoring(input, this.vsphereTkgsDataService);
                        }
                    } else {
                        this.vsphereTkgsDataService.changeEnableTanzuExtension(false);
                        this.vsphereTkgsDataService.changeEnableLoggingExtension(false);
                        this.vsphereTkgsDataService.changeEnableMonitoringExtension(false);
                    }
                } else {
                    this.vsphereTkgsDataService.changeEnableTanzuExtension(false);
                    this.vsphereTkgsDataService.changeEnableLoggingExtension(false);
                    this.vsphereTkgsDataService.changeEnableMonitoringExtension(false);
                }
            }
        }
    }

    public setParamsFromInputJSONTkgsWcp(input) {
        if (input) {
            this.vsphereTkgsDataService.changeInputFileStatus(true);
            // Dumy Component
            if (input.hasOwnProperty('envSpec')) {
                if (input['envSpec'].hasOwnProperty('infraComponents')) {
                    if (input['envSpec']['infraComponents'].hasOwnProperty('dnsServersIp')) {
                        const dns = input['envSpec']['infraComponents']['dnsServersIp'];
                        this.vsphereTkgsDataService.changeDnsServer(dns);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('ntpServers')) {
                        const ntp = input['envSpec']['infraComponents']['ntpServers'];
                        this.vsphereTkgsDataService.changeNtpServer(ntp);
                    }
                    if (input['envSpec']['infraComponents'].hasOwnProperty('searchDomains')) {
                        const searchDomain = input['envSpec']['infraComponents'].searchDomains;
                        this.vsphereTkgsDataService.changeSearchDomain(searchDomain);
                    }
                }
                if (input['envSpec'].hasOwnProperty('vcenterDetails')) {
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterAddress')) {
                        this.vsphereTkgsDataService.changeVCAddress(input['envSpec']['vcenterDetails']['vcenterAddress']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoUser')) {
                        this.vsphereTkgsDataService.changeVCUser(input['envSpec']['vcenterDetails']['vcenterSsoUser']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoPasswordBase64')) {
                        this.vsphereTkgsDataService.changeVCPass(atob(input['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']));
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterDatastore')) {
                        this.vsphereTkgsDataService.changeDatastore(input['envSpec']['vcenterDetails']['vcenterDatastore']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterCluster')) {
                        this.vsphereTkgsDataService.changeCluster(input['envSpec']['vcenterDetails']['vcenterCluster']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterDatacenter')) {
                        this.vsphereTkgsDataService.changeDatacenter(input['envSpec']['vcenterDetails']['vcenterDatacenter']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('contentLibraryName')) {
                        if (input['envSpec']['vcenterDetails']['contentLibraryName'] !== '') {
                            this.vsphereTkgsDataService.changeIsMarketplace(false);
                        }
                        this.vsphereTkgsDataService.changeContentLib(
                            input['envSpec']['vcenterDetails']['contentLibraryName']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('aviOvaName')) {
                        if (input['envSpec']['vcenterDetails']['aviOvaName'] !== '') {
                            this.vsphereTkgsDataService.changeIsMarketplace(false);
                        }
                        this.vsphereTkgsDataService.changeOvaImage(
                            input['envSpec']['vcenterDetails']['aviOvaName']);
                    }
                }
                if (input['envSpec'].hasOwnProperty('marketplaceSpec')) {
                    if (input['envSpec']['marketplaceSpec'].hasOwnProperty('refreshToken')) {
                        if (input['envSpec']['vcenterDetails']['aviOvaName'] === '' &&
                            input['envSpec']['vcenterDetails']['contentLibraryName'] === '') {
                            if (input['envSpec']['marketplaceSpec']['refreshToken'] !== '') {
                                this.vsphereTkgsDataService.changeIsMarketplace(true);
                            }
                        }
                        this.vsphereTkgsDataService.changeMarketplaceRefreshToken(
                            input['envSpec']['marketplaceSpec']['refreshToken']);
                    }
                }
                if (input['envSpec'].hasOwnProperty('saasEndpoints')) {
                    if (input['envSpec']['saasEndpoints'].hasOwnProperty('tmcDetails')) {
                        if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcAvailability')) {
                            if (input['envSpec']['saasEndpoints']['tmcDetails']['tmcAvailability'] === 'true') {
                                this.apiClient.tmcEnabled = true;
                                this.vsphereTkgsDataService.changeEnableTMC(true);
                                if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcRefreshToken')) {
                                    this.vsphereTkgsDataService.changeApiToken(
                                        input['envSpec']['saasEndpoints']['tmcDetails']['tmcRefreshToken']);
                                }
                                if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcSupervisorClusterName')) {
                                    this.vsphereTkgsDataService.changeSupervisorClusterName(
                                        input['envSpec']['saasEndpoints']['tmcDetails']['tmcSupervisorClusterName']);
                                }
                            } else {
                                this.vsphereTkgsDataService.changeEnableTMC(false);
                                this.apiClient.toEnabled = false;
                                this.apiClient.tmcEnabled = false;
                                this.vsphereTkgsDataService.changeEnableTO(false);
                                this.vsphereTkgsDataService.changeEnableTSM(false);
                            }
                        }
                    }
                }
            }
            if (input.hasOwnProperty('tkgsComponentSpec')) {
                if (input['tkgsComponentSpec'].hasOwnProperty('controlPlaneSize')) {
                    this.vsphereTkgsDataService.changeControlPlaneSize(
                        input['tkgsComponentSpec']['controlPlaneSize']);
                }

                if (input['tkgsComponentSpec'].hasOwnProperty('aviComponents')) {
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController01Fqdn')) {
                        this.vsphereTkgsDataService.changeAviFqdn(
                            input['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']);
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController01Ip')) {
                        this.vsphereTkgsDataService.changeAviIp(
                            input['tkgsComponentSpec']['aviComponents']['aviController01Ip']);
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviPasswordBase64')) {
                        this.vsphereTkgsDataService.changeAviPassword(
                            atob(input['tkgsComponentSpec']['aviComponents']['aviPasswordBase64']));
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviBackupPassphraseBase64')) {
                        this.vsphereTkgsDataService.changeAviBackupPassword(
                            atob(input['tkgsComponentSpec']['aviComponents']['aviBackupPassphraseBase64']));
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('enableAviHa')) {
                        if(input['tkgsComponentSpec']['aviComponents']['enableAviHa'] === 'true') {
                            this.vsphereTkgsDataService.changeEnableAviHA(true);
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController02Fqdn')) {
                                this.vsphereTkgsDataService.changeAviFqdn02(
                                    input['tkgsComponentSpec']['aviComponents']['aviController02Fqdn']);
                            }
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController02Ip')) {
                                this.vsphereTkgsDataService.changeAviIp02(
                                    input['tkgsComponentSpec']['aviComponents']['aviController02Ip']);
                            }
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController03Fqdn')) {
                                this.vsphereTkgsDataService.changeAviFqdn03(
                                    input['tkgsComponentSpec']['aviComponents']['aviController03Fqdn']);
                            }
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviController03Ip')) {
                                this.vsphereTkgsDataService.changeAviIp03(
                                    input['tkgsComponentSpec']['aviComponents']['aviController03Ip']);
                            }
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviClusterIp')) {
                                this.vsphereTkgsDataService.changeAviClusterIp(
                                    input['tkgsComponentSpec']['aviComponents']['aviClusterIp']);
                            }
                            if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviClusterFqdn')) {
                                this.vsphereTkgsDataService.changeAviClusterFqdn(
                                    input['tkgsComponentSpec']['aviComponents']['aviClusterFqdn']);
                            }
                        } else {
                            this.vsphereTkgsDataService.changeEnableAviHA(false);
                        }
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviSize')) {
                        this.vsphereTkgsDataService.changeAviSize(input['tkgsComponentSpec']['aviComponents']['aviSize']);
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviCertPath')) {
                        this.vsphereTkgsDataService.changeAviCertPath(input['tkgsComponentSpec']['aviComponents']['aviCertPath']);
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviCertKeyPath')) {
                        this.vsphereTkgsDataService.changeAviCertKeyPath(input['tkgsComponentSpec']['aviComponents']['aviCertKeyPath']);
                    }
                    if (input['tkgsComponentSpec']['aviComponents'].hasOwnProperty('aviLicenseKey')) {
                        this.vsphereTkgsDataService.changeAviLicenseKey(input['tkgsComponentSpec']['aviComponents']['aviLicenseKey']);
                    }
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('aviMgmtNetwork')) {
                    if (input['tkgsComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkName')) {
                        this.vsphereTkgsDataService.changeAviSegment(
                            input['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName']);
                    }
                    if (input['tkgsComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtNetworkGatewayCidr')) {
                        this.vsphereTkgsDataService.changeAviGateway(
                            input['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkGatewayCidr']);
                    }
                    if (input['tkgsComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtServiceIpStartRange')) {
                        this.vsphereTkgsDataService.changeAviDhcpStart(
                            input['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtServiceIpStartRange']);
                    }
                    if (input['tkgsComponentSpec']['aviMgmtNetwork'].hasOwnProperty('aviMgmtServiceIpEndRange')) {
                        this.vsphereTkgsDataService.changeAviDhcpEnd(
                            input['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtServiceIpEndRange']);
                    }
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('tkgsVipNetwork')) {
                    if (input['tkgsComponentSpec']['tkgsVipNetwork'].hasOwnProperty('tkgsVipNetworkName')) {
                        this.vsphereTkgsDataService.changeAviClusterVipNetworkName(
                            input['tkgsComponentSpec']['tkgsVipNetwork']['tkgsVipNetworkName']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVipNetwork'].hasOwnProperty('tkgsVipNetworkGatewayCidr')) {
                        this.vsphereTkgsDataService.changeAviClusterVipGatewayIp(
                            input['tkgsComponentSpec']['tkgsVipNetwork']['tkgsVipNetworkGatewayCidr']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVipNetwork'].hasOwnProperty('tkgsVipIpStartRange')) {
                        this.vsphereTkgsDataService.changeAviClusterVipStartIp(
                            input['tkgsComponentSpec']['tkgsVipNetwork']['tkgsVipIpStartRange']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVipNetwork'].hasOwnProperty('tkgsVipIpEndRange')) {
                        this.vsphereTkgsDataService.changeAviClusterVipEndIp(
                            input['tkgsComponentSpec']['tkgsVipNetwork']['tkgsVipIpEndRange']);
                    }
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('tkgsMgmtNetworkSpec')) {
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkGatewayCidr')) {
                        this.vsphereTkgsDataService.changeMgmtGateway(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkGatewayCidr']);
                    }
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkName')) {
                        this.vsphereTkgsDataService.changeMgmtSegment(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkName']);
                    }
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkStartingIp')) {
                        this.vsphereTkgsDataService.changeMgmtStartIp(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkStartingIp']);
                    }
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkDnsServers')) {
                        this.vsphereTkgsDataService.changeMgmtDns(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkDnsServers']);
                    }
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkSearchDomains')) {
                        this.vsphereTkgsDataService.changeMgmtSearchDomain(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkSearchDomains']);
                    }
                    if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('tkgsMgmtNetworkNtpServers')) {
                        this.vsphereTkgsDataService.changeMgmtNtp(
                            input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkNtpServers']);
                    }
                }
                if (input['tkgsComponentSpec']['tkgsMgmtNetworkSpec'].hasOwnProperty('subscribedContentLibraryName')) {
                    this.vsphereTkgsDataService.changeSubsContentLibrary(
                        input['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['subscribedContentLibraryName']);
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('tkgsStoragePolicySpec')) {
                    if (input['tkgsComponentSpec']['tkgsStoragePolicySpec'].hasOwnProperty('masterStoragePolicy')) {
                        this.vsphereTkgsDataService.changeMasterStoragePolicy(
                           input['tkgsComponentSpec']['tkgsStoragePolicySpec']['masterStoragePolicy']);
                    }
                    if (input['tkgsComponentSpec']['tkgsStoragePolicySpec'].hasOwnProperty('ephemeralStoragePolicy')) {
                        this.vsphereTkgsDataService.changeEphemeralStoragePolicy(
                            input['tkgsComponentSpec']['tkgsStoragePolicySpec']['ephemeralStoragePolicy']);
                    }
                    if (input['tkgsComponentSpec']['tkgsStoragePolicySpec'].hasOwnProperty('imageStoragePolicy')) {
                        this.vsphereTkgsDataService.changeImageStoragePolicy(
                            input['tkgsComponentSpec']['tkgsStoragePolicySpec']['imageStoragePolicy']);
                    }
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('tkgsPrimaryWorkloadNetwork')) {
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsPrimaryWorkloadNetworkGatewayCidr')) {
                        this.vsphereTkgsDataService.changeWrkGateway(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsPrimaryWorkloadNetworkGatewayCidr']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsPrimaryWorkloadNetworkName')) {
                        this.vsphereTkgsDataService.changeWorkloadSegmentName(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsPrimaryWorkloadNetworkName']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsPrimaryWorkloadPortgroupName')) {
                        this.vsphereTkgsDataService.changeWrkSegment(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsPrimaryWorkloadPortgroupName']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsPrimaryWorkloadNetworkStartRange')) {
                        this.vsphereTkgsDataService.changeWrkStartIp(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsPrimaryWorkloadNetworkStartRange']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsPrimaryWorkloadNetworkEndRange')) {
                        this.vsphereTkgsDataService.changeWrkEndIp(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsPrimaryWorkloadNetworkEndRange']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsWorkloadDnsServers')) {
                        this.vsphereTkgsDataService.changeWrkDns(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsWorkloadDnsServers']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsWorkloadNtpServers')) {
                        this.vsphereTkgsDataService.changeWrkNtp(
                            input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsWorkloadNtpServers']);
                    }
                    if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'].hasOwnProperty('tkgsWorkloadServiceCidr')) {
                        if (input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsWorkloadServiceCidr'] !== '') {
                            this.vsphereTkgsDataService.changeWrkServiceCidr(
                                input['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork']['tkgsWorkloadServiceCidr']);
                        }
                    }
                }

                if(input['tkgsComponentSpec'].hasOwnProperty('tkgServiceConfig')) {
                    if(input['tkgsComponentSpec']['tkgServiceConfig'].hasOwnProperty('defaultCNI')) {
                        this.vsphereTkgsDataService.changeDefaultCNI(input['tkgsComponentSpec']['tkgServiceConfig']['defaultCNI']);
                    }

                    if (input['tkgsComponentSpec']['tkgServiceConfig'].hasOwnProperty('proxySpec')) {
                        if (input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'].hasOwnProperty('enableProxy')) {
                            if (input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['enableProxy'] === 'true') {
                                this.vsphereTkgsDataService.changeTkgsEnableProxy(true);
                                if (input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'].hasOwnProperty('httpProxy') &&
                                    input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'].hasOwnProperty('httpsProxy')) {
                                        this.processTkgsProxyParam(input);
                                    }
                                if (input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'].hasOwnProperty('noProxy')) {
                                    this.vsphereTkgsDataService.changeTkgsNoProxy(
                                        input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['noProxy']);
                                }
                                if(input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'].hasOwnProperty('proxyCert')) {
                                    this.vsphereTkgsDataService.changeTkgsProxyCert(
                                        input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['proxyCert']);
                                }
                            } else {
                                this.vsphereTkgsDataService.changeTkgsEnableProxy(false);
                            }
                        }
                    }

                    if(input['tkgsComponentSpec']['tkgServiceConfig'].hasOwnProperty('additionalTrustedCAs')) {
                        let additionalCert = new Map<string, string>();
                        if(input['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs'].hasOwnProperty('paths')) {
                            let paths = input['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs']['paths'];
                            for (let path in paths) {
                                additionalCert.set(paths[path], 'Path');
                            }
                        }
                        if(input['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs'].hasOwnProperty('endpointUrls')) {
                            let urls = input['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs']['endpointUrls'];
                            for (let url in urls) {
                                additionalCert.set(urls[url], 'Endpoint');
                            }
                        }
                        this.apiClient.tkgsAdditionalCerts = additionalCert;
                    }
                }
            }
        }
    }

    public setParamsFromInputJSONTkgsNamespace(input) {
        if (input) {
            this.vsphereTkgsDataService.changeInputFileStatus(true);
            if (input.hasOwnProperty('envSpec')) {
                if (input['envSpec'].hasOwnProperty('vcenterDetails')) {
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterAddress')) {
                        this.vsphereTkgsDataService.changeVCAddress(input['envSpec']['vcenterDetails']['vcenterAddress']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoUser')) {
                        this.vsphereTkgsDataService.changeVCUser(input['envSpec']['vcenterDetails']['vcenterSsoUser']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterSsoPasswordBase64')) {
                        this.vsphereTkgsDataService.changeVCPass(atob(input['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']));
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterCluster')) {
                        this.vsphereTkgsDataService.changeCluster(input['envSpec']['vcenterDetails']['vcenterCluster']);
                    }
                    if (input['envSpec']['vcenterDetails'].hasOwnProperty('vcenterDatacenter')) {
                        this.vsphereTkgsDataService.changeDatacenter(input['envSpec']['vcenterDetails']['vcenterDatacenter']);
                    }
                }
                if (input['envSpec'].hasOwnProperty('saasEndpoints')) {
                    if (input['envSpec']['saasEndpoints'].hasOwnProperty('tmcDetails')) {
                        if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcAvailability')) {
                            // input['envSpec']['saasEndpoints']['tmcDetails']['tmcAvailability'] = 'false';
                            if (input['envSpec']['saasEndpoints']['tmcDetails']['tmcAvailability'] === 'true') {
                                this.vsphereTkgsDataService.changeEnableTMC(true);
                                this.apiClient.tmcEnabled = true;
                                if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcRefreshToken')) {
                                    this.vsphereTkgsDataService.changeApiToken(
                                        input['envSpec']['saasEndpoints']['tmcDetails']['tmcRefreshToken']);
                                }
                                if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcInstanceURL')) {
                                    this.vsphereTkgsDataService.changeInstanceUrl(
                                        input['envSpec']['saasEndpoints']['tmcDetails']['tmcInstanceURL']);
                                }
                                if (input['envSpec']['saasEndpoints']['tmcDetails'].hasOwnProperty('tmcSupervisorClusterName')) {
                                    this.vsphereTkgsDataService.changeSupervisorClusterName(
                                        input['envSpec']['saasEndpoints']['tmcDetails']['tmcSupervisorClusterName']);
                                }
                                if (input['envSpec']['saasEndpoints'].hasOwnProperty('tanzuObservabilityDetails')) {
                                    if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityAvailability')) {
                                        if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityAvailability'] === 'true') {
                                            this.vsphereTkgsDataService.changeEnableTO(true);
                                            this.apiClient.toEnabled = true;
                                            if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityUrl')) {
                                                this.vsphereTkgsDataService.changeTOUrl(
                                                    input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityUrl']);
                                            }
                                            if (input['envSpec']['saasEndpoints']['tanzuObservabilityDetails'].hasOwnProperty('tanzuObservabilityRefreshToken')) {
                                                this.vsphereTkgsDataService.changeTOApiToken(
                                                    input['envSpec']['saasEndpoints']['tanzuObservabilityDetails']['tanzuObservabilityRefreshToken']);
                                            }
                                        } else {
                                            this.apiClient.toEnabled = false;
                                            this.vsphereTkgsDataService.changeEnableTO(false);
                                        }
                                    }
                                }
                            } else {
                                this.vsphereTkgsDataService.changeEnableTMC(false);
                                this.apiClient.toEnabled = false;
                                this.apiClient.tmcEnabled = false;
                                this.vsphereTkgsDataService.changeEnableTO(false);
                                this.vsphereTkgsDataService.changeEnableTSM(false);
                            }
                        }
                    }
                }
            }
            // Dumy Component
            if (input.hasOwnProperty('tkgsComponentSpec')) {
                if (input['tkgsComponentSpec'].hasOwnProperty('tkgsWorkloadNetwork')) {
                    if (input['tkgsComponentSpec']['tkgsWorkloadNetwork'].hasOwnProperty('tkgsWorkloadNetworkGatewayCidr')) {
                        this.vsphereTkgsDataService.changeWrkGateway(
                            input['tkgsComponentSpec']['tkgsWorkloadNetwork']['tkgsWorkloadNetworkGatewayCidr']);
                    }
                    if (input['tkgsComponentSpec']['tkgsWorkloadNetwork'].hasOwnProperty('tkgsWorkloadNetworkName')) {
                        this.vsphereTkgsDataService.changeWorkloadSegmentName(
                            input['tkgsComponentSpec']['tkgsWorkloadNetwork']['tkgsWorkloadNetworkName']);
                    }
                    if (input['tkgsComponentSpec']['tkgsWorkloadNetwork'].hasOwnProperty('tkgsWorkloadPortgroupName')) {
                        this.vsphereTkgsDataService.changeWrkSegment(
                            input['tkgsComponentSpec']['tkgsWorkloadNetwork']['tkgsWorkloadPortgroupName']);
                    }
                    if (input['tkgsComponentSpec']['tkgsWorkloadNetwork'].hasOwnProperty('tkgsWorkloadNetworkStartRange')) {
                        this.vsphereTkgsDataService.changeWrkStartIp(
                            input['tkgsComponentSpec']['tkgsWorkloadNetwork']['tkgsWorkloadNetworkStartRange']);
                    }
                    if (input['tkgsComponentSpec']['tkgsWorkloadNetwork'].hasOwnProperty('tkgsWorkloadNetworkEndRange')) {
                        this.vsphereTkgsDataService.changeWrkEndIp(
                            input['tkgsComponentSpec']['tkgsWorkloadNetwork']['tkgsWorkloadNetworkEndRange']);
                    }
                    if (input['tkgsComponentSpec']['tkgsWorkloadNetwork'].hasOwnProperty('tkgsWorkloadServiceCidr')) {
                        if (input['tkgsComponentSpec']['tkgsWorkloadNetwork']['tkgsWorkloadServiceCidr'] !== '') {
                            this.vsphereTkgsDataService.changeWrkServiceCidr(
                                input['tkgsComponentSpec']['tkgsWorkloadNetwork']['tkgsWorkloadServiceCidr']);
                        }
                    }
                }
                if (input['tkgsComponentSpec'].hasOwnProperty('tkgsVsphereNamespaceSpec')) {
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceName')) {
                        this.vsphereTkgsDataService.changeNamespaceName(
                            input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceName']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceDescription')) {
                        this.vsphereTkgsDataService.changeNamespaceDescription(
                            input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceDescription']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceWorkloadNetwork')) {
                        this.vsphereTkgsDataService.changeNamespaceSegment(
                            input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceWorkloadNetwork']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceContentLibrary')) {
                        this.vsphereTkgsDataService.changeNamespaceContentLib(
                            input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceContentLibrary']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceVmClasses')) {
                        this.vsphereTkgsDataService.changeNamespaceVmClass(
                            input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceVmClasses']);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceResourceSpec')) {
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec'].hasOwnProperty('cpuLimit')) {
                            this.vsphereTkgsDataService.changeCpuLimit(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec']['cpuLimit']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec'].hasOwnProperty('memoryLimit')) {
                            this.vsphereTkgsDataService.changeMemLimit(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec']['memoryLimit']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec'].hasOwnProperty('storageRequestLimit')) {
                            this.vsphereTkgsDataService.changeStorageLimit(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceResourceSpec']['storageRequestLimit']);
                        }
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereNamespaceStorageSpec')) {
                        // tslint:disable-next-line:max-line-length
                        const storagePolicy: Map<string, string> = new Map<string, string>();
                        let policyName;
                        let policyLimit;
                        let inputVal = input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereNamespaceStorageSpec'];
                        // tslint:disable-next-line:max-line-length
                        for(const spec in inputVal) {
                            if (inputVal[spec].hasOwnProperty('storagePolicy') &&
                                inputVal[spec].hasOwnProperty('storageLimit')) {
                                policyName = inputVal[spec]['storagePolicy'];
                                policyLimit = inputVal[spec]['storageLimit'];
                                storagePolicy.set(policyName, policyLimit);
                            } else if (inputVal[spec].hasOwnProperty('storagePolicy')) {
                                policyName = inputVal[spec]['storagePolicy'];
                                storagePolicy.set(policyName, "");
                            }
                        }
                        this.vsphereTkgsDataService.changeStorageSpec(storagePolicy);
                    }
                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec'].hasOwnProperty('tkgsVsphereWorkloadClusterSpec')) {
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgsVsphereNamespaceName')) {
                            this.vsphereTkgsDataService.changeWrkNamespaceName(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgsVsphereWorkloadClusterName')) {
                            this.vsphereTkgsDataService.changeWrkClusterName(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterName']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('allowedStorageClasses')) {
                            this.vsphereTkgsDataService.changeAllowedStorageClass(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['allowedStorageClasses']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('defaultStorageClass')) {
                            this.vsphereTkgsDataService.changeDefaultStorageClass(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['defaultStorageClass']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('nodeStorageClass')) {
                            this.vsphereTkgsDataService.changeNodeStorageClass(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['nodeStorageClass']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgsVsphereWorkloadClusterVersion')) {
                            this.vsphereTkgsDataService.changeClusterVersion(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterVersion']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('serviceCidrBlocks')) {
                            if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['serviceCidrBlocks'] !== '') {
                                this.vsphereTkgsDataService.changeServiceCidr(
                                    input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['serviceCidrBlocks']);
                            }
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('podCidrBlocks')) {
                            if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['podCidrBlocks'] !== '') {
                                this.vsphereTkgsDataService.changePodCidr(
                                    input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['podCidrBlocks']);
                            }
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('controlPlaneVmClass')) {
                            this.vsphereTkgsDataService.changeControlPlaneVmClass(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['controlPlaneVmClass']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('workerVmClass')) {
                            this.vsphereTkgsDataService.changeWorkerVmClass(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['workerVmClass']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('workerNodeCount')) {
                            this.vsphereTkgsDataService.changeWrkWorkerNodeCount(
                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['workerNodeCount']);
                        }

                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('enableControlPlaneHa')) {
                            if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['enableControlPlaneHa'] === 'true') {
                                this.vsphereTkgsDataService.changeEnableHA(true);
                            } else {
                                this.vsphereTkgsDataService.changeEnableHA(false);
                            }
                        }
                        let tmcEnabled;
                        this.vsphereTkgsDataService.currentEnableTMC.subscribe(enableTmc => tmcEnabled = enableTmc);
                        if (tmcEnabled) {
                            if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgWorkloadTsmIntegration')) {
                                if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadTsmIntegration'] === 'true') {
                                    this.vsphereTkgsDataService.changeEnableTSM(true);
                                    if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('namespaceExclusions')) {
                                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['namespaceExclusions'].hasOwnProperty('exactName')) {
                                            this.vsphereTkgsDataService.changeTsmExactNamespaceExclusion(
                                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['namespaceExclusions']['exactName']);
                                        }
                                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['namespaceExclusions'].hasOwnProperty('startsWith')) {
                                            this.vsphereTkgsDataService.changeTsmStartsWithNamespaceExclusion(
                                                input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['namespaceExclusions']['startsWith']);
                                        }
                                    }
                                } else {
                                    this.vsphereTkgsDataService.changeEnableTSM(false);
                                }
                            } else {
                                this.vsphereTkgsDataService.changeEnableTSM(false);
                            }
                        } else {
                            this.vsphereTkgsDataService.changeEnableTSM(false);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('controlPlaneVolumes')) {
                            // tslint:disable-next-line:max-line-length
                            const tkgsVolumes: Map<string, string> = new Map<string, string>();
                            let volumeName;
                            let volumeMount;
                            let volumeCapacity;
                            let volumeStorageClass;
                            let inputVal = input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['controlPlaneVolumes'];
                            // tslint:disable-next-line:max-line-length
                            for(const spec in inputVal) {
                                if (inputVal[spec].hasOwnProperty('name') &&
                                    inputVal[spec].hasOwnProperty('mountPath') &&
                                    inputVal[spec].hasOwnProperty('storage')) {

                                    volumeName = inputVal[spec]['name'];
                                    volumeMount = inputVal[spec]['mountPath'];
                                    volumeCapacity = inputVal[spec]['storage'];

                                    let mountCap;
                                    volumeCapacity = volumeCapacity.split('Gi')[0];
                                    if (inputVal[spec].hasOwnProperty('storageClass')) {
                                        volumeStorageClass = inputVal[spec]['storageClass'];
                                        mountCap = volumeMount + ":" + volumeCapacity + "#" + volumeStorageClass;
                                    }
                                    else {
                                        volumeStorageClass = "";
                                        mountCap = volumeMount + ":" + volumeCapacity + "#" + volumeStorageClass;
                                    }
                                    tkgsVolumes.set(volumeName, mountCap);
                                }
                            }
                            this.apiClient.tkgsControlPlaneVolumes = tkgsVolumes;
                            this.vsphereTkgsDataService.changeTkgsControlVolumes(tkgsVolumes);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('workerVolumes')) {
                            // tslint:disable-next-line:max-line-length
                            const tkgsVolumes: Map<string, string> = new Map<string, string>();
                            let volumeName;
                            let volumeMount;
                            let volumeCapacity;
                            let volumeStorageClass;
                            let inputVal = input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['workerVolumes'];
                            // tslint:disable-next-line:max-line-length
                            for(const spec in inputVal) {
                                if (inputVal[spec].hasOwnProperty('name') &&
                                    inputVal[spec].hasOwnProperty('mountPath') &&
                                    inputVal[spec].hasOwnProperty('storage')) {

                                    volumeName = inputVal[spec]['name'];
                                    volumeMount = inputVal[spec]['mountPath'];
                                    volumeCapacity = inputVal[spec]['storage'];
                                    //Remove Gi from end
                                    volumeCapacity = volumeCapacity.split('Gi')[0];
                                    let mountCap;
                                    volumeCapacity = volumeCapacity.split('Gi')[0];
                                    if (inputVal[spec].hasOwnProperty('storageClass')) {
                                        volumeStorageClass = inputVal[spec]['storageClass'];
                                        mountCap = volumeMount + ":" + volumeCapacity + "#" + volumeStorageClass;
                                    }
                                    else {
                                        volumeStorageClass = "";
                                        mountCap = volumeMount + ":" + volumeCapacity + "#" + volumeStorageClass;
                                    }
                                    volumeStorageClass = inputVal[spec]['storageClass'];
                                    tkgsVolumes.set(volumeName, mountCap);
                                }
                            }
                            this.apiClient.tkgsWorkerVolumes = tkgsVolumes;
                            this.vsphereTkgsDataService.changeTkgsWorkerVolumes(tkgsVolumes);
                        }

                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgsWorkloadClusterGroupName')) {
                            this.vsphereTkgsDataService.changeWrkClusterGroupName(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgsWorkloadClusterGroupName']);
                        }
                        if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgsWorkloadEnableDataProtection')) {
                            if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgsWorkloadEnableDataProtection'] === 'true' && this.apiClient.tmcEnabled) {
                                this.vsphereTkgsDataService.changeWrkEnableDataProtection(true);
                                this.apiClient.wrkDataProtectionEnabled = true;
                                if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgWorkloadClusterCredential')) {
                                    this.vsphereTkgsDataService.changeWrkDataProtectionCreds(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterCredential'])
                                }
                                if (input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgWorkloadClusterBackupLocation')) {
                                    this.vsphereTkgsDataService.changeWrkDataProtectionTargetLocation(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterBackupLocation'])
                                }
                            } else {
                                this.vsphereTkgsDataService.changeWrkEnableDataProtection(false);
                                this.apiClient.wrkDataProtectionEnabled = false;
                            }
                        } else {
                            this.vsphereTkgsDataService.changeWrkEnableDataProtection(false);
                            this.apiClient.wrkDataProtectionEnabled = false;
                        }
                        if(!this.apiClient.tmcEnabled) {
                            if(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec'].hasOwnProperty('tkgWorkloadClusterVeleroDataProtection')) {
                                if(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('enableVelero')) {
                                    if(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection']['enableVelero'] === 'true') {
                                        this.vsphereTkgsDataService.changeWrkEnableVelero(true);
                                    }
                                } else {
                                    this.vsphereTkgsDataService.changeWrkEnableVelero(false);
                                }
                                if(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('username')) {
                                    this.vsphereTkgsDataService.changeWrkVeleroUsername(
                                        input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection']['username']);
                                }
                                if(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('passwordBase64')) {
                                    this.vsphereTkgsDataService.changeWrkVeleroPassword(
                                        atob(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection']['passwordBase64']));
                                }
                                if(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('bucketName')) {
                                    this.vsphereTkgsDataService.changeWrkVeleroBucketName(
                                        input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection']['bucketName']);
                                }
                                if(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('backupRegion')) {
                                    this.vsphereTkgsDataService.changeWrkVeleroRegion(
                                        input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection']['backupRegion']);
                                }
                                if(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('backupS3Url')) {
                                    this.vsphereTkgsDataService.changeWrkVeleroS3Url(
                                        input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection']['backupS3Url']);
                                }
                                if(input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection'].hasOwnProperty('backupPublicUrl')) {
                                    this.vsphereTkgsDataService.changeWrkVeleroPublicUrl(
                                        input['tkgsComponentSpec']['tkgsVsphereNamespaceSpec']['tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterVeleroDataProtection']['backupPublicUrl']);
                                }
                            } else {
                                this.vsphereTkgsDataService.changeWrkEnableVelero(false);
                            }
                        } else {
                            this.vsphereTkgsDataService.changeWrkEnableVelero(false);
                        }
                    }
                }
                if(input['tkgsComponentSpec'].hasOwnProperty('tkgServiceConfig')) {
                    if(input['tkgsComponentSpec']['tkgServiceConfig'].hasOwnProperty('defaultCNI')) {
                        this.vsphereTkgsDataService.changeDefaultCNI(input['tkgsComponentSpec']['tkgServiceConfig']['defaultCNI']);
                    }

                    if (input['tkgsComponentSpec']['tkgServiceConfig'].hasOwnProperty('proxySpec')) {
                        if (input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'].hasOwnProperty('enableProxy')) {
                            if (input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['enableProxy'] === 'true') {
                                this.vsphereTkgsDataService.changeTkgsEnableProxy(true);
                                if (input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'].hasOwnProperty('httpProxy') &&
                                    input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'].hasOwnProperty('httpsProxy')) {
                                        this.processTkgsProxyParam(input);
                                    }
                                if (input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'].hasOwnProperty('noProxy')) {
                                    this.vsphereTkgsDataService.changeTkgsNoProxy(
                                        input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['noProxy']);
                                }
                                if(input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'].hasOwnProperty('proxyCert')) {
                                    this.vsphereTkgsDataService.changeTkgsProxyCert(
                                        input['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['proxyCert']);
                                }
                            } else {
                                this.vsphereTkgsDataService.changeTkgsEnableProxy(false);
                            }
                        }
                    }

                    if(input['tkgsComponentSpec']['tkgServiceConfig'].hasOwnProperty('additionalTrustedCAs')) {
                        let additionalCert = new Map<string, string>();
                        if(input['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs'].hasOwnProperty('paths')) {
                            let paths = input['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs']['paths'];
                            for (let num in paths) {
                                additionalCert.set(paths[num], 'Path');
                            }
                        }
                        if(input['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs'].hasOwnProperty('endpointUrls')) {
                            let urls = input['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs']['endpointUrls'];
                            for (let num in urls) {
                                additionalCert.set(urls[num], 'Endpoint');
                            }
                        }
                        this.apiClient.tkgsAdditionalCerts = additionalCert;
                    }
                }
            }
            if (input.hasOwnProperty('tanzuExtensions')) {
                if (input['tanzuExtensions']['enableExtensions'] === 'true') {
                    if (input['tanzuExtensions'].hasOwnProperty('harborSpec')) {
                        if(input['tanzuExtensions']['harborSpec'].hasOwnProperty('enableHarborExtension')){
                            if(input['tanzuExtensions']['harborSpec']['enableHarborExtension'] === 'true'){
                                this.vsphereTkgsDataService.changeEnableHarbor(true);
                                if (input['tanzuExtensions']['harborSpec'].hasOwnProperty('harborFqdn')) {
                                    this.vsphereTkgsDataService.changeHarborFqdn(
                                        input['tanzuExtensions']['harborSpec']['harborFqdn']);
                                }
                                if (input['tanzuExtensions']['harborSpec'].hasOwnProperty('harborPasswordBase64')) {
                                    this.vsphereTkgsDataService.changeHarborPassword(
                                        atob(input['tanzuExtensions']['harborSpec']['harborPasswordBase64']));
                                }
                                if (input['tanzuExtensions']['harborSpec'].hasOwnProperty('harborCertPath')) {
                                    this.vsphereTkgsDataService.changeHarborCertPath(
                                        input['tanzuExtensions']['harborSpec']['harborCertPath']);
                                }
                                if (input['tanzuExtensions']['harborSpec'].hasOwnProperty('harborCertKeyPath')) {
                                    this.vsphereTkgsDataService.changeHarborCertKey(
                                        input['tanzuExtensions']['harborSpec']['harborCertKeyPath']);
                                }
                            }
                        }
                    } else {
                        this.vsphereTkgsDataService.changeEnableHarbor(false);
                    }
                }
                if (input['tanzuExtensions'].hasOwnProperty('enableExtensions')) {
                    if (input['tanzuExtensions']['enableExtensions'] === 'true') {
                        this.vsphereTkgsDataService.changeEnableTanzuExtension(true);
                        if (input['tanzuExtensions'].hasOwnProperty('tkgClustersName')) {
                            this.vsphereTkgsDataService.changeTkgClusters(input['tanzuExtensions']['tkgClustersName']);
                            this.processEnableLogging(input, this.vsphereTkgsDataService);
                            this.processEnableMonitoring(input, this.vsphereTkgsDataService);
                        }
                    } else {
                        this.vsphereTkgsDataService.changeEnableTanzuExtension(false);
                        this.vsphereTkgsDataService.changeEnableLoggingExtension(false);
                        this.vsphereTkgsDataService.changeEnableMonitoringExtension(false);
                    }
                } else {
                    this.vsphereTkgsDataService.changeEnableTanzuExtension(false);
                    this.vsphereTkgsDataService.changeEnableLoggingExtension(false);
                    this.vsphereTkgsDataService.changeEnableMonitoringExtension(false);
                }
            }
        }
    }

    public navigateToWizardWithoutUpload(): void {
        this.loading = true;
        this.noupload = true;
        this.inputFile = null;
        this.readFile = false;
        if (this.infraType === 'tkgm') {
            this.attachment.nativeElement.value = '';
        }
        this.fileUploaded = false;
        this.fileName = '';
        this.file = null;
        this.dataService.changeInputFileStatus(false);
        FormMetaDataStore.deleteAllSavedData();
        this.clusterType = 'management';
        if (this.infraType === PROVIDERS.TKGM) {
            if (this.provider === PROVIDERS.VSPHERE) this.router.navigate([APP_ROUTES.WIZARD_MGMT_CLUSTER]);
            else this.router.navigate([APP_ROUTES.VCD_WIZARD]);
        } else if (this.infraType === PROVIDERS.TKGS) {
            this.router.navigate([APP_ROUTES.TKGS_VSPHERE_WIZARD]);
        }
    }

    /**
     * @method navigateToWizard
     * @desc helper method to trigger router navigation to wizard
     * @param provider - the provider to load wizard for
     */
    public navigateToWizard(providerType: string): void {
        this.loading = true;
        this.showLoginLoader = true;
        this.clusterType = 'management';
        if (this.infraType === PROVIDERS.TKGM) {
            if (this.provider === PROVIDERS.VSPHERE){
                this.setParamsFromInputJSON(this.inputFile);
            } else if(this.provider === PROVIDERS.VCD) {
                this.setParamsFromInputJSONForVCD(this.inputFile);
            }
            FormMetaDataStore.deleteAllSavedData();
        } else if (this.infraType === PROVIDERS.TKGS) {
            if (this.apiClient.tkgsStage === 'wcp') {
                this.setParamsFromInputJSONTkgsWcp(this.inputFile);
                FormMetaDataStore.deleteAllSavedData();
            } else if(this.apiClient.tkgsStage === 'namespace') {
                this.setParamsFromInputJSONTkgsNamespace(this.inputFile);
                FormMetaDataStore.deleteAllSavedData();
            }
        }
        let wizard;
        switch (this.infraType) {
            case PROVIDERS.TKGM: {
                if (this.provider === PROVIDERS.VSPHERE){
                    wizard = APP_ROUTES.WIZARD_MGMT_CLUSTER;
                }
                else {
                    wizard = APP_ROUTES.VCD_WIZARD;
                }
                break;
            }
            case PROVIDERS.TKGS: {
                wizard = APP_ROUTES.TKGS_VSPHERE_WIZARD;
                break;
            }
        }
        this.router.navigate([wizard]);
    }

    public openFormPanel() {
    }

    public uploadFile(event) {
        if (!event || !event.target || !event.target.files || event.target.files.length === 0) {
            this.fileUploaded = false;
            this.noupload = true;
            return;
        }
        this.noupload = false;
        this.file = event.target.files[0];
        const file = this.file;
        const name = this.file.name;
        const lastDot = name.lastIndexOf('.');

        this.fileName = name.substring(0, lastDot);
        this.fileUploaded = true;
        const ext = name.substring(lastDot + 1);
        this.fileName = this.fileName + '.' + ext;

        const self = this;
        if (this.fileName !== '' && this.fileUploaded) {
            const reader = new FileReader();
            // tslint:disable-next-line:only-arrow-functions
            reader.readAsText(file, 'UTF-8');
            reader.onload = async function(evt) {
                if (typeof evt.target.result === 'string') {
                    self.inputFile = await (JSON.parse(evt.target.result));
                    if (await self.inputFile !== null) {
                        self.readFile = true;
                    }
                    await console.log(' ');
                }
            };
            // tslint:disable-next-line:only-arrow-functions
            reader.onerror = function(evt) {
                console.log('Error Reading Input File');
                self.inputFile = null;
            };
        } else {
        }
    }

    public removeFile() {
        if (this.fileName) {
            this.noupload = true;
            this.inputFile = null;
            this.readFile = false;
            if (this.infraType === 'tkgm') {
            this.attachment.nativeElement.value = '';
        }
            this.fileUploaded = false;
            this.fileName = '';
            this.file = null;
        }
    }
    getEnvType(): string {
        return this.apiClient.tkgsStage;
    }

    cardClick(nodeType: string) {
        if(nodeType === 'Enable Workload control plane') {
            this.apiClient.tkgsStage = 'wcp';
        } else if (nodeType === 'Namespace and Workload cluster'){
            this.apiClient.tkgsStage = 'namespace';
        } else {
            this.apiClient.tkgsStage = '';
        }
    }
}
