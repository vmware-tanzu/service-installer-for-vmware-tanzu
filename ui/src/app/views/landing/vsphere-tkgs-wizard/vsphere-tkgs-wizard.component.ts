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
import {FormMetaDataStore} from 'src/app/views/landing/wizard/shared/FormMetaDataStore';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
import { PROVIDERS, Providers } from '../../../shared/constants/app.constants';
import { APP_ROUTES, Routes } from '../../../shared/constants/routes.constants';
import { AppDataService } from '../../../shared/service/app-data.service';
import { DataService } from '../../../shared/service/data.service';
import { VMCDataService } from '../../../shared/service/vmc-data.service';
import { VsphereNsxtDataService } from '../../../shared/service/vsphere-nsxt-data.service';
import { VsphereTkgsService } from '../../../shared/service/vsphere-tkgs-data.service';
import { APIClient } from '../../../swagger/api-client.service';
import { ViewJSONModalComponent } from 'src/app/views/landing/wizard/shared/components/modals/view-json-modal/view-json-modal.component';
// import { CliFields, CliGenerator } from '../wizard/shared/utils/cli-generator';
import { WizardBaseDirective } from '../wizard/shared/wizard-base/wizard-base';
// import { VsphereRegionalClusterParams } from 'src/app/swagger/models/vsphere-regional-cluster-params.model';

@Component({
    selector: 'app-tkgs-wizard',
    templateUrl: './vsphere-tkgs-wizard.component.html',
    styleUrls: ['./vsphere-tkgs-wizard.component.scss'],
})
export class VSphereTkgsWizardComponent extends WizardBaseDirective implements OnInit {
    @ViewChild(ViewJSONModalComponent) viewJsonModal: ViewJSONModalComponent;
    @ViewChild('attachments') attachment : any;
    @Input() public form;
//     @Input() public AVIFormValid;
    @Input() public providerType = 'vsphere';
    @Input() public infraType = 'tkgs';
    public APP_ROUTES: Routes = APP_ROUTES;
    public PROVIDERS: Providers = PROVIDERS;

//     public datacenterMoid: Observable<string>;
    // tkrVersion: Observable<string>;
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
        // public wizardFormService: VSphereWizardFormService,
        private appDataService: AppDataService,
        private formBuilder: FormBuilder,
        formMetaDataService: FormMetaDataService,
        dataService: DataService,
        vmcDataService: VMCDataService,
        nsxtDataService: VsphereNsxtDataService,
        vsphereTkgsDataService: VsphereTkgsService,
        titleService: Title,
        el: ElementRef) {
//
        super(router, el, formMetaDataService, titleService, dataService, vmcDataService, nsxtDataService, vsphereTkgsDataService);
//
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
            });
        }
//         // this.form.get('vsphereInfraDetailsForm').addControl('proxySettings', new FormControl('', [
//         //     Validators.required]));
//         this.provider = this.appDataService.getProviderType();
//         // this.tkrVersion = this.appDataService.getTkrVersion();
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
//         else if (stepName === 'infra') {
//             if (this.getFieldValue('vsphereInfraDetailsForm', 'dns') &&
//                 this.getFieldValue('vsphereInfraDetailsForm', 'ntp')) {
//                 return 'Infrastructure details are configured';
//             } else {
//                 return 'Configure infrastructure settings for Tanzu on vpshere';
//             }
//         } else if (stepName === 'mgmtNodeSetting') {
//             if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneSetting')) {
//                 let mode = 'Development cluster selected: 1 node control plane';
//                 if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneSetting') === 'prod') {
//                     mode = 'Production cluster selected: 3 node control plane';
//                 }
//                 return mode;
//             } else {
//                 return `Configure the resources backing the Management cluster`;
//             }
//         } else if (stepName === 'sharedServiceNodeSetting') {
//             if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneSetting')) {
//                 let mode = 'Development cluster selected: 1 node control plane';
//                 if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneSetting') === 'prod') {
//                     mode = 'Production cluster selected: 3 node control plane';
//                 }
//                 return mode;
//                 } else {
//                 return `Configure the resources backing the Shared Service cluster`;
//             }
//         } else if (stepName === 'workloadNodeSetting') {
//             if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneSetting')) {
//                 let mode = 'Development cluster selected: 1 node control plane';
//                 if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneSetting') === 'prod') {
//                     mode = 'Production cluster selected: 3 node control plane';
//                 }
//                 return mode;
//             } else {
//                 return `Configure the resources backing the Workload cluster`;
//             }
//         }
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
//         } else if (stepName === 'TKGMgmtDataNW') {
//             if (this.getFieldValue('TKGMgmtDataNWForm', 'gatewayCidr')) {
//                 return 'TKG Management Data Network set';
//             } else {
//                 return 'Configure TKG Management Data Network Settings';
//             }
//         } else if (stepName === 'tkgWorkloadDataNW') {
//             if (this.getFieldValue('TKGWorkloadDataNWForm', 'gatewayCidr')) {
//                 return 'TKG Workload Data Network configured';
//             } else {
//                 return 'Configure TKG Workload Data Network Settings';
//             }
//         }
        else if (stepName === 'tanzuSaasSetting') {
            return 'Configure Tanzu Saas Services';
        } else if (stepName === 'customRepoSettings') {
            return 'Configure Custom Repository settings';
        }
    }

//     public getCard(): string {
//             return this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneSetting');
//         }

    // public openFormPanel() {
    //     // this.readInputFile();
    //     // this.setFormInput();
    //     this.displayWizard = true;
    //     this.show = true;
    // }

    // public uploadFile(event) {
    //     // var inputFile = document.getElementById( 'inputFile' );
    //     // inputFile.addEventListener( 'change', showFileName );
    //     // var input = event.target;
    //     // console.log(input);
    //     // this.fileName = input.files[0].name;
    //     // this.fileUploaded = true;
    //
    //
    //     // var ele: HTMLInputElement = document.getElementById('inputFile');
    //     // console.log(ele);
    //     // let name = ele.files.item(0).name;
    //     // if (name) {
    //     //     this.fileUploaded = true;
    //     //     this.fileName = name;
    //     //     console.log(name);
    //     // } else {
    //     //     this.fileUploaded = false;
    //     // }
    //
    //     if (!event || !event.target || !event.target.files || event.target.files.length === 0) {
    //         this.fileUploaded = false;
    //         return;
    //     }
    //     this.file = event.target.files[0];
    //     const name = this.file.name;
    //     const lastDot = name.lastIndexOf('.');
    //
    //     this.fileName = name.substring(0, lastDot);
    //     this.fileUploaded = true;
    //     // const ext = name.substring(lastDot + 1);
    //     // outputfile.value = fileName;
    //     // extension.value = ext;
    // }

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
//             'aviMgmtNetworkGatewayCidr': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtGatewayIp'),
//             'aviMgmtServiceIpStartrange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtDhcpStartRange'),
//             'aviMgmtServiceIpEndrange': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviMgmtDhcpEndRange'),
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
//         this.showIPValidationSuccess = false;
//         this.showIPValidationSuccess = false;
        // Turn this ON
//         this.validateIPAndNetwork();
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

//     getArcasHttpProxyParam() {
//         if (this.getBooleanFieldValue('vsphereInfraDetailsForm', 'proxySettings')) {
//             if (this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUsername') !== '') {
//                 let username = this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUsername');
//                 let password = this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyPassword');
//                 let url = this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUrl');
//                 let httpProxy = 'http://' + username + ':' + password +'@'+ url.substr(7);
//                 return httpProxy;
//             } else {
//                 return this.getFieldValue('vsphereInfraDetailsForm', 'httpProxyUrl');
//             }
//         } else {
//             return '';
//         }
//     }

//     getArcasHttpsProxyParam() {
//         if (this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUsername') !== '') {
//             let username = this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUsername');
//             let password = this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyPassword');
//             let url = this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUrl');
//             let httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
//             return httpsProxy;
//         } else {
//             return this.getFieldValue('vsphereInfraDetailsForm', 'httpsProxyUrl');
//         }
//     }

//     public getArcasHttpsProxy() {
//         let httpsProxy = '';
//         if (this.getBooleanFieldValue('vsphereInfraDetailsForm', 'proxySettings')) {
//             if (this.getBooleanFieldValue('vsphereInfraDetailsForm', 'isSameAsHttp')) {
//                 httpsProxy = this.getArcasHttpProxyParam();
//             } else {
//                 httpsProxy = this.getArcasHttpsProxyParam();
//             }
//         } else {
//             httpsProxy = '';
//         }
//         return httpsProxy;
//     }

//     getMgmtHttpProxyParam() {
//         if (this.getBooleanFieldValue('vsphereMgmtNodeSettingForm', 'proxySettings')) {
//             if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyUsername') !== '') {
//                 let username = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyUsername');
//                 let password = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyPassword');
//                 let url = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyUrl');
//                 let httpProxy = 'http://' + username + ':' + password + '@' + url.substr(7);
//                 return httpProxy;
//             } else {
//                 return this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpProxyUrl' );
//             }
//         } else {
//             return '';
//         }
//     }

//     getMgmtHttpsProxyParam() {
//         if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyUsername') !== '') {
//             let username = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyUsername');
//             let password = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyPassword');
//             let url = this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyUrl');
//             let httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
//             return httpsProxy;
//         } else {
//             return this.getFieldValue('vsphereMgmtNodeSettingForm', 'httpsProxyUrl');
//         }
//     }

//     public getMgmtClusterHttpsProxy() {
//         let httpsProxy = '';
//         if (this.getBooleanFieldValue('vsphereMgmtNodeSettingForm', 'proxySettings')) {
//             if (this.getBooleanFieldValue('vsphereMgmtNodeSettingForm', 'isSameAsHttp')) {
//                 httpsProxy = this.getMgmtHttpProxyParam();
//             } else {
//                 httpsProxy = this.getMgmtHttpsProxyParam();
//             }
//         } else {
//             httpsProxy = '';
//         }
//         return httpsProxy;
//     }

//     getSharedHttpProxyParam() {
//         if (this.getBooleanFieldValue('vsphereSharedServiceNodeSettingForm', 'proxySettings')) {
//             if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyUsername') !== '') {
//                 let username = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyUsername');
//                 let password = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyPassword');
//                 let url = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyUrl');
//                 let httpProxy = 'http://' + username + ':' + password + '@' + url.substr(7);
//                 return httpProxy;
//             } else {
//                 return this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpProxyUrl');
//             }
//         } else {
//             return '';
//         }
//     }

//     getSharedHttpsProxyParam() {
//         if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyUsername') !== '') {
//             let username = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyUsername');
//             let password = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyPassword');
//             let url = this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyUrl');
//             let httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
//             return httpsProxy;
//         } else {
//             return this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'httpsProxyUrl');
//         }
//     }

//     public getSharedClusterHttpsProxy() {
//         let httpsProxy = '';
//         if (this.getBooleanFieldValue('vsphereSharedServiceNodeSettingForm', 'proxySettings')) {
//             if (this.getBooleanFieldValue('vsphereSharedServiceNodeSettingForm', 'isSameAsHttp')) {
//                 httpsProxy = this.getSharedHttpProxyParam();
//             } else {
//                 httpsProxy = this.getSharedHttpsProxyParam();
//             }
//         } else {
//             httpsProxy = '';
//         }
//         return httpsProxy;
//     }

//     getWorkloadHttpProxyParam() {
//         if (this.getBooleanFieldValue('vsphereWorkloadNodeSettingForm', 'proxySettings')) {
//             if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyUsername') !== '') {
//                 let username = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyUsername');
//                 let password = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyPassword');
//                 let url = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyUrl');
//                 let httpProxy = 'http://' + username + ':' + password + '@' + url.substr(7);
//                 return httpProxy;
//             } else {
//                 return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpProxyUrl');
//             }
//         } else {
//             return '';
//         }
//     }

//     getWorkloadHttpsProxyParam() {
//         if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyUsername') !== '') {
//             let username = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyUsername');
//             let password = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyPassword');
//             let url = this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyUrl');
//             let httpsProxy = 'https://' + username + ':' + password + '@' + url.substr(8);
//             return httpsProxy;
//         } else {
//             return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'httpsProxyUrl');
//         }
//     }

//     public getWorkloadClusterHttpsProxy() {
//         let httpsProxy = '';
//         if (this.getBooleanFieldValue('vsphereWorkloadNodeSettingForm', 'proxySettings')) {
//             if (this.getBooleanFieldValue('vsphereWorkloadNodeSettingForm', 'isSameAsHttp')) {
//                 httpsProxy = this.getWorkloadHttpProxyParam();
//             } else {
//                 httpsProxy = this.getWorkloadHttpsProxyParam();
//             }
//         } else {
//             httpsProxy = '';
//         }
//         return httpsProxy;
//     }

//     public getMgmtClusterSize() {
//         if (this.getFieldValue('vsphereMgmtNodeSettingForm', 'controlPlaneSetting') === 'dev') {
//             return this.getFieldValue('vsphereMgmtNodeSettingForm', 'devInstanceType');
//         } else {
//             return this.getFieldValue('vsphereMgmtNodeSettingForm', 'prodInstanceType');
//         }
//     }

//     public getSharedClusterSize() {
//         if (this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'controlPlaneSetting') === 'dev') {
//             return this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'devInstanceType');
//         } else {
//             return this.getFieldValue('vsphereSharedServiceNodeSettingForm', 'prodInstanceType');
//         }
//     }

//     public getWorkloadClusterSize() {
//         if (this.getFieldValue('vsphereWorkloadNodeSettingForm', 'controlPlaneSetting') === 'dev') {
//             return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'devInstanceType');
//         } else {
//             return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'prodInstanceType');
//         }
//     }

//     public getSharedClusterProxy(key: string) {
//         if (key === 'http') {
//             return this.getSharedHttpProxyParam();
//         } else if (key === 'https') {
//             return this.getSharedClusterHttpsProxy();
//         }
//     }

//     public getWorkloadClusterProxy(key: string) {
//         if (key === 'http') {
//             return this.getWorkloadHttpProxyParam();
//         } else if (key === 'https') {
//                 return this.getWorkloadClusterHttpsProxy();
//         }
//     }

//     public getCustomRepoImage() {
//         if (this.getBooleanFieldValue('customRepoSettingForm', 'customRepoSetting')) {
//             return this.getFieldValue('customRepoSettingForm', 'repoImage');
//         } else {
//             return '';
//         }
//     }

//     public getCustomRepoPublicCaCert() {
//         if (this.getBooleanFieldValue('customRepoSettingForm', 'customRepoSetting')) {
//             return this.getStringBoolFieldValue('customRepoSettingForm', 'publicCaCert');
//         } else {
//             return '';
//         }
//     }

//     public getCustomRepoUsername() {
//         if (this.getBooleanFieldValue('customRepoSettingForm', 'customRepoSetting')) {
//             return this.getFieldValue('customRepoSettingForm', 'repoUsername');
//         } else {
//             return '';
//         }
//     }

//     public getCustomRepoPassword() {
//         if (this.getBooleanFieldValue('customRepoSettingForm', 'customRepoSetting')) {
//             return this.getFieldValue('customRepoSettingForm', 'repoPassword');
//         } else {
//             return '';
//         }
//     }

    public enableLoggingExtension(key) {
        if (this.getFieldValue('extensionSettingForm', 'loggingEndpoint') === key) {
            return 'true';
        } else {
            return 'false';
        }
    }

//     public setTSMEnable() {
//         let tmcEnable = this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings');
//         if (tmcEnable === 'true') {
//             return this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'tsmSettings');
//         } else {
//             return 'false';
//         }
//     }

//     public setTSMExactName() {
//         let tmcEnable = this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings');
//         if (tmcEnable === 'true') {
//             let tsmEnable = this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'tsmSettings');
//             if (tsmEnable === 'true') {
//                 return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'exactName');
//             } else {
//                 return '';
//             }
//         } else {
//             return '';
//         }
//     }
//
//     public setTSMStartsWithName() {
//         let tmcEnable = this.getStringBoolFieldValue('tanzuSaasSettingForm', 'tmcSettings');
//         if (tmcEnable === 'true') {
//             let tsmEnable = this.getStringBoolFieldValue('vsphereWorkloadNodeSettingForm', 'tsmSettings');
//             if (tsmEnable === 'true') {
//                 return this.getFieldValue('vsphereWorkloadNodeSettingForm', 'startsWithName');
//             } else {
//                 return '';
//             }
//         } else {
//             return '';
//         }
//     }

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

    public getPayload() {
        // console.log((this.form.get('vsphereProviderForm') as FormGroup).get('password').value);
        // console.log(document.getElementById('ssoPassword'));
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
                        'aviController01Ip': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerIp'),
                        'aviController01Fqdn': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerFqdn'),
                        'aviController02Ip': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerIp02'),
                        'aviController02Fqdn': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerFqdn02'),
                        'aviController03Ip': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerIp03'),
                        'aviController03Fqdn': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviControllerFqdn03'),
                        'aviClusterIp': this.getFieldValue('vsphereAVINetworkSettingForm', 'clusterIp'),
                        'aviClusterFqdn': this.getFieldValue('vsphereAVINetworkSettingForm', 'clusterFqdn'),
                        'aviSize': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviSize'),
//                         'aviLicenseKey': this.getFieldValue('vsphereAVINetworkSettingForm', 'aviLicenseKey'),
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
//                         'tkgsVsphereNamespaceWorkloadNetwork': this.getFieldValue('namespaceForm', 'segmentName'),
                        'tkgsVsphereNamespaceContentLibrary': this.getFieldValue('namespaceForm', 'contentLib'),
                        'tkgsVsphereNamespaceVmClasses': this.getFieldValue('namespaceForm', 'vmClass'),
                        'tkgsVsphereNamespaceResourceSpec': this.getTkgsResourceSpec(),
                        'tkgsVsphereNamespaceStorageSpec': this.getTkgsStorageSpec(),
                        'tkgsVsphereWorkloadClusterSpec': {
                            'tkgsVsphereNamespaceName': this.getFieldValue('namespaceForm', 'namespaceName') === 'CREATE NEW' ? this.getFieldValue('namespaceForm', 'newNamespaceName') : this.getFieldValue('namespaceForm', 'namespaceName'),
                            'tkgsVsphereWorkloadClusterName': this.getFieldValue('workloadClusterForm', 'clusterName'),
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
                            'tkgWorkloadClusterBackupLocation': this.getFieldValue('workloadClusterForm', 'veleroTargetLocation')
                        },
                    },
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
                        // 'elasticSearchEndpoint': {
                        //     'enableElasticSearchEndpoint': !this.apiClient.toEnabled ? this.enableLoggingExtension('Elastic Search') : "false",
                        //     'elasticSearchEndpointAddress': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'elasticSearchAddress') : "",
                        //     'elasticSearchEndpointPort': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'elasticSearchPort') : "",
                        // },
                        'kafkaEndpoint': {
                            'enableKafkaEndpoint': this.enableLoggingExtension('Kafka'),
                            'kafkaBrokerServiceName': this.getFieldValue('extensionSettingForm', 'kafkaBrokerServiceName'),
                            'kafkaTopicName': this.getFieldValue('extensionSettingForm', 'kafkaTopicName'),
                        },
                        // 'splunkEndpoint': {
                        //     'enableSplunkEndpoint': !this.apiClient.toEnabled ? this.enableLoggingExtension('Splunk') : "false",
                        //     'splunkEndpointAddress': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'splunkAddress') : "",
                        //     'splunkEndpointPort': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'splunkPort') : "",
                        //     'splunkEndpointToken': !this.apiClient.toEnabled ? this.getFieldValue('extensionSettingForm', 'splunkToken') : "",
                        // },
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
        // TODO Change Enable control plane ha key here
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
