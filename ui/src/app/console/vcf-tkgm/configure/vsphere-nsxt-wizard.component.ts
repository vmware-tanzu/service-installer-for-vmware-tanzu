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
import { saveAs as importedSaveAs } from "file-saver";
import { ClrLoadingState } from '@clr/angular';

// Third party imports
import {Observable} from 'rxjs';

// App imports
import { FormMetaDataService } from 'src/app/shared/service/form-meta-data.service';
import { PROVIDERS, Providers } from 'src/app/shared/constants/app.constants';
import { APP_ROUTES, Routes } from 'src/app/shared/constants/routes.constants';
import { AppDataService } from 'src/app/shared/service/app-data.service';
import { DataService } from 'src/app/shared/service/data.service';
import { VMCDataService } from 'src/app/shared/service/vmc-data.service';
import { VsphereNsxtDataService } from 'src/app/shared/service/vsphere-nsxt-data.service';
import { VsphereTkgsService } from "src/app/shared/service/vsphere-tkgs-data.service";
import { APIClient } from 'src/app/swagger/api-client.service';
import { ViewJSONModalComponent } from 'src/app/views/landing/wizard/shared/components/modals/view-json-modal/view-json-modal.component';
import { WizardBaseDirective } from 'src/app/views/landing/wizard/shared/wizard-base/wizard-base';
import { VCDDataService } from 'src/app/shared/service/vcd-data.service';

@Component({
    selector: 'app-wizard',
    templateUrl: './vsphere-nsxt-wizard.component.html',
    styleUrls: ['./vsphere-nsxt-wizard.component.scss'],
})
export class VSphereNsxtWizardComponent extends WizardBaseDirective implements OnInit {
    @ViewChild(ViewJSONModalComponent) viewJsonModal: ViewJSONModalComponent;
    @ViewChild('attachments') attachment : any;
    @Input() public form;
    @Input() public AVIFormValid;
    @Input() public providerType = 'vsphere-nsxt';
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
    public generatedFileName: string;
    public logFileName = 'service_installer_log_bundle';
    public fileUploaded = false;
    public file: File;
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    constructor(
        public apiClient: APIClient,
        router: Router,
        private appDataService: AppDataService,
        private formBuilder: FormBuilder,
        formMetaDataService: FormMetaDataService,
        dataService: DataService,
        vmcDataService: VMCDataService,
        vsphereNsxtDataService: VsphereNsxtDataService,
        vsphereTkgsDataService: VsphereTkgsService,
        vcdDataService: VCDDataService,
        titleService: Title,
        el: ElementRef) {

        super(router, el, formMetaDataService, titleService, dataService, vmcDataService, vsphereNsxtDataService, vsphereTkgsDataService, vcdDataService);

        this.form = this.formBuilder.group({
            vsphereProviderForm: this.formBuilder.group({
            }),
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
            IdentityMgmtForm: this.formBuilder.group({
            }),
            customRepoSettingForm: this.formBuilder.group({
            }),
            dnsNTPStepForm: this.formBuilder.group({
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
            return 'Validate the vSphere provider and NSX-T account for Tanzu Kubernetes Grid configurations';
        } else if (stepName === 'infra') {
            if (this.getFieldValue('vsphereInfraDetailsForm', 'dns') &&
                this.getFieldValue('vsphereInfraDetailsForm', 'ntp')) {
                return 'Infrastructure details are configured';
            } else {
                return 'Configure infrastructure settings for Tanzu Kubernetes Grid on vSphere wth NSX-T';
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
            return  'Configure User-managed packages for Tanzu Kubernetes Grid clusters';
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
                let username = this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUsername');
                let password = this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyPassword');
                let url = this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUrl');
                let httpProxy = 'http://' + username + ':' + password +'@'+ url.substr(7);
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
            let username = this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUsername');
            let password = this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyPassword');
            let url = this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUrl');
            let httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
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
                let username = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyUsername');
                let password = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyPassword');
                let url = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyUrl');
                let httpProxy = 'http://' + username + ':' + password + '@' + url.substr(7);
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
            let username = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyUsername');
            let password = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyPassword');
            let url = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyUrl');
            let httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
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
                let username = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyUsername');
                let password = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyPassword');
                let url = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyUrl');
                let httpProxy = 'http://' + username + ':' + password + '@' + url.substr(7);
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
            let username = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyUsername');
            let password = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyPassword');
            let url = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyUrl');
            let httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
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
                let username = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyUsername');
                let password = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyPassword');
                let url = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyUrl');
                let httpProxy = 'http://' + username + ':' + password + '@' + url.substr(7);
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
            let username = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyUsername');
            let password = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyPassword');
            let url = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyUrl');
            let httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
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
        let tmcEnable = this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings');
        if (tmcEnable === 'true') {
            return this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'tsmSettings');
        } else {
            return 'false';
        }
    }

    public setTSMExactName() {
        let tmcEnable = this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings');
        if (tmcEnable === 'true') {
            let tsmEnable = this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'tsmSettings');
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
        let tmcEnable = this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings');
        if (tmcEnable === 'true') {
            let tsmEnable = this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'tsmSettings');
            if (tsmEnable === 'true') {
                return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'startsWithName');
            } else {
                return '';
            }
        } else {
            return '';
        }
    }


    public getCustomCertsAsList(certs: string) {
        if (certs === "" || certs.length === 0) return [];
        let certList = certs.split(',');
        let listOfCerts = [];
        let iter = 0;
        while (iter < certList.length){
            listOfCerts.push(certList[iter].trim());
            iter++;
        }
        return listOfCerts;
    }

    public getPayload() {
        let workloadGiven = this.apiClient.workloadClusterSettings;
        const payload = {
            'envSpec': {
                'vcenterDetails': {
                    'vcenterAddress': this.getFieldValue('vsphereProviderForm', 'vcenterAddress'),
                    'vcenterSsoUser': this.getFieldValue('vsphereProviderForm', 'username'),
                    'vcenterSsoPasswordBase64': btoa(this.form.get('vsphereProviderForm').get('password').value),
                    'modeOfDeployment': this.getFieldValue('vsphereProviderForm', 'modeOfDeployment') === '' ? 'orchestrated' : this.getFieldValue('vsphereProviderForm', 'modeOfDeployment'),
                    'vcenterDatacenter': this.getFieldValue('vsphereProviderForm', 'datacenter'),
                    'vcenterCluster': this.getFieldValue('vsphereProviderForm', 'cluster'),
                    'vcenterDatastore': this.getFieldValue('vsphereProviderForm', 'datastore'),
                    'contentLibraryName': this.getFieldValue('vsphereProviderForm', 'contentLib'),
                    'aviOvaName': this.getFieldValue('vsphereProviderForm', 'aviOvaImage'),
                    'resourcePoolName': this.getFieldValue('vsphereProviderForm', 'resourcePool'),
                    'nsxtAddress': this.getFieldValue('vsphereProviderForm', 'nsxtAddress'),
                    'nsxtUser': this.getFieldValue('vsphereProviderForm', 'nsxtUsername'),
                    'nsxtUserPasswordBase64': btoa(this.getFieldValue('vsphereProviderForm', 'nsxtPassword')),
                    'nsxtTier1RouterDisplayName': this.getFieldValue('vsphereProviderForm', 'tier1Router'),
                    'nsxtOverlay': this.getFieldValue('vsphereProviderForm', 'nsxtOverlay'),
                },
                'marketplaceSpec' : {
                    'refreshToken': this.getFieldValue('vsphereProviderForm', 'marketplaceRefreshToken'),
                },
                'compliantSpec': {
                    'compliantDeployment': this.getStringBoolFieldValue('vsphereMgmtNodeSettingForm', 'compliantDeployment'),
                },
                'ceipParticipation' : this.getStringBoolFieldValue('vsphereProviderForm', 'isCeipEnabled'),
                'customRepositorySpec': {
                    'tkgCustomImageRepository': this.getCustomRepoImage(),
                    'tkgCustomImageRepositoryPublicCaCert': this.getCustomRepoPublicCaCert(),
                },
                'saasEndpoints': {
                    'tmcDetails': {
                        'tmcAvailability': this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings'),
                        'tmcRefreshToken': this.getFieldValue('tanzuSaasSettingForm', 'refreshToken'),
                        'tmcInstanceURL': this.getFieldValue('tanzuSaasSettingForm', 'tmcInstanceURL'),
                    },
                    'tanzuObservabilityDetails': {
                        'tanzuObservabilityAvailability': this.getStringBoolFieldValue('tanzuSaasSettingForm', 'toSettings'),
                        'tanzuObservabilityUrl': this.getFieldValue('tanzuSaasSettingForm', 'toUrl'),
                        'tanzuObservabilityRefreshToken': this.getFieldValue('tanzuSaasSettingForm', 'toRefreshToken')
                    }
                },

                'infraComponents': {
                    'dnsServersIp': this.getFieldValue('dnsNTPStepForm', 'dnsServer'),
                    'searchDomains': this.getFieldValue('dnsNTPStepForm', 'searchDomain'),
                    'ntpServers': this.getFieldValue('dnsNTPStepForm', 'ntpServer'),
                },
                'proxySpec': {
                    'arcasVm': {
                        'enableProxy': this.getStringBoolFieldValue('vsphereInfraDetailsForm', 'proxySettings'),
                        'httpProxy': this.getArcasHttpProxyParam(),
                        'httpsProxy': this.getArcasHttpsProxy(),
                        'noProxy': this.getFieldValue('vsphereInfraDetailsForm', 'noProxy'),
                        'proxyCert': this.getFieldValue('vsphereInfraDetailsForm', 'proxyCert'),
                    },
                    'tkgMgmt': {
                        'enableProxy': this.getStringBoolFieldValue('vsphereMgmtNodeSettingForm', 'proxySettings'),
                        'httpProxy': this.getMgmtHttpProxyParam(),
                        'httpsProxy': this.getMgmtClusterHttpsProxy(),
                        'noProxy': this.getFieldValue('vsphereMgmtNodeSettingForm', 'noProxy'),
                        'proxyCert': this.getFieldValue('vsphereMgmtNodeSettingForm', 'proxyCert'),
                    },
                    'tkgSharedservice': {
                        'enableProxy': this.getStringBoolFieldValue('vsphereSharedServiceNodeSettingForm', 'proxySettings'),
                        'httpProxy': this.getSharedClusterProxy('http'),
                        'httpsProxy': this.getSharedClusterProxy('https'),
                        'noProxy': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'noProxy'),
                        'proxyCert': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'proxyCert'),
                    },
                    'tkgWorkload': {
                        'enableProxy': this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'proxySettings'),
                        'httpProxy': this.getWorkloadClusterProxy('http'),
                        'httpsProxy': this.getWorkloadClusterProxy('https'),
                        'noProxy': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'noProxy'),
                        'proxyCert': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'proxyCert'),
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
                    'aviCertPath': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviCertPath'),
                    'aviCertKeyPath': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviCertKeyPath'),
                },
                'identityManagementSpec': {
                    'identityManagementType': this.getFieldValue('IdentityMgmtForm', 'identityType'),
                    'oidcSpec': {
                        'oidcIssuerUrl': this.getFieldValue('IdentityMgmtForm', 'issuerURL'),
                        'oidcClientId': this.getFieldValue('IdentityMgmtForm', 'clientId'),
                        'oidcClientSecret': this.getFieldValue('IdentityMgmtForm', 'clientSecret'),
                        'oidcScopes': this.getFieldValue('IdentityMgmtForm', 'scopes'),
                        'oidcUsernameClaim': this.getFieldValue('IdentityMgmtForm', 'oidcUsernameClaim'),
                        'oidcGroupsClaim': this.getFieldValue('IdentityMgmtForm', 'oidcGroupsClaim'),
                    },
                    'ldapSpec': {
                        'ldapEndpointIp': this.getFieldValue('IdentityMgmtForm', 'endpointIp'),
                        'ldapEndpointPort': this.getFieldValue('IdentityMgmtForm', 'endpointPort'),
                        'ldapBindPWBase64': btoa(this.getFieldValue('IdentityMgmtForm', 'bindPW')),
                        'ldapBindDN': this.getFieldValue('IdentityMgmtForm', 'bindDN'),
                        'ldapUserSearchBaseDN': this.getFieldValue('IdentityMgmtForm', 'userSearchBaseDN'),
                        'ldapUserSearchFilter': this.getFieldValue('IdentityMgmtForm', 'userSearchFilter'),
                        'ldapUserSearchUsername': this.getFieldValue('IdentityMgmtForm', 'userSearchUsername'),
                        'ldapGroupSearchBaseDN': this.getFieldValue('IdentityMgmtForm', 'groupSearchBaseDN'),
                        'ldapGroupSearchFilter': this.getFieldValue('IdentityMgmtForm', 'groupSearchFilter'),
                        'ldapGroupSearchUserAttr': this.getFieldValue('IdentityMgmtForm', 'groupSearchUserAttr'),
                        'ldapGroupSearchGroupAttr': this.getFieldValue('IdentityMgmtForm', 'groupSearchGroupAttr'),
                        'ldapGroupSearchNameAttr': this.getFieldValue('IdentityMgmtForm', 'groupSearchNameAttr'),
                        'ldapRootCAData': this.getFieldValue('IdentityMgmtForm', 'ldapRootCAData'),
                    }
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
                    'tkgMgmtClusterGroupName': this.apiClient.tmcEnabled ? this.getFieldValue('vsphereMgmtNodeSettingForm', 'clusterGroupName') : "",

                    'tkgMgmtRbacUserRoleSpec': {
                        'clusterAdminUsers': this.getFieldValue('vsphereMgmtNodeSettingForm', 'clusterAdminUsers'),
                        'adminUsers': this.getFieldValue('vsphereMgmtNodeSettingForm', 'adminUsers'),
                        'editUsers': this.getFieldValue('vsphereMgmtNodeSettingForm', 'editUsers'),
                        'viewUsers': this.getFieldValue('vsphereMgmtNodeSettingForm', 'viewUsers'),
                    },
                },
                'tkgSharedserviceSpec': {
                    'tkgSharedserviceNetworkName': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'segmentName'),
                    'tkgSharedserviceGatewayCidr': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'gatewayAddress'),
                    'tkgSharedserviceDhcpStartRange': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'DhcpStartRange'),
                    'tkgSharedserviceDhcpEndRange': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'DhcpEndRange'),
                    'tkgSharedserviceClusterName': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'clusterName'),
                    'tkgSharedserviceSize': this.getSharedClusterSize(),
                    'tkgSharedserviceCpuSize': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'sharedCpu').toString(),
                    'tkgSharedserviceMemorySize': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'sharedMemory').toString(),
                    'tkgSharedserviceStorageSize': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'sharedStorage').toString(),
                    'tkgSharedserviceDeploymentType': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneSetting'),
                    'tkgSharedserviceWorkerMachineCount': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'workerNodeCount').toString(),
                    'tkgSharedserviceClusterCidr': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'clusterCidr'),
                    'tkgSharedserviceServiceCidr': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'serviceCidr'),
                    'tkgSharedserviceBaseOs': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'baseImage'),
                    'tkgSharedserviceKubeVersion': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'baseImageVersion'),
                    'tkgSharedserviceEnableAviL7': this.getStringBoolFieldValue('vsphereSharedServiceNodeSettingForm', 'enableL7'),
                    'tkgCustomCertsPath': this.getCustomCertsAsList(this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'tkgCustomCert')),
                    'tkgSharedserviceRbacUserRoleSpec': {
                        'clusterAdminUsers': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'clusterAdminUsers'),
                        'adminUsers': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'adminUsers'),
                        'editUsers': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'editUsers'),
                        'viewUsers': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'viewUsers'),
                    },
                    'tkgSharedserviceClusterGroupName': this.apiClient.tmcEnabled ? this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'clusterGroupName'): "",
                    'tkgSharedserviceEnableDataProtection': this.apiClient.tmcEnabled ? this.getStringBoolFieldValue('vsphereSharedServiceNodeSettingForm', 'enableDataProtection') : "false",
                    'tkgSharedClusterCredential': this.apiClient.tmcEnabled ? this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'veleroCredential') : "",
                    'tkgSharedClusterBackupLocation': this.apiClient.tmcEnabled ? this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'veleroTargetLocation'): "",
                    'tkgSharedClusterVeleroDataProtection': {
                        'enableVelero': this.apiClient.tmcEnabled ? "false" : this.getStringBoolFieldValue('vsphereSharedServiceNodeSettingForm', 'enableVelero'),
                        'username': this.apiClient.tmcEnabled ? "" : this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'veleroUsername'),
                        'passwordBase64': this.apiClient.tmcEnabled ? "" : btoa(this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'veleroPassword')),
                        'bucketName': this.apiClient.tmcEnabled ? "" : this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'veleroBucket'),
                        'backupRegion': this.apiClient.tmcEnabled ? "" : this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'veleroRegion'),
                        'backupS3Url': this.apiClient.tmcEnabled ? "" : this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'veleroS3Url'),
                        'backupPublicUrl': this.apiClient.tmcEnabled ? "" : this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'veleroPublicUrl'),
                    },
                },
            },
            'tkgWorkloadComponents': {
                'tkgWorkloadNetworkName': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'segmentName'),
                'tkgWorkloadGatewayCidr': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'gatewayAddress'),
                'tkgWorkloadDhcpStartRange': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'DhcpStartRange'),
                'tkgWorkloadDhcpEndRange': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'DhcpEndRange'),
                'tkgWorkloadClusterName': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'clusterName'),
                'tkgWorkloadSize': !workloadGiven ? "" : this.getWorkloadClusterSize(),
                'tkgWorkloadCpuSize': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'wrkCpu').toString(),
                'tkgWorkloadMemorySize': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'wrkMemory').toString(),
                'tkgWorkloadStorageSize': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'wrkStorage').toString(),
                'tkgWorkloadDeploymentType': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneSetting'),
                'tkgWorkloadWorkerMachineCount': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'workerNodeCount').toString(),
                'tkgWorkloadClusterCidr': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'clusterCidr'),
                'tkgWorkloadServiceCidr': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'serviceCidr'),
                'tkgWorkloadBaseOs': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'baseImage'),
                'tkgWorkloadKubeVersion': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'baseImageVersion'),
                'tkgWorkloadEnableAviL7': !workloadGiven ? "false": this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'enableL7'),
                'tkgWorkloadRbacUserRoleSpec': {
                    'clusterAdminUsers': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'clusterAdminUsers'),
                    'adminUsers': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'adminUsers'),
                    'editUsers': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'editUsers'),
                    'viewUsers': !workloadGiven ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'viewUsers'),
                },
                'tkgWorkloadTsmIntegration': !workloadGiven ? "false" : this.setTSMEnable(),
                'namespaceExclusions': {
                    'exactName': !workloadGiven ? "" : this.setTSMExactName(),
                    'startsWith': !workloadGiven ? "" : this.setTSMStartsWithName(),
                },
                'tkgWorkloadClusterGroupName': !workloadGiven ? "" : this.apiClient.tmcEnabled ? this.getFieldValue('vsphereWorkloadNodeSettingForm', 'clusterGroupName') : "",
                'tkgWorkloadEnableDataProtection': !workloadGiven ? "false" : this.apiClient.tmcEnabled ? this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'enableDataProtection') : "false",
                'tkgWorkloadClusterCredential': !workloadGiven ? "" : this.apiClient.tmcEnabled ? this.getFieldValue('vsphereWorkloadNodeSettingForm', 'veleroCredential') : "",
                'tkgWorkloadClusterBackupLocation': !workloadGiven ? "" : this.apiClient.tmcEnabled ? this.getFieldValue('vsphereWorkloadNodeSettingForm', 'veleroTargetLocation') : "",
                'tkgWorkloadClusterVeleroDataProtection': {
                    'enableVelero': !workloadGiven ? "false" : this.apiClient.tmcEnabled ? "false" : this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'enableVelero'),
                    'username': !workloadGiven ? "" : this.apiClient.tmcEnabled ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'veleroUsername'),
                    'passwordBase64': !workloadGiven ? "" : this.apiClient.tmcEnabled ? "" : btoa(this.getFieldValue('vsphereWorkloadNodeSettingForm', 'veleroPassword')),
                    'bucketName': !workloadGiven ? "" : this.apiClient.tmcEnabled ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'veleroBucket'),
                    'backupRegion': !workloadGiven ? "" : this.apiClient.tmcEnabled ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'veleroRegion'),
                    'backupS3Url': !workloadGiven ? "" : this.apiClient.tmcEnabled ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'veleroS3Url'),
                    'backupPublicUrl': !workloadGiven ? "" : this.apiClient.tmcEnabled ? "" : this.getFieldValue('vsphereWorkloadNodeSettingForm', 'veleroPublicUrl'),
                },
            },
            'harborSpec': {
                'enableHarborExtension': this.apiClient.sharedServicesClusterSettings.toString(),
                'harborFqdn': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'harborFqdn'),
                'harborPasswordBase64': btoa(this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'harborPassword')),
                'harborCertPath': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'harborCertPath'),
                'harborCertKeyPath': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'harborCertKeyPath'),
            },
            'tanzuExtensions': {
                'enableExtensions': this.getStringBoolFieldValue('extensionSettingForm', 'tanzuExtensions'),
                'tkgClustersName': this.getFieldValue('extensionSettingForm', 'tanzuExtensionClusters'),
                'logging': {
                    'syslogEndpoint': {
                        'enableSyslogEndpoint': this.enableLoggingExtension('Syslog'),
                        'syslogEndpointAddress': this.getFieldValue('extensionSettingForm', 'syslogEndpointAddress'),
                        'syslogEndpointPort': this.getFieldValue('extensionSettingForm', 'syslogEndpointPort'),
                        'syslogEndpointMode': this.getFieldValue('extensionSettingForm', 'syslogEndpointMode'),
                        'syslogEndpointFormat': this.getFieldValue('extensionSettingForm', 'syslogEndpointFormat'),
                    },
                    'httpEndpoint': {
                        'enableHttpEndpoint': this.enableLoggingExtension('HTTP'),
                        'httpEndpointAddress': this.getFieldValue('extensionSettingForm', 'httpEndpointAddress'),
                        'httpEndpointPort': this.getFieldValue('extensionSettingForm', 'httpEndpointPort'),
                        'httpEndpointUri': this.getFieldValue('extensionSettingForm', 'httpEndpointUri'),
                        'httpEndpointHeaderKeyValue': this.getFieldValue('extensionSettingForm', 'httpEndpointHeaderKeyValue'),
                    },
                    'kafkaEndpoint': {
                        'enableKafkaEndpoint': this.enableLoggingExtension('Kafka'),
                        'kafkaBrokerServiceName': this.getFieldValue('extensionSettingForm', 'kafkaBrokerServiceName'),
                        'kafkaTopicName': this.getFieldValue('extensionSettingForm', 'kafkaTopicName'),
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
        this.apiClient.vsphereNsxtPayload = payload
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
        if(this.checkProxy()) {
            this.generatedFileName = 'vsphere-nsxt-tkgm-proxy.json';
        } else{
            this.generatedFileName = 'vsphere-nsxt-tkgm.json';
        }
        this.viewJsonModal.open(this.generatedFileName);
    }

    public deploy() {
        const payload = this.getPayload();
        this.disableDeployButton = true;
        if(this.checkProxy()) {
            this.generatedFileName = 'vsphere-nsxt-tkgm-proxy.json';
        } else{
            this.generatedFileName = 'vsphere-nsxt-tkgm.json';
        }
        this.filePath = this.apiClient.jsonFileHomePath + '/' + this.apiClient.loggedInUser + '/' + this.generatedFileName;
        this.showAwsTestMessage = false;
        // Call the Generate API
        this.apiClient.generateInputJSON(payload, this.generatedFileName, 'vcf').subscribe((data: any) => {
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
            this.errorNotification = "Failed to download Support Bundle for Service Installer";
            this.loadingState = ClrLoadingState.DEFAULT;
        });
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
