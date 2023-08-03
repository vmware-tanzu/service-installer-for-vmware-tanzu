/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { Component, ElementRef, Input, OnInit, ViewChild } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';
import { saveAs as importedSaveAs } from "file-saver";
import { ClrLoadingState } from '@clr/angular';

// App imports
import { FormMetaDataService } from 'src/app/shared/service/form-meta-data.service';
import { FormMetaDataStore } from 'src/app/views/landing/wizard/shared/FormMetaDataStore';
import { PROVIDERS, Providers } from 'src/app/shared/constants/app.constants';
import { APP_ROUTES, Routes } from 'src/app/shared/constants/routes.constants';
import { DataService } from 'src/app/shared/service/data.service';
import { VMCDataService } from 'src/app/shared/service/vmc-data.service';
import { VsphereNsxtDataService } from 'src/app/shared/service/vsphere-nsxt-data.service';
import { VsphereTkgsService } from 'src/app/shared/service/vsphere-tkgs-data.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { ViewJSONModalComponent } from 'src/app/views/landing/wizard/shared/components/modals/view-json-modal/view-json-modal.component';
import { WizardBaseDirective } from 'src/app/views/landing/wizard/shared/wizard-base/wizard-base';
import { VCDDataService } from 'src/app/shared/service/vcd-data.service';

@Component({
    selector: 'app-tkgs-wizard',
    templateUrl: './vsphere-tkgs-wizard.component.html',
    styleUrls: ['./vsphere-tkgs-wizard.component.scss'],
})
export class VSphereTkgsWizardComponent extends WizardBaseDirective implements OnInit {
    @ViewChild(ViewJSONModalComponent) viewJsonModal: ViewJSONModalComponent;
    @ViewChild('attachments') attachment : any;
    @Input() public form;

    @Input() public providerType = 'vsphere';
    @Input() public infraType = 'tkgs';
    public APP_ROUTES: Routes = APP_ROUTES;
    public PROVIDERS: Providers = PROVIDERS;

    public deploymentPending = false;
    public disableDeployButton = false;
    public showAwsTestMessage = false;
    public showIPValidationSuccess = false;
    public errorNotification: string;
    public successNotification: string;
    public filePath: string;
    public generatedFileName: string;
    public show = false;

    public displayWizard = false;
    public fileName: string;
    public logFileName = 'service_installer_log_bundle';
    public fileUploaded = false;
    public file: File;

    public jsonWizard: boolean = false;
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    constructor(
        public apiClient: APIClient,
        router: Router,
        private formBuilder: FormBuilder,
        formMetaDataService: FormMetaDataService,
        dataService: DataService,
        vmcDataService: VMCDataService,
        nsxtDataService: VsphereNsxtDataService,
        vsphereTkgsDataService: VsphereTkgsService,
        vcdDataService: VCDDataService,
        titleService: Title,
        el: ElementRef) {
        super(router, el, formMetaDataService, titleService, dataService, vmcDataService, nsxtDataService, vsphereTkgsDataService, vcdDataService);
        if(this.apiClient.tkgsStage === 'wcp') {
            this.form = this.formBuilder.group({
                dumyForm: this.formBuilder.group({
                }),
                vsphereProviderForm: this.formBuilder.group({
                }),
                tanzuSaasSettingForm: this.formBuilder.group({
                }),
                vsphereAVINetworkSettingForm: this.formBuilder.group({
                }),
                controlPlaneSizeForm: this.formBuilder.group({
                }),
                mgmtNwForm: this.formBuilder.group({
                }),
                wrkNwForm: this.formBuilder.group({
                }),
                storagePolicyForm: this.formBuilder.group({
                }),
                TKGSGlobalConfigForm: this.formBuilder.group({
                }),
                proxyForm: this.formBuilder.group({
                }),
            });
        }
        else if (this.apiClient.tkgsStage === 'namespace') {
            this.form = this.formBuilder.group({
                vCenterDetailsForm: this.formBuilder.group({
                }),
                tanzuSaasSettingForm: this.formBuilder.group({
                }),
                workloadNetworkForm: this.formBuilder.group({
                }),
                namespaceForm: this.formBuilder.group({
                }),
                workloadClusterForm: this.formBuilder.group({
                }),
                extensionSettingForm: this.formBuilder.group({
                }),
                TKGSGlobalConfigForm: this.formBuilder.group({
                }),
                proxyForm: this.formBuilder.group({
                }),
            });
        }
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
        } else if (stepName === 'controlPlane') {
            if (this.getFieldValue('controlPlaneSizeForm', 'controlPlaneSize')) {
                return this.getFieldValue('controlPlaneSizeForm', 'controlPlaneSize') + ' size selected.';
            } else {
                return 'Select the size and resources available for control plane VM on the cluster';
            }
        }

        else if (stepName === 'aviNetworkSetting') {
            if (this.getFieldValue('vsphereAVINetworkSettingForm', 'mgmtSegmentName')) {
                return 'VMware NSX Advanced Load Balancer settings configured';
            } else {
                return 'Configure VMware NSX Advanced Load Balancer settings';
            }
        }
        else if (stepName === 'extensionSetting') {
            return  'Configure Extension settings for Tanzu Kubernestes Grid workload cluster';
        }
        else if (stepName === 'tanzuSaasSetting') {
            return 'Configure Tanzu Saas Services';
        } else if (stepName === 'customRepoSettings') {
            return 'Configure Custom Repository settings';
        }
    }


    public removeFile() {
        if (this.fileName) {
            this.attachment.nativeElement.value = '';
            this.fileUploaded = false;
            this.fileName = '';
            this.file = null;
        }
    }

    public arrToString(array) {
        let arrStr = '';
        var i=0;
        for (i; i<array.length-1; i++) {
            arrStr = arrStr + array[i] + ', ';
        }
        arrStr = arrStr + array[i];
        return arrStr;
    }

    public reviewConfiguration(review) {
        const pageTitle = 'vSphere TKGS Confirm Settings';
        this.titleService.setTitle(pageTitle);
        this.disableDeployButton = false;
        this.errorNotification = '';
        this.showAwsTestMessage = false;

        FormMetaDataStore.deleteMetaDataEntry('TKGSGlobalConfigForm', 'newCertType');
        FormMetaDataStore.deleteMetaDataEntry('TKGSGlobalConfigForm', 'newCertValue');

        let paths = this.getAdditionalTrustedCA('paths');
        let endpointUrls = this.getAdditionalTrustedCA('endpointUrls');

        FormMetaDataStore.saveMetaDataEntry('TKGSGlobalConfigForm', 'newCertType', {
            label: 'ADDITIONAL CERTIFICATE PATHS',
            displayValue: this.arrToString(paths),
        });

        FormMetaDataStore.saveMetaDataEntry('TKGSGlobalConfigForm', 'newCertValue', {
            label: 'ADDITIONAL CERTIFICATE URLs',
            displayValue: this.arrToString(endpointUrls),
        });

        if (this.apiClient.tkgsStage === 'namespace') {
            if(this.getFieldValue('namespaceForm', 'namespaceName') === 'CREATE NEW') {
                FormMetaDataStore.deleteMetaDataEntry('namespaceForm', 'newStoragePolicy');
                FormMetaDataStore.deleteMetaDataEntry('namespaceForm', 'newStoragePolicyLimit');
                FormMetaDataStore.deleteMetaDataEntry('workloadClusterForm', 'allowedStorageClass');

                let storagePolicy = [...this.getFieldValue('namespaceForm', 'storageSpec').keys()];
                let storageLimit = [...this.getFieldValue('namespaceForm', 'storageSpec').values()];
                FormMetaDataStore.saveMetaDataEntry('namespaceForm', 'newStoragePolicy', {
                    label: 'STORAGE POLICY',
                    displayValue: this.arrToString(storagePolicy),
                });
                FormMetaDataStore.saveMetaDataEntry('namespaceForm', 'newStoragePolicyLimit', {
                    label: 'STORAGE POLICY LIMIT',
                    displayValue: this.arrToString(storageLimit),
                });
                let vmClass = this.getFieldValue('namespaceForm', 'vmClass');
                FormMetaDataStore.saveMetaDataEntry('namespaceForm', 'vmClass', {
                    label: 'VM CLASS',
                    displayValue: this.arrToString(vmClass),
                });
                let allowedStorageClass = this.getFieldValue('workloadClusterForm', 'allowedStorageClass');
                FormMetaDataStore.saveMetaDataEntry('workloadClusterForm', 'allowedStorageClass', {
                    label: 'ALLOWED STORAGE CLASS',
                    displayValue: this.arrToString(allowedStorageClass),
                });
            }

            // Control Plane Additional Volume labels
            let ctrlVolumes = this.getFieldValue('workloadClusterForm', 'tkgsControlVolumes');

            FormMetaDataStore.deleteMetaDataEntry('workloadClusterForm', 'newControlVolumeName');
            FormMetaDataStore.deleteMetaDataEntry('workloadClusterForm', 'newControlMountPath');
            FormMetaDataStore.deleteMetaDataEntry('workloadClusterForm', 'newControlCapacity');
            FormMetaDataStore.deleteMetaDataEntry('workloadClusterForm', 'newControlStorageClass');
            let ctrlVolNames=[], ctrlMountPaths=[], ctrlStorage=[], ctrlStorageClasses=[];
            for (const [name, value] of ctrlVolumes) {
                ctrlVolNames.push(name);
                ctrlMountPaths.push(value.split(':')[0]);
                ctrlStorage.push(value.split(':')[1].split('#')[0] + 'Gi');
                ctrlStorageClasses.push(value.split('#')[1]);
            }

            FormMetaDataStore.saveMetaDataEntry('workloadClusterForm', 'newControlVolumeName' , {
                label: 'CONTROL PLANE ADDTIONAL VOLUME NAMES',
                displayValue: this.arrToString(ctrlVolNames),
            });
            FormMetaDataStore.saveMetaDataEntry('workloadClusterForm', 'newControlMountPath' , {
                label: 'CONTROL PLANE ADDTIONAL VOLUME MOUNT PATHS',
                displayValue: this.arrToString(ctrlMountPaths),
            });
            FormMetaDataStore.saveMetaDataEntry('workloadClusterForm', 'newControlCapacity' , {
                label: 'CONTROL PLANE ADDTIONAL CAPACITIES',
                displayValue: this.arrToString(ctrlStorage),
            });
            FormMetaDataStore.saveMetaDataEntry('workloadClusterForm', 'newControlStorageClass' , {
                label: 'CONTROL PLANE ADDTIONAL STORAGE CLASSES',
                displayValue: this.arrToString(ctrlStorageClasses),
            });

            let volumes = this.getFieldValue('workloadClusterForm', 'tkgsWorkerVolumes');
            FormMetaDataStore.deleteMetaDataEntry('workloadClusterForm', 'newWorkerVolumeName');
            FormMetaDataStore.deleteMetaDataEntry('workloadClusterForm', 'newWorkerMountPath');
            FormMetaDataStore.deleteMetaDataEntry('workloadClusterForm', 'newWorkerCapacity');
            FormMetaDataStore.deleteMetaDataEntry('workloadClusterForm', 'newWorkerStorageClass');

            let volNames=[], mountPaths=[], storage=[], storageClasses=[];

            for (const [name, value] of volumes) {
                volNames.push(name);
                mountPaths.push(value.split(':')[0]);
                storage.push(value.split(':')[1].split('#')[0] + 'Gi');
                storageClasses.push(value.split('#')[1]);
            }

            FormMetaDataStore.saveMetaDataEntry('workloadClusterForm', 'newWorkerVolumeName' , {
                label: 'WORKER NODES ADDTIONAL VOLUME NAMES',
                displayValue: this.arrToString(volNames),
            });
            FormMetaDataStore.saveMetaDataEntry('workloadClusterForm', 'newWorkerMountPath' , {
                label: 'WORKER NODES ADDTIONAL VOLUME MOUNT PATHS',
                displayValue: this.arrToString(mountPaths),
            });
            FormMetaDataStore.saveMetaDataEntry('workloadClusterForm', 'newWorkerCapacity' , {
                label: 'WORKER NODES ADDTIONAL CAPACITIES',
                displayValue: this.arrToString(storage),
            });
            FormMetaDataStore.saveMetaDataEntry('workloadClusterForm', 'newWorkerStorageClass' , {
                label: 'WORKER NODES ADDTIONAL STORAGE CLASSES',
                displayValue: this.arrToString(storageClasses),
            });
        }
        this.review = review;
    }


    public downloadSupportBundle() {
        this.loadingState = ClrLoadingState.LOADING;
        this.apiClient.downloadLogBundle('vsphere').subscribe(blob => {
            importedSaveAs(blob, this.logFileName);
            this.loadingState = ClrLoadingState.DEFAULT;
        }, (error: any) => {
            this.errorNotification = "Failed to download Support Bundle for Service Installer";
            this.loadingState = ClrLoadingState.LOADING;
        });
    }


    getTkgsHttpProxyParam() {
        if (this.getBooleanFieldValue('proxyForm', 'proxySettings')) {
            if (this.getFieldValue('proxyForm', 'httpProxyUsername') !== '') {
                let username = this.getFieldValue('proxyForm', 'httpProxyUsername');
                let password = this.getFieldValue('proxyForm', 'httpProxyPassword');
                let url = this.getFieldValue('proxyForm', 'httpProxyUrl');
                let httpProxy = 'http://' + username + ':' + password +'@'+ url.substr(7);
                return httpProxy;
            } else {
                return this.getFieldValue('proxyForm', 'httpProxyUrl');
            }
        } else {
            return '';
        }
    }

    getTkgsHttpsProxyParam() {
        if (this.getFieldValue('proxyForm', 'httpsProxyUsername') !== '') {
            let username = this.getFieldValue('proxyForm', 'httpsProxyUsername');
            let password = this.getFieldValue('proxyForm', 'httpsProxyPassword');
            let url = this.getFieldValue('proxyForm', 'httpsProxyUrl');
            let httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
            return httpsProxy;
        } else {
            return this.getFieldValue('proxyForm', 'httpsProxyUrl');
        }
    }

    public getTkgsHttpsProxy() {
        let httpsProxy = '';
        if (this.getBooleanFieldValue('proxyForm', 'proxySettings')) {
            if (this.getBooleanFieldValue('proxyForm', 'isSameAsHttp')) {
                httpsProxy = this.getTkgsHttpProxyParam();
            } else {
                httpsProxy = this.getTkgsHttpsProxyParam();
            }
        } else {
            httpsProxy = '';
        }
        return httpsProxy;
    }

    public enableLoggingExtension(key) {
        if (this.getFieldValue('extensionSettingForm', 'loggingEndpoint') === key) {
            return 'true';
        } else {
            return 'false';
        }
    }

    public getTkgsStorageSpec() {
        let storageSpec = this.getFieldValue('namespaceForm', 'storageSpec');
        let specList = [];
        for (const [key, value] of storageSpec) {
            if (value !== "") {
                let param = {
                    'storageLimit': value,
                    'storagePolicy': key,
                };
                specList.push(param);
            } else {
                let param = {
                    'storagePolicy': key,
                };
                specList.push(param);
            }
        }
        return specList;
    }

    public getTkgsControlPlaneAdditionalVolumes() {
        let volumeList = [];
        let cluster_kind = this.getFieldValue('workloadClusterForm', "tkgsVsphereWorkloadClusterKind");
        if (cluster_kind === "ClusterClass") return volumeList;

        let volumes = this.getFieldValue('workloadClusterForm', 'tkgsControlVolumes');
        for (const [name, value] of volumes) {
            let volumeConfig = {
                'name': name,
                'mountPath': value.split(':')[0],
                'storage': value.split(':')[1].split('#')[0] + 'Gi',
                'storageClass': value.split('#')[1],
            }
            volumeList.push(volumeConfig);
        }
        return volumeList;
    }

    public getTkgsWorkerAdditionalVolumes() {
        let volumeList = [];
        let cluster_kind = this.getFieldValue('workloadClusterForm', "tkgsVsphereWorkloadClusterKind");
        if (cluster_kind === "ClusterClass") return volumeList;

        let volumes = this.getFieldValue('workloadClusterForm', 'tkgsWorkerVolumes');
        for (const [name, value] of volumes) {
            let volumeConfig = {
                'name': name,
                'mountPath': value.split(':')[0],
                'storage': value.split(':')[1].split('#')[0] + 'Gi',
                'storageClass': value.split('#')[1],
            }
            volumeList.push(volumeConfig);
        }
        return volumeList;
    }

    public getTkgsResourceSpec() {
        let cpuLimit = this.getFieldValue('namespaceForm', 'cpuLimit');
        let memLimit = this.getFieldValue('namespaceForm', 'memLimit');
        let storageLimit = this.getFieldValue('namespaceForm', 'storageLimit');
        let specDict = {};
        if (cpuLimit!=="") {
            specDict['cpuLimit'] = cpuLimit;
        }
        if (memLimit!=="") {
            specDict['memoryLimit'] = memLimit;
        }
        if (storageLimit!=="") {
            specDict['storageRequestLimit'] = storageLimit;
        }
        return specDict;
    }

    public setTSMEnable() {
        const tmcEnable = this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings');
        if (tmcEnable === 'true') {
            return this.getStringBoolFieldValue('workloadClusterForm', 'tsmSettings');
        } else {
            return 'false';
        }
    }

    public setTSMExactName() {
        const tmcEnable = this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings');
        if (tmcEnable === 'true') {
            const tsmEnable = this.getStringBoolFieldValue('workloadClusterForm', 'tsmSettings');
            if (tsmEnable === 'true') {
                return this.getFieldValue('workloadClusterForm', 'exactName');
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
            const tsmEnable = this.getStringBoolFieldValue('workloadClusterForm', 'tsmSettings');
            if (tsmEnable === 'true') {
                return this.getFieldValue('workloadClusterForm', 'startsWithName');
            } else {
                return '';
            }
        } else {
            return '';
        }
    }

    public getAdditionalTrustedCA(type: string) {
        let addCerts = this.apiClient.tkgsAdditionalCerts;
        let paths = [];
        let endpointUrls = [];
        for (let [cert, type] of addCerts) {
            // console.log(cert);
            if(type.toLowerCase() === 'path') {
                paths.push(cert);
            } else if (type.toLowerCase() === 'endpoint') {
                endpointUrls.push(cert);
            }
        }
        if(type === 'paths') return paths;
        else if(type === 'endpointUrls') return endpointUrls;
        else return [];
    }
    public getPayload() {
        let payload;
        if (this.apiClient.tkgsStage === 'wcp') {
            payload = {
                'envSpec': {
                    'envType': 'tkgs-wcp',
                    'vcenterDetails': {
                        'vcenterAddress': this.getFieldValue('vsphereProviderForm', 'vcenterAddress'),
                        'vcenterSsoUser': this.getFieldValue('vsphereProviderForm', 'username'),
                        'vcenterSsoPasswordBase64': btoa(this.form.get('vsphereProviderForm').get('password').value),
                        'vcenterDatacenter': this.getFieldValue('vsphereProviderForm', 'datacenter'),
                        'vcenterCluster': this.getFieldValue('vsphereProviderForm', 'cluster'),
                        'vcenterDatastore': this.getFieldValue('vsphereProviderForm', 'datastore'),
                        'contentLibraryName': this.getFieldValue('vsphereProviderForm', 'contentLib'),
                        'aviOvaName': this.getFieldValue('vsphereProviderForm', 'aviOvaImage'),
                    },
                    'marketplaceSpec': {
                        'refreshToken': this.getFieldValue('vsphereProviderForm', 'marketplaceRefreshToken'),
                    },
                    'saasEndpoints': {
                        'tmcDetails': {
                            'tmcAvailability': this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings'),
                            'tmcRefreshToken': this.getFieldValue('tanzuSaasSettingForm', 'refreshToken'),
                            'tmcInstanceURL': this.getFieldValue('tanzuSaasSettingForm', 'tmcInstanceURL'),
                            'tmcSupervisorClusterName': this.getFieldValue('tanzuSaasSettingForm', 'clusterName'),
                            'tmcSupervisorClusterGroupName': this.getFieldValue('tanzuSaasSettingForm', 'clusterGroupName'),
                        },
                    },
                    'infraComponents': {
                        'dnsServersIp': this.getFieldValue('dumyForm', 'dnsServer'),
                        'searchDomains': this.getFieldValue('dumyForm', 'searchDomain'),
                        'ntpServers': this.getFieldValue('dumyForm', 'ntpServer'),
                    },
                },
                'tkgsComponentSpec': {
                    'controlPlaneSize': this.getFieldValue('controlPlaneSizeForm', 'controlPlaneSize'),
                    'aviMgmtNetwork': {
                        'aviMgmtNetworkName': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtNetworkName'),
                        'aviMgmtNetworkGatewayCidr': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtGatewayIp'),
                        'aviMgmtServiceIpStartRange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtDhcpStartRange'),
                        'aviMgmtServiceIpEndRange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtDhcpEndRange'),
                    },
                    'aviComponents': {
                        'aviPasswordBase64': btoa(this.getFieldValue('vsphereAVINetworkSettingForm', 'aviPassword')),
                        'aviBackupPassphraseBase64': btoa(this.getFieldValue('vsphereAVINetworkSettingForm', 'aviBackupPassphrase')),
                        'enableAviHa': this.getStringBoolFieldValue('vsphereAVINetworkSettingForm', 'enableHA'),
                        'typeOfLicense': this.getFieldValue('vsphereAVINetworkSettingForm', 'typeOfLicense') === '' ? 'enterprise' : this.getFieldValue('vsphereAVINetworkSettingForm', 'typeOfLicense'),
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
                    'tkgsVipNetwork': {
                        'tkgsVipNetworkName': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviClusterVipNetworkName'),
                        'tkgsVipNetworkGatewayCidr': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviClusterVipGatewayIp'),
                        'tkgsVipIpStartRange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviClusterVipStartRange'),
                        'tkgsVipIpEndRange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviClusterVipEndRange'),
                    },
                    'tkgsMgmtNetworkSpec': {
                        'tkgsMgmtNetworkName': this.getFieldValue('mgmtNwForm', 'segmentName'),
                        'tkgsMgmtNetworkGatewayCidr': this.getFieldValue('mgmtNwForm', 'gatewayAddress'),
                        'tkgsMgmtNetworkStartingIp': this.getFieldValue('mgmtNwForm', 'startAddress'),
                        'tkgsMgmtNetworkDnsServers': this.getFieldValue('mgmtNwForm', 'dnsServer'),
                        'tkgsMgmtNetworkSearchDomains': this.getFieldValue('mgmtNwForm', 'searchDomain'),
                        'tkgsMgmtNetworkNtpServers': this.getFieldValue('mgmtNwForm', 'ntpServer'),
                        'subscribedContentLibraryName': this.getFieldValue('mgmtNwForm', 'contentLib'),
                    },
                    'tkgsStoragePolicySpec': {
                        'masterStoragePolicy': this.getFieldValue('storagePolicyForm', 'masterStoragePolicy'),
                        'ephemeralStoragePolicy': this.getFieldValue('storagePolicyForm', 'ephemeralStoragePolicy'),
                        'imageStoragePolicy': this.getFieldValue('storagePolicyForm', 'imageStoragePolicy'),
                    },
                    'tkgsPrimaryWorkloadNetwork': {
                        'tkgsPrimaryWorkloadPortgroupName': this.getFieldValue('wrkNwForm', 'segmentName'),
                        'tkgsPrimaryWorkloadNetworkName': this.getFieldValue('wrkNwForm', 'workloadSegmentName'),
                        'tkgsPrimaryWorkloadNetworkGatewayCidr': this.getFieldValue('wrkNwForm', 'gatewayAddress'),
                        'tkgsPrimaryWorkloadNetworkStartRange': this.getFieldValue('wrkNwForm', 'startAddress'),
                        'tkgsPrimaryWorkloadNetworkEndRange': this.getFieldValue('wrkNwForm', 'endAddress'),
                        'tkgsWorkloadDnsServers': this.getFieldValue('wrkNwForm', 'dnsServer'),
                        'tkgsWorkloadNtpServers': this.getFieldValue('wrkNwForm', 'ntpServer'),
                        'tkgsWorkloadServiceCidr': this.getFieldValue('wrkNwForm', 'serviceCidr'),
                    },
                    'tkgServiceConfig': {
                        'proxySpec': {
                            'enableProxy': this.getStringBoolFieldValue('proxyForm', 'proxySettings'),
                            'httpProxy': this.getTkgsHttpProxyParam(),
                            'httpsProxy': this.getTkgsHttpsProxy(),
                            'noProxy': this.getFieldValue('proxyForm', 'noProxy'),
                            'proxyCert': this.getFieldValue('proxyForm', 'proxyCert'),
                        },
                        'defaultCNI': this.getFieldValue('TKGSGlobalConfigForm', 'defaultCNI'),
                        'additionalTrustedCAs': {
                            'paths': this.getAdditionalTrustedCA('paths'),
                            'endpointUrls': this.getAdditionalTrustedCA('endpointUrls'),
                        }
                    }
                },
            };
        } else if (this.apiClient.tkgsStage === 'namespace') {
            payload = {
                'envSpec': {
                    'envType': 'tkgs-ns',
                    'vcenterDetails': {
                        'vcenterAddress': this.getFieldValue('vCenterDetailsForm', 'vcenterAddress'),
                        'vcenterSsoUser': this.getFieldValue('vCenterDetailsForm', 'username'),
                        'vcenterSsoPasswordBase64': btoa(this.getFieldValue('vCenterDetailsForm', 'password')),
                        'vcenterDatacenter': this.getFieldValue('vCenterDetailsForm', 'datacenter'),
                        'vcenterCluster': this.getFieldValue('vCenterDetailsForm', 'cluster'),
                    },
                    'saasEndpoints': {
                        'tmcDetails': {
                            'tmcAvailability': this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings'),
                            'tmcRefreshToken': this.getFieldValue('tanzuSaasSettingForm', 'refreshToken'),
                            'tmcInstanceURL': this.getFieldValue('tanzuSaasSettingForm', 'tmcInstanceURL'),
                            'tmcSupervisorClusterName': this.getFieldValue('tanzuSaasSettingForm', 'clusterName'),
                        },
                        'tanzuObservabilityDetails': {
                            'tanzuObservabilityAvailability': this.getStringBoolFieldValue('tanzuSaasSettingForm', 'toSettings'),
                            'tanzuObservabilityUrl': this.getFieldValue('tanzuSaasSettingForm', 'toUrl'),
                            'tanzuObservabilityRefreshToken': this.getFieldValue('tanzuSaasSettingForm', 'toRefreshToken')
                        }
                    },
                },
                'tkgsComponentSpec': {
                    'tkgsWorkloadNetwork': {
                        'tkgsWorkloadNetworkName': this.getFieldValue('workloadNetworkForm', 'networkName') === 'CREATE NEW' ? this.getFieldValue('workloadNetworkForm', 'newNetworkName') : this.getFieldValue('workloadNetworkForm', 'networkName'),
                        'tkgsWorkloadPortgroupName': this.getFieldValue('workloadNetworkForm', 'portGroup'),
                        'tkgsWorkloadNetworkGatewayCidr': this.getFieldValue('workloadNetworkForm', 'gatewayAddress'),
                        'tkgsWorkloadNetworkStartRange': this.getFieldValue('workloadNetworkForm', 'startAddress'),
                        'tkgsWorkloadNetworkEndRange': this.getFieldValue('workloadNetworkForm', 'endAddress'),
                        'tkgsWorkloadServiceCidr': this.getFieldValue('wrkNwForm', 'serviceCidr'),
                    },
                    'tkgsVsphereNamespaceSpec': {
                        'tkgsVsphereNamespaceName': this.getFieldValue('namespaceForm', 'namespaceName') === 'CREATE NEW' ? this.getFieldValue('namespaceForm', 'newNamespaceName') : this.getFieldValue('namespaceForm', 'namespaceName'),
                        'tkgsVsphereNamespaceDescription': this.getFieldValue('namespaceForm', 'namespaceDescription'),
                        'tkgsVsphereNamespaceContentLibrary': this.getFieldValue('namespaceForm', 'contentLib'),
                        'tkgsVsphereNamespaceVmClasses': this.getFieldValue('namespaceForm', 'vmClass') === "" ? [] : this.getFieldValue('namespaceForm', 'vmClass'),
                        'tkgsVsphereNamespaceResourceSpec': this.getTkgsResourceSpec(),
                        'tkgsVsphereNamespaceStorageSpec': this.getTkgsStorageSpec(),
                        'tkgsVsphereWorkloadClusterSpec': {
                            'tkgsVsphereNamespaceName': this.getFieldValue('namespaceForm', 'namespaceName') === 'CREATE NEW' ? this.getFieldValue('namespaceForm', 'newNamespaceName') : this.getFieldValue('namespaceForm', 'namespaceName'),
                            'tkgsVsphereWorkloadClusterName': this.getFieldValue('workloadClusterForm', 'clusterName'),
                            'tkgsVsphereWorkloadClusterKind': this.apiClient.vcenterVersion === "8" ? this.getFieldValue('workloadClusterForm', 'clusterKind') : "TanzuKubernetesCluster",
                            'tkgsVsphereWorkloadClusterVersion': this.getFieldValue('workloadClusterForm', 'clusterVersion'),
                            'allowedStorageClasses': this.getFieldValue('workloadClusterForm', 'allowedStorageClass'),
                            'defaultStorageClass': this.getFieldValue('workloadClusterForm', 'defaultStorageClass'),
                            'nodeStorageClass': this.getFieldValue('workloadClusterForm', 'nodeStorageClass'),
                            'serviceCidrBlocks': this.getFieldValue('workloadClusterForm', 'serviceCidr'),
                            'podCidrBlocks': this.getFieldValue('workloadClusterForm', 'podCidr'),
                            'controlPlaneVmClass': this.getFieldValue('workloadClusterForm', 'controlPlaneVmClass'),
                            'workerVmClass': this.getFieldValue('workloadClusterForm', 'workerVmClass'),
                            'workerNodeCount': this.getFieldValue('workloadClusterForm', 'workerNodeCount').toString(),
                            'enableControlPlaneHa': this.getStringBoolFieldValue('workloadClusterForm', 'enableHA'),
                            'tkgWorkloadTsmIntegration': this.setTSMEnable(),
                            'namespaceExclusions': {
                                'exactName': this.setTSMExactName(),
                                'startsWith': this.setTSMStartsWithName(),
                            },
                            'tkgsWorkloadClusterGroupName': this.getFieldValue('workloadClusterForm', 'clusterGroupName'),
                            'tkgsWorkloadEnableDataProtection': this.getStringBoolFieldValue('workloadClusterForm', 'enableDataProtection'),
                            'tkgWorkloadClusterCredential': this.getFieldValue('workloadClusterForm', 'veleroCredential'),
                            'tkgWorkloadClusterBackupLocation': this.getFieldValue('workloadClusterForm', 'veleroTargetLocation'),
                            'controlPlaneVolumes': this.getTkgsControlPlaneAdditionalVolumes(),
                            'workerVolumes': this.getTkgsWorkerAdditionalVolumes(),
                            'tkgWorkloadClusterVeleroDataProtection': {
                                'enableVelero': this.getStringBoolFieldValue('workloadClusterForm', 'enableVelero'),
                                'username': this.getFieldValue('workloadClusterForm', 'veleroUsername'),
                                'passwordBase64': btoa(this.getFieldValue('workloadClusterForm', 'veleroPassword')),
                                'bucketName': this.getFieldValue('workloadClusterForm', 'veleroBucket'),
                                'backupRegion': this.getFieldValue('workloadClusterForm', 'veleroRegion'),
                                'backupS3Url': this.getFieldValue('workloadClusterForm', 'veleroS3Url'),
                                'backupPublicUrl': this.getFieldValue('workloadClusterForm', 'veleroPublicUrl'),
                            },
                        },
                    },
                    'tkgServiceConfig': {
                        'proxySpec': {
                            'enableProxy': this.getStringBoolFieldValue('proxyForm', 'proxySettings'),
                            'httpProxy': this.getTkgsHttpProxyParam(),
                            'httpsProxy': this.getTkgsHttpsProxy(),
                            'noProxy': this.getFieldValue('proxyForm', 'noProxy'),
                            'proxyCert': this.getFieldValue('proxyForm', 'proxyCert'),
                        },
                        'defaultCNI': this.getFieldValue('TKGSGlobalConfigForm', 'defaultCNI'),
                        'additionalTrustedCAs': {
                            'paths': this.getAdditionalTrustedCA('paths'),
                            'endpointUrls': this.getAdditionalTrustedCA('endpointUrls'),
                        }
                    }
                },
                'tanzuExtensions': {
                    'enableExtensions': this.getStringBoolFieldValue('extensionSettingForm', 'tanzuExtensions'),
                    'tkgClustersName': this.getFieldValue('extensionSettingForm', 'tanzuExtensionClusters'),
                    'harborSpec': {
                        'enableHarborExtension': this.getStringBoolFieldValue('extensionSettingForm', 'harborSettings'),
                        'harborFqdn': this.getFieldValue('extensionSettingForm', 'harborFqdn'),
                        'harborPasswordBase64': btoa(this.getFieldValue('extensionSettingForm', 'harborPassword')),
                        'harborCertPath': this.getFieldValue('extensionSettingForm', 'harborCertPath'),
                        'harborCertKeyPath': this.getFieldValue('extensionSettingForm', 'harborCertKeyPath'),
                    },
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
        }
        this.apiClient.vpshereTkgsPayload = payload;
        return payload;
    }

    openViewJsonModal() {
        const payload = this.getPayload();
        if(payload['envSpec']['envType']==='tkgs-ns') {
            this.generatedFileName = 'vsphere-dvs-tkgs-namespace.json';
        } else if (payload['envSpec']['envType']==='tkgs-wcp') {
            this.generatedFileName = 'vsphere-dvs-tkgs-wcp.json';
        }
        this.viewJsonModal.open(this.generatedFileName);
    }

    public deploy() {
        const payload = this.getPayload();
        this.disableDeployButton = true;
        if(payload['envSpec']['envType']==='tkgs-ns') {
            this.generatedFileName = 'vsphere-dvs-tkgs-namespace.json';
        } else if (payload['envSpec']['envType']==='tkgs-wcp') {
            this.generatedFileName = 'vsphere-dvs-tkgs-wcp.json';
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
