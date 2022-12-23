/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { Component, ElementRef, Input, OnInit, ViewChild } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';
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
import { VCDDataService } from 'src/app/shared/service/vcd-data.service';

@Component({
    selector: 'vcd-wizard',
    templateUrl: './vcd-wizard.component.html',
    styleUrls: ['./vcd-wizard.component.scss'],
})
export class VCDWizardComponent extends WizardBaseDirective implements OnInit {
    @ViewChild(ViewJSONModalComponent) viewJsonModal: ViewJSONModalComponent;
    @ViewChild('attachments') attachment: any;
    @Input() public form;
    @Input() public providerType = 'vcd';
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
        public vcdDataService: VCDDataService,
        titleService: Title,
        el: ElementRef) {

        super(router, el, formMetaDataService, titleService, dataService, vmcDataService, nsxtDataService, vsphereTkgsDataService, vcdDataService);

        this.form = this.formBuilder.group({
            dnsNtpForm: this.formBuilder.group({}),
            vcdSpecForm: this.formBuilder.group({}),
            aviControllerForm: this.formBuilder.group({}),
            aviNsxtCloudForm: this.formBuilder.group({}),
            t0RouterForm: this.formBuilder.group({}),
            svcOrgForm: this.formBuilder.group({}),
            svcOrgVdcForm: this.formBuilder.group({}),
            svcOrgEdgeGatewayForm: this.formBuilder.group({}),
            segForm: this.formBuilder.group({}),
            catalogForm: this.formBuilder.group({}),
            vappForm: this.formBuilder.group({}),
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

        this.titleService.setTitle('Service Installer');
    }

    public getStepDescription(stepName: string): string {
        if (stepName === 'vcdSpecForm') {
            return 'Validate the vCloud Director account for Tanzu Kubernetes Grid configuration';
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
        } else if (stepName === 'identity') {
            if (this.getFieldValue('IdentityMgmtForm', 'identityType') === 'oidc' &&
                this.getFieldValue('IdentityMgmtForm', 'issuerURL')) {
                return 'OIDC configured: ' + this.getFieldValue('IdentityMgmtForm', 'issuerURL')
            } else if (this.getFieldValue('IdentityMgmtForm', 'identityType') === 'ldap' &&
                        this.getFieldValue('IdentityMgmtForm', 'endpointIp')) {
                return 'LDAP configured: ' + this.getFieldValue('IdentityMgmtForm', 'endpointIp') + ':' +
                    this.getFieldValue('IdentityMgmtForm', 'endpointPort');
            } else {
                return 'Specify identity management'
            }
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


    public reviewConfiguration(review) {
        const pageTitle = 'VCD Confirm Settings';
        this.titleService.setTitle(pageTitle);
        this.disableDeployButton = false;
        this.errorNotification = '';
        this.showAwsTestMessage = false;
        this.review = review;
    }


    public getAviControllerSpec(deployAvi: boolean) {
        let aviSpec;
        if(deployAvi) {
            // GREENFIELD
            aviSpec = {
                'deployAvi': 'true',
                'vcenterDetails': {
                    'vcenterAddress': this.getFieldValue('aviControllerForm', 'vcenterAddress'),
                    'vcenterSsoUser': this.getFieldValue('aviControllerForm', 'vcenterSsoUser'),
                    'vcenterSsoPasswordBase64': btoa(this.getFieldValue('aviControllerForm', 'vcenterSsoPasswordBase64')),
                    'vcenterDatacenter': this.getFieldValue('aviControllerForm', 'vcenterDatacenter'),
                    'vcenterCluster': this.getFieldValue('aviControllerForm', 'vcenterCluster'),
                    'vcenterDatastore': this.getFieldValue('aviControllerForm', 'vcenterDatastore'),
                    'contentLibraryName': this.getFieldValue('aviControllerForm', 'contentLibraryName'),
                    'aviOvaName': this.getFieldValue('aviControllerForm', 'aviOvaName'),
                    'resourcePoolName': this.getFieldValue('aviControllerForm', 'resourcePoolName'),
                },
                'aviMgmtNetwork': {
                    'aviMgmtNetworkName': this.getFieldValue('aviControllerForm', 'aviMgmtNetworkName'),
                    'aviMgmtNetworkGatewayCidr': this.getFieldValue('aviControllerForm', 'aviMgmtNetworkGatewayCidr'),
                },
                'aviComponentsSpec': {
                    'aviUsername': this.getFieldValue('aviControllerForm', 'aviUsername'),
                    'aviPasswordBase64': btoa(this.getFieldValue('aviControllerForm', 'aviPasswordBase64'),),
                    'aviBackupPassphraseBase64': btoa(this.getFieldValue('aviControllerForm', 'aviBackupPassphraseBase64'),),
                    'enableAviHa': this.getStringBoolFieldValue('aviControllerForm', 'enableAviHa'),
                    'aviController01Ip': this.getFieldValue('aviControllerForm', 'aviController01Ip'),
                    'aviController01Fqdn': this.getFieldValue('aviControllerForm', 'aviController01Fqdn'),
                    'aviController02Ip': this.getFieldValue('aviControllerForm', 'aviController02Ip'),
                    'aviController02Fqdn': this.getFieldValue('aviControllerForm', 'aviController02Fqdn'),
                    'aviController03Ip': this.getFieldValue('aviControllerForm', 'aviController03Ip'),
                    'aviController03Fqdn': this.getFieldValue('aviControllerForm', 'aviController03Fqdn'),
                    'aviClusterIp': this.getFieldValue('aviControllerForm', 'aviClusterIp'),
                    'aviClusterFqdn': this.getFieldValue('aviControllerForm', 'aviClusterFqdn'),
                    'aviSize': this.getFieldValue('aviControllerForm', 'aviSize'),
                    'aviCertPath': this.getFieldValue('aviControllerForm', 'aviCertPath'),
                    'aviCertKeyPath': this.getFieldValue('aviControllerForm', 'aviCertKeyPath'),
                },
                'aviVcdDisplayName': this.getFieldValue('aviControllerForm', 'aviVcdDisplayName'),
            };
        } else {
            aviSpec = {
                'deployAvi': 'false',
                'aviComponentsSpec': {
                    'aviClusterIp': this.getFieldValue('aviControllerForm', 'aviClusterIp'),
                    'aviClusterFqdn': this.getFieldValue('aviControllerForm', 'aviClusterFqdn'),
                    'aviUsername': this.getFieldValue('aviControllerForm', 'aviUsername'),
                    'aviPasswordBase64': btoa(this.getFieldValue('aviControllerForm', 'aviPasswordBase64')),
                },
                'aviVcdDisplayName': this.getFieldValue('aviControllerForm', 'aviVcdDisplayName') === 'IMPORT TO VCD' ? this.getFieldValue('aviControllerForm', 'aviVcdDisplayNameInput') : this.getFieldValue('aviControllerForm', 'aviVcdDisplayName'),
            };
        }
        return aviSpec;
    }


    public getNSXTCloudSpec(deployNSXTCloud: boolean) {
        let nsxtCloudSpec;
        if(deployNSXTCloud) {
            nsxtCloudSpec  = {
                'configureAviNsxtCloud': 'true',
                'nsxDetails': {
                    'nsxtAddress': this.getFieldValue('aviNsxtCloudForm', 'nsxtAddress'),
                    'nsxtUser': this.getFieldValue('aviNsxtCloudForm', 'nsxtUser'),
                    'nsxtUserPasswordBase64': btoa(this.getFieldValue('aviNsxtCloudForm', 'nsxtUserPasswordBase64')),
                },
                'vcenterDetails': {
                    'vcenterAddress': this.getFieldValue('aviNsxtCloudForm', 'vcenterAddress'),
                    'vcenterSsoUser': this.getFieldValue('aviNsxtCloudForm', 'vcenterSsoUser'),
                    'vcenterSsoPasswordBase64': btoa(this.getFieldValue('aviNsxtCloudForm', 'vcenterSsoPasswordBase64')),
                },
                'aviSeTier1Details': {
                    'nsxtTier1SeMgmtNetworkName': this.getFieldValue('aviNsxtCloudForm', 'nsxtTier1SeMgmtNetworkName'),
                    'nsxtOverlay': this.getFieldValue('aviNsxtCloudForm', 'nsxtOverlay'),
                },
                'aviSeMgmtNetwork': {
                    'aviSeMgmtNetworkName': this.getFieldValue('aviNsxtCloudForm', 'aviSeMgmtNetworkName'),
                    'aviSeMgmtNetworkGatewayCidr': this.getFieldValue('aviNsxtCloudForm', 'aviSeMgmtNetworkGatewayCidr'),
                    'aviSeMgmtNetworkDhcpStartRange': this.getFieldValue('aviNsxtCloudForm', 'aviSeMgmtNetworkDhcpStartRange'),
                    'aviSeMgmtNetworkDhcpEndRange': this.getFieldValue('aviNsxtCloudForm', 'aviSeMgmtNetworkDhcpEndRange'),
                },
                'aviNsxCloudName': this.getFieldValue('aviNsxtCloudForm', 'aviNsxCloudName'),
                'nsxtCloudVcdDisplayName': this.getFieldValue('aviNsxtCloudForm', 'nsxtCloudVcdDisplayName'),
            };
        } else {
            nsxtCloudSpec  = {
                'configureAviNsxtCloud': 'false',
                'nsxDetails': {
                    'nsxtAddress': this.getFieldValue('aviNsxtCloudForm', 'nsxtAddress'),
                    'nsxtUser': this.getFieldValue('aviNsxtCloudForm', 'nsxtUser'),
                    'nsxtUserPasswordBase64': btoa(this.getFieldValue('aviNsxtCloudForm', 'nsxtUserPasswordBase64')),
                },
                'vcenterDetails': {
                    'vcenterAddress': this.getFieldValue('aviNsxtCloudForm', 'vcenterAddress'),
                    'vcenterSsoUser': this.getFieldValue('aviNsxtCloudForm', 'vcenterSsoUser'),
                    'vcenterSsoPasswordBase64': btoa(this.getFieldValue('aviNsxtCloudForm', 'vcenterSsoPasswordBase64')),
                },
                'aviSeTier1Details': {
                    'nsxtOverlay': this.getFieldValue('aviNsxtCloudForm', 'nsxtOverlay'),
                },
                'aviNsxCloudName': this.getFieldValue('aviNsxtCloudForm', 'aviNsxCloudName'),
                'nsxtCloudVcdDisplayName': this.getFieldValue('aviNsxtCloudForm', 'nsxtCloudVcdDisplayName') === 'IMPORT TO VCD' ? this.getFieldValue('aviNsxtCloudForm', 'nsxtCloudVcdDisplayNameInput') : this.getFieldValue('aviNsxtCloudForm', 'nsxtCloudVcdDisplayName'),
            };            
        }
        return nsxtCloudSpec;
    }


    public getStoragePolicySpec() {
        let storageSpec = this.getFieldValue('svcOrgVdcForm', 'storageSpec');
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


    public getSEGSpec() {
        let segSpec;
        if(this.getFieldValue('segForm', 'createSeGroup')) {
            segSpec = {
                'createSeGroup': 'true',
                'serviceEngineGroupName': this.getFieldValue('segForm', 'serviceEngineGroupName'),
                'serviceEngineGroupVcdDisplayName': this.getFieldValue('segForm', 'serviceEngineGroupVcdDisplayName'),
                'reservationType': this.getFieldValue('segForm', 'reservationType'),
                'vcenterPlacementDetails': {
                    'vcenterDatacenter': this.getFieldValue('segForm', 'vcenterDatacenter'),
                    'vcenterCluster': this.getFieldValue('segForm', 'vcenterCluster'),
                    'vcenterDatastore': this.getFieldValue('segForm', 'vcenterDatastore'),
                    'vcenterContentSeLibrary': this.getFieldValue('segForm', 'vcenterContentSeLibrary') === 'CREATE NEW' ? this.getFieldValue('segForm', 'newVcenterContentSeLibrary') : this.getFieldValue('segForm', 'vcenterContentSeLibrary'),
                }
            };
        } else {
            if(this.getFieldValue('segForm', 'serviceEngineGroupVcdDisplayName') === 'IMPORT TO VCD') {
                segSpec = {
                    'createSeGroup': 'false',
                    'serviceEngineGroupName': this.getFieldValue('segForm', 'serviceEngineGroupName'),
                    'serviceEngineGroupVcdDisplayName': this.getFieldValue('segForm', 'serviceEngineGroupVcdDisplayNameInput'),
                    'reservationType': this.getFieldValue('segForm', 'reservationType'),
                };
            } else {
                segSpec = {
                    'createSeGroup': 'false',
                    'serviceEngineGroupName': this.getFieldValue('segForm', 'serviceEngineGroupName'),
                    'serviceEngineGroupVcdDisplayName': this.getFieldValue('segForm', 'serviceEngineGroupVcdDisplayName'),
                };
            }
        }
        return segSpec;
    }

    public getTier0GatewaySpec() {
        if(this.getFieldValue('t0RouterForm', 'importTier0')) {
            let t0Spec = {
                'importTier0': 'true',
                'tier0Router': this.getFieldValue('t0RouterForm', 'tier0Router'),
                'tier0GatewayName': this.getFieldValue('t0RouterForm', 'tier0GatewayName'),
                'extNetGatewayCIDR': this.getFieldValue('t0RouterForm', 'extNetGatewayCIDR'),
                'extNetStartIP': this.getFieldValue('t0RouterForm', 'extNetStartIP'),
                'extNetEndIP': this.getFieldValue('t0RouterForm', 'extNetEndIP'),
            };
            return t0Spec;
        } else {
            let t0Spec = {
                'importTier0': 'false',
                'tier0GatewayName': this.getFieldValue('t0RouterForm', 'tier0GatewayName'),
            };
            return t0Spec;
        }
    }


    public getPayload() {
        const payload = {
            'envSpec': {
                'envType': 'vcd-avi',
                'marketplaceSpec' : {
                    'refreshToken': this.getFieldValue('vsphereProviderForm', 'marketplaceRefreshToken'),
                },
                'ceipParticipation' : this.getStringBoolFieldValue('vcdSpecForm', 'isCeipEnabled'),
                'infraComponents': {
                    'dnsServersIp': this.getFieldValue('dnsNtpForm', 'dnsServer'),
                    'ntpServers': this.getFieldValue('dnsNtpForm', 'ntpServer'),
                    'searchDomains': this.getFieldValue('dnsNtpForm', 'searchDomain'),
                },
                'vcdSpec': {
                    'vcdComponentSpec': {
                        'vcdAddress': this.getFieldValue('vcdSpecForm', 'vcdAddress'),
                        'vcdSysAdminUserName': this.getFieldValue('vcdSpecForm', 'vcdSysAdminUserName'),
                        'vcdSysAdminPasswordBase64': btoa(this.form.get('vcdSpecForm').get('vcdSysAdminPasswordBase64').value),
                    }
                },
                'aviCtrlDeploySpec': this.getAviControllerSpec(this.getFieldValue('aviControllerForm', 'deployAvi')),
                'aviNsxCloudSpec': this.getNSXTCloudSpec(this.getFieldValue('aviNsxtCloudForm', 'configureAviNsxtCloud')),
                'cseSpec': {
                    'svcOrgSpec': {
                        'svcOrgName': this.getFieldValue('svcOrgForm', 'svcOrgName') === 'CREATE NEW' ? this.getFieldValue('svcOrgForm', 'svcOrgNameInput') : this.getFieldValue('svcOrgForm', 'svcOrgName'),
                        'svcOrgFullName': this.getFieldValue('svcOrgForm', 'svcOrgFullName'),
                    },
                    'svcOrgVdcSpec': {
                        'svcOrgVdcName': this.getFieldValue('svcOrgVdcForm', 'svcOrgVdcName'),
                        'svcOrgVdcResourceSpec': {
                            'providerVDC': this.getFieldValue('svcOrgVdcForm', 'providerVDC'),
                            'cpuAllocation': this.getFieldValue('svcOrgVdcForm', 'cpuAllocation'),
                            'cpuGuaranteed': this.getFieldValue('svcOrgVdcForm', 'cpuGuaranteed') === '' ? '20' : this.getFieldValue('svcOrgVdcForm', 'cpuGuaranteed'),
                            'memoryAllocation': this.getFieldValue('svcOrgVdcForm', 'memoryAllocation'),
                            'memoryGuaranteed': this.getFieldValue('svcOrgVdcForm', 'memoryGuaranteed') === '' ? '20' : this.getFieldValue('svcOrgVdcForm', 'memoryGuaranteed'),
                            'vcpuSpeed': this.getFieldValue('svcOrgVdcForm', 'vcpuSpeed') === '' ? '1' : this.getFieldValue('svcOrgVdcForm', 'vcpuSpeed'),
                            'vmQuota': this.getFieldValue('svcOrgVdcForm', 'vmQuota') === '' ? '100' : this.getFieldValue('svcOrgVdcForm', 'vmQuota'),
                            'networkPoolName': this.getFieldValue('svcOrgVdcForm', 'networkPoolName'),
                            'networkQuota': this.getFieldValue('svcOrgVdcForm', 'networkQuota') === '' ? '100' : this.getFieldValue('svcOrgVdcForm', 'networkQuota'),
                            'storagePolicySpec': {
                                'storagePolicies': this.getStoragePolicySpec(),
                                'defaultStoragePolicy': this.getFieldValue('svcOrgVdcForm', 'defaultStoragePolicy'),
                            },
                            'isElastic': this.getStringBoolFieldValue('svcOrgVdcForm', 'isElastic'),
                            'includeMemoryOverhead': this.getStringBoolFieldValue('svcOrgVdcForm', 'includeMemoryOverhead'),
                            'thinProvisioning': this.getStringBoolFieldValue('svcOrgVdcForm', 'thinProvisioning'),
                            'fastProvisioning': this.getStringBoolFieldValue('svcOrgVdcForm', 'fastProvisioning'),
                        },
                        'serviceEngineGroup': this.getSEGSpec(),
                        'svcOrgVdcGatewaySpec': {
                            'tier0GatewaySpec': this.getTier0GatewaySpec(),
                            'tier1GatewaySpec': {
                                'tier1GatewayName': this.getFieldValue('svcOrgEdgeGatewayForm', 'tier1GatewayName'),
                                'isDedicated': this.getStringBoolFieldValue('svcOrgEdgeGatewayForm', 'isDedicated'),
                                'primaryIp': this.getFieldValue('svcOrgEdgeGatewayForm', 'primaryIp'),
                                'ipAllocationStartIP': this.getFieldValue('svcOrgEdgeGatewayForm', 'ipAllocationStartIP'),
                                'ipAllocationEndIP': this.getFieldValue('svcOrgEdgeGatewayForm', 'ipAllocationEndIP'),
                            },
                        },
                        'svcOrgVdcNetworkSpec': {
                            'networkName': this.getFieldValue('svcOrgEdgeGatewayForm', 'networkName'),
                            'gatewayCIDR': this.getFieldValue('svcOrgEdgeGatewayForm', 'gatewayCIDR'),
                            'staticIpPoolStartAddress': this.getFieldValue('svcOrgEdgeGatewayForm', 'staticIpPoolStartAddress'),
                            'staticIpPoolEndAddress': this.getFieldValue('svcOrgEdgeGatewayForm', 'staticIpPoolEndAddress'),
                            'primaryDNS': this.getFieldValue('svcOrgEdgeGatewayForm', 'primaryDNS'),
                            'secondaryDNS': this.getFieldValue('svcOrgEdgeGatewayForm', 'secondaryDNS'),
                            'dnsSuffix': this.getFieldValue('svcOrgEdgeGatewayForm', 'dnsSuffix'),
                        },
                        'svcOrgCatalogSpec': {
                            'cseOvaCatalogName': this.getFieldValue('catalogForm', 'cseOvaCatalogName') === 'CREATE NEW' ? this.getFieldValue('catalogForm', 'newCseOvaCatalogName') : this.getFieldValue('catalogForm', 'cseOvaCatalogName'),
                            'k8sTemplatCatalogName': this.getFieldValue('catalogForm', 'k8sTemplatCatalogName') === 'CREATE NEW' ? this.getFieldValue('catalogForm', 'newK8sTemplatCatalogName') : this.getFieldValue('catalogForm', 'k8sTemplatCatalogName'),
                        },
                    },
                    'cseServerDeploySpec': {
                        'vAppName': this.getFieldValue('vappForm', 'vAppName'),
                        'customCseProperties': {
                            'cseSvcAccountName': this.getFieldValue('vappForm', 'cseSvcAccountName'),
                            'cseSvcAccountPasswordBase64': btoa(this.form.get('vappForm').get('cseSvcAccountPasswordBase64').value)
                        }
                    }
                },
            },
        };
        this.apiClient.vcdPayload = payload;
        return payload;
    }

    openViewJsonModal() {
        this.getPayload();
        this.generatedFileName = 'vcd-cse-tkg.json';
        this.viewJsonModal.open(this.generatedFileName);
    }

    public generateInput() {
        const payload = this.getPayload();
        this.disableDeployButton = true;

        this.generatedFileName = 'vcd-cse-tkg.json';
        this.filePath = '/opt/vmware/arcas/src/' + this.generatedFileName;
        this.showAwsTestMessage = false;
        // Call the Generate API
        this.apiClient.generateInputJSON(payload, this.generatedFileName, 'vcd').subscribe((data: any) => {
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

}
