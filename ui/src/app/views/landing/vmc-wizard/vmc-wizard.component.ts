// Angular imports
import { AfterViewInit, Component, ElementRef, Input, OnInit, ViewChild } from '@angular/core';
import {FormBuilder, FormControl, FormGroup, Validators} from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';
import { Netmask } from 'netmask';
import {saveAs as importedSaveAs} from "file-saver";
import {ClrLoadingState} from '@clr/angular';
// import { KUBE_VIP } from './../wizard/shared/components/steps/load-balancer/load-balancer-step.component';

// Third party imports
import {Observable, Subscription} from 'rxjs';

// App imports
import { FormMetaDataService } from 'src/app/shared/service/form-meta-data.service';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
import { PROVIDERS, Providers } from '../../../shared/constants/app.constants';
import { APP_ROUTES, Routes } from '../../../shared/constants/routes.constants';
import { AppDataService } from '../../../shared/service/app-data.service';
import {VMCDataService} from '../../../shared/service/vmc-data.service';
import {DataService} from '../../../shared/service/data.service';
import {VsphereNsxtDataService} from '../../../shared/service/vsphere-nsxt-data.service';
import { VsphereTkgsService } from "../../../shared/service/vsphere-tkgs-data.service";
import { APIClient } from '../../../swagger/api-client.service';
// import { CliFields, CliGenerator } from '../wizard/shared/utils/cli-generator';
import { WizardBaseDirective } from '../wizard/shared/wizard-base/wizard-base';
import {ViewJSONModalComponent} from 'src/app/views/landing/wizard/shared/components/modals/view-json-modal/view-json-modal.component';
// import { VsphereRegionalClusterParams } from 'src/app/swagger/models/vsphere-regional-cluster-params.model';

@Component({
    selector: 'app-vmc-wizard',
    templateUrl: './vmc-wizard.component.html',
    styleUrls: ['./vmc-wizard.component.scss'],
})
export class VMCWizardComponent extends WizardBaseDirective implements OnInit {
    @ViewChild(ViewJSONModalComponent) viewJsonModal: ViewJSONModalComponent;
    @ViewChild('attachments') attachment : any;
    @Input() public form;
    @Input() public AVIFormValid;
    @Input() public providerType = 'vmc';
    @Input() public infraType = 'tkgm';
    public APP_ROUTES: Routes = APP_ROUTES;
    public PROVIDERS: Providers = PROVIDERS;

    public deploymentPending = false;
    public disableDeployButton = false;
    public showAwsTestMessage = false;
    public showIPValidationSuccess = false;
    public errorNotification: string;
    public successNotification: string;
    public filePath: string;
    public logFileName = 'service_installer_log_bundle';
    public show = false;

    public displayWizard = false;
    public fileName: string;
    public fileUploaded = false;
    public file: File;
    public generatedFileName: string;
    public uploadStatus = false;

    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    constructor(
        public apiClient: APIClient,
        router: Router,
        private appDataService: AppDataService,
        private formBuilder: FormBuilder,
        formMetaDataService: FormMetaDataService,
        vmcDataService: VMCDataService,
        dataService: DataService,
        nsxtDataService: VsphereNsxtDataService,
        vsphereTkgsDataService: VsphereTkgsService,
        titleService: Title,
        el: ElementRef) {

        super(router, el, formMetaDataService, titleService, dataService, vmcDataService, nsxtDataService, vsphereTkgsDataService);

        this.form = this.formBuilder.group({
            vmcProviderForm: this.formBuilder.group({
            }),
            vmcMgmtNodeSettingForm: this.formBuilder.group({
            }),
            vmcSharedServiceNodeSettingForm: this.formBuilder.group({
            }),
            vmcWorkloadNodeSettingForm: this.formBuilder.group({
            }),
            vmcAVINetworkSettingForm: this.formBuilder.group({
            }),
            vmcExtensionSettingForm: this.formBuilder.group({
            }),
            vmcTKGMgmtDataNWForm: this.formBuilder.group({
            }),
            vmcTKGWorkloadDataNWForm: this.formBuilder.group({
            }),
            vmcTanzuSaasSettingForm: this.formBuilder.group({
            }),
            dnsNtpForm: this.formBuilder.group({
            }),
            IdentityMgmtForm: this.formBuilder.group({
            }),
        });
        this.provider = this.appDataService.getProviderType();
//         this.vmcDataService.currentInputFileStatus.subscribe(
//             (uploadStatus) => this.uploadStatus = uploadStatus);
    }

    public ngOnInit() {
        super.ngOnInit();
//         this.form.reset();
        // delay showing first panel to avoid panel not defined console err
        setTimeout((_) => {
            if (this.uploadStatus) {
                this.vmcUploadNextStep();
                this.show = true;
            } else {
                this.show = true;
            }
        });

        this.titleService.setTitle('ARCAS');
    }

    public getStepDescription(stepName: string): string {
        if (stepName === 'provider') {
            return 'Validate SDDC token for VMC connectivity.';
        }
        else if (stepName === 'mgmtNodeSetting') {
            if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneSetting')) {
                let mode = 'Development cluster selected: 1 node control plane';
                if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneSetting') === 'prod') {
                    mode = 'Production cluster selected: 3 node control plane';
                }
                return mode;
            } else {
                return `Configure the resources backing the management cluster`;
            }
        }
        else if (stepName === 'sharedServiceNodeSetting') {
        if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneSetting')) {
            let mode = 'Development cluster selected: 1 node control plane';
            if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneSetting') === 'prod') {
                mode = 'Production cluster selected: 3 node control plane';
            }
            return mode;
            } else {
            return `Configure the resources backing the shared services cluster`;
            }
        }
        else if (stepName === 'workloadNodeSetting') {
            if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneSetting')) {
                let mode = 'Development cluster selected: 1 node control plane';
                if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneSetting') === 'prod') {
                    mode = 'Production cluster selected: 3 node control plane';
                }
                return mode;
            } else {
                return `Configure the resources backing the workload cluster`;
            }
        }
        else if (stepName === 'aviNetworkSetting') {
            if (this.getFieldValue('vmcAVINetworkSettingForm', 'mgmtSegmentName')) {
                return 'VMware NSX Advanced Load Balancer settings configured';
            } else {
                return 'Configure VMware NSX Advanced Load Balancer settings';
            }
        }
        else if (stepName === 'extensionSetting') {
            return  'Configure User-managed packages for Tanzu Kubernetes Grid clusters';
        }
        else if (stepName === 'TKGMgmtDataNW') {
            if (this.getFieldValue('TKGMgmtDataNWForm', 'gatewayCidr')) {
                return 'Tanzu Kubernetes Grid management data network set';
            } else {
                return 'Configure Tanzu Kubernetes Grid management data network settings';
            }
        }
        else if (stepName === 'tkgWorkloadDataNW') {
            if (this.getFieldValue('TKGWorkloadDataNWForm', 'gatewayCidr')) {
                return 'Tanzu Kubernetes Grid workload data network configured';
            } else {
                return 'Configure Tanzu Kubernetes Grid workload data network settings';
            }
        }
        else if (stepName === 'tanzuSaasSetting') {
            return 'Configure Tanzu Mission Control and Tanzu Observability endpoints';
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

//     public validateIPAndNetwork() {
//         const ipData = {
//             'avi-mgmt-network-gateway-cidr': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtGatewayIp'),
//             'avi-mgmt-service-ip-startrange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtDhcpStartRange'),
//             'avi-mgmt-service-ip-endrange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtDhcpEndRange'),
//
//             'tkgMgmtGatewayCidr': this.getFieldValue('vsphereMgmtNodeSettingForm', 'gatewayAddress'),
//             'tkg-mgmt-controlplane-ip': this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneEndpointIP'),
//             'tkg-sharedservice-controlplane-ip': this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneEndpointIP'),
//
//             'tkgMgmtDataNetworkGatewayCidr': this.getFieldValue('TKGMgmtDataNWForm', 'TKGMgmtGatewayCidr'),
//             'tkgMgmtAviServiceIpStartRange': this.getFieldValue('TKGMgmtDataNWForm', 'TKGMgmtDhcpStartRange'),
//             'tkgMgmtAviServiceIpEndRange': this.getFieldValue('TKGMgmtDataNWForm', 'TKGMgmtDhcpEndRange'),
//
//             'tkgWorkloadDataNetworkGatewayCidr': this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataGatewayCidr'),
//             'tkgWorkloadAviServiceIpStartRange': this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataDhcpStartRange'),
//             'tkgWorkloadAviServiceIpEndRange': this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataDhcpEndRange'),
//
//             'tkgWorkloadGatewayCidr': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'gatewayAddress'),
//             'tkg-workload-controlplane-ip': this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneEndpointIP'),
//         };
//
//         this.apiClient.validateIpAndNetwork(ipData).subscribe((data: any) => {
//               if (data && data !== null) {
//                   if (data.responseType === 'SUCCESS') {
//                     this.disableDeployButton = false;
//                     this.showAwsTestMessage = false;
//                     this.showIPValidationSuccess = true;
//                     this.errorNotification = '';
//                   } else if (data.responseType === 'ERROR') {
//                     this.errorNotification = data.msg;
//                   }
//               } else {
//                   this.showIPValidationSuccess = false;
//                   this.errorNotification = 'IP Validation Failed, Edit and Review Configuration again.';
//                   this.disableDeployButton = true;
//               }
//             }, (error: any) => {
//             this.showIPValidationSuccess = false;
//             this.disableDeployButton = true;
//             if (error.responseType === 'ERROR') {
//                 this.errorNotification = error.msg;
//             } else {
//                 this.errorNotification = 'Some Error Occurred while validating IPs';
//             }
//         });
//     }
    public reviewConfiguration(review) {
        const pageTitle = 'VMC Confirm Settings';
        this.titleService.setTitle(pageTitle);
        this.disableDeployButton = true;
        this.errorNotification = '';
        this.showAwsTestMessage = false;
        this.showIPValidationSuccess = false;

        this.disableDeployButton = false;
        this.showAwsTestMessage = false;
        this.errorNotification = '';
//         this.showIPValidationSuccess = true;
        // Turn this ON
//         this.validateIPAndNetwork();
        this.review = review;
    }

//     public onTkgWrkDataValidateClick() {
//         const gatewayIp = this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataGatewayCidr');
//         const dhcpStart = this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataDhcpStartRange');
//         const dhcpEnd = this.getFieldValue('TKGWorkloadDataNWForm', 'TKGDataDhcpEndRange');
//         const block = new Netmask(gatewayIp);
//         if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
//             this.apiClient.TkgWrkDataNwValidated = true;
//             this.errorNotification = '';
//         } else if (!block.contains(dhcpStart) && !block.contains(dhcpEnd)) {
//             this.errorNotification = 'DHCP Start and End IP are out of the provided subnet';
//         } else if (!block.contains(dhcpStart)) {
//             this.errorNotification = 'DHCP Start IP is out of the provided subnet.';
//         } else if (!block.contains(dhcpEnd)) {
//             this.errorNotification = 'DHCP End IP is out of the provided subnet';
//         }
//     }

    public getMgmtClusterSize() {
        if (this.getFieldValue('vmcMgmtNodeSettingForm', 'controlPlaneSetting') === 'dev') {
            return this.getFieldValue('vmcMgmtNodeSettingForm', 'devInstanceType');
        } else {
            return this.getFieldValue('vmcMgmtNodeSettingForm', 'prodInstanceType');
        }
    }

    public getSharedClusterSize() {
        if (this.getFieldValue('vmcSharedServiceNodeSettingForm', 'controlPlaneSetting') === 'dev') {
            return this.getFieldValue('vmcSharedServiceNodeSettingForm', 'devInstanceType');
        } else {
            return this.getFieldValue('vmcSharedServiceNodeSettingForm', 'prodInstanceType');
        }
    }

    public getWorkloadClusterSize() {
        if (this.getFieldValue('vmcWorkloadNodeSettingForm', 'controlPlaneSetting') === 'dev') {
            return this.getFieldValue('vmcWorkloadNodeSettingForm', 'devInstanceType');
        } else {
            return this.getFieldValue('vmcWorkloadNodeSettingForm', 'prodInstanceType');
        }
    }

    public enableLoggingExtension(key) {
        if (this.getFieldValue('vmcExtensionSettingForm', 'loggingEndpoint') === key) {
            return 'true';
        } else {
            return 'false';
        }
    }

    public setTSMEnable() {
        let tmcEnable = this.getStringBoolFieldValue('vmcTanzuSaasSettingForm', 'tmcSettings');
        if (tmcEnable === 'true') {
            return this.getStringBoolFieldValue('vmcWorkloadNodeSettingForm', 'tsmSettings');
        } else {
            return 'false';
        }
    }

    public setTSMExactName() {
        let tmcEnable = this.getStringBoolFieldValue('vmcTanzuSaasSettingForm', 'tmcSettings');
        if (tmcEnable === 'true') {
            let tsmEnable = this.getStringBoolFieldValue('vmcWorkloadNodeSettingForm', 'tsmSettings');
            if (tsmEnable === 'true') {
                return this.getFieldValue('vmcWorkloadNodeSettingForm', 'exactName');
            } else {
                return '';
            }
        } else {
            return '';
        }
    }

    public setTSMStartsWithName() {
        let tmcEnable = this.getStringBoolFieldValue('vmcTanzuSaasSettingForm', 'tmcSettings');
        if (tmcEnable === 'true') {
            let tsmEnable = this.getStringBoolFieldValue('vmcWorkloadNodeSettingForm', 'tsmSettings');
            if (tsmEnable === 'true') {
                return this.getFieldValue('vmcWorkloadNodeSettingForm', 'startsWithName');
            } else {
                return '';
            }
        } else {
            return '';
        }
    }

    public getPayload() {
        let workloadGiven = this.apiClient.workloadClusterSettings && this.apiClient.workloadDataSettings;
        const payload = {
            'envSpec': {
                'sddcRefreshToken': this.getFieldValue('vmcProviderForm', 'sddcToken'),
                'orgName': this.getFieldValue('vmcProviderForm', 'orgName'),
                'sddcName': this.getFieldValue('vmcProviderForm', 'sddcName'),
                'sddcDatacenter': this.getFieldValue('vmcProviderForm', 'datacenter'),
                'sddcCluster': this.getFieldValue('vmcProviderForm', 'cluster'),
                'sddcDatastore': this.getFieldValue('vmcProviderForm', 'datastore'),
                'contentLibraryName': this.getFieldValue('vmcProviderForm', 'contentLib'),
                'aviOvaName': this.getFieldValue('vmcProviderForm', 'aviOvaImage'),
                'resourcePoolName': this.getFieldValue('vmcProviderForm', 'resourcePool'),
            },
            'marketplaceSpec': {
                'refreshToken': this.getFieldValue('vmcProviderForm', 'marketplaceRefreshToken'),
            },
            'ceipParticipation' : this.getStringBoolFieldValue('vmcProviderForm', 'isCeipEnabled'),
            'envVariablesSpec': {
                'dnsServersIp': this.getFieldValue('dnsNtpForm', 'dnsServer'),
                'searchDomains': this.getFieldValue('dnsNtpForm', 'searchDomain'),
                'ntpServersIp': this.getFieldValue('dnsNtpForm', 'ntpServer'),
            },
            'saasEndpoints': {
                'tmcDetails': {
                    'tmcAvailability': this.getStringBoolFieldValue('vmcTanzuSaasSettingForm', 'tmcSettings'),
                    'tmcRefreshToken': this.getFieldValue('vmcTanzuSaasSettingForm', 'refreshToken'),
                    'tmcInstanceURL': this.getFieldValue('vmcTanzuSaasSettingForm', 'tmcInstanceURL'),
                },
                'tanzuObservabilityDetails': {
                    'tanzuObservabilityAvailability': this.getStringBoolFieldValue('vmcTanzuSaasSettingForm', 'toSettings'),
                    'tanzuObservabilityUrl': this.getFieldValue('vmcTanzuSaasSettingForm', 'toUrl'),
                    'tanzuObservabilityRefreshToken': this.getFieldValue('vmcTanzuSaasSettingForm', 'toRefreshToken'),
                },
            },
            'componentSpec': {
                'aviMgmtNetworkSpec': {
                    'aviMgmtGatewayCidr': this.getFieldValue('vmcAVINetworkSettingForm', 'aviMgmtGatewayIp'),
                    'aviMgmtDhcpStartRange': this.getFieldValue('vmcAVINetworkSettingForm', 'aviMgmtDhcpStartRange'),
                    'aviMgmtDhcpEndRange': this.getFieldValue('vmcAVINetworkSettingForm', 'aviMgmtDhcpEndRange'),
                },
                'aviComponentSpec': {
                    'aviPasswordBase64': btoa(this.getFieldValue('vmcAVINetworkSettingForm', 'aviPassword')),
                    'aviBackupPassPhraseBase64': btoa(this.getFieldValue('vmcAVINetworkSettingForm', 'aviBackupPassphrase')),
                    'enableAviHa': this.getStringBoolFieldValue('vmcAVINetworkSettingForm', 'enableHA'),
                    'aviClusterIp': this.getFieldValue('vmcAVINetworkSettingForm', 'clusterIp'),
                    'aviSize': this.getFieldValue('vmcAVINetworkSettingForm', 'aviSize'),
//                     'aviLicenseKey': this.getFieldValue('vmcAVINetworkSettingForm', 'aviLicenseKey'),
                    'aviCertPath': this.getFieldValue('vmcAVINetworkSettingForm', 'aviCertPath'),
                    'aviCertKeyPath': this.getFieldValue('vmcAVINetworkSettingForm', 'aviCertKeyPath'),
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
//                         'ldapTestUserName': this.getFieldValue('IdentityMgmtForm', 'testUserName'),
//                         'ldapTestGroupName': this.getFieldValue('IdentityMgmtForm', 'testGroupName'),
                    }
                },
                'tkgClusterVipNetwork': {
                    'tkgClusterVipNetworkGatewayCidr': this.getFieldValue('vmcAVINetworkSettingForm', 'aviClusterVipGatewayIp'),
                    'tkgClusterVipDhcpStartRange': this.getFieldValue('vmcAVINetworkSettingForm', 'aviClusterVipStartRange'),
                    'tkgClusterVipDhcpEndRange': this.getFieldValue('vmcAVINetworkSettingForm', 'aviClusterVipEndRange'),
                    'tkgClusterVipIpStartRange': this.getFieldValue('vmcAVINetworkSettingForm', 'aviClusterVipSeStartRange'),
                    'tkgClusterVipIpEndRange': this.getFieldValue('vmcAVINetworkSettingForm', 'aviClusterVipSeEndRange'),
                },
                'tkgMgmtSpec': {
                    'tkgMgmtNetworkName': this.getFieldValue('vmcMgmtNodeSettingForm', 'segmentName'),
                    'tkgMgmtGatewayCidr': this.getFieldValue('vmcMgmtNodeSettingForm', 'gatewayAddress'),
                    'tkgMgmtClusterName': this.getFieldValue('vmcMgmtNodeSettingForm', 'clusterName'),
                    'tkgMgmtSize': this.getMgmtClusterSize(),
                    'tkgMgmtCpuSize': this.getFieldValue('vmcMgmtNodeSettingForm', 'mgmtCpu').toString(),
                    'tkgMgmtMemorySize': this.getFieldValue('vmcMgmtNodeSettingForm', 'mgmtMemory').toString(),
                    'tkgMgmtStorageSize': this.getFieldValue('vmcMgmtNodeSettingForm', 'mgmtStorage').toString(),
                    'tkgMgmtDeploymentType': this.getFieldValue('vmcMgmtNodeSettingForm', 'controlPlaneSetting'),
                    'tkgMgmtClusterCidr': this.getFieldValue('vmcMgmtNodeSettingForm', 'clusterCidr'),
                    'tkgMgmtServiceCidr': this.getFieldValue('vmcMgmtNodeSettingForm', 'serviceCidr'),
                    'tkgMgmtBaseOs': this.getFieldValue('vmcMgmtNodeSettingForm', 'baseImage'),
                    'tkgMgmtRbacUserRoleSpec': {
                        'clusterAdminUsers': this.getFieldValue('vmcMgmtNodeSettingForm', 'clusterAdminUsers'),
                        'adminUsers': this.getFieldValue('vmcMgmtNodeSettingForm', 'adminUsers'),
                        'editUsers': this.getFieldValue('vmcMgmtNodeSettingForm', 'editUsers'),
                        'viewUsers': this.getFieldValue('vmcMgmtNodeSettingForm', 'viewUsers'),
                    },
                    'tkgMgmtClusterGroupName': this.getFieldValue('vmcMgmtNodeSettingForm', 'clusterGroupName')
                },
                'tkgSharedServiceSpec': {
                    'tkgSharedGatewayCidr': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'gatewayAddress'),
                    'tkgSharedDhcpStartRange': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'sharedServiceDhcpStartRange'),
                    'tkgSharedDhcpEndRange': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'sharedServiceDhcpEndRange'),
                    'tkgSharedClusterName': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'clusterName'),
                    'tkgSharedserviceSize': this.getSharedClusterSize(),
                    'tkgSharedserviceCpuSize': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'sharedCpu').toString(),
                    'tkgSharedserviceMemorySize': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'sharedMemory').toString(),
                    'tkgSharedserviceStorageSize': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'sharedStorage').toString(),
                    'tkgSharedserviceDeploymentType': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'controlPlaneSetting'),
                    'tkgSharedserviceWorkerMachineCount': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'workerNodeCount').toString(),
                    'tkgSharedserviceClusterCidr': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'clusterCidr'),
                    'tkgSharedserviceServiceCidr': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'serviceCidr'),
                    'tkgSharedserviceBaseOs': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'baseImage'),
                    'tkgSharedserviceKubeVersion': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'baseImageVersion'),
                    'tkgSharedserviceRbacUserRoleSpec': {
                        'clusterAdminUsers': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'clusterAdminUsers'),
                        'adminUsers': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'adminUsers'),
                        'editUsers': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'editUsers'),
                        'viewUsers': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'viewUsers'),
                    },
                    'tkgSharedserviceClusterGroupName': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'clusterGroupName'),
                    'tkgSharedserviceEnableDataProtection': this.getStringBoolFieldValue('vmcSharedServiceNodeSettingForm', 'enableDataProtection'),
                    'tkgSharedClusterCredential': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'veleroCredential'),
                    'tkgSharedClusterBackupLocation': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'veleroTargetLocation'),                    
                },
                'tkgMgmtDataNetworkSpec': {
                    'tkgMgmtDataGatewayCidr': this.getFieldValue('vmcTKGMgmtDataNWForm', 'TKGMgmtGatewayCidr'),
                    'tkgMgmtDataDhcpStartRange': this.getFieldValue('vmcTKGMgmtDataNWForm', 'TKGMgmtDhcpStartRange'),
                    'tkgMgmtDataDhcpEndRange': this.getFieldValue('vmcTKGMgmtDataNWForm', 'TKGMgmtDhcpEndRange'),
                    'tkgMgmtDataServiceStartRange': this.getFieldValue('vmcTKGMgmtDataNWForm', 'TKGMgmtServiceStartRange'),
                    'tkgMgmtDataServiceEndRange': this.getFieldValue('vmcTKGMgmtDataNWForm', 'TKGMgmtServiceEndRange'),
                },
                'tkgWorkloadDataNetworkSpec': {
                    'tkgWorkloadDataGatewayCidr': !workloadGiven ? "" : this.getFieldValue('vmcTKGWorkloadDataNWForm', 'TKGDataGatewayCidr'),
                    'tkgWorkloadDataDhcpStartRange': !workloadGiven ? "" : this.getFieldValue('vmcTKGWorkloadDataNWForm', 'TKGDataDhcpStartRange'),
                    'tkgWorkloadDataDhcpEndRange': !workloadGiven ? "" : this.getFieldValue('vmcTKGWorkloadDataNWForm', 'TKGDataDhcpEndRange'),
                    'tkgWorkloadDataServiceStartRange': !workloadGiven ? "" : this.getFieldValue('vmcTKGWorkloadDataNWForm', 'TKGWrkServiceStartRange'),
                    'tkgWorkloadDataServiceEndRange': !workloadGiven? "" : this.getFieldValue('vmcTKGWorkloadDataNWForm', 'TKGWrkServiceEndRange'),
                },
                'tkgWorkloadSpec': {
                    'tkgWorkloadGatewayCidr': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'gatewayAddress'),
                    'tkgWorkloadDhcpStartRange': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'workloadDhcpStartRange'),
                    'tkgWorkloadDhcpEndRange': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'workloadDhcpEndRange'),
                    'tkgWorkloadClusterName': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'clusterName'),
                    'tkgWorkloadSize': !workloadGiven ? "" : this.getWorkloadClusterSize(),
                    'tkgWorkloadCpuSize': !workloadGiven? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'wrkCpu').toString(),
                    'tkgWorkloadMemorySize': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'wrkMemory').toString(),
                    'tkgWorkloadStorageSize': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'wrkStorage').toString(),
                    'tkgWorkloadDeploymentType': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'controlPlaneSetting'),
                    'tkgWorkloadWorkerMachineCount': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'workerNodeCount').toString(),
                    'tkgWorkloadClusterCidr': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'clusterCidr'),
                    'tkgWorkloadServiceCidr': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'serviceCidr'),
                    'tkgWorkloadBaseOs': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'baseImage'),
                    'tkgWorkloadKubeVersion': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'baseImageVersion'),
                    'tkgWorkloadRbacUserRoleSpec': {
                        'clusterAdminUsers': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'clusterAdminUsers'),
                        'adminUsers': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'adminUsers'),
                        'editUsers': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'editUsers'),
                        'viewUsers': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'viewUsers'),
                    },
                    'tkgWorkloadTsmIntegration': !workloadGiven ? 'false' : this.setTSMEnable(),
                    'namespaceExclusions': {
                        'exactName': !workloadGiven ? "" : this.setTSMExactName(),
                        'startsWith': !workloadGiven ? "" : this.setTSMStartsWithName(),
                    },
                    'tkgWorkloadClusterGroupName': !workloadGiven ? "default" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'clusterGroupName'),
                    'tkgWorkloadEnableDataProtection': !workloadGiven ? "false" : this.getStringBoolFieldValue('vmcWorkloadNodeSettingForm', 'enableDataProtection'),
                    'tkgWorkloadClusterCredential': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'veleroCredential'),
                    'tkgWorkloadClusterBackupLocation': !workloadGiven ? "" : this.getFieldValue('vmcWorkloadNodeSettingForm', 'veleroTargetLocation')
                },
                'harborSpec': {
                    'enableHarborExtension': this.apiClient.sharedServicesClusterSettings.toString(),
                    'harborFqdn': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'harborFqdn'),
                    'harborPasswordBase64': btoa(this.getFieldValue('vmcSharedServiceNodeSettingForm', 'harborPassword')),
                    'harborCertPath': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'harborCertPath'),
                    'harborCertKeyPath': this.getFieldValue('vmcSharedServiceNodeSettingForm', 'harborCertKeyPath'),
                }
            },
            'tanzuExtensions': {
                'enableExtensions': this.getStringBoolFieldValue('vmcExtensionSettingForm', 'tanzuExtensions'),
                'tkgClustersName': this.getFieldValue('vmcExtensionSettingForm', 'tanzuExtensionClusters'),
                'logging': {
                    'syslogEndpoint': {
                        'enableSyslogEndpoint': this.enableLoggingExtension('Syslog'),
                        'syslogEndpointAddress': this.getFieldValue('vmcExtensionSettingForm', 'syslogEndpointAddress'),
                        'syslogEndpointPort': this.getFieldValue('vmcExtensionSettingForm', 'syslogEndpointPort'),
                        'syslogEndpointMode': this.getFieldValue('vmcExtensionSettingForm', 'syslogEndpointMode'),
                        'syslogEndpointFormat': this.getFieldValue('vmcExtensionSettingForm', 'syslogEndpointFormat'),
                    },
                    'httpEndpoint': {
                        'enableHttpEndpoint': this.enableLoggingExtension('HTTP'),
                        'httpEndpointAddress': this.getFieldValue('vmcExtensionSettingForm', 'httpEndpointAddress'),
                        'httpEndpointPort': this.getFieldValue('vmcExtensionSettingForm', 'httpEndpointPort'),
                        'httpEndpointUri': this.getFieldValue('vmcExtensionSettingForm', 'httpEndpointUri'),
                        'httpEndpointHeaderKeyValue': this.getFieldValue('vmcExtensionSettingForm', 'httpEndpointHeaderKeyValue'),
                    },
                    // 'elasticSearchEndpoint': {
                    //     'enableElasticSearchEndpoint': !this.apiClient.toEnabled ? this.enableLoggingExtension('Elastic Search') : "false",
                    //     'elasticSearchEndpointAddress': !this.apiClient.toEnabled ? this.getFieldValue('vmcExtensionSettingForm', 'elasticSearchAddress') : "",
                    //      'elasticSearchEndpointPort': !this.apiClient.toEnabled ? this.getFieldValue('vmcExtensionSettingForm', 'elasticSearchPort') : "",
                    // },
                    'kafkaEndpoint': {
                        'enableKafkaEndpoint': this.enableLoggingExtension('Kafka'),
                        'kafkaBrokerServiceName': this.getFieldValue('vmcExtensionSettingForm', 'kafkaBrokerServiceName'),
                        'kafkaTopicName': this.getFieldValue('vmcExtensionSettingForm', 'kafkaTopicName'),
                    },
                    // 'splunkEndpoint': {
                    //     'enableSplunkEndpoint': !this.apiClient.toEnabled ? this.enableLoggingExtension('Splunk') : "false",
                    //     'splunkEndpointAddress': !this.apiClient.toEnabled ? this.getFieldValue('vmcExtensionSettingForm', 'splunkAddress') : "",
                    //     'splunkEndpointPort': !this.apiClient.toEnabled ? this.getFieldValue('vmcExtensionSettingForm', 'splunkPort') : "",
                    //     'splunkEndpointToken': !this.apiClient.toEnabled ? this.getFieldValue('vmcExtensionSettingForm', 'splunkToken') : "",
                    // },
                },
                'monitoring': {
                    'enableLoggingExtension': !this.apiClient.toEnabled ? this.getStringBoolFieldValue('vmcExtensionSettingForm', 'enableMonitoring') : "false",
                    'prometheusFqdn': !this.apiClient.toEnabled ? this.getFieldValue('vmcExtensionSettingForm', 'prometheusFqdn') : "",
                    'prometheusCertPath': !this.apiClient.toEnabled ? this.getFieldValue('vmcExtensionSettingForm', 'prometheusCertPath') : "",
                    'prometheusCertKeyPath': !this.apiClient.toEnabled ? this.getFieldValue('vmcExtensionSettingForm', 'prometheusCertKeyPath') : "",
                    'grafanaFqdn': !this.apiClient.toEnabled ? this.getFieldValue('vmcExtensionSettingForm', 'grafanaFqdn') : "",
                    'grafanaCertPath': !this.apiClient.toEnabled ? this.getFieldValue('vmcExtensionSettingForm', 'grafanaCertPath') : "",
                    'grafanaCertKeyPath': !this.apiClient.toEnabled ? this.getFieldValue('vmcExtensionSettingForm', 'grafanaCertKeyPath') : "",
                    'grafanaPasswordBase64': !this.apiClient.toEnabled ? btoa(this.getFieldValue('vmcExtensionSettingForm', 'grafanaPassword')) : "",
                }
            }
        };
        this.apiClient.vmcPayload = payload;
        return payload;
    }

    openViewJsonModal() {
        this.getPayload();
        this.generatedFileName = 'vmc-tkgm.json';
        this.viewJsonModal.open(this.generatedFileName);
    }

    public generateInput() {
        const payload = this.getPayload();
        this.disableDeployButton = true;
        this.generatedFileName = 'vmc-tkgm.json';
        this.filePath = '/opt/vmware/arcas/src/' + this.generatedFileName;
        this.showAwsTestMessage = false;
        // Call the Generate API
        this.apiClient.generateInputJSON(payload, this.generatedFileName, 'vmc').subscribe((data: any) => {
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

    public deploy() {
        this.getPayload();
        this.navigate(APP_ROUTES.WIZARD_PROGRESS);
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

    // getPayload(): VsphereRegionalClusterParams {
    //     const payload: VsphereRegionalClusterParams = {};
    //     this.initPayloadWithCommons(payload);
    //     const mappings = [
    //         ['datacenter', 'vsphereProviderForm', 'datacenter'],
    //         ['ssh_key', 'vsphereProviderForm', 'ssh_key'],
    //         ['clusterName', 'vsphereNodeSettingForm', 'clusterName'],
    //         ['controlPlaneFlavor', 'vsphereNodeSettingForm', 'controlPlaneSetting'],
    //         ['controlPlaneEndpoint', 'vsphereNodeSettingForm', 'controlPlaneEndpointIP'],
    //         ['datastore', 'resourceForm', 'datastore'],
    //         ['folder', 'resourceForm', 'vmFolder'],
    //         ['resourcePool', 'resourceForm', 'resourcePool']
    //     ];
    //     mappings.forEach(attr => payload[attr[0]] = this.getFieldValue(attr[1], attr[2]));
    //     payload.controlPlaneNodeType = this.getControlPlaneType(this.getFieldValue('vsphereNodeSettingForm', 'controlPlaneSetting'));
    //     payload.workerNodeType = (this.clusterType !== 'standalone') ?
    //         this.getFieldValue('vsphereNodeSettingForm', 'workerNodeInstanceType') : payload.controlPlaneNodeType;
    //     payload.machineHealthCheckEnabled = this.getFieldValue('vsphereNodeSettingForm', "machineHealthChecksEnabled") === true;
    //
    //     const vsphereCredentialsMappings = [
    //         ['host', 'vsphereProviderForm', 'vcenterAddress'],
    //         ['password', 'vsphereProviderForm', 'password'],
    //         ['username', 'vsphereProviderForm', 'username'],
    //         ['thumbprint', 'vsphereProviderForm', 'thumbprint']
    //     ];
    //     payload.vsphereCredentials = {};
    //
    //     payload.enableAuditLogging = this.getBooleanFieldValue('vsphereNodeSettingForm', "enableAuditLogging");
    //
    //     vsphereCredentialsMappings.forEach(attr => payload.vsphereCredentials[attr[0]] = this.getFieldValue(attr[1], attr[2]));
    //
    //     const endpointProvider = this.getFieldValue('vsphereNodeSettingForm', 'controlPlaneEndpointProvider');
    //     if (endpointProvider === KUBE_VIP) {
    //         payload.aviConfig['controlPlaneHaProvider'] = false;
    //     } else {
    //         payload.aviConfig['controlPlaneHaProvider'] = true;
    //     }
    //     payload.aviConfig['managementClusterVipNetworkName'] = this.getFieldValue("loadBalancerForm", "managementClusterNetworkName");
    //     if (!payload.aviConfig['managementClusterVipNetworkName']) {
    //         payload.aviConfig['managementClusterVipNetworkName'] = this.getFieldValue('loadBalancerForm', 'networkName');
    //     }
    //     payload.aviConfig['managementClusterVipNetworkCidr'] = this.getFieldValue("loadBalancerForm", "managementClusterNetworkCIDR");
    //     if (!payload.aviConfig['managementClusterVipNetworkCidr']) {
    //         payload.aviConfig['managementClusterVipNetworkCidr'] = this.getFieldValue('loadBalancerForm', 'networkCIDR')
    //     }
    //
    //     return payload;
    // }

    /**
     * @method method to trigger deployment
     */
    // createRegionalCluster(payload: any): Observable<any> {
    //     return this.apiClient.createVSphereRegionalCluster(payload);
    // }

    /**
     * Return management/standalone cluster name
     */
    // getMCName() {
    //     return this.getFieldValue('vsphereNodeSettingForm', 'clusterName');
    // }

    /**
     * Get the CLI used to deploy the management/standalone cluster
     */
    // getCli(configPath: string): string {
    //     const cliG = new CliGenerator();
    //     const cliParams: CliFields = {
    //         configPath: configPath,
    //         clusterType: this.clusterType,
    //         clusterName: this.getMCName()
    //     };
    //     return cliG.getCli(cliParams);
    // }

    /**
     * Apply the settings captured via UI to backend TKG config without
     * actually creating the management/standalone cluster.
     */
    // applyTkgConfig() {
    //     return this.apiClient.applyTKGConfigForVsphere({ params: this.getPayload() });
    //     return 'Success';
    // }

    /**
     * @method getControlPlaneType
     * helper method to return value of dev instance type or prod instance type
     * depending on what type of control plane is selected
     * @param controlPlaneType {string} the control plane type (dev/prod)
     * @returns {any}
     */
//     public getControlPlaneType(controlPlaneType: string) {
//         if (controlPlaneType === 'dev') {
//             return this.getFieldValue('vsphereNodeSettingForm', 'devInstanceType');
//         } else if (controlPlaneType === 'prod') {
//             return this.getFieldValue('vsphereNodeSettingForm', 'prodInstanceType');
//         } else {
//             return null;
//         }
//     }

}
