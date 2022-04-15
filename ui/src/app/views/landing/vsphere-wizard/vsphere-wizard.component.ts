/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { Component, ElementRef, Input, OnInit, ViewChild } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';
import { Netmask } from 'netmask';
import {saveAs as importedSaveAs} from "file-saver";
import {ClrLoadingState} from '@clr/angular';

// Third party imports
import { Observable } from 'rxjs';

// App imports
import { FormMetaDataService } from 'src/app/shared/service/form-meta-data.service';
import { PROVIDERS, Providers } from '../../../shared/constants/app.constants';
import { APP_ROUTES, Routes } from '../../../shared/constants/routes.constants';
import { AppDataService } from '../../../shared/service/app-data.service';
import { DataService } from '../../../shared/service/data.service';
import { VMCDataService } from '../../../shared/service/vmc-data.service';
import { VsphereNsxtDataService } from '../../../shared/service/vsphere-nsxt-data.service';
import { VsphereTkgsService } from '../../../shared/service/vsphere-tkgs-data.service';
import { APIClient } from '../../../swagger/api-client.service';
import { ViewJSONModalComponent } from 'src/app/views/landing/wizard/shared/components/modals/view-json-modal/view-json-modal.component';
import { WizardBaseDirective } from '../wizard/shared/wizard-base/wizard-base';

@Component({
    selector: 'app-wizard',
    templateUrl: './vsphere-wizard.component.html',
    styleUrls: ['./vsphere-wizard.component.scss'],
})
export class VSphereWizardComponent extends WizardBaseDirective implements OnInit {
    @ViewChild(ViewJSONModalComponent) viewJsonModal: ViewJSONModalComponent;
    @ViewChild('attachments') attachment: any;
    @Input() public form;
    @Input() public AVIFormValid;
    @Input() public providerType = 'vsphere';
    @Input() public infraType = 'tkgm';
    public APP_ROUTES: Routes = APP_ROUTES;
    public PROVIDERS: Providers = PROVIDERS;

    public datacenterMoid: Observable<string>;
    public deploymentPending = false;
    public disableDeployButton = false;
    public showAwsTestMessage = false;
    public showIPValidationSuccess = false;
    public errorNotification: string;
    public successNotification: string;
    public filePath: string;
    public show = false;

    public displayWizard = false;
    public fileName: string;
    public fileUploaded = false;
    public file: File;
    public generatedFileName: string;
    public logFileName = 'service_installer_log_bundle';
    public jsonWizard = false;

    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    constructor(
        public apiClient: APIClient,
        router: Router,
        private appDataService: AppDataService,
        private formBuilder: FormBuilder,
        formMetaDataService: FormMetaDataService,
        dataService: DataService,
        vmcDataService: VMCDataService,
        nsxtDataService: VsphereNsxtDataService,
        vsphereTkgsDataService: VsphereTkgsService,
        titleService: Title,
        el: ElementRef) {

        super(router, el, formMetaDataService, titleService, dataService, vmcDataService, nsxtDataService, vsphereTkgsDataService);

        this.form = this.formBuilder.group({
            vsphereProviderForm: this.formBuilder.group({
            }),
            // tslint:disable-next-line:object-literal-sort-keys
            vsphereInfraDetailsForm: this.formBuilder.group({
            }),
            vsphereMgmtNodeSettingForm: this.formBuilder.group({
            }),
            vsphereSharedServiceNodeSettingForm: this.formBuilder.group({
            }),
            vsphereWorkloadNodeSettingForm: this.formBuilder.group({
            }),
            vsphereAVINetworkSettingForm: this.formBuilder.group({
            }),
            extensionSettingForm: this.formBuilder.group({
            }),
            TKGMgmtDataNWForm: this.formBuilder.group({
            }),
            TKGWorkloadDataNWForm: this.formBuilder.group({
            }),
            tanzuSaasSettingForm: this.formBuilder.group({
            }),
//             customRepoSettingForm: this.formBuilder.group({
//             }),
            dumyForm: this.formBuilder.group({
            }),
        });
        this.provider = this.appDataService.getProviderType();
    }

    public ngOnInit() {
        super.ngOnInit();

        // delay showing first panel to avoid panel not defined console err
        setTimeout((_) => {
            if (this.uploadStatus) {
                this.uploadNextStep();
                this.show = true;
            } else {
                this.show = true;
            }
        });

        this.titleService.setTitle('ARCAS');
    }

    public getStepDescription(stepName: string): string {
        if (stepName === 'provider') {
            return 'Validate the vSphere provider account for Tanzu Kubernetes Grid configuration';
        } else if (stepName === 'infra') {
            if (this.getFieldValue('vsphereInfraDetailsForm', 'dns') &&
                this.getFieldValue('vsphereInfraDetailsForm', 'ntp')) {
                return 'Infrastructure details are configured';
            } else {
                return 'Configure infrastructure settings for Tanzu Kubernetes Grid clusters on vsphere';
            }
        } else if (stepName === 'mgmtNodeSetting') {
            if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneSetting')) {
                let mode = 'Development cluster selected: 1 node control plane';
                if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneSetting') === 'prod') {
                    mode = 'Production cluster selected: 3 node control plane';
                }
                return mode;
            } else {
                return `Configure the resources backing the management cluster`;
            }
        } else if (stepName === 'sharedServiceNodeSetting') {
            if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneSetting')) {
                let mode = 'Development cluster selected: 1 node control plane';
                if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneSetting') === 'prod') {
                    mode = 'Production cluster selected: 3 node control plane';
                }
                return mode;
                } else {
                return `Configure the resources backing the shared services cluster`;
            }
        } else if (stepName === 'workloadNodeSetting') {
            if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneSetting')) {
                let mode = 'Development cluster selected: 1 node control plane';
                if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneSetting') === 'prod') {
                    mode = 'Production cluster selected: 3 node control plane';
                }
                return mode;
            } else {
                return `Configure the resources backing the workload cluster`;
            }
        } else if (stepName === 'aviNetworkSetting') {
            if (this.getFieldValue('vsphereAVINetworkSettingForm', 'mgmtSegmentName')) {
                return 'VMware NSX Advanced Load Balancer settings configured';
            } else {
                return 'Configure VMware NSX Advanced Load Balancer settings';
            }
        } else if (stepName === 'extensionSetting') {
            return  'Configure User-managed packages for Tanzu Kubernetes Grid clusterss';
        } else if (stepName === 'TKGMgmtDataNW') {
            if (this.getFieldValue('TKGMgmtDataNWForm', 'gatewayCidr')) {
                return 'Tanzu Kubernetes Grid management data network set';
            } else {
                return 'Configure Tanzu Kubernetes Grid management data network settings';
            }
        } else if (stepName === 'tkgWorkloadDataNW') {
            if (this.getFieldValue('TKGWorkloadDataNWForm', 'gatewayCidr')) {
                return 'Tanzu Kubernetes Grid workload data network configured';
            } else {
                return 'Configure Tanzu Kubernetes Grid workload data network settings';
            }
        } else if (stepName === 'tanzuSaasSetting') {
            return 'Configure Tanzu saas services';
        } else if (stepName === 'customRepoSettings') {
            return 'Configure custom repository settings';
        }
    }

    public getCard(): string {
            return this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneSetting');
        }

    public removeFile() {
        if (this.fileName) {
            this.attachment.nativeElement.value = '';
            this.fileUploaded = false;
            this.fileName = '';
            this.file = null;
        }
    }

    public validateIPAndNetwork() {
        const ipData = {
            'aviMgmtNetworkGatewayCidr': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtGatewayIp'),
            'aviMgmtServiceIpStartrange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtDhcpStartRange'),
            'aviMgmtServiceIpEndrange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtDhcpEndRange'),

            'tkgMgmtGatewayCidr': this.getFieldValue('vsphereMgmtNodeSettingForm', 'gatewayAddress'),
            'tkgMgmtControlplaneIp': this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneEndpointIP'),
            'tkgSharedserviceControlplaneIp': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneEndpointIP'),

            'tkgMgmtDataNetworkGatewayCidr': this.getFieldValue('TKGMgmtDataNWForm', 'TKGMgmtGatewayCidr'),
            'tkgMgmtAviServiceIpStartRange': this.getFieldValue('TKGMgmtDataNWForm', 'TKGMgmtDhcpStartRange'),
            'tkgMgmtAviServiceIpEndRange': this.getFieldValue('TKGMgmtDataNWForm', 'TKGMgmtDhcpEndRange'),

            'tkgWorkloadDataNetworkGatewayCidr': this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataGatewayCidr'),
            'tkgWorkloadAviServiceIpStartRange': this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataDhcpStartRange'),
            'tkgWorkloadAviServiceIpEndRange': this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataDhcpEndRange'),

            'tkgWorkloadGatewayCidr': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'gatewayAddress'),
            'tkgWorkloadControlplaneIp': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneEndpointIP'),
        };

        this.apiClient.validateIpAndNetwork(ipData).subscribe((data: any) => {
              if (data && data !== null) {
                  if (data.responseType === 'SUCCESS') {
                    this.disableDeployButton = false;
                    this.showAwsTestMessage = false;
                    this.showIPValidationSuccess = true;
                    this.errorNotification = '';
                  } else if (data.responseType === 'ERROR') {
                    this.errorNotification = data.msg;
                  }
              } else {
                  this.showIPValidationSuccess = false;
                  this.errorNotification = 'IP Validation Failed, Edit and Review Configuration again.';
                  this.disableDeployButton = true;
              }
            }, (error: any) => {
            this.showIPValidationSuccess = false;
            this.disableDeployButton = true;
            if (error.responseType === 'ERROR') {
                this.errorNotification = error.msg;
            } else {
                this.errorNotification = 'Some Error Occurred while validating IPs';
            }
        });
    }
    public reviewConfiguration(review) {
        const pageTitle = 'vSphere Confirm Settings';
        this.titleService.setTitle(pageTitle);
        this.disableDeployButton = false;
        this.errorNotification = '';
        this.showAwsTestMessage = false;
        this.review = review;
    }

    public onTkgWrkDataValidateClick() {
        const gatewayIp = this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataGatewayCidr');
        const dhcpStart = this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataDhcpStartRange');
        const dhcpEnd = this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataDhcpEndRange');
        const block = new Netmask(gatewayIp);
        if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
            this.apiClient.TkgWrkDataNwValidated = true;
            this.errorNotification = '';
        } else if (!block.contains(dhcpStart) && !block.contains(dhcpEnd)) {
            this.errorNotification = 'DHCP Start and End IP are out of the provided subnet';
        } else if (!block.contains(dhcpStart)) {
            this.errorNotification = 'DHCP Start IP is out of the provided subnet.';
        } else if (!block.contains(dhcpEnd)) {
            this.errorNotification = 'DHCP End IP is out of the provided subnet';
        }
    }

    getArcasHttpProxyParam() {
        if (this.getBooleanFieldValue('vsphereInfraDetailsForm', 'proxySettings')) {
            if (this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUsername') !== '') {
                const username = this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUsername');
                const password = this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyPassword');
                const url = this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUrl');
                const httpProxy = 'http://' + username + ':' + password + '@' + url.substr(7);
                return httpProxy;
            } else {
                return this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUrl');
            }
        } else {
            return '';
        }
    }

    getArcasHttpsProxyParam() {
        if (this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUsername') !== '') {
            const username = this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUsername');
            const password = this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyPassword');
            const url = this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUrl');
            const httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
            return httpsProxy;
        } else {
            return this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUrl');
        }
    }

    public getArcasHttpsProxy() {
        let httpsProxy = '';
        if (this.getBooleanFieldValue('vsphereInfraDetailsForm', 'proxySettings')) {
            if (this.getBooleanFieldValue('vsphereInfraDetailsForm', 'isSameAsHttp')) {
                httpsProxy = this.getArcasHttpProxyParam();
            } else {
                httpsProxy = this.getArcasHttpsProxyParam();
            }
        } else {
            httpsProxy = '';
        }
        return httpsProxy;
    }

    getMgmtHttpProxyParam() {
        if (this.getBooleanFieldValue('vsphereMgmtNodeSettingForm', 'proxySettings')) {
            if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyUsername') !== '') {
                const username = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyUsername');
                const password = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyPassword');
                const url = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyUrl');
                const httpProxy = 'http://' + username + ':' + password + '@' + url.substr(7);
                return httpProxy;
            } else {
                return this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyUrl' );
            }
        } else {
            return '';
        }
    }

    getMgmtHttpsProxyParam() {
        if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyUsername') !== '') {
            const username = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyUsername');
            const password = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyPassword');
            const url = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyUrl');
            const httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
            return httpsProxy;
        } else {
            return this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyUrl');
        }
    }

    public getMgmtClusterHttpsProxy() {
        let httpsProxy = '';
        if (this.getBooleanFieldValue('vsphereMgmtNodeSettingForm', 'proxySettings')) {
            if (this.getBooleanFieldValue('vsphereMgmtNodeSettingForm', 'isSameAsHttp')) {
                httpsProxy = this.getMgmtHttpProxyParam();
            } else {
                httpsProxy = this.getMgmtHttpsProxyParam();
            }
        } else {
            httpsProxy = '';
        }
        return httpsProxy;
    }

    getSharedHttpProxyParam() {
        if (this.getBooleanFieldValue('vsphereSharedServiceNodeSettingForm', 'proxySettings')) {
            if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyUsername') !== '') {
                const username = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyUsername');
                const password = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyPassword');
                const url = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyUrl');
                const httpProxy = 'http://' + username + ':' + password + '@' + url.substr(7);
                return httpProxy;
            } else {
                return this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyUrl');
            }
        } else {
            return '';
        }
    }

    getSharedHttpsProxyParam() {
        if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyUsername') !== '') {
            const username = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyUsername');
            const password = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyPassword');
            const url = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyUrl');
            const httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
            return httpsProxy;
        } else {
            return this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyUrl');
        }
    }

    public getSharedClusterHttpsProxy() {
        let httpsProxy = '';
        if (this.getBooleanFieldValue('vsphereSharedServiceNodeSettingForm', 'proxySettings')) {
            if (this.getBooleanFieldValue('vsphereSharedServiceNodeSettingForm', 'isSameAsHttp')) {
                httpsProxy = this.getSharedHttpProxyParam();
            } else {
                httpsProxy = this.getSharedHttpsProxyParam();
            }
        } else {
            httpsProxy = '';
        }
        return httpsProxy;
    }

    getWorkloadHttpProxyParam() {
        if (this.getBooleanFieldValue('vsphereWorkloadNodeSettingForm', 'proxySettings')) {
            if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyUsername') !== '') {
                const username = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyUsername');
                const password = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyPassword');
                const url = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyUrl');
                const httpProxy = 'http://' + username + ':' + password + '@' + url.substr(7);
                return httpProxy;
            } else {
                return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyUrl');
            }
        } else {
            return '';
        }
    }

    getWorkloadHttpsProxyParam() {
        if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyUsername') !== '') {
            const username = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyUsername');
            const password = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyPassword');
            const url = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyUrl');
            const httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
            return httpsProxy;
        } else {
            return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyUrl');
        }
    }

    public getWorkloadClusterHttpsProxy() {
        let httpsProxy = '';
        if (this.getBooleanFieldValue('vsphereWorkloadNodeSettingForm', 'proxySettings')) {
            if (this.getBooleanFieldValue('vsphereWorkloadNodeSettingForm', 'isSameAsHttp')) {
                httpsProxy = this.getWorkloadHttpProxyParam();
            } else {
                httpsProxy = this.getWorkloadHttpsProxyParam();
            }
        } else {
            httpsProxy = '';
        }
        return httpsProxy;
    }

    public getMgmtClusterSize() {
        if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneSetting') === 'dev') {
            return this.getFieldValue('vsphereMgmtNodeSettingForm', 'devInstanceType');
        } else {
            return this.getFieldValue('vsphereMgmtNodeSettingForm', 'prodInstanceType');
        }
    }

    public getSharedClusterSize() {
        if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneSetting') === 'dev') {
            return this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'devInstanceType');
        } else {
            return this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'prodInstanceType');
        }
    }

    public getWorkloadClusterSize() {
        if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneSetting') === 'dev') {
            return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'devInstanceType');
        } else {
            return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'prodInstanceType');
        }
    }

    public getSharedClusterProxy(key: string) {
        if (key === 'http') {
            return this.getSharedHttpProxyParam();
        } else if (key === 'https') {
            return this.getSharedClusterHttpsProxy();
        }
    }

    public getWorkloadClusterProxy(key: string) {
        if (key === 'http') {
            return this.getWorkloadHttpProxyParam();
        } else if (key === 'https') {
                return this.getWorkloadClusterHttpsProxy();
        }
    }

    public getCustomRepoImage() {
        if (this.getBooleanFieldValue('customRepoSettingForm', 'customRepoSetting')) {
            return this.getFieldValue('customRepoSettingForm', 'repoImage');
        } else {
            return '';
        }
    }

    public getCustomRepoPublicCaCert() {
        if (this.getBooleanFieldValue('customRepoSettingForm', 'customRepoSetting')) {
            return this.getStringBoolFieldValue('customRepoSettingForm', 'publicCaCert');
        } else {
            return '';
        }
    }

    public getCustomRepoUsername() {
        if (this.getBooleanFieldValue('customRepoSettingForm', 'customRepoSetting')) {
            return this.getFieldValue('customRepoSettingForm', 'repoUsername');
        } else {
            return '';
        }
    }

    public getCustomRepoPassword() {
        if (this.getBooleanFieldValue('customRepoSettingForm', 'customRepoSetting')) {
            return this.getFieldValue('customRepoSettingForm', 'repoPassword');
        } else {
            return '';
        }
    }

    public enableLoggingExtension(key) {
        if (this.getFieldValue('extensionSettingForm', 'loggingEndpoint') === key) {
            return 'true';
        } else {
            return 'false';
        }
    }

    public setTSMEnable() {
        const tmcEnable = this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings');
        if (tmcEnable === 'true') {
            return this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'tsmSettings');
        } else {
            return 'false';
        }
    }

    public setTSMExactName() {
        const tmcEnable = this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings');
        if (tmcEnable === 'true') {
            const tsmEnable = this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'tsmSettings');
            if (tsmEnable === 'true') {
                return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'exactName');
            } else {
                return '';
            }
        } else {
            return '';
        }
    }

    public setTSMStartsWithName() {
        const tmcEnable = this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings');
        if (tmcEnable === 'true') {
            const tsmEnable = this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'tsmSettings');
            if (tsmEnable === 'true') {
                return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'startsWithName');
            } else {
                return '';
            }
        } else {
            return '';
        }
    }
    public getPayload() {
        const payload = {
            'envSpec': {
                'vcenterDetails': {
                    'vcenterAddress': this.getFieldValue('vsphereProviderForm', 'vcenterAddress'),
                    'vcenterSsoUser': this.getFieldValue('vsphereProviderForm', 'username'),
                    'vcenterSsoPasswordBase64': btoa(this.form.get('vsphereProviderForm').get('password').value),
                    'vcenterDatacenter': this.getFieldValue('vsphereProviderForm', 'datacenter'),
                    'vcenterCluster': this.getFieldValue('vsphereProviderForm', 'cluster'),
                    'vcenterDatastore': this.getFieldValue('vsphereProviderForm', 'datastore'),
                    'contentLibraryName': this.getFieldValue('vsphereProviderForm', 'contentLib'),
                    'aviOvaName': this.getFieldValue('vsphereProviderForm', 'aviOvaImage'),
                    'resourcePoolName': this.getFieldValue('vsphereProviderForm', 'resourcePool'),
                },
                'envType': 'tkgm',
                'marketplaceSpec' : {
                    'refreshToken': this.getFieldValue('vsphereProviderForm', 'marketplaceRefreshToken'),
                },
//                 'customRepositorySpec': {
//                     'tkgCustomImageRepository' : this.getCustomRepoImage(),
//                     'tkgCustomImageRepositoryPublicCaCert' : this.getCustomRepoPublicCaCert(),
//                 },
                'saasEndpoints': {
                    'tmcDetails': {
                        'tmcAvailability': this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings'),
                        'tmcRefreshToken': this.getFieldValue('tanzuSaasSettingForm', 'refreshToken'),
                    },
                    'tanzuObservabilityDetails': {
                        'tanzuObservabilityAvailability': this.getStringBoolFieldValue('tanzuSaasSettingForm', 'toSettings'),
                        'tanzuObservabilityUrl': this.getFieldValue('tanzuSaasSettingForm', 'toUrl'),
                        'tanzuObservabilityRefreshToken': this.getFieldValue('tanzuSaasSettingForm', 'toRefreshToken')
                    }
                },

                'infraComponents': {
                    'dnsServersIp': this.getFieldValue('dumyForm', 'dnsServer'),
                    'ntpServers': this.getFieldValue('dumyForm', 'ntpServer'),
                    'searchDomains': this.getFieldValue('dumyForm', 'searchDomain'),
                },
                'proxySpec': {
                    'arcasVm': {
                        'enableProxy': this.getStringBoolFieldValue('vsphereInfraDetailsForm', 'proxySettings'),
                        'httpProxy': this.getArcasHttpProxyParam(),
                        'httpsProxy': this.getArcasHttpsProxy(),
                        'noProxy': this.getFieldValue('vsphereInfraDetailsForm', 'noProxy'),
                    },
                    'tkgMgmt': {
                        'enableProxy': this.getStringBoolFieldValue('vsphereMgmtNodeSettingForm', 'proxySettings'),
                        'httpProxy': this.getMgmtHttpProxyParam(),
                        'httpsProxy': this.getMgmtClusterHttpsProxy(),
                        'noProxy': this.getFieldValue('vsphereMgmtNodeSettingForm', 'noProxy'),
                    },
                    'tkgSharedservice': {
                        'enableProxy': this.getStringBoolFieldValue('vsphereSharedServiceNodeSettingForm', 'proxySettings'),
                        'httpProxy': this.getSharedClusterProxy('http'),
                        'httpsProxy': this.getSharedClusterProxy('https'),
                        'noProxy': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'noProxy'),
                    },
                    'tkgWorkload': {
                        'enableProxy': this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'proxySettings'),
                        'httpProxy': this.getWorkloadClusterProxy('http'),
                        'httpsProxy': this.getWorkloadClusterProxy('https'),
                        'noProxy': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'noProxy'),
                    },
                },
            },
            'tkgComponentSpec': {
                'aviMgmtNetwork': {
                    'aviMgmtNetworkName': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtNetworkName'),
                    'aviMgmtNetworkGatewayCidr': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtGatewayIp'),
                    'aviMgmtServiceIpStartRange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtDhcpStartRange'),
                    'aviMgmtServiceIpEndRange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtDhcpEndRange'),
                },
                'tkgClusterVipNetwork': {
                    'tkgClusterVipNetworkName': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviClusterVipNetworkName'),
                    'tkgClusterVipNetworkGatewayCidr': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviClusterVipGatewayIp'),
                    'tkgClusterVipIpStartRange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviClusterVipStartRange'),
                    'tkgClusterVipIpEndRange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviClusterVipEndRange'),
                },
                'aviComponents': {
                    'aviPasswordBase64': btoa(this.getFieldValue('vsphereAVINetworkSettingForm', 'aviPassword')),
                    'aviBackupPassphraseBase64': btoa(this.getFieldValue('vsphereAVINetworkSettingForm', 'aviBackupPassphrase')),
                    'enableAviHa': this.getStringBoolFieldValue('vsphereAVINetworkSettingForm', 'enableHA'),
                    'aviController01Ip': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerIp'),
                    'aviController01Fqdn': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerFqdn'),
                    'aviController02Ip': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerIp02'),
                    'aviController02Fqdn': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerFqdn02'),
                    'aviController03Ip': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerIp03'),
                    'aviController03Fqdn': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerFqdn03'),
                    'aviClusterIp': this.getFieldValue('vsphereAVINetworkSettingForm', 'clusterIp'),
                    'aviClusterFqdn': this.getFieldValue('vsphereAVINetworkSettingForm', 'clusterFqdn'),
                    'aviSize': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviSize'),
//                     'aviLicenseKey': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviLicenseKey'),
                    'aviCertPath': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviCertPath'),
                    'aviCertKeyPath': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviCertKeyPath'),
                },
                'tkgMgmtComponents': {
                    'tkgMgmtNetworkName': this.getFieldValue('vsphereMgmtNodeSettingForm', 'segmentName'),
                    'tkgMgmtGatewayCidr': this.getFieldValue('vsphereMgmtNodeSettingForm', 'gatewayAddress'),
                    'tkgMgmtClusterName': this.getFieldValue('vsphereMgmtNodeSettingForm', 'clusterName'),
                    'tkgMgmtSize': this.getMgmtClusterSize(),
                    'tkgMgmtCpuSize': this.getFieldValue('vsphereMgmtNodeSettingForm', 'mgmtCpu').toString(),
                    'tkgMgmtMemorySize': this.getFieldValue('vsphereMgmtNodeSettingForm', 'mgmtMemory').toString(),
                    'tkgMgmtStorageSize': this.getFieldValue('vsphereMgmtNodeSettingForm', 'mgmtStorage').toString(),
                    'tkgMgmtDeploymentType': this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneSetting'),
                    'tkgMgmtClusterCidr': this.getFieldValue('vsphereMgmtNodeSettingForm', 'clusterCidr'),
                    'tkgMgmtServiceCidr': this.getFieldValue('vsphereMgmtNodeSettingForm', 'serviceCidr'),
                    'tkgMgmtBaseOs': this.getFieldValue('vsphereMgmtNodeSettingForm', 'baseImage'),
                    'tkgSharedserviceClusterName': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'clusterName'),
                    'tkgSharedserviceSize': this.getSharedClusterSize(),
                    'tkgSharedserviceCpuSize': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'sharedCpu').toString(),
                    'tkgSharedserviceMemorySize': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'sharedMemory').toString(),
                    'tkgSharedserviceStorageSize': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'sharedStorage').toString(),
                    'tkgSharedserviceDeploymentType': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneSetting'),
                    // tslint:disable-next-line:max-line-length
                    'tkgSharedserviceWorkerMachineCount': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'workerNodeCount').toString(),
                    'tkgSharedserviceClusterCidr': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'clusterCidr'),
                    'tkgSharedserviceServiceCidr': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'serviceCidr'),
                    'tkgSharedserviceBaseOs': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'baseImage'),
                    'tkgSharedserviceKubeVersion': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'baseImageVersion'),
                },
            },
            'tkgMgmtDataNetwork': {
                'tkgMgmtDataNetworkName': this.getFieldValue('TKGMgmtDataNWForm', 'TKGMgmtSegmentName'),
                'tkgMgmtDataNetworkGatewayCidr': this.getFieldValue('TKGMgmtDataNWForm', 'TKGMgmtGatewayCidr'),
                'tkgMgmtAviServiceIpStartRange': this.getFieldValue('TKGMgmtDataNWForm', 'TKGMgmtDhcpStartRange'),
                'tkgMgmtAviServiceIpEndRange': this.getFieldValue('TKGMgmtDataNWForm', 'TKGMgmtDhcpEndRange'),
            },
            'tkgWorkloadDataNetwork': {
                'tkgWorkloadDataNetworkName': this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataSegmentName'),
                'tkgWorkloadDataNetworkGatewayCidr': this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataGatewayCidr'),
                'tkgWorkloadAviServiceIpStartRange': this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataDhcpStartRange'),
                'tkgWorkloadAviServiceIpEndRange': this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataDhcpEndRange'),
            },
            'tkgWorkloadComponents': {
                'tkgWorkloadNetworkName': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'segmentName'),
                'tkgWorkloadGatewayCidr': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'gatewayAddress'),
                'tkgWorkloadClusterName': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'clusterName'),
                'tkgWorkloadSize': this.getWorkloadClusterSize(),
                'tkgWorkloadCpuSize': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'wrkCpu').toString(),
                'tkgWorkloadMemorySize': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'wrkMemory').toString(),
                'tkgWorkloadStorageSize': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'wrkStorage').toString(),
                'tkgWorkloadDeploymentType': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneSetting'),
                'tkgWorkloadWorkerMachineCount': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'workerNodeCount').toString(),
                'tkgWorkloadClusterCidr': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'clusterCidr'),
                'tkgWorkloadServiceCidr': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'serviceCidr'),
                'tkgWorkloadBaseOs': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'baseImage'),
                'tkgWorkloadKubeVersion': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'baseImageVersion'),
                'tkgWorkloadTsmIntegration': this.setTSMEnable(),
                'namespaceExclusions': {
                    'exactName': this.setTSMExactName(),
                    'startsWith': this.setTSMStartsWithName(),
                },
            },
            'harborSpec': {
                'enableHarborExtension': 'true',
                'harborFqdn': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'harborFqdn'),
                'harborPasswordBase64': btoa(this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'harborPassword')),
                'harborCertPath': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'harborCertPath'),
                'harborCertKeyPath': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'harborCertKeyPath'),
            },
            'tanzuExtensions': {
                'enableExtensions': !this.apiClient.toEnabled ? this.getStringBoolFieldValue('extensionSettingForm', 'tanzuExtensions') : "false",
                'tkgClustersName': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'tanzuExtensionClusters') : "",
                'logging': {
                    'syslogEndpoint': {
                        'enableSyslogEndpoint': !this.apiClient.toEnabled ? this.enableLoggingExtension('Syslog') : "false",
                        'syslogEndpointAddress': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'syslogEndpointAddress') : "",
                        'syslogEndpointPort': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'syslogEndpointPort') : "",
                        'syslogEndpointMode': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'syslogEndpointMode') : "",
                        'syslogEndpointFormat': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'syslogEndpointFormat') : "",
                    },
                    'httpEndpoint': {
                        'enableHttpEndpoint': !this.apiClient.toEnabled ? this.enableLoggingExtension('HTTP') : "false",
                        'httpEndpointAddress': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'httpEndpointAddress') : "",
                        'httpEndpointPort': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'httpEndpointPort') : "",
                        'httpEndpointUri': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'httpEndpointUri') : "",
                        'httpEndpointHeaderKeyValue': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'httpEndpointHeaderKeyValue') : "",
                    },
                    'elasticSearchEndpoint': {
                        'enableElasticSearchEndpoint': !this.apiClient.toEnabled ? this.enableLoggingExtension('Elastic Search') : "false",
                        'elasticSearchEndpointAddress': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'elasticSearchAddress') : "",
                        'elasticSearchEndpointPort': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'elasticSearchPort') : "",
                    },
                    'kafkaEndpoint': {
                        'enableKafkaEndpoint': !this.apiClient.toEnabled ? this.enableLoggingExtension('Kafka') : "false",
                        'kafkaBrokerServiceName': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'kafkaBrokerServiceName') : "",
                        'kafkaTopicName': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'kafkaTopicName') : "",
                    },
                    'splunkEndpoint': {
                        'enableSplunkEndpoint': !this.apiClient.toEnabled ? this.enableLoggingExtension('Splunk') : "false",
                        'splunkEndpointAddress': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'splunkAddress') : "",
                        'splunkEndpointPort': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'splunkPort') : "",
                        'splunkEndpointToken': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'splunkToken') : "",
                    },
                },
                'monitoring': {
                    'enableLoggingExtension': !this.apiClient.toEnabled ? this.getStringBoolFieldValue('extensionSettingForm', 'enableMonitoring') : "false",
                    'prometheusFqdn': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'prometheusFqdn') : "",
                    'prometheusCertPath': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'prometheusCertPath') : "",
                    'prometheusCertKeyPath': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'prometheusCertKeyPath') : "",
                    'grafanaFqdn': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'grafanaFqdn') : "",
                    'grafanaCertPath': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'grafanaCertPath') : "",
                    'grafanaCertKeyPath': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'grafanaCertKeyPath') : "",
                    'grafanaPasswordBase64': !this.apiClient.toEnabled ? btoa(this.getFieldValue('extensionSettingForm', 'grafanaPassword')) : "",
                }
            }
        };
        this.apiClient.vspherePayload = payload;
        return payload;
    }

    public checkAirgapped(){
        if(this.getCustomRepoImage() === "") return false;
        else return true;
    }

    public checkProxy() {
        if(this.getFieldValue('vsphereInfraDetailsForm', 'proxySettings') ||
            this.getFieldValue('vsphereMgmtNodeSettingForm', 'proxySettings') ||
            this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'proxySettings') ||
            this.getFieldValue('vsphereWorkloadNodeSettingForm', 'proxySettings')) {
            return true;
        }
        else{
            return false;
        }
    }

    openViewJsonModal() {
        this.getPayload();
//         if (this.checkAirgapped()) {
//             this.generatedFileName = 'vsphere-dvs-tkgm-airgapped.json';
//         }else
        if(this.checkProxy()) {
            this.generatedFileName = 'vsphere-dvs-tkgm-proxy.json';
        } else{
            this.generatedFileName = 'vsphere-dvs-tkgm.json';
        }
        this.viewJsonModal.open(this.generatedFileName);
    }

    public generateInput() {
        const payload = this.getPayload();
        this.disableDeployButton = true;
//         if (this.checkAirgapped()) {
//             this.generatedFileName = 'vsphere-dvs-tkgm-airgapped.json';
//         }else
        if(this.checkProxy()) {
            this.generatedFileName = 'vsphere-dvs-tkgm-proxy.json';
        } else{
            this.generatedFileName = 'vsphere-dvs-tkgm.json';
        }
        this.filePath = '/opt/vmware/arcas/src/' + this.generatedFileName;
        this.showAwsTestMessage = false;
        // Call the Generate API
        this.apiClient.generateInputJSON(payload, this.generatedFileName, 'vsphere').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.showAwsTestMessage = true;
                } else if (data.responseType === 'ERROR') {
                    this.errorNotification = data.msg;
                }
            } else {
                this.errorNotification = 'Generation of input json failed.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.errorNotification = error.msg;
            } else {
                this.errorNotification = 'Generation of input json failed.';
            }
        });
    }

    public downloadSupportBundle() {
        this.loadingState = ClrLoadingState.LOADING;
        this.apiClient.downloadLogBundle('vsphere').subscribe(blob => {
            importedSaveAs(blob, this.logFileName);
            this.loadingState = ClrLoadingState.DEFAULT;
        }, (error: any) => {
            this.loadingState = ClrLoadingState.DEFAULT;
            this.errorNotification = "Failed to download Support Bundle for Service Installer";
        });
    }

    public deploy() {
        this.getPayload();
        this.navigate(APP_ROUTES.WIZARD_PROGRESS);
    }


    /**
     * @method getControlPlaneType
     * helper method to return value of dev instance type or prod instance type
     * depending on what type of control plane is selected
     * @param controlPlaneType {string} the control plane type (dev/prod)
     * @returns {any}
     */
    public getControlPlaneType(controlPlaneType: string) {
        if (controlPlaneType === 'dev') {
            return this.getFieldValue('vsphereNodeSettingForm', 'devInstanceType');
        } else if (controlPlaneType === 'prod') {
            return this.getFieldValue('vsphereNodeSettingForm', 'prodInstanceType');
        } else {
            return null;
        }
    }

}
