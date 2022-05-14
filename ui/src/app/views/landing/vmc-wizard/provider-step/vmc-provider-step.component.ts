/**
 * Angular Modules
 */
import {Component, OnInit} from '@angular/core';
import {FormControl, Validators} from '@angular/forms';
import {Router} from '@angular/router';
import {ClrLoadingState} from '@clr/angular';
import {Subscription} from 'rxjs';
import {debounceTime, distinctUntilChanged, takeUntil} from 'rxjs/operators';

/**
 * App imports
 */
import {AppEdition} from 'src/app/shared/constants/branding.constants';
import {APP_ROUTES, Routes} from 'src/app/shared/constants/routes.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import {kubernetesOvas, NodeType} from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import {VMCDataService} from '../../../../shared/service/vmc-data.service';
import {StepFormDirective} from '../../wizard/shared/step-form/step-form';
import {ValidationService} from '../../wizard/shared/validation/validation.service';

declare var sortPaths: any;

const SupervisedField = ['sddcToken', 'orgName', 'sddcName'];
const MarketplaceField = ['marketplaceRefreshToken'];

/**
 * vSphere Version Info definition
 */
export interface VsphereVersioninfo {
    version: string,
    build: string;
}

@Component({
    selector: 'app-vmc-provider-step',
    templateUrl: './vmc-provider-step.component.html',
    styleUrls: ['./vmc-provider-step.component.scss']
})
export class VMCProviderStepComponent extends StepFormDirective implements OnInit {

    APP_ROUTES: Routes = APP_ROUTES;

    loading = false;
    loadData = false;
    connected = false;
    validateToken = false;
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    dataLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    validateLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;

    fetchResources = false;
    validateRefreshToken = false;
    fetchCluster: boolean = false;
    fetchDatastore: boolean = false;
    fetchOvaImage = false;
    aviOvaErrorNotification;

    datacenters = [];
    clusters = [];
    datastores = [];
    resourcePools = [];
    contentLibs = [];
    aviOvaImages = [];
    nodeTypes: Array<NodeType> = [];
    kubernetesOvas: Array<NodeType> = kubernetesOvas;

    edition: AppEdition = AppEdition.TCE;

    datastoreError = false;
    datastoreErrorMsg = 'Provided Datastore is not found, please select again.';
    clusterError = false;
    clusterErrorMsg = 'Provided Cluster is not found, please select again.';
    datacenterError = false;
    datacenterErrorMsg = 'Provided Datacenter is not found, please select again.';
    contentLibError = false;
    contentLibErrorMsg = 'Provided Content Library is not found, please select again.';
    ovaImageError = false;
    ovaImageErrorMsg = 'Provided AVI Ova Image is not found, please select again.';
    resourcePoolError = false;
    resourcePoolErrorMsg = 'Provided Resource Pool is not found, please select again.';

    subscription: Subscription;
    uploadStatus: boolean;
    private sddcToken;

    private vmcDatacenter;
    private vmcCluster;
    private vmcDatastore;
    private vmcContentLib;
    private vmcOvaImage;
    private vmcResourcePool;
    private orgName;
    private sddcName;
    customerConnect = false;
    private custUsername;
    private custPassword;
    private kubernetesOva;
    private jwtToken;

    isMarketplace = false;
    private marketplaceRefreshToken;

    constructor(private validationService: ValidationService,
                private apiClient: APIClient,
                private router: Router,
                private dataService: VMCDataService) {
        super();
        this.nodeTypes = [...kubernetesOvas];
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl('sddcToken', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('orgName', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('sddcName', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));

        this.formGroup.addControl('datacenter', new FormControl('', [Validators.required]));
        this.formGroup.addControl('cluster', new FormControl('', [Validators.required]));
        this.formGroup.addControl('datastore', new FormControl('', [Validators.required]));
        this.formGroup.addControl('resourcePool', new FormControl('', []));
        // Optional if marketplace is enabled
        this.formGroup.addControl('contentLib', new FormControl('', [Validators.required]));
        this.formGroup.addControl('aviOvaImage', new FormControl('', [Validators.required]));
        // Customer Connect form fields
        this.formGroup.addControl('customerConnect', new FormControl(false));
        this.formGroup.addControl('custUsername', new FormControl('', []));
        this.formGroup.addControl('custPassword', new FormControl('', []));
        this.formGroup.addControl('kubernetesOva', new FormControl('', []));
        this.formGroup.addControl('jwtToken', new FormControl('', []));
        // Marketplace form fields
        this.formGroup.addControl('isMarketplace', new FormControl(false));
        this.formGroup.addControl('marketplaceRefreshToken', new FormControl('', []));
        this.disableFormFields();

        MarketplaceField.forEach(field => {
            this.formGroup.get(field).valueChanges
                .pipe(
                    debounceTime(500),
                    distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                    takeUntil(this.unsubscribe))
                    .subscribe(() => {
                        this.validateToken = false;
                });
        });
        SupervisedField.forEach(field => {
            // tslint:disable-next-line:max-line-length
            this.formGroup.get(field).valueChanges.pipe(
                debounceTime(500),
                distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                takeUntil(this.unsubscribe))
                .subscribe(() => {
                    this.connected = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    this.formGroup.get('datacenter').setValue('');
                    this.datacenters = [];
                    this.formGroup.get('datacenter').disable();

                    this.formGroup.get('cluster').setValue('');
                    this.clusters = [];
                    this.formGroup.get('cluster').disable();

                    this.formGroup.get('datastore').setValue('');
                    this.datastores = [];
                    this.formGroup.get('datastore').disable();

                    this.formGroup.get('resourcePool').setValue('');
                    this.resourcePools = [];
                    this.formGroup.get('resourcePool').disable();
                    this.formGroup.get('contentLib').setValue('');
                    this.contentLibs = [];
                    this.formGroup.get('contentLib').disable();
                    this.formGroup.get('aviOvaImage').setValue('');
                    this.aviOvaImages = [];
                    this.formGroup.get('aviOvaImage').disable();
                });
        });
        this.formGroup['canMoveToNext'] = () => {
            if (this.formGroup.value['isMarketplace']) {
                this.vmcSession();
                return this.formGroup.valid && this.fetchResources && this.validateToken && this.fetchCluster && this.fetchDatastore;
            } else {
                this.vmcSession();
                return this.formGroup.valid && this.fetchResources && this.fetchOvaImage && this.fetchCluster && this.fetchDatastore;
            }
        };
        this.formGroup.get('datastore').valueChanges.subscribe(() => this.datastoreError = false);
        this.formGroup.get('cluster').valueChanges.subscribe(() => this.clusterError = false);
        this.formGroup.get('datacenter').valueChanges.subscribe(() => this.datacenterError = false);
        this.formGroup.get('resourcePool').valueChanges.subscribe(() => this.resourcePoolError = false);
        this.formGroup.get('contentLib').valueChanges.subscribe(() => this.contentLibError = false);
        this.formGroup.get('aviOvaImage').valueChanges.subscribe(() => this.ovaImageError = false);

        this.subscription = this.dataService.currentInputFileStatus.subscribe(
            (uploadStatus) => this.uploadStatus = uploadStatus);
        if (this.uploadStatus) {
            this.subscription = this.dataService.currentSddcToken.subscribe(
                (sddcToken) => this.sddcToken = sddcToken);
            this.formGroup.get('sddcToken').setValue(this.sddcToken);
            this.subscription = this.dataService.currentOrgName.subscribe(
                (orgName) => this.orgName = orgName);
            this.formGroup.get('orgName').setValue(this.orgName);
            this.subscription = this.dataService.currentSddcName.subscribe(
                (sddcName) => this.sddcName = sddcName);
            this.formGroup.get('sddcName').setValue(this.sddcName);
            this.subscription = this.dataService.currentDatacenter.subscribe(
                (datacenter) => this.vmcDatacenter = datacenter);
            this.subscription = this.dataService.currentCluster.subscribe(
                (cluster) => this.vmcCluster = cluster);
            this.subscription = this.dataService.currentDatastore.subscribe(
                (datastore) => this.vmcDatastore = datastore);
            this.subscription = this.dataService.currentResourcePool.subscribe(
                (resourcePool) => this.vmcResourcePool = resourcePool);
            this.subscription = this.dataService.currentContentLib.subscribe(
                (contentLib) => this.vmcContentLib = contentLib);
            this.subscription = this.dataService.currentOvaImage.subscribe(
                (ovaImage) => this.vmcOvaImage = ovaImage);
            this.subscription = this.dataService.currentMarketplace.subscribe(
                (marketplace) => this.isMarketplace = marketplace);
            this.formGroup.get('isMarketplace').setValue(this.isMarketplace);
            // this.subscription = this.dataService.currentCustomerConnect.subscribe(
            //     (customerConnect) => this.customerConnect = customerConnect);
            // this.formGroup.get('customerConnect').setValue(this.customerConnect);
            // if (this.customerConnect) {
            //     this.toggleCustomerConnect();
            //     this.subscription = this.dataService.currentCustUsername.subscribe(
            //         (custUsername) => this.custUsername = custUsername);
            //     this.formGroup.get('custUsername').setValue(this.custUsername);
            //     this.subscription = this.dataService.currentCustPassword.subscribe(
            //         (custPassword) => this.custPassword = custPassword);
            //     this.formGroup.get('custPassword').setValue(this.custPassword);
            //     this.subscription = this.dataService.currentJwtToken.subscribe(
            //         (jwtToken) => this.jwtToken = jwtToken);
            //     this.formGroup.get('jwtToken').setValue(this.jwtToken);
            //     this.subscription = this.dataService.currentKubernetesOva.subscribe(
            //         (kubernetesOva) => this.kubernetesOva = kubernetesOva);
            //     this.formGroup.get('kubernetesOva').setValue(this.kubernetesOva);
            // }
            /** If Marketplace is enabled, updating:
             * Marketplace Refresh Token
             */
            if (this.isMarketplace) {
                this.toggleMarketPlace();
                this.subscription = this.dataService.currentMarketplaceRefreshToken.subscribe(
                    (marketplaceToken) => this.marketplaceRefreshToken = marketplaceToken);
                this.formGroup.get('marketplaceRefreshToken').setValue(this.marketplaceRefreshToken);
            }
        }
        // this.subscription = this.dataService.currentCluster.subscribe(
        //     (cluster) => this.VcCluster = cluster);
        // this.formGroup.get('cluster').setValue(this.VcCluster);
        this.toggleMarketPlace();
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // don't fill password field with ****
        if (!this.uploadStatus) {
            this.formGroup.get('sddcToken').setValue('');
            // this.formGroup.get('custPassword').setValue('');
        } else {
            this.formGroup.get('sddcToken').setValue('');
        }
    }

    validateSDDCToken() {
        let refreshToken = this.formGroup.value['sddcToken'];
        this.apiClient.verifySDDCRefreshToken(refreshToken).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.validateRefreshToken = true;
                    this.vmcSession();
                } else if (data.responseType === 'ERROR') {
                    this.validateRefreshToken = false;
                    this.errorNotification = data.msg;
                }
            } else {
                this.validateRefreshToken = false;
                this.errorNotification = 'Validation of SDDC Token has failed.';
            }
        }, (err: any) => {
            this.validateRefreshToken = false;
            const error = err.error.msg || err.msg || JSON.stringify(err);
            this.errorNotification = 'Failed to connect to the SDDC Token. ${error}';
        });
    }
    /**
     * @method connectVMC
     * helper method to make connection to VC environment, call retrieveDatacenters
     * method if VC connection successful
     */
    connectVMC() {
        this.loadingState = ClrLoadingState.LOADING;
        this.vmcResources();
        //Uncomment above one line

        // Remove from 133 to 144
//         this.dumyFormFields();
//         this.errorNotification = '';
//         this.enableAllFormFields();
//         this.connected = true;
//         if (this.uploadStatus) {
//             this.validateResourceGroupData();
//         }
//         this.loadingState = ClrLoadingState.DEFAULT;
    }

    validateResourceGroupData() {
        this.errorNotification = '';
        if (!this.uploadStatus) {
            return true;
        } else {
            let invalidResourceGroup = '';
//             if (this.datastores.indexOf(this.vmcDatastore) === -1) {
//                 this.datastoreError = true;
//             } else {
//                 this.datastoreError = false;
//                 this.formGroup.get('datastore').setValue(this.vmcDatastore);
//             }
//             if (this.clusters.indexOf(this.vmcCluster) === -1) {
//                 this.clusterError = true;
//             } else {
//                 this.clusterError = false;
//                 this.formGroup.get('cluster').setValue(this.vmcCluster);
//             }
            if (this.datacenters.indexOf(this.vmcDatacenter) === -1) {
                this.datacenterError = true;
            } else {
                this.datacenterError = false;
                this.formGroup.get('datacenter').setValue(this.vmcDatacenter);
            }
            if (this.resourcePools.indexOf(this.vmcResourcePool) === -1) {
                this.resourcePoolError = true;
            } else {
                this.resourcePoolError = false;
                this.formGroup.get('resourcePool').setValue(this.vmcResourcePool);
            }
            if (!this.isMarketplace) {
                if (this.contentLibs.indexOf(this.vmcContentLib) === -1) {
                    this.contentLibError = true;
                } else {
                    this.contentLibError = false;
                    this.formGroup.get('contentLib').setValue(this.vmcContentLib);
                }
                if (this.aviOvaImages.indexOf(this.vmcOvaImage) === -1) {
                    this.ovaImageError = true;
                } else {
                    this.ovaImageError = false;
                    this.formGroup.get('aviOvaImage').setValue(this.vmcOvaImage);
                }
            }
        }
    }

//     getSSLThumbprint(vsphereHost) {
//         let payload = {
//             'envSpec': {
//                 'vcenterDetails': {
//                     'vcenterAddress':vsphereHost
//                 }
//             }
//         };
//         this.apiClient.getSSLThumbprint(payload).subscribe((data: any) => {
//             if (data && data !== null) {
//                 if (data.responseType === 'SUCCESS') {
//                     // this.connected = true;
//                     this.thumbprint = data.SHA1;
//                     this.formGroup.controls['thumbprint'].setValue(this.thumbprint);
//                     FormMetaDataStore.saveMetaDataEntry(this.formName, 'thumbprint', {
//                         label: 'SSL THUMBPRINT',
//                         displayValue: this.thumbprint,
//                     });
// //                     this.sslThumbprintModal.open();
//                     this.getVsphereData();
//                     // this.errorNotification = '';
//                     // this.connected = true;
//                     this.validateResourceGroupData();
//                 } else if (data.responseType === 'ERROR') {
//                     this.connected = false;
//                     this.errorNotification = data.msg;
//                 }
//             } else {
//                 this.connected = false;
//                 this.errorNotification = 'Some Error Occurred while Retrieving SSL Thumbprint';
//             }
//         }, (err: any) => {
//             const error = err.error.msg || err.msg || JSON.stringify(err);
//             this.errorNotification =
//                                 'Failed to connect to the specified vCenter Server. ${error}';
//         });
//     }
//
//     thumbprintModalResponse(validThumbprint: boolean) {
//         if (validThumbprint) {
//             this.login();
//         } else {
//             this.errorNotification = "Connection failed. Certificate thumbprint was not validated.";
//         }
//     }

    login() {
        this.loadingState = ClrLoadingState.LOADING;
        this.connected = true;
        this.errorNotification = '';
        this.loadingState = ClrLoadingState.DEFAULT;
    }

    /**
     * @method getDisabled
     * helper method to get if connect btn should be disabled
     */
    getDisabled(): boolean {
        return !(this.formGroup.get('sddcToken').valid);
    }

    disableFormFields() {

        this.formGroup.get('datacenter').disable();
        this.formGroup.get('cluster').disable();
        this.formGroup.get('datastore').disable();
        this.formGroup.get('resourcePool').disable();
        this.formGroup.get('contentLib').disable();
        this.formGroup.get('aviOvaImage').disable();
    }

    enableAllFormFields() {
        this.formGroup.get('orgName').enable();
        this.formGroup.get('sddcName').enable();
        this.formGroup.get('datacenter').enable();
//         this.formGroup.get('cluster').enable();
//         this.formGroup.get('datastore').enable();
        this.formGroup.get('resourcePool').enable();
        this.formGroup.get('contentLib').enable();
        // this.formGroup.get('aviOvaImage').enable();
    }
    dumyFormFields() {
        this.datacenters = ['Datacenter-1', 'Datacenter-2'];
        this.clusters = ['Cluster-1', 'Cluster-2'];
        this.datastores = ['Datastore-1', 'Datastore-2'];
        this.resourcePools = ['Resource-pool-1', 'Resource-pool-2'];
        this.contentLibs = ['Content-lib-1', 'Content-lib-2'];
        this.aviOvaImages = ['Ova-image-1', 'Ova-image-2'];
        this.apiClient.networks = ['Network-1', 'Network-2', 'Network-3', 'Network-4'];
        this.fetchResources = true;
        this.fetchOvaImage = true;
    }

    getOvaImagesUnderContentLib(contentLibName: string) {
        let vmcData = {
            "sddcToken": "",
            "sddcName": "",
            "orgName": ""
        };

        vmcData['sddcToken'] = this.formGroup.get('sddcToken').value;
        vmcData['sddcName'] = this.formGroup.get('sddcName').value;
        vmcData['orgName'] = this.formGroup.get('orgName').value;

        this.apiClient.getOvaImagesUnderContentLib(vmcData, contentLibName, 'vmc').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.aviOvaImages = data.CONTENT_LIBRARY_FILES;
                    this.formGroup.get('aviOvaImage').enable();
                    this.fetchOvaImage = true;
                    this.aviOvaErrorNotification = '';
                    if (this.uploadStatus) {
                        if (this.vmcOvaImage !== '') {
                            if (this.aviOvaImages.indexOf(this.vmcOvaImage) === -1) {
                                this.ovaImageError = true;
                            } else {
                                this.ovaImageError = false;
                                this.formGroup.get('aviOvaImage').setValue(this.vmcOvaImage);
                            }
                        }
                    }
                } else if (data.responseType === 'ERROR') {
                    this.fetchOvaImage = false;
                    this.aviOvaErrorNotification = 'Fetch OVA Images: ' + data.msg;
                }
            } else {
                this.fetchOvaImage = false;
                this.aviOvaErrorNotification = 'Fetch OVA Images: Some error occurred while listing Content Library Files.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.fetchOvaImage = false;
                this.aviOvaErrorNotification = 'Fetch OVA Images: ' + error.msg;
            } else {
                this.fetchOvaImage = false;
                this.aviOvaErrorNotification = 'Fetch OVA Images: Some error occurred while listing Content Library Files.';
            }
        });
    }

    getClustersUnderDatacenter(datacenter: string) {
        let vmcData = {
            "sddcToken": "",
            "sddcName": "",
            "orgName": "",
            "datacenter": datacenter,
        };

        vmcData['sddcToken'] = this.formGroup.get('sddcToken').value;
        vmcData['sddcName'] = this.formGroup.get('sddcName').value;
        vmcData['orgName'] = this.formGroup.get('orgName').value;

        this.apiClient.getClustersUnderDatacenterVMC(vmcData, 'vmc', 'tkgm').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.clusters = data.CLUSTERS;
                    this.formGroup.get('cluster').enable();
                    this.fetchCluster = true;
                    this.clusterErrorMsg = '';
                    if (this.uploadStatus) {
                        if (this.vmcCluster !== '') {
                            if (this.clusters.indexOf(this.vmcCluster) !== -1) {
                                this.formGroup.get('cluster').setValue(this.vmcCluster);
                            }
                        }
                    }
                    this.getDatastoresUnderDatacenter(datacenter);
                } else if (data.responseType === 'ERROR') {
                    this.fetchCluster = false;
                    this.clusterError = true;
                    this.clusterErrorMsg = 'Fetch Clusters: ' + data.msg;
                }
            } else {
                this.fetchCluster = false;
                this.clusterError = true;
                this.clusterErrorMsg = 'Fetch Clusters: Some error occurred while listing Clusters under datacenter - ' + datacenter;
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.fetchCluster = false;
                this.clusterError = true;
                this.clusterErrorMsg = 'Fetch Clusters: ' + error.msg;
            } else {
                this.fetchCluster = false;
                this.clusterError = true;
                this.clusterErrorMsg = 'Fetch Clusters: Some error occurred while listing Clusters under datacenter - ' + datacenter;
            }
        });
    }

    getDatastoresUnderDatacenter(datacenter: string) {
        let vmcData = {
            "sddcToken": "",
            "sddcName": "",
            "orgName": "",
            "datacenter": datacenter,
        };

        vmcData['sddcToken'] = this.formGroup.get('sddcToken').value;
        vmcData['sddcName'] = this.formGroup.get('sddcName').value;
        vmcData['orgName'] = this.formGroup.get('orgName').value;

        this.apiClient.getDatastoresUnderDatacenterVMC(vmcData, 'vmc', 'tkgm').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.datastores = data.DATASTORES;
                    this.formGroup.get('datastore').enable();
                    this.fetchDatastore = true;
                    this.datastoreErrorMsg = '';
                    if (this.uploadStatus) {
                        if (this.vmcDatastore !== '') {
                            if (this.datastores.indexOf(this.vmcDatastore) !== -1) {
                                this.formGroup.get('datastore').setValue(this.vmcDatastore);
                            }
                        }
                    }
                } else if (data.responseType === 'ERROR') {
                    this.fetchDatastore = false;
                    this.datastoreError = true;
                    this.datastoreErrorMsg = 'Fetch Datastores: ' + data.msg;
                }
            } else {
                this.fetchDatastore = false;
                this.datastoreError = true;
                this.datastoreErrorMsg = 'Fetch Datastores: Some error occurred while listing Datastores under datacenter - ' + datacenter;
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.fetchDatastore = false;
                this.datastoreError = true;
                this.datastoreErrorMsg = 'Fetch Datastores: ' + error.msg;
            } else {
                this.fetchDatastore = false;
                this.datastoreError = true;
                this.datastoreErrorMsg = 'Fetch Datastores: Some error occurred while listing Datastores under datacenter - ' + datacenter;
            }
        });
    }

    vmcSession() {
        let data = {
            'sddcRefreshToken' : this.formGroup.get('sddcToken').value,
            'orgName': this.formGroup.get('orgName').value,
            'sddcName': this.formGroup.get('sddcName').value,
            'sddcDatacenter': this.formGroup.get('datacenter').value,
            'sddcCluster': this.formGroup.get('cluster').value,
            'sddcDatastore': this.formGroup.get('datastore').value,
            'resourcePoolName': this.formGroup.get('resourcePool').value,
            'refreshToken': this.formGroup.get('marketplaceRefreshToken').value,
            'contentLibraryName': this.formGroup.get('contentLib').value,
            'aviOvaName': this.formGroup.get('aviOvaImage').value,
        };
        this.apiClient.getVMCSession(data, 'vmc').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                } else if (data.responseType === 'ERROR') {
                    this.errorNotification = data.msg;
                }
            } else {
                this.errorNotification = 'Failed to establish a session to the VMC environment';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.errorNotification = error.msg;
            } else {
                this.errorNotification = 'Failed to establish a session to the VMC environment';
            }
        });
    }

    vmcResources() {
        let sddcToken = this.formGroup.get('sddcToken').value;
        let sddcName = this.formGroup.get('sddcName').value;
        let orgName = this.formGroup.get('orgName').value;

        this.apiClient.getVMCResources(sddcToken, sddcName, orgName).subscribe((data: any) => {
              if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.datacenters = data.DATACENTERS;
//                     this.clusters = data.CLUSTERS;
//                     this.datastores = data.DATASTORES;
                    this.resourcePools = data.RESOURCEPOOLS;
                    this.contentLibs = data.CONTENTLIBRARY_NAMES;
                    // this.aviOvaImages = data.CONTENTLIBRARY_FILES;
                    if (this.uploadStatus){
                        if (this.datacenters.indexOf(this.vmcDatacenter) === -1) {
                            this.datacenterError = true;
                        } else {
                            this.datacenterError = false;
                            this.formGroup.get('datacenter').setValue(this.vmcDatacenter);
                            this.getClustersUnderDatacenter(this.vmcDatacenter);
                        }
//                         if (this.clusters.indexOf(this.vmcCluster) === -1) {
//                             this.clusterError = true;
//                         } else {
//                             this.clusterError = false;
//                             this.formGroup.get('cluster').setValue(this.vmcCluster);
//                         }
//                         if (this.datastores.indexOf(this.vmcDatastore) === -1) {
//                             this.datastoreError = true;
//                         } else {
//                             this.datastoreError = false;
//                             this.formGroup.get('datastore').setValue(this.vmcDatastore);
//                         }
                        if (this.resourcePools.indexOf(this.vmcResourcePool) === -1) {
                            this.resourcePoolError = true;
                        } else {
                            this.resourcePoolError = false;
                            this.formGroup.get('resourcePool').setValue(this.vmcResourcePool);
                        }
                        if (!this.isMarketplace) {
                            if (this.contentLibs.indexOf(this.vmcContentLib) === -1) {
                                this.contentLibError = true;
                            } else {
                                this.contentLibError = false;
                                this.formGroup.get('contentLib').setValue(this.vmcContentLib);
                                this.getOvaImagesUnderContentLib(this.vmcContentLib);
                            }
                        }
                    }
                    this.apiClient.networks = data.NETWORKS;
                    this.fetchResources = true;
                    this.errorNotification = '';
                    this.connected = true;
                    this.enableAllFormFields();
                    this.loadingState = ClrLoadingState.DEFAULT;
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.errorNotification = data.msg;
                    this.loadingState = ClrLoadingState.DEFAULT;
                }
              } else {
                this.fetchResources = false;
                this.errorNotification = 'Some Error Occurred while Fetching Resources, Please check SDDC Token, Org Name and SDDC Name again';
                this.loadingState = ClrLoadingState.DEFAULT;
              }
            }, (error: any) => {
              if (error.responseType === 'ERROR') {
                this.fetchResources = false;
                this.errorNotification = error.msg;
                this.loadingState = ClrLoadingState.DEFAULT;
              } else {
                this.fetchResources = false;
                this.errorNotification = 'Some Error Occurred while Fetching Resources, Please check SDDC Token, Org Name and SDDC Name again';
                this.loadingState = ClrLoadingState.DEFAULT;
              }
            });
    }

    reloadVMCResources() {
        let sddcToken = this.formGroup.get('sddcToken').value;
        let sddcName = this.formGroup.get('sddcName').value;
        let orgName = this.formGroup.get('orgName').value;
        this.dataLoadingState = ClrLoadingState.LOADING;
        this.apiClient.getVMCResources(sddcToken, sddcName, orgName).subscribe((data: any) => {
              if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.datacenters = data.DATACENTERS;
//                     this.clusters = data.CLUSTERS;
//                     this.datastores = data.DATASTORES;
                    this.resourcePools = data.RESOURCEPOOLS;
                    this.apiClient.networks = data.NETWORKS;
                    this.contentLibs = data.CONTENTLIBRARY_NAMES ;
                    // this.aviOvaImages = data.CONTENTLIBRARY_FILES ;
                    this.fetchResources = true;
                    this.errorNotification = '';
                    this.connected = true;
                    this.loadData = true;
                    this.dataLoadingState = ClrLoadingState.DEFAULT;
                    this.enableAllFormFields();
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.errorNotification = data.msg;
                    this.loadData = false;
                    this.dataLoadingState = ClrLoadingState.DEFAULT;
                }
              } else {
                this.fetchResources = false;
                this.loadData = false;
                this.errorNotification = 'Some Error Occurred while Fetching Resources, Please check SDDC Token, Org Name and SDDC Name again';
                this.dataLoadingState = ClrLoadingState.DEFAULT;
              }
            }, (error: any) => {
              if (error.responseType === 'ERROR') {
                this.fetchResources = false;
                this.loadData = false;
                this.errorNotification = error.msg;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
              } else {
                this.fetchResources = false;
                this.loadData = false;
                this.errorNotification = 'Some Error Occurred while Fetching Resources, Please check SDDC Token, Org Name and SDDC Name again';
                this.dataLoadingState = ClrLoadingState.DEFAULT;
              }
            });
    }

    toggleCustomerConnect() {
        const customerAccountSettingsFields = [
            'custUsername',
            'custPassword',
            'jwtToken',
            'kubernetesOva',
        ];
        const contentLibFields = [
            'contentLib',
            'aviOvaImage',
        ];
        if (!this.formGroup.value['customerConnect']) {
            this.resurrectField('contentLib', [
                Validators.required
            ], this.formGroup.value['contentLib']);
            this.resurrectField('aviOvaImage', [
                Validators.required
            ], this.formGroup.value['aviOvaImage']);
            customerAccountSettingsFields.forEach((field) => {
                this.disarmField(field, true);
            });
        } else {
            this.resurrectField('custUsername', [
                Validators.required, this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['custUsername']);
            this.resurrectField('custPassword', [
                Validators.required
            ], this.formGroup.value['custPassword']);
            this.resurrectField('jwtToken', [
                Validators.required, this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['jwtToken']);
            this.resurrectField('kubernetesOva', [
                Validators.required
            ], this.formGroup.value['kubernetesOva']);
            contentLibFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    toggleMarketPlace() {
        const marketplaceFields = [
            'marketplaceRefreshToken',
        ];
        const contentLibFields = [
            'contentLib',
            'aviOvaImage',
        ];
        if (!this.formGroup.value['isMarketplace']) {
            this.resurrectField('contentLib', [
                Validators.required
            ], this.formGroup.value['contentLib']);
            this.resurrectField('aviOvaImage', [
                Validators.required
            ], this.formGroup.value['aviOvaImage']);
            marketplaceFields.forEach((field) => {
                this.disarmField(field, true);
            });
        } else {
            this.resurrectField('marketplaceRefreshToken', [
                Validators.required, this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['marketplaceRefreshToken']);
            contentLibFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    verifyMarketplaceRefreshToken() {
        let refreshToken = this.formGroup.controls['marketplaceRefreshToken'].value;
        this.validateLoadingState = ClrLoadingState.LOADING;
        this.apiClient.verifyMarketplaceToken(refreshToken, 'vmc').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.validateToken = true;
                    this.validateLoadingState = ClrLoadingState.DEFAULT;
                } else if (data.responseType === 'ERROR') {
                    this.validateToken = false;
                    this.validateLoadingState = ClrLoadingState.DEFAULT;
                    if (data.hasOwnProperty('msg')) {
                        this.errorNotification = data.msg;
                    } else {
                        this.errorNotification = 'Validation of Marketplace Refresh Token has failed. Please ensure the env has connectivity to external networks.';
                    }
                }
            } else {
                this.validateToken = false;
                this.validateLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Validation of Marketplace Refresh Token has failed. Please ensure the env has connectivity to external networks.';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.validateToken = false;
                this.validateLoadingState = ClrLoadingState.DEFAULT;
                // tslint:disable-next-line:max-line-length
                this.errorNotification = 'Validation of Marketplace Refresh Token has failed. Please ensure the env has connectivity to external networks. ' + err.msg;
            } else {
                this.validateToken = false;
                this.validateLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Validation of Marketplace Refresh Token has failed. Please ensure the env has connectivity to external networks.';
            }
        });
    }
    dumyTokenValidation() {
        let refreshToken = this.formGroup.controls['marketplaceRefreshToken'].value;
        this.validateToken = true;
        this.validateLoadingState = ClrLoadingState.DEFAULT;
    }

    onContentLibChange() {
        if (!this.formGroup.get('isMarketplace').value) {
            if (this.formGroup.get('contentLib').value !== '') {
                this.formGroup.get('aviOvaImage').disable();
                this.getOvaImagesUnderContentLib(this.formGroup.get('contentLib').value);
            }
        }
    }

    onDatacenterChange() {
        if (this.formGroup.get('datacenter').value !== '') {
            this.formGroup.get('cluster').disable();
            this.formGroup.get('datastore').disable();
            this.getClustersUnderDatacenter(this.formGroup.get('datacenter').value);
        }
    }
}
