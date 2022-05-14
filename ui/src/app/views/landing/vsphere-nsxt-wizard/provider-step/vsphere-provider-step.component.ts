/**
 * Angular Modules
 */
import {Component, OnInit, ViewChild} from '@angular/core';
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
import {VsphereNsxtDataService} from '../../../../shared/service/vsphere-nsxt-data.service';
import {SSLThumbprintModalComponent} from '../../wizard/shared/components/modals/ssl-thumbprint-modal/ssl-thumbprint-modal.component';
import {FormMetaDataStore} from '../../wizard/shared/FormMetaDataStore';
import {StepFormDirective} from '../../wizard/shared/step-form/step-form';
import {ValidationService} from '../../wizard/shared/validation/validation.service';

declare var sortPaths: any;

const SupervisedField = ['vcenterAddress', 'username', 'password', 'nsxtAddress', 'nsxtUsername', 'nsxtPassword'];
const MarketplaceField = ['marketplaceRefreshToken'];
/**
 * vSphere Version Info definition
 */
export interface VsphereVersioninfo {
    version: string,
    build: string;
}

@Component({
    selector: 'app-vsphere-provider-step',
    templateUrl: './vsphere-provider-step.component.html',
    styleUrls: ['./vsphere-provider-step.component.scss']
})
export class VSphereProviderStepComponent extends StepFormDirective implements OnInit {
    @ViewChild(SSLThumbprintModalComponent) sslThumbprintModal: SSLThumbprintModalComponent;

    APP_ROUTES: Routes = APP_ROUTES;

    loading: boolean = false;
    connected: boolean = false;
    validateToken = false;
    loadData: boolean = false;
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    dataLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    validateLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;

    fetchResources: boolean = false;
    fetchNsxtResources: boolean = false;
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
    tier1Routers = [];
    nsxtOverlays = [];

    vsphereHost: string;
    thumbprint: string;
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
    nsxtTier1RouterError = false;
    nsxtTier1RouterErrorMsg = 'Provided Tier1 Router is not found, please select again';
    nsxtOverlayError = false;
    nsxtOverlayErrorMsg = 'Provided NSX-T Overlay is not found, please select again';
    subscription: Subscription;
    uploadStatus: boolean;

    nodeTypes: Array<NodeType> = [];
    kubernetesOvas: Array<NodeType> = kubernetesOvas;
    private VcFqdn;
    private VcUser;
    private VcPassword;
    private VcDatacenter;
    private VcCluster;
    private VcDatastore;
    private VcContentLib;
    private VcOvaImage;
    private VcResourcePool;
    private VcNsxtAddress;
    private VcNsxtUsername;
    private VcNsxtPassword;
    private NsxtTier1Router;
    private NsxtOverlay;

    private customerConnect = false;
    private custUsername;
    private custPassword;
    private kubernetesOva;
    private jwtToken;

    arcasHttpUsername: string;
    arcasHttpsUsername: string;
    arcasHttpUrl: string;
    arcasHttpsUrl: string;
    arcasSameAsHttp: boolean;
    arcasHttpPassword: string;
    arcasHttpsPassword: string;

    isMarketplace = false;
    private marketplaceRefreshToken;
    constructor(private validationService: ValidationService,
                private apiClient: APIClient,
                private router: Router,
                private dataService: VsphereNsxtDataService) {
        super();
        this.nodeTypes = [...kubernetesOvas];
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl('vcenterAddress', new FormControl('', [Validators.required,
            this.validationService.isValidIpOrFqdn(),
            this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('username', new FormControl('', [Validators.required,
            this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('password',
            new FormControl('', [
                Validators.required]
            ));
        this.formGroup.addControl('nsxtAddress', new FormControl('', [Validators.required,
            this.validationService.isValidIpOrFqdn(),
            this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('nsxtUsername', new FormControl('', [Validators.required,
            this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('nsxtPassword', new FormControl('', [Validators.required]));
        this.formGroup.addControl('datacenter', new FormControl('', [Validators.required]));
        this.formGroup.addControl('cluster', new FormControl('', [Validators.required]));
        this.formGroup.addControl('datastore', new FormControl('', [Validators.required]));
        this.formGroup.addControl('resourcePool', new FormControl('', []));
        this.formGroup.addControl('tier1Router', new FormControl('', [Validators.required]));
        this.formGroup.addControl('nsxtOverlay', new FormControl('', [Validators.required]));
        // Customer Connect form fields
        // this.formGroup.addControl('customerConnect', new FormControl(false));
        // this.formGroup.addControl('custUsername', new FormControl('', []));
        // this.formGroup.addControl('custPassword', new FormControl('', []));
        // this.formGroup.addControl('jwtToken', new FormControl('', []));
        // this.formGroup.addControl('kubernetesOva', new FormControl('', []));
        // Marketplace form fields
        this.formGroup.addControl('isMarketplace', new FormControl(false));
        this.formGroup.addControl('marketplaceRefreshToken', new FormControl('', []));
        // Optional if marketplace is enabled
        this.formGroup.addControl('contentLib', new FormControl('', [Validators.required]));
        this.formGroup.addControl('aviOvaImage', new FormControl('', [Validators.required]));
        // Fetched from Backend, no use on UI
        this.formGroup.addControl('thumbprint', new FormControl('', []));

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

                    this.formGroup.get('contentLib').setValue('');
                    this.contentLibs = [];
                    this.formGroup.get('contentLib').disable();

                    this.formGroup.get('aviOvaImage').setValue('');
                    this.aviOvaImages = [];
                    this.formGroup.get('aviOvaImage').disable();

                    this.formGroup.get('resourcePool').setValue('');
                    this.aviOvaImages = [];
                    this.formGroup.get('resourcePool').disable();

                    this.formGroup.get('tier1Router').setValue('');
                    this.aviOvaImages = [];
                    this.formGroup.get('tier1Router').disable();

                    this.formGroup.get('nsxtOverlay').setValue('');
                    this.nsxtOverlays = [];
                    this.formGroup.get('nsxtOverlay').disable();

                });
        });
        this.formGroup['canMoveToNext'] = () => {
            if (this.formGroup.value['isMarketplace']) {
                this.startSession();
                return this.formGroup.valid && this.fetchResources && this.validateToken && this.fetchCluster && this.fetchDatastore;
            } else {
                this.startSession();
                return this.formGroup.valid && this.fetchResources && this.fetchOvaImage && this.fetchCluster && this.fetchDatastore;
            }
            // if (this.apiClient.arcasProxyEnabled) {
            //     this.disarmField('kubernetesOva', true);
            //     return this.formGroup.valid && this.fetchResources;
            // } else {
            //     if (this.formGroup.get('customerConnect').value) {
            //         this.resurrectField('kubernetesOva', [
            //             Validators.required
            //         ], this.formGroup.value['kubernetesOva']);
            //         return this.formGroup.valid && this.fetchResources;
            //     } else {
            //         this.disarmField('kubernetesOva', true);
            //         return this.formGroup.valid && this.fetchResources;
            //     }
            // }
        };
        this.formGroup.get('datastore').valueChanges.subscribe(() => this.datastoreError = false);
        this.formGroup.get('cluster').valueChanges.subscribe(() => this.clusterError = false);
        this.formGroup.get('datacenter').valueChanges.subscribe(() => this.datacenterError = false);
        this.formGroup.get('contentLib').valueChanges.subscribe(() => this.contentLibError = false);
        this.formGroup.get('aviOvaImage').valueChanges.subscribe(() => this.ovaImageError = false);
        this.formGroup.get('resourcePool').valueChanges.subscribe(() => this.resourcePoolError = false);
        this.formGroup.get('tier1Router').valueChanges.subscribe(() => this.nsxtTier1RouterError = false);
        this.formGroup.get('nsxtOverlay').valueChanges.subscribe(() => this.nsxtOverlayError = false);
        this.subscription = this.dataService.currentInputFileStatus.subscribe(
            (uploadStatus) => this.uploadStatus = uploadStatus);
        if (this.uploadStatus) {
            this.subscription = this.dataService.currentVcAddress.subscribe(
                (VcFqdn) => this.VcFqdn = VcFqdn);
            this.formGroup.get('vcenterAddress').setValue(this.VcFqdn);
            this.subscription = this.dataService.currentVcUser.subscribe(
                (VcUser) => this.VcUser = VcUser);
            this.formGroup.get('username').setValue(this.VcUser);
            this.subscription = this.dataService.currentVcPass.subscribe(
                (VcPass) => this.VcPassword = VcPass);
            this.formGroup.get('password').setValue(this.VcPassword);
            this.subscription = this.dataService.currentNsxtAddress.subscribe(
                (nsxtAddress) => this.VcNsxtAddress = nsxtAddress);
            this.formGroup.get('nsxtAddress').setValue(this.VcNsxtAddress);
            this.subscription = this.dataService.currentNsxtUsername.subscribe(
                (nsxtUsername) => this.VcNsxtUsername = nsxtUsername);
            this.formGroup.get('nsxtUsername').setValue(this.VcNsxtUsername);
            this.subscription = this.dataService.currentNsxtPassword.subscribe(
                (nsxtPassword) => this.VcNsxtPassword = nsxtPassword);
            this.formGroup.get('nsxtPassword').setValue(this.VcNsxtPassword);

            this.subscription = this.dataService.currentDatacenter.subscribe(
                (datacenter) => this.VcDatacenter = datacenter);
            this.subscription = this.dataService.currentCluster.subscribe(
                (cluster) => this.VcCluster = cluster);
            this.subscription = this.dataService.currentDatastore.subscribe(
                (datastore) => this.VcDatastore = datastore);
            this.subscription = this.dataService.currentContentLib.subscribe(
                (contentLib) => this.VcContentLib = contentLib);
            this.subscription = this.dataService.currentOvaImage.subscribe(
                (ovaImage) => this.VcOvaImage = ovaImage);
            this.subscription = this.dataService.currentResourcePool.subscribe(
                (resourcePool) => this.VcResourcePool = resourcePool);
            this.subscription = this.dataService.currentTier1Router.subscribe(
                (tier1Router) => this.NsxtTier1Router = tier1Router);
            this.subscription = this.dataService.currentNsxtOverlay.subscribe(
                (nsxtOverlay) => this.NsxtOverlay = nsxtOverlay);
            // this.subscription = this.dataService.currentCustomerConnect.subscribe(
            //     (customerConnect) => this.customerConnect = customerConnect);
            // this.formGroup.get('customerConnect').setValue(this.customerConnect);
            // this.toggleCustomerConnect();
            // Setting Marketplace Toggle as per Uploaded JSON
            this.subscription = this.dataService.currentMarketplace.subscribe(
                (marketplace) => this.isMarketplace = marketplace);
            this.formGroup.get('isMarketplace').setValue(this.isMarketplace);
            // if (this.customerConnect) {
            //     this.subscription = this.dataService.currentCustUsername.subscribe(
            //         (custUsername) => this.custUsername = custUsername);
            //     this.formGroup.get('custUsername').setValue(this.custUsername);
            //     this.subscription = this.dataService.currentCustPassword.subscribe(
            //         (custPassword) => this.custPassword = custPassword);
            //     this.formGroup.get('custPassword').setValue(this.custPassword);
            //     this.subscription = this.dataService.currentJwtToken.subscribe(
            //         (jwtToken) => this.jwtToken = jwtToken);
            //     this.formGroup.get('jwtToken').setValue(this.jwtToken);
            //     if (!this.apiClient.arcasProxyEnabled) {
            //         this.subscription = this.dataService.currentKubernetesOva.subscribe(
            //             (kubernetesOva) => this.kubernetesOva = kubernetesOva);
            //         if (this.kubernetesOva === 'photon') {
            //             this.formGroup.get('kubernetesOva').setValue(this.nodeTypes[0].id);
            //         }
            //     }
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
            this.toggleMarketPlace();
        }
        this.toggleMarketPlace();
    }

    // checkArcasProxy() {
    //     if (this.apiClient.arcasProxyEnabled) {
    //         this.resurrectField('kubernetesOva', [],
    //             this.formGroup.value['kubernetesOva']);
    //     } else {
    //         this.resurrectField('kubernetesOva', [
    //             Validators.required
    //         ], this.formGroup.value['kubernetesOva']);
    //     }
    // }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // don't fill password field with ****
        if (!this.uploadStatus) {
            this.formGroup.get('password').setValue('');
            this.formGroup.get('nsxtPassword').setValue('');
            // this.formGroup.get('custPassword').setValue('');
        } else {
            this.formGroup.get('password').setValue('');
            this.formGroup.get('nsxtPassword').setValue('');
        }
    }

    /**
     * @method connectVC
     * helper method to make connection to VC environment, call retrieveDatacenters
     * method if VC connection successful
     */
    connectVC() {
        this.loadingState = ClrLoadingState.LOADING;
        this.vsphereHost = this.formGroup.controls['vcenterAddress'].value;
        // Keep below line
        this.getSSLThumbprint(this.vsphereHost);
        // Remove all
//         this.thumbprint = "XYXYXYXYXYXYX";
//         FormMetaDataStore.deleteMetaDataEntry('vsphereProviderForm', 'thumbprint');
//         this.formGroup.controls['thumbprint'].setValue(this.thumbprint);
//         FormMetaDataStore.saveMetaDataEntry(this.formName, 'thumbprint', {
//             label: 'SSL THUMBPRINT',
//             displayValue: this.thumbprint,
//         });
//         this.sslThumbprintModal.open();
//         this.dumyFormFields();
//         this.errorNotification = '';
//         this.enableAllFormFields();
//         this.connected = true;
//         if (this.uploadStatus) {
//             console.log(this.datastores);
//             console.log(this.VcDatastore);
//             console.log(this.clusters);
//             console.log(this.VcCluster);
//             console.log(this.contentLibs);
//             console.log(this.VcContentLib);
//             console.log(this.datacenters);
//             console.log(this.VcDatacenter);
//             console.log(this.aviOvaImages);
//             console.log(this.VcOvaImage);
//
//             this.validateResourceGroupData();
//         }
    }

    validateResourceGroupData() {
        this.errorNotification = '';
        if (!this.uploadStatus) {
            return true;
        } else {
            let invalidResourceGroup = '';
//             if (this.datastores.indexOf(this.VcDatastore) === -1) {
//                 this.datastoreError = true;
//             } else {
//                 this.datastoreError = false;
//                 this.formGroup.get('datastore').setValue(this.VcDatastore);
//             }
            if (this.clusters.indexOf(this.VcCluster) === -1) {
                this.clusterError = true;
            } else {
                this.clusterError = false;
                this.formGroup.get('cluster').setValue(this.VcCluster);
            }
            if (this.datacenters.indexOf(this.VcDatacenter) === -1) {
                this.datacenterError = true;
            } else {
                this.datacenterError = false;
                this.formGroup.get('datacenter').setValue(this.VcDatacenter);
            }
            if (!this.isMarketplace) {
                if (this.contentLibs.indexOf(this.VcContentLib) === -1) {
                    this.contentLibError = true;
                } else {
                    this.contentLibError = false;
                    this.formGroup.get('contentLib').setValue(this.VcContentLib);
                }
                if (this.aviOvaImages.indexOf(this.VcOvaImage) === -1) {
                    this.ovaImageError = true;
                } else {
                    this.ovaImageError = false;
                    this.formGroup.get('aviOvaImage').setValue(this.VcOvaImage);
                }
            }
            if (this.resourcePools.indexOf(this.VcResourcePool) === -1) {
                this.resourcePoolError = true;
            } else {
                this.resourcePoolError = false;
                this.formGroup.get('resourcePool').setValue(this.VcResourcePool);
            }
            if (this.tier1Routers.indexOf(this.NsxtTier1Router) === -1) {
                this.nsxtTier1RouterError = true;
            } else {
                this.nsxtTier1RouterError = false;
                this.formGroup.get('tier1Router').setValue(this.NsxtTier1Router);
            }
            if (this.nsxtOverlays.indexOf(this.NsxtOverlay) === -1) {
                this.nsxtOverlayError = true;
            } else {
                this.nsxtOverlayError = false;
                this.formGroup.get('nsxtOverlay').setValue(this.NsxtOverlay);
            }
        }
    }

    getSSLThumbprint(vsphereHost) {
        let payload = {
            'envSpec': {
                'vcenterDetails': {
                    'vcenterAddress': vsphereHost
                }
            }
        };
        this.apiClient.getSSLThumbprint(payload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.thumbprint = data.SHA1;
                    this.formGroup.controls['thumbprint'].setValue(this.thumbprint);
                    FormMetaDataStore.saveMetaDataEntry(this.formName, 'thumbprint', {
                        label: 'SSL THUMBPRINT',
                        displayValue: this.thumbprint,
                    });
                    this.sslThumbprintModal.open();
                    this.getVsphereData();
//                     this.validateResourceGroupData();
                } else if (data.responseType === 'ERROR') {
                    this.connected = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = data.msg;
                }
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Some Error Occurred while Retrieving SSL Thumbprint';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: ' + err.msg;
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: Please verify vCenter FQDN.';
            }
        });
    }

    thumbprintModalResponse(validThumbprint: boolean) {
        if (validThumbprint) {
            this.login();
        } else {
            this.errorNotification = 'Connection failed. Certificate thumbprint was not validated.';
        }
    }

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
        return !(this.formGroup.get('vcenterAddress').valid &&
                this.formGroup.get('username').valid &&
                this.formGroup.get('password').valid &&
                this.formGroup.get('nsxtAddress').valid &&
                this.formGroup.get('nsxtPassword').valid &&
                this.formGroup.get('nsxtUsername').valid);
    }

    disableFormFields() {
        this.formGroup.get('datacenter').disable();
        this.formGroup.get('cluster').disable();
        this.formGroup.get('datastore').disable();
        this.formGroup.get('resourcePool').disable();
        this.formGroup.get('contentLib').disable();
        this.formGroup.get('aviOvaImage').disable();
        this.formGroup.get('resourcePool').disable();
        this.formGroup.get('tier1Router').disable();
        this.formGroup.get('nsxtOverlay').disable();
    }

    enableAllFormFields() {
        this.formGroup.get('datacenter').enable();
//         this.formGroup.get('cluster').enable();
//         this.formGroup.get('datastore').enable();
        this.formGroup.get('resourcePool').enable();
        this.formGroup.get('contentLib').enable();
        // this.formGroup.get('aviOvaImage').enable();
        this.formGroup.get('tier1Router').enable();
        this.formGroup.get('nsxtOverlay').enable();
    }
    dumyFormFields() {
        this.datacenters = ['Datacenter-1', 'Datacenter-2'];
        this.clusters = ['Cluster-1', 'Cluster-2'];
        this.datastores = ['Datastore-1', 'Datastore-2'];
        this.resourcePools = ['Resource-pool-1', 'Resource-pool-2'];
        this.contentLibs = ['Content-lib-1', 'Content-lib-2'];
        this.aviOvaImages = ['Ova-image-1', 'Ova-image-2'];
        this.tier1Routers = ['Router-1', 'Router-2'];
        this.nsxtOverlays = ['Router-1', 'Router-2'];
        this.apiClient.networks = ['Network-1', 'Network-2', 'Network-3', 'Network-4'];
        this.fetchResources = true;
        this.fetchNsxtResources = true;
        this.fetchOvaImage = true;
    }

    getOvaImagesUnderContentLib(contentLibName: string) {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": ""
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;

        this.apiClient.getOvaImagesUnderContentLib(vCenterData, contentLibName, 'vcf').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.aviOvaImages = data.CONTENT_LIBRARY_FILES;
                    this.formGroup.get('aviOvaImage').enable();
                    this.fetchOvaImage = true;
                    this.aviOvaErrorNotification = '';
                    if (this.uploadStatus) {
                        if (this.VcOvaImage !== '') {
                            if (this.aviOvaImages.indexOf(this.VcOvaImage) === -1) {
                                this.ovaImageError = true;
                            } else {
                                this.ovaImageError = false;
                                this.formGroup.get('aviOvaImage').setValue(this.VcOvaImage);
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
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": "",
            "datacenter": datacenter,
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;

        this.apiClient.getClustersUnderDatacenter(vCenterData, 'vcf', 'tkgm').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.clusters = data.CLUSTERS;
                    this.formGroup.get('cluster').enable();
                    this.fetchCluster = true;
                    this.clusterErrorMsg = '';
                    if (this.uploadStatus) {
                        if (this.VcCluster !== '') {
                            if (this.clusters.indexOf(this.VcCluster) !== -1) {
                                this.formGroup.get('cluster').setValue(this.VcCluster);
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
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": "",
            "datacenter": datacenter,
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;

        this.apiClient.getDatastoresUnderDatacenter(vCenterData, 'vcf', 'tkgm').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.datastores = data.DATASTORES;
                    this.formGroup.get('datastore').enable();
                    this.fetchDatastore = true;
                    this.datastoreErrorMsg = '';
                    if (this.uploadStatus) {
                        if (this.VcDatastore !== '') {
                            if (this.datastores.indexOf(this.VcDatastore) !== -1) {
                                this.formGroup.get('datastore').setValue(this.VcDatastore);
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

    getVsphereData() {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": ""
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;
        this.apiClient.getVsphereData(vCenterData, 'vcf', 'tkgm').subscribe((data: any) => {
              if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.datacenters = data.DATACENTERS;
//                     this.clusters = data.CLUSTERS;
//                     this.datastores = data.DATASTORES;
                    this.resourcePools = data.RESOURCEPOOLS;
                    this.contentLibs = data.CONTENTLIBRARY_NAMES;
                    this.aviOvaImages = data.CONTENTLIBRARY_FILES;
                    this.apiClient.networks = data.NETWORKS;
                    this.getNsxtData();
                    if (this.uploadStatus){
                        if (this.datacenters.indexOf(this.VcDatacenter) === -1) {
                            this.datacenterError = true;
                        } else {
                            this.datacenterError = false;
                            this.formGroup.get('datacenter').setValue(this.VcDatacenter);
                            this.getClustersUnderDatacenter(this.VcDatacenter);
                        }
//                         if (this.clusters.indexOf(this.VcCluster) === -1) {
//                             this.clusterError = true;
//                         } else {
//                             this.clusterError = false;
//                             this.formGroup.get('cluster').setValue(this.VcCluster);
//                         }
//                         if (this.datastores.indexOf(this.VcDatastore) === -1) {
//                             this.datastoreError = true;
//                         } else {
//                             this.datastoreError = false;
//                             this.formGroup.get('datastore').setValue(this.VcDatastore);
//                         }
                        if (!this.isMarketplace) {
                            if (this.contentLibs.indexOf(this.VcContentLib) === -1) {
                                this.contentLibError = true;
                            } else {
                                this.contentLibError = false;
                                this.formGroup.get('contentLib').setValue(this.VcContentLib);
                                this.getOvaImagesUnderContentLib(this.VcContentLib);
                            }
                        }
                        if (this.resourcePools.indexOf(this.VcResourcePool) === -1) {
                            this.resourcePoolError = true;
                        } else {
                            this.resourcePoolError = false;
                            this.formGroup.get('resourcePool').setValue(this.VcResourcePool);
                        }
                    }
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.connected = false;
                    this.errorNotification = 'vCenter: ' + data.msg;
                }
              } else {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources. Please verify vCenter credentials';
              }
            }, (error: any) => {
              if (error.responseType === 'ERROR') {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'vCenter: ' + error.msg;
              } else {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources. Please verify vCenter credentials.';
              }
            });
    }

    getNsxtData() {
        let nsxtData = {
            "nsxtAddress": "",
            "nsxtUsername": "",
            "nsxtPassword": ""
        };

        nsxtData['nsxtAddress'] = this.formGroup.get('nsxtAddress').value;
        nsxtData['nsxtUsername'] = this.formGroup.get('nsxtUsername').value;
        nsxtData['nsxtPassword'] = this.formGroup.get('nsxtPassword').value;

        this.apiClient.getNsxtData(nsxtData).subscribe((data: any) => {
              if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.tier1Routers = data.TIER1_DETAILS;
                    this.nsxtOverlays = data.OVERLAY_LIST;
                    this.fetchResources = true;
                    this.errorNotification = '';
                    this.connected = true;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    if (this.uploadStatus){
                        if (this.tier1Routers.indexOf(this.NsxtTier1Router) === -1) {
                            this.nsxtTier1RouterError = true;
                        } else {
                            this.nsxtTier1RouterError = false;
                            this.formGroup.get('tier1Router').setValue(this.NsxtTier1Router);
                        }
                        if (this.nsxtOverlays.indexOf(this.NsxtOverlay) === -1) {
                            this.nsxtOverlayError = true;
                        } else {
                            this.nsxtOverlayError = false;
                            this.formGroup.get('nsxtOverlay').setValue(this.NsxtOverlay);
                        }
                    }
                    this.enableAllFormFields();
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.connected = false;
                    this.errorNotification = 'NSX-T: ' + data.msg;
                }
              } else {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'NSX-T: Some Error Occurred while Fetching Resources. Please verify NSX-T credentials.';
              }
            }, (error: any) => {
              if (error.responseType === 'ERROR') {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'NSX-T: ' + error.msg;
              } else {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'NSX-T: Some Error Occurred while Fetching Resources. Please verify NSX-T credentials.';
              }
            });
    }

    reloadVsphereData() {
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": ""
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['ssoUser'] = this.formGroup.get('username').value;
        vCenterData['ssoPassword'] = this.formGroup.get('password').value;
        this.dataLoadingState = ClrLoadingState.LOADING;
        this.apiClient.getVsphereData(vCenterData, 'vcf', 'tkgm').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.datacenters = data.DATACENTERS;
//                     this.clusters = data.CLUSTERS;
//                     this.datastores = data.DATASTORES;
                    this.resourcePools = data.RESOURCEPOOLS;
                    this.contentLibs = data.CONTENTLIBRARY_NAMES;
//                     this.aviOvaImages = data.CONTENTLIBRARY_FILES;
                    this.apiClient.networks = data.NETWORKS;
                    this.reloadNsxtData();
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.loadData = false;
                    this.dataLoadingState = ClrLoadingState.DEFAULT;
                    this.connected = false;
                    this.errorNotification = 'vCenter: ' + data.msg;
                }
              } else {
                this.fetchResources = false;
                this.connected = false;
                this.loadData = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources. Please verify vCenter credentials.';
              }
            }, (error: any) => {
              if (error.responseType === 'ERROR') {
                this.fetchResources = false;
                this.loadData = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.connected = false;
                this.errorNotification = 'vCenter: ' + error.msg;
              } else {
                this.fetchResources = false;
                this.loadData = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.connected = false;
                this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources. Please verify vCenter credentials.';
              }
            });
    }

    reloadNsxtData() {
        let nsxtData = {
            "nsxtAddress": "",
            "nsxtUsername": "",
            "nsxtPassword": ""
        };

        nsxtData['nsxtAddress'] = this.formGroup.get('nsxtAddress').value;
        nsxtData['nsxtUsername'] = this.formGroup.get('nsxtUsername').value;
        nsxtData['nsxtPassword'] = this.formGroup.get('nsxtPassword').value;

        this.apiClient.getNsxtData(nsxtData).subscribe((data: any) => {
              if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.tier1Routers = data.TIER1_DETAILS;
                    this.nsxtOverlays = data.OVERLAY_LIST;
                    this.fetchResources = true;
                    this.errorNotification = '';
                    this.connected = true;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    this.loadData = true;
                    this.dataLoadingState = ClrLoadingState.DEFAULT;
                    this.enableAllFormFields();
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.connected = false;
                    this.errorNotification = 'NSX-T: ' + data.msg;
                    this.loadData = false;
                    this.dataLoadingState = ClrLoadingState.DEFAULT;
                }
              } else {
                this.fetchResources = false;
                this.connected = false;
                this.loadData = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'NSX-T: Some Error Occurred while Fetching Resources. Please verify NSX-T credentials.';
              }
            }, (error: any) => {
              if (error.responseType === 'ERROR') {
                this.fetchResources = false;
                this.connected = false;
                this.loadData = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'NSX-T: ' + error.msg;
              } else {
                this.fetchResources = false;
                this.connected = false;
                this.loadData = false;
                this.dataLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'NSX-T: Some Error Occurred while Fetching Resources. Please verify NSX-T credentials.';
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
        const airgappedFields = [
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
            airgappedFields.forEach((field) => {
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
        this.apiClient.verifyMarketplaceToken(refreshToken, 'vcf').subscribe((data: any) => {
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

    getArcasHttpProxyParam() {
        this.dataService.currentArcasHttpProxyUsername.subscribe((httpUsername) => this.arcasHttpUsername = httpUsername);
        if (this.arcasHttpUsername !== '') {
            this.dataService.currentArcasHttpProxyUrl.subscribe((httpUrl) => this.arcasHttpUrl = httpUrl);
            this.dataService.currentArcasHttpProxyPassword.subscribe((httpPassword) => this.arcasHttpPassword = httpPassword);
            let httpProxyVal = 'http://' + this.arcasHttpUsername + ':' + this.arcasHttpPassword + '@' + this.arcasHttpUrl.substring(7);
            return httpProxyVal;
        } else {
            this.dataService.currentArcasHttpProxyUrl.subscribe((httpUrl) => this.arcasHttpUrl = httpUrl);
            return this.arcasHttpUrl;
        }
    }

    getArcasHttpsProxyParam() {
        this.dataService.currentArcasHttpsProxyUsername.subscribe((httpsUsername) => this.arcasHttpsUsername = httpsUsername);
        if (this.arcasHttpsUsername !== '') {
            this.dataService.currentArcasHttpsProxyUrl.subscribe((httpsUrl) => this.arcasHttpsUrl = httpsUrl);
            this.dataService.currentArcasHttpsProxyPassword.subscribe((httpsPassword) => this.arcasHttpsPassword = httpsPassword);
            let httpsProxyVal = 'https://' + this.arcasHttpsUsername + ':' + this.arcasHttpsPassword + '@' + this.arcasHttpsUrl.substring(8);
            return httpsProxyVal;
        } else {
            this.dataService.currentArcasHttpsProxyUrl.subscribe((httpsUrl) => this.arcasHttpsUrl = httpsUrl);
            return this.arcasHttpsUrl;
        }
    }

    public getArcasHttpsProxy() {
        let httpsProxyVal = '';
        this.dataService.currentArcasIsSameAsHttp.subscribe((sameAsHttp) => this.arcasSameAsHttp = sameAsHttp);
        if (this.arcasSameAsHttp) {
            httpsProxyVal = this.getArcasHttpProxyParam();
        } else {
            httpsProxyVal = this.getArcasHttpsProxyParam();
        }
        return httpsProxyVal;
    }

    connectMarketplace() {
        this.validateLoadingState = ClrLoadingState.LOADING;
        let arcasEnableProxy;
        this.dataService.currentArcasEnableProxy.subscribe((enableProxy) => arcasEnableProxy = enableProxy);
        this.dataService.currentArcasNoProxy.subscribe((noProxy) => this.arcasNoProxy = noProxy);
        if (!(this.apiClient.proxyConfiguredVCF) && arcasEnableProxy) {
            let httpProxy = this.getArcasHttpProxyParam();
            let httpsProxy = this.getArcasHttpsProxy();
            let noProxy = this.arcasNoProxy;
            this.apiClient.enableArcasProxy(httpProxy, httpsProxy, noProxy, 'vcf').subscribe((data: any) => {
                if (data && data !== null) {
                    if (data.responseType === 'SUCCESS') {
                        this.apiClient.proxyConfiguredVCF = true;
                        this.verifyMarketplaceRefreshToken();
                    } else if (data.responseType === 'ERROR') {
                        this.validateToken = false;
                        this.validateLoadingState = ClrLoadingState.DEFAULT;
                        if (data.hasOwnProperty('msg')) {
                            this.errorNotification = data.msg;
                        } else {
                            this.errorNotification = 'Validation of TMC API Token has failed. Failed to configure Proxy on Arcas VM.';
                        }
                    }
                } else {
                    this.validateToken = false;
                    this.validateLoadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = 'Validation of TMC API Token has failed. Failed to configure Proxy on Arcas VM.';
                }
            }, (err: any) => {
                this.validateToken = false;
                this.validateLoadingState = ClrLoadingState.DEFAULT;
                const error = err.error.msg || err.msg || JSON.stringify(err);
                this.errorNotification = 'Failed to connect to the TMC Account. Failed to configure Proxy on Arcas VM. ' + error;
            });
        } else {
            this.verifyMarketplaceRefreshToken();
            // this.dumyVerifyTMCToken();
        }
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

    startSession() {
        let data = {
            'vcenterAddress' : this.formGroup.get('vcenterAddress').value,
            'username': this.formGroup.get('username').value,
            'password': this.formGroup.get('password').value,
            'datacenter': this.formGroup.get('datacenter').value,
            'cluster': this.formGroup.get('cluster').value,
            'datastore': this.formGroup.get('datastore').value,
            'resourcePoolName': this.formGroup.get('resourcePool').value,
            'refreshToken': this.formGroup.get('marketplaceRefreshToken').value,
            'contentLibraryName': this.formGroup.get('contentLib').value,
            'aviOvaName': this.formGroup.get('aviOvaImage').value,
        };
        this.apiClient.getVMCSession(data, 'vcf').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                } else if (data.responseType === 'ERROR') {
                    this.errorNotification = data.msg;
                }
            } else {
                this.errorNotification = 'Failed to establish a session to the vSphere environment';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.errorNotification = error.msg;
            } else {
                this.errorNotification = 'Failed to establish a session to the vSphere environment';
            }
        });
    }
}
