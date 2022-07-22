import { TkgEventType } from 'src/app/shared/service/Messenger';
/**
 * Angular Modules
 */
import { Component, OnInit, Input } from '@angular/core';
import {
    Validators,
    FormControl
} from '@angular/forms';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';

/**
 * App imports
 */
import { PROVIDERS, Providers } from '../../../../shared/constants/app.constants';
import { NodeType, vSphereNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';

import Broker from 'src/app/shared/service/broker';
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import { APIClient } from 'src/app/swagger/api-client.service';
import { Subscription } from "rxjs";
import { VsphereNsxtDataService } from "../../../../shared/service/vsphere-nsxt-data.service";

@Component({
    selector: 'app-extension-setting-step',
    templateUrl: './extension-step.component.html',
    styleUrls: ['./extension-step.component.scss']
})
export class ExtensionSettingComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    PROVIDERS: Providers = PROVIDERS;
    // loggingEndpoints  = ['Syslog', 'HTTP', 'Elastic Search', 'Kafka', 'Splunk'];
    loggingEndpoints  = ['Syslog', 'HTTP', 'Kafka'];
    syslogEndpointModes = ['tcp', 'udp'];
    // syslogEndpointFormat = ['rfc6587', 'rfc5424', 'rfc3164'];
    syslogEndpointFormat = ['rfc5424', 'rfc3164'];
    allClusters;
    mgmtCluster: string;
    sharedCluster: string;
    wrkCluster: string;
    selection: any;
    selected: any;
    displayLogging = true;

    subscription: Subscription;
    private uploadStatus = false;
    private enableTanzuExtensions;

    private tkgClusters;
    tkgClusterError = false;
    tkgClusterErrorMsg = 'The provided cluster names are not found, please select one from drop-down';

    private enableLogging;
    private enableMonitoring;
    private loggingEndpoint;
    loggingEndpointError = false;
    loggingEndpointErrorMsg = 'The provided Logging Endpoint value is invalid, please chose one from the drop-down';

    private syslogAddress;
    private syslogPort;
    private syslogMode;
    syslogModeError = false;
    syslogModeErrorMsg = 'The provided syslog mode is invalid, please chose one from below.';
    private syslogFormat;
    syslogFormatError = false;
    syslogFormatErrorMsg = 'The provided syslog format is invalid, please chose one from below.';

    private httpAddress;
    private httpPort;
    private httpUri;
    private httpHeaderKeyValue;
    private elasticSearchAddress;
    private elasticSearchPort;
    private kafkaBrokerServiceName;
    private kafkaTopicName;
    private splunkAddress;
    private splunkPort;
    private splunkToken;
    private prometheusFqdn;
    private prometheusCertPath;
    private prometheusCertKeyPath;
    private grafanaFqdn;
    private grafanaPassword;
    private grafanaCertPath;
    private grafanaCertKeyPath;


    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private dataService: VsphereNsxtDataService) {

            super();
    }

    ngOnInit() {
            super.ngOnInit();
            this.formGroup.addControl('tanzuExtensions', new FormControl(false));
            this.formGroup.addControl('tanzuExtensionClusters', new FormControl('', []));
            this.formGroup.addControl('enableLogging', new FormControl(false));
            this.formGroup.addControl('enableMonitoring', new FormControl(false));
            // Logging Fields
            this.formGroup.addControl('loggingEndpoint', new FormControl('', []));
            // Syslog Fields
            this.formGroup.addControl('syslogEndpointAddress', new FormControl('', []));
            this.formGroup.addControl('syslogEndpointFormat', new FormControl('', []));
            this.formGroup.addControl('syslogEndpointPort', new FormControl('', []));
            this.formGroup.addControl('syslogEndpointMode', new FormControl('', []));
            //HTTP Fields
            this.formGroup.addControl('httpEndpointAddress', new FormControl('', []));
            this.formGroup.addControl('httpEndpointPort', new FormControl('', []));
            this.formGroup.addControl('httpEndpointUri', new FormControl('', []));
            this.formGroup.addControl('httpEndpointHeaderKeyValue', new FormControl('', []));
            // Elastic Search Fields
            this.formGroup.addControl('elasticSearchAddress', new FormControl('', []));
            this.formGroup.addControl('elasticSearchPort', new FormControl('', []));
            // Kafka Fields
            this.formGroup.addControl('kafkaBrokerServiceName', new FormControl('', []));
            this.formGroup.addControl('kafkaTopicName', new FormControl('', []));
            // Splunk Fields
            this.formGroup.addControl('splunkAddress', new FormControl('', []));
            this.formGroup.addControl('splunkPort', new FormControl('', []));
            this.formGroup.addControl('splunkToken', new FormControl('', []));
            // Monitoring Fields
            this.formGroup.addControl('prometheusFqdn', new FormControl('', []));
            this.formGroup.addControl('prometheusCertPath', new FormControl('', []));
            this.formGroup.addControl('prometheusCertKeyPath', new FormControl('', []));
            this.formGroup.addControl('grafanaFqdn', new FormControl('', []));
            this.formGroup.addControl('grafanaCertPath', new FormControl('', []));
            this.formGroup.addControl('grafanaCertKeyPath', new FormControl('', []));
            this.formGroup.addControl('grafanaPassword', new FormControl('', []));
//             this.dataService.currentMgmtClusterName.subscribe(
//                 (mgmt) => this.mgmtCluster = mgmt);
            this.dataService.currentSharedClusterName.subscribe(
                (shared) => this.sharedCluster = shared);
            this.dataService.currentWrkClusterName.subscribe(
                (wrk) => this.wrkCluster = wrk);
            this.apiClient.allClusters = [this.sharedCluster, this.wrkCluster];

            this.formGroup['canMoveToNext'] = () => {
                this.toggleTanzuExtension();
                return this.formGroup.valid;
            };
            setTimeout(_ => {
                this.formGroup.get('syslogEndpointFormat').valueChanges.subscribe(
                    (data) => this.syslogFormatError = false);
                this.formGroup.get('syslogEndpointMode').valueChanges.subscribe(
                    (data) => this.syslogModeError = false);
                this.formGroup.get('tanzuExtensionClusters').valueChanges.subscribe(
                    (data) => this.apiClient.tkgClusterError = false);
                this.subscription = this.dataService.currentInputFileStatus.subscribe(
                    (uploadStatus) => this.uploadStatus = uploadStatus);
                if (this.uploadStatus) {
                    this.subscription = this.dataService.currentEnableTanzuExtension.subscribe(
                        (enableTanzuExtensions) => this.enableTanzuExtensions = enableTanzuExtensions);
                    this.formGroup.get('tanzuExtensions').setValue(this.enableTanzuExtensions);
                    this.subscription = this.dataService.currentTkgClusters.subscribe(
                        (tkgClusters) => this.tkgClusters = tkgClusters);

                    if (this.enableTanzuExtensions) {
                        this.toggleTanzuExtension();
                        if (this.apiClient.allClusters.indexOf(this.tkgClusters) === -1) {
                            this.apiClient.tkgClusterError = true;
                        } else {
                            this.apiClient.tkgClusterError = false;
                            this.formGroup.get('tanzuExtensionClusters').setValue(this.tkgClusters);
                        }
                    }
                    if (!this.apiClient.toEnabled) {
                        this.subscription = this.dataService.currentEnableMonitoringExtension.subscribe(
                            (enableMonitoring) => this.enableMonitoring = enableMonitoring);
                        this.formGroup.get('enableMonitoring').setValue(this.enableMonitoring);
                        if (this.enableMonitoring) {
                            this.toggleEnableMonitoring();
                            this.subscription = this.dataService.currentPrometheusFqdn.subscribe(
                                (prometheusFqdn) => this.prometheusFqdn = prometheusFqdn);
                            this.formGroup.get('prometheusFqdn').setValue(this.prometheusFqdn);
                            this.subscription = this.dataService.currentPrometheusCertPath.subscribe(
                                (prometheusCertPath) => this.prometheusCertPath = prometheusCertPath);
                            this.formGroup.get('prometheusCertPath').setValue(this.prometheusCertPath);
                            this.subscription = this.dataService.currentPrometheusCertkeyPath.subscribe(
                                (prometheusCertKeyPath) => this.prometheusCertKeyPath = prometheusCertKeyPath);
                            this.formGroup.get('prometheusCertKeyPath').setValue(this.prometheusCertKeyPath);
                            this.subscription = this.dataService.currentGrafanaFqdn.subscribe(
                                (grafanaFqdn) => this.grafanaFqdn = grafanaFqdn);
                            this.formGroup.get('grafanaFqdn').setValue(this.grafanaFqdn);
                            this.subscription = this.dataService.currentGrafanaPassword.subscribe(
                                (grafanaPassword) => this.grafanaPassword = grafanaPassword);
                            this.formGroup.get('grafanaPassword').setValue(this.grafanaPassword);
                            this.subscription = this.dataService.currentGrafanaCertPath.subscribe(
                                (grafanaCertPath) => this.grafanaCertPath = grafanaCertPath);
                            this.formGroup.get('grafanaCertPath').setValue(this.grafanaCertPath);
                            this.subscription = this.dataService.currentGrafanaCertKeyPath.subscribe(
                                (grafanaCertKeyPath) => this.grafanaCertKeyPath = grafanaCertKeyPath);
                            this.formGroup.get('grafanaCertKeyPath').setValue(this.grafanaCertKeyPath);
                        }
                    }
                    this.subscription = this.dataService.currentEnableLoggingExtension.subscribe(
                        (enableLogging) => this.enableLogging = enableLogging);
                    this.formGroup.get('enableLogging').setValue(this.enableLogging);
                    if (this.enableLogging) {
                        this.toggleEnableLogging();
                    }
                    this.subscription = this.dataService.currentLoggingEndpoint.subscribe(
                        (loggingEndpoint) => this.loggingEndpoint = loggingEndpoint);
                    if (this.enableLogging) {
                        if (this.loggingEndpoints.indexOf(this.loggingEndpoint) === -1) {
                            this.loggingEndpointError = true;
                        } else {
                            this.loggingEndpointError = false;
                            this.formGroup.get('loggingEndpoint').setValue(this.loggingEndpoint);
                            this.setLoggingEndpoint();
                            this.subscription = this.dataService.currentSyslogAddress.subscribe(
                                (syslogAddress) => this.syslogAddress = syslogAddress);
                            this.formGroup.get('syslogEndpointAddress').setValue(this.syslogAddress);
                            this.subscription = this.dataService.currentSyslogPort.subscribe(
                                (syslogPort) => this.syslogPort = syslogPort);
                            this.formGroup.get('syslogEndpointPort').setValue(this.syslogPort);
                            // TODO: Add Check for Format and Mode Here
                            this.subscription = this.dataService.currentSyslogMode.subscribe(
                                (syslogMode) => this.syslogMode = syslogMode);
                            if (this.loggingEndpoint === 'Syslog') {
                                if (this.syslogEndpointModes.indexOf(this.syslogMode) === -1) {
                                    this.syslogModeError = true;
                                } else {
                                    this.syslogModeError = false;
                                    this.formGroup.get('syslogEndpointMode').setValue(this.syslogMode);
                                }
                            }
                            this.subscription = this.dataService.currentSyslogFormat.subscribe(
                                (syslogFormat) => this.syslogFormat = syslogFormat);
                            if (this.loggingEndpoint === 'Syslog') {
                                if (this.syslogEndpointFormat.indexOf(this.syslogFormat) === -1) {
                                    this.syslogFormatError = true;
                                } else {
                                    this.syslogFormatError = false;
                                    this.formGroup.get('syslogEndpointFormat').setValue(this.syslogFormat);
                                }
                            }
                            this.subscription = this.dataService.currentHttpAddress.subscribe(
                                (httpAddress) => this.httpAddress = httpAddress);
                            this.formGroup.get('httpEndpointAddress').setValue(this.httpAddress);
                            this.subscription = this.dataService.currentHttpPort.subscribe(
                                (httpPort) => this.httpPort = httpPort);
                            this.formGroup.get('httpEndpointPort').setValue(this.httpPort);
                            this.subscription = this.dataService.currentHttpUri.subscribe(
                                (httpUri) => this.httpUri = httpUri);
                            this.formGroup.get('httpEndpointUri').setValue(this.httpUri);
                            this.subscription = this.dataService.currentHttpHeaderKey.subscribe(
                                (httpHeaderKeyValue) => this.httpHeaderKeyValue = httpHeaderKeyValue);
                            this.formGroup.get('httpEndpointHeaderKeyValue').setValue(this.httpHeaderKeyValue);
//                             this.subscription = this.dataService.currentElasticSearchAddress.subscribe(
//                                 (elasticSearchAddress) => this.elasticSearchAddress = elasticSearchAddress);
//                             this.formGroup.get('elasticSearchAddress').setValue(this.elasticSearchAddress);
//                             this.subscription = this.dataService.currentElasticSearchPort.subscribe(
//                                 (elasticSearchPort) => this.elasticSearchPort = elasticSearchPort);
//                             this.formGroup.get('elasticSearchPort').setValue(this.elasticSearchPort);
                            this.subscription = this.dataService.currentKafkaServiceName.subscribe(
                                (kafkaBrokerServiceName) => this.kafkaBrokerServiceName = kafkaBrokerServiceName);
                            this.formGroup.get('kafkaBrokerServiceName').setValue(this.kafkaBrokerServiceName);
                            this.subscription = this.dataService.currentKafkaTopicName.subscribe(
                                (kafkaTopicName) => this.kafkaTopicName = kafkaTopicName);
                            this.formGroup.get('kafkaTopicName').setValue(this.kafkaTopicName);
//                             this.subscription = this.dataService.currentSplunkAddress.subscribe(
//                                 (splunkAddress) => this.splunkAddress = splunkAddress);
//                             this.formGroup.get('splunkAddress').setValue(this.splunkAddress);
//                             this.subscription = this.dataService.currentSplunkPort.subscribe(
//                                 (splunkPort) => this.splunkPort = splunkPort);
//                             this.formGroup.get('splunkPort').setValue(this.splunkPort);
//                             this.subscription = this.dataService.currentSplunkToken.subscribe(
//                                 (splunkToken) => this.splunkToken = splunkToken);
//                             this.formGroup.get('splunkToken').setValue(this.splunkToken);
                        }
                    }
                }
            });
        }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // don't fill password field with ****
        if (!this.uploadStatus) {
            this.formGroup.get('tanzuExtensions').setValue(false);
            this.formGroup.get('grafanaPassword').setValue('');
        } else {

        }
    }

    validateCluster() {
        let clusterArray = this.formGroup.get('tanzuExtensionClusters').value.split(',');
        if (clusterArray.length === 1) {
            if (this.apiClient.allClusters.indexOf(clusterArray[0]) === -1) {
                this.apiClient.tkgClusterError = true;
            } else {
                this.apiClient.tkgClusterError = false;
                this.formGroup.get('tanzuExtensionClusters').setValue(this.tkgClusters);
            }
        } else if (clusterArray.length === 2) {
            if ((this.apiClient.allClusters.indexOf(clusterArray[0]) === -1) && (this.apiClient.allClusters.indexOf(clusterArray[1]) === -1)) {
                this.apiClient.tkgClusterError = true;
            } else {
                this.apiClient.tkgClusterError = false;
                this.formGroup.get('tanzuExtensionClusters').setValue(this.tkgClusters);
            }
        } else if (clusterArray.length > 2){
            this.apiClient.tkgClusterError = true;
        }
    }

    toggleTanzuExtension() {
        const enableExtensionFields = [
            'tanzuExtensionClusters',
            'loggingEndpoint',
            'syslogEndpointAddress',
            'syslogEndpointFormat',
            'syslogEndpointPort',
            'syslogEndpointMode',
            'httpEndpointAddress',
            'httpEndpointPort',
            'httpEndpointUri',
            'httpEndpointHeaderKeyValue',
            'kafkaBrokerServiceName',
            'kafkaTopicName',
            'prometheusFqdn',
            'prometheusCertPath',
            'prometheusCertKeyPath',
            'grafanaFqdn',
            'grafanaCertPath',
            'grafanaCertKeyPath',
            'grafanaPassword',
            'enableMonitoring',
            'enableLogging',
        ];
        if (this.formGroup.get('tanzuExtensions').value) {
            this.resurrectField('tanzuExtensionClusters', [Validators.required], this.formGroup.value['tanzuExtensionClusters']);
//             this.formGroup.get('tanzuExtensionClusters').setValue(
//                 (this.sharedCluster + ', ' + this.wrkCluster));
        } else {
            enableExtensionFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }
    setLoggingEndpoint() {
        const syslogFields = [
            'syslogEndpointAddress',
            'syslogEndpointFormat',
            'syslogEndpointPort',
            'syslogEndpointMode',
        ];
        const httpFields = [
            'httpEndpointAddress',
            'httpEndpointPort',
            'httpEndpointUri',
            'httpEndpointHeaderKeyValue',
        ];
        const elasticSearchFields = [
            'elasticSearchAddress',
            'elasticSearchPort',
        ];
        const kafkaFields = [
            'kafkaBrokerServiceName',
            'kafkaTopicName',
        ];
        const splunkFields = [
            'splunkAddress',
            'splunkPort',
            'splunkToken',
        ];
        if (this.formGroup.get('loggingEndpoint').value === 'Syslog') {
            this.resurrectField('syslogEndpointAddress', [
                Validators.required, this.validationService.isValidIpOrFqdn(), this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['syslogEndpointAddress']);
            this.resurrectField('syslogEndpointFormat', [Validators.required],
                this.formGroup.value['syslogEndpointFormat']);
            this.resurrectField('syslogEndpointPort', [
                Validators.required, this.validationService.isValidPort(), this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['syslogEndpointPort']);
            this.resurrectField('syslogEndpointMode', [Validators.required],
                this.formGroup.value['syslogEndpointMode']);
            httpFields.forEach((field) => {this.disarmField(field, true);
            });
            elasticSearchFields.forEach((field) => {this.disarmField(field, true);
            });
            kafkaFields.forEach((field) => {this.disarmField(field, true);
            });
            splunkFields.forEach((field) => {this.disarmField(field, true);
            });
        } else if (this.formGroup.get('loggingEndpoint').value === 'HTTP') {
            this.resurrectField('httpEndpointAddress', [
                Validators.required, this.validationService.isValidIpOrFqdn(), this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['httpEndpointAddress']);
            this.resurrectField('httpEndpointPort', [
                Validators.required, this.validationService.isValidPort(), this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['httpEndpointPort']);
            this.resurrectField('httpEndpointUri', [
                Validators.required, this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['httpEndpointUri']);
            this.resurrectField('httpEndpointHeaderKeyValue', [Validators.required, this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['httpEndpointHeaderKeyValue']);
            syslogFields.forEach((field) => {this.disarmField(field, true);
            });
            elasticSearchFields.forEach((field) => {this.disarmField(field, true);
            });
            kafkaFields.forEach((field) => {this.disarmField(field, true);
            });
            splunkFields.forEach((field) => {this.disarmField(field, true);
            });
        } else if (this.formGroup.get('loggingEndpoint').value === 'Elastic Search') {
            this.resurrectField('elasticSearchAddress', [
                Validators.required, this.validationService.isValidIpOrFqdn(), this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['elasticSearchAddress']);
            this.resurrectField('elasticSearchPort', [
                Validators.required, this.validationService.isValidPort(), this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['elasticSearchPort']);
            syslogFields.forEach((field) => {this.disarmField(field, true);
            });
            httpFields.forEach((field) => {this.disarmField(field, true);
            });
            kafkaFields.forEach((field) => {this.disarmField(field, true);
            });
            splunkFields.forEach((field) => {this.disarmField(field, true);
            });
        } else if (this.formGroup.get('loggingEndpoint').value === 'Kafka') {
            this.resurrectField('kafkaBrokerServiceName', [Validators.required, this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['kafkaBrokerServiceName']);
            this.resurrectField('kafkaTopicName', [Validators.required, this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['kafkaTopicName']);
            syslogFields.forEach((field) => {this.disarmField(field, true);
            });
            httpFields.forEach((field) => {this.disarmField(field, true);
            });
            elasticSearchFields.forEach((field) => {this.disarmField(field, true);
            });
            splunkFields.forEach((field) => {this.disarmField(field, true);
            });
        } else if (this.formGroup.get('loggingEndpoint').value === 'Splunk') {
            this.resurrectField('splunkAddress', [
                Validators.required, this.validationService.isValidIpOrFqdn(), this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['splunkAddress']);
            this.resurrectField('splunkPort', [
                Validators.required, this.validationService.isValidPort(), this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['splunkPort']);
            this.resurrectField('splunkToken', [Validators.required, this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['splunkToken']);
            syslogFields.forEach((field) => {this.disarmField(field, true);
            });
            httpFields.forEach((field) => {this.disarmField(field, true);
            });
            elasticSearchFields.forEach((field) => {this.disarmField(field, true);
            });
            kafkaFields.forEach((field) => {this.disarmField(field, true);
            });
        } else {
            syslogFields.forEach((field) => {this.disarmField(field, true);
            });
            httpFields.forEach((field) => {this.disarmField(field, true);
            });
            elasticSearchFields.forEach((field) => {this.disarmField(field, true);
            });
            kafkaFields.forEach((field) => {this.disarmField(field, true);
            });
            splunkFields.forEach((field) => {this.disarmField(field, true);
            });
        }
    }

    toggleEnableLogging() {
        const enableLoggingFields = [
            'loggingEndpoint',
            'syslogEndpointAddress',
            'syslogEndpointFormat',
            'syslogEndpointPort',
            'syslogEndpointMode',
            'httpEndpointAddress',
            'httpEndpointPort',
            'httpEndpointUri',
            'httpEndpointHeaderKeyValue',
            'kafkaBrokerServiceName',
            'kafkaTopicName',
        ];
        if (this.formGroup.get('enableLogging').value) {
            this.resurrectField('loggingEndpoint', [Validators.required],
            this.formGroup.value['loggingEndpoint']);
        } else {
            enableLoggingFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    toggleEnableMonitoring() {
        const enableMonitoringFields = [
            'prometheusFqdn',
            'prometheusCertPath',
            'prometheusCertKeyPath',
            'grafanaFqdn',
            'grafanaCertPath',
            'grafanaCertKeyPath',
            'grafanaPassword',
        ];
        if (this.formGroup.get('enableMonitoring').value) {
            this.resurrectField('prometheusFqdn', [
                Validators.required, this.validationService.isValidFqdn(), this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['prometheusFqdn']);
            this.resurrectField('prometheusCertPath', [
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['prometheusCertPath']);
            this.resurrectField('prometheusCertKeyPath', [
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['prometheusCertKeyPath']);
            this.resurrectField('grafanaFqdn', [
                Validators.required, this.validationService.isValidFqdn(), this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['grafanaFqdn']);
            this.resurrectField('grafanaCertPath', [
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['grafanaCertPath']);
            this.resurrectField('grafanaCertKeyPath', [
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.value['grafanaCertKeyPath']);
            this.resurrectField('grafanaPassword', [
                Validators.required], this.formGroup.value['grafanaPassword']);
        } else {
            enableMonitoringFields.forEach((field) => {this.disarmField(field, true);
            });
        }
    }
}