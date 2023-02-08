/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
/**
 * Angular Modules
 */
import { Component, OnInit, Input, ViewChild } from '@angular/core';
import { Validators, FormControl } from '@angular/forms';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';

/**
 * App imports
 */
import { VCDDataService } from 'src/app/shared/service/vcd-data.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
import { Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { ClrLoadingState } from '@clr/angular';
import { FormMetaDataStore } from '../../wizard/shared/FormMetaDataStore';
import { SSLThumbprintModalComponent } from '../../wizard/shared/components/modals/ssl-thumbprint-modal/ssl-thumbprint-modal.component';
import { aviSize, NodeType } from '../../wizard/shared/constants/wizard.constants';
import { Netmask } from 'netmask';

const SupervisedField = ['vcenterAddress', 'vcenterSsoUser', 'vcenterSsoPasswordBase64'];
const MarketplaceField = ['marketplaceRefreshToken'];

const AviGreenfieldNoHa = ['aviController01Ip', 'aviController01Fqdn'];
const AviBrownfield = ['aviClusterIp', 'aviClusterFqdn'];
const AviGreenfieldHa = ['aviController01Ip', 'aviController01Fqdn', 'aviController02Ip', 'aviController02Fqdn', 'aviController03Ip', 'aviController03Fqdn', 'aviClusterIp', 'aviClusterFqdn'];

@Component({
    selector: 'app-avi-controller-step',
    templateUrl: './avi-controller.component.html',
    styleUrls: ['./avi-controller.component.scss'],
})
export class AviControllerComponent extends StepFormDirective implements OnInit {
    @Input() InputAviVcdDisplayName;
    @Input() providerType: string;
    @ViewChild(SSLThumbprintModalComponent) sslThumbprintModal: SSLThumbprintModalComponent;
    // =========================== COMMON PROPERTIES ========================================
    private uploadStatus;
    subscription: Subscription;
    // =========================== AVI PROPERTIES ========================================
    private deployAvi;
    // =========================== GREENFIELD MARKETPLACE ========================================
    isMarketplace: any;
    marketplaceRefreshToken: any;
    // =========================== GREENFIELD VSPHERE PROPERTIES ========================================
    reloadLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    connectLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    nameResolutionLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    validateLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;

    resourcePools: any = [];
    contentLibs: any = [];
    datacenters: any = [];
    datastores: any = [];
    clusters: any = [];
    aviOvaImages: any = [];

    resourcePoolError: boolean = false;
    contentLibError: boolean = false;
    datacenterError: boolean = false;
    datastoreError: boolean = false;
    clusterError: boolean = false;
    ovaImageError: boolean = false;
    aviMgmtNetworkNameError: boolean = false;

    datastoreErrorMsg: string = 'Provided Datastore is not found, please select again.';
    clusterErrorMsg: string = 'Provided Cluster is not found, please select again.';

    resourcePoolName: any;
    contentLibraryName: string;
    vcenterDatacenter: string;
    vcenterDatastore: any;
    vcenterCluster: any;
    aviOvaName: any;
    vcenterSsoPasswordBase64: any;
    vcenterSsoUser: any;
    vcenterAddress: any;
    thumbprint: any;

    fetchDatastore: boolean = false;    
    fetchCluster: boolean = false;
    fetchOvaImage: boolean = false;
    validateToken: boolean = false;
    fetchResources: boolean = false;
    connected: boolean = false;
    loadData: boolean = false;

    aviOvaErrorNotification: string;
    nodeTypes: Array<NodeType> = [];
    // =========================== GREENFIELD AVI Management Network PROPERTIES ========================================
    private aviMgmtNetworkName;
    private aviMgmtNetworkGatewayCidr;
    // ================================== GREENFIELD AVI COMPONENTS ============================================
    nameResolution: boolean = false;
    private aviUsername;
    private aviPasswordBase64;
    private aviBackupPassphraseBase64;
    private enableAviHa;
    private aviController01Ip;
    private aviController01Fqdn;
    private aviController02Ip;
    private aviController02Fqdn;
    private aviController03Ip;
    private aviController03Fqdn;
    private aviClusterIp;
    private aviClusterFqdn;
    private aviSizeForm: string;
    private aviCertPath;
    private aviCertKeyPath;
    // =========================================== AVI VCD DISPLAY NAME =============================================
    private fetchAviVcdDisplayNames: boolean = false;
    private aviVcdDisplayName;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                private apiClient: APIClient,
                public dataService: VCDDataService) {

        super();
        this.nodeTypes = [...aviSize];
    }

    ngOnInit() {
        super.ngOnInit();

        this.formGroup.addControl('deployAvi', new FormControl(false));
        // ============================== GREENFIELD ==========================================

        // MARKETPLACE
        this.formGroup.addControl('isMarketplace', new FormControl(false));
        this.formGroup.addControl('marketplaceRefreshToken', new FormControl('', []));

        // VSPHERE
        this.formGroup.addControl('vcenterAddress', new FormControl('', [Validators.required, this.validationService.isValidIpOrFqdn(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('vcenterSsoUser', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('vcenterSsoPasswordBase64', new FormControl('', [Validators.required]));

        this.formGroup.addControl('vcenterDatacenter', new FormControl('', [Validators.required]));
        this.formGroup.addControl('vcenterCluster', new FormControl('', [Validators.required]));
        this.formGroup.addControl('vcenterDatastore', new FormControl('', [Validators.required]));
        this.formGroup.addControl('resourcePoolName', new FormControl('', []));
        this.formGroup.addControl('contentLibraryName', new FormControl('', [Validators.required]));  // Optional if marketplace is enabled
        this.formGroup.addControl('aviOvaName', new FormControl('', [Validators.required]));  // Optional if marketplace is enabled
        this.formGroup.addControl('thumbprint', new FormControl('', [])); // Fetched from Backend, no use on UI

        //AVI MANAGEMENT NETWORK
        this.formGroup.addControl('aviMgmtNetworkName', new FormControl('', [Validators.required]));
        this.formGroup.addControl('aviMgmtNetworkGatewayCidr', new FormControl('', [Validators.required, this.validationService.isValidIpNetworkSegment(), this.validationService.noWhitespaceOnEnds()]));

        // AVI COMPPONENT SPECIFICATIONS
        this.formGroup.addControl('aviUsername', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviPasswordBase64', new FormControl('', [Validators.required, Validators.minLength(8), this.validationService.isValidAviPassword()]));
        this.formGroup.addControl('aviBackupPassphraseBase64', new FormControl('', [Validators.required, Validators.minLength(8), this.validationService.isValidAviPassword()]));
        this.formGroup.addControl('enableAviHa', new FormControl(false, []));
        this.formGroup.addControl('aviController01Ip', new FormControl('', [Validators.required, this.validationService.isValidIp(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviController01Fqdn', new FormControl('', [Validators.required, this.validationService.isValidFqdn(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviController02Ip', new FormControl('', [this.validationService.isValidIp(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviController02Fqdn', new FormControl('', [this.validationService.isValidFqdn(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviController03Ip', new FormControl('', [this.validationService.isValidIp(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviController03Fqdn', new FormControl('', [this.validationService.isValidFqdn(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviClusterIp', new FormControl('', [this.validationService.isValidIp(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviClusterFqdn', new FormControl('', [this.validationService.isValidFqdn(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviSize', new FormControl('', [Validators.required]));
        this.formGroup.addControl('aviCertPath', new FormControl('', [this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviCertKeyPath', new FormControl('', [this.validationService.noWhitespaceOnEnds()]));

        //AVI VCD DISPLAY NAME
        this.formGroup.addControl('aviVcdDisplayName', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviVcdDisplayNameInput', new FormControl('', []));

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
        /** If vSphere FQDN, username or password changes, following will be reset
         * Datacenter
         * Cluster
         * Datastore
         * Content Library
         * AVI OVA image
         */
         SupervisedField.forEach(field => {
            // tslint:disable-next-line:max-line-length
            this.formGroup.get(field).valueChanges.pipe(
                debounceTime(500),
                distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                takeUntil(this.unsubscribe))
                .subscribe(() => {
                    this.connected = false;
                    this.connectLoadingState = ClrLoadingState.DEFAULT;
                    this.formGroup.get('vcenterDatacenter').setValue('');
                    this.datacenters = [];
                    this.formGroup.get('vcenterDatacenter').disable();

                    this.formGroup.get('vcenterCluster').setValue('');
                    this.clusters = [];
                    this.formGroup.get('vcenterCluster').disable();

                    this.formGroup.get('vcenterDatastore').setValue('');
                    this.datastores = [];
                    this.formGroup.get('vcenterDatastore').disable();

                    this.formGroup.get('contentLibraryName').setValue('');
                    this.contentLibs = [];
                    this.formGroup.get('contentLibraryName').disable();

                    this.formGroup.get('aviOvaName').setValue('');
                    this.aviOvaImages = [];
                    this.formGroup.get('aviOvaName').disable();

                    this.formGroup.get('resourcePoolName').setValue('');
                    this.resourcePools = [];
                    this.formGroup.get('resourcePoolName').disable();

                    this.formGroup.get('aviMgmtNetworkName').setValue('');
                    this.apiClient.networks = [];
                    this.formGroup.get('aviMgmtNetworkName').disable();
                });
        });

        // let aviField = [];
        // if(this.formGroup.get('deployAvi').value) {
        //     if(this.formGroup.get('enableAviHa').value) {
        //         aviField = AviGreenfieldHa;
        //     } else aviField = AviGreenfieldNoHa
        // } else {
        //     aviField = AviBrownfield;
        // }
        // console.log(aviField);
        AviGreenfieldHa.forEach(field => {
            // tslint:disable-next-line:max-line-length
            this.formGroup.get(field).valueChanges.pipe(
                debounceTime(500),
                distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                takeUntil(this.unsubscribe))
                .subscribe(() => {
                    this.nameResolution = false;
                    this.nameResolutionLoadingState = ClrLoadingState.DEFAULT;
                    // console.log(this.nameResolution);
                });
        });


        this.formGroup['canMoveToNext'] = () => {
            // return true;
            this.toggleDeployAvi();
            let result: boolean = this.formGroup.valid;

            if(this.formGroup.get('deployAvi').value) {
                if(this.formGroup.get('isMarketplace').value) {
                    result = result && this.validateToken;
                } else {
                    result = result && this.fetchOvaImage;
                }

                if(this.formGroup.get('enableAviHa').value) {
                    result = result && !this.apiClient.aviController01Error && !this.apiClient.aviController02Error && !this.apiClient.aviController03Error && !this.apiClient.clusterIpError;
                } else {
                    result = result && !this.apiClient.aviController01Error;
                }

                result = result && this.fetchResources && this.fetchCluster && this.fetchDatastore;
            }
            result = result && this.nameResolution;
            return result;
        };


        this.formGroup.get('vcenterDatacenter').valueChanges.subscribe(() => this.datacenterError = false);
        this.formGroup.get('vcenterCluster').valueChanges.subscribe(() => this.clusterError = false);
        this.formGroup.get('vcenterDatastore').valueChanges.subscribe(() => this.datastoreError = false);
        this.formGroup.get('contentLibraryName').valueChanges.subscribe(() => this.contentLibError = false);
        this.formGroup.get('aviOvaName').valueChanges.subscribe(() => this.ovaImageError = false);
        this.formGroup.get('resourcePoolName').valueChanges.subscribe(() => this.resourcePoolError = false);
        this.formGroup.get('aviMgmtNetworkName').valueChanges.subscribe(() => this.aviMgmtNetworkNameError = false);

        // this.formGroup.get('aviController01Ip').valueChanges.subscribe(() => this.datacenterError = false);
        // this.formGroup.get('aviController02Ip').valueChanges.subscribe(() => this.clusterError = false);
        // this.formGroup.get('aviController03Ip').valueChanges.subscribe(() => this.datastoreError = false);
        // this.formGroup.get('aviController03Fqdn').valueChanges.subscribe(() => this.contentLibError = false);
        // this.formGroup.get('aviController02Fqdn').valueChanges.subscribe(() => this.ovaImageError = false);
        // this.formGroup.get('aviController01Fqdn').valueChanges.subscribe(() => this.resourcePoolError = false);
        // this.formGroup.get('aviMgmtNetworkName').valueChanges.subscribe(() => this.aviMgmtNetworkNameError = false);

        setTimeout(_ => {
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentDeployAvi.subscribe(
                    (deploy) => this.deployAvi = deploy);
                this.formGroup.get('deployAvi').setValue(this.deployAvi);
                this.toggleDeployAvi();
                // ===================================== GREENFIELD ============================================
                if(this.deployAvi) {
                    // MARKETPLACE
                    this.subscription = this.dataService.currentMarketplace.subscribe(
                        (marketplace) => this.isMarketplace = marketplace);
                    this.formGroup.get('isMarketplace').setValue(this.isMarketplace);
                    if (this.isMarketplace) {
                        this.subscription = this.dataService.currentMarketplaceRefreshToken.subscribe(
                            (marketplaceToken) => this.marketplaceRefreshToken = marketplaceToken);
                        this.formGroup.get('marketplaceRefreshToken').setValue(this.marketplaceRefreshToken);
                    }
                    this.toggleMarketPlace();

                    // ===================================== VSPHERE =====================================
                    this.subscription = this.dataService.currentVcAddress.subscribe(
                        (VcFqdn) => this.vcenterAddress = VcFqdn);
                    this.formGroup.get('vcenterAddress').setValue(this.vcenterAddress);

                    this.subscription = this.dataService.currentVcUser.subscribe(
                        (VcUser) => this.vcenterSsoUser = VcUser);
                    this.formGroup.get('vcenterSsoUser').setValue(this.vcenterSsoUser);

                    this.subscription = this.dataService.currentVcPass.subscribe(
                        (VcPass) => this.vcenterSsoPasswordBase64 = VcPass);
                    this.formGroup.get('vcenterSsoPasswordBase64').setValue(this.vcenterSsoPasswordBase64);
                    /**
                     * Updating all the local properties with values fetched from the uploaded JSON file
                     * The form fields will get updated on verifying if it is a correct values after connecting to vcenter
                     */
                    this.subscription = this.dataService.currentDatacenter.subscribe(
                        (datacenter) => this.vcenterDatacenter = datacenter);
                    this.subscription = this.dataService.currentCluster.subscribe(
                        (cluster) => this.vcenterCluster = cluster);
                    this.subscription = this.dataService.currentDatastore.subscribe(
                        (datastore) => this.vcenterDatastore = datastore);
                    this.subscription = this.dataService.currentResourcePool.subscribe(
                        (resourcePool) => this.resourcePoolName = resourcePool);
                    this.subscription = this.dataService.currentContentLib.subscribe(
                        (contentLib) => this.contentLibraryName = contentLib);
                    this.subscription = this.dataService.currentOvaImage.subscribe(
                        (ovaImage) => this.aviOvaName = ovaImage);

                    // ===================================== AVI Management Network =====================================
                    this.subscription = this.dataService.currentAviMgmtNetworkName.subscribe(
                        (networkName) => this.aviMgmtNetworkName = networkName);
                    // The network name will be updated when the User click on connect for vSphere
                    this.subscription = this.dataService.currentAviMgmtNetworkGatewayCidr.subscribe(
                        (cidr) => this.aviMgmtNetworkGatewayCidr = cidr);
                    this.formGroup.get('aviMgmtNetworkGatewayCidr').setValue(this.aviMgmtNetworkGatewayCidr);
                    
                    // ==================================== AVI Component Spec =============================================
                    this.subscription = this.dataService.currentAviUsername.subscribe(
                        (username) => this.aviUsername = username);
                    this.formGroup.get('aviUsername').setValue(this.aviUsername);
                    this.subscription = this.dataService.currentAviPasswordBase64.subscribe(
                        (pass) => this.aviPasswordBase64 = pass);
                    this.formGroup.get('aviPasswordBase64').setValue(this.aviPasswordBase64);
                    this.subscription = this.dataService.currentAviBackupPassphraseBase64.subscribe(
                        (backup) => this.aviBackupPassphraseBase64 = backup);
                    this.formGroup.get('aviBackupPassphraseBase64').setValue(this.aviBackupPassphraseBase64);
                    this.subscription = this.dataService.currentEnableAviHa.subscribe(
                        (enable) => this.enableAviHa = enable);
                    this.formGroup.get('enableAviHa').setValue(this.enableAviHa);
                    if(this.enableAviHa) {
                        this.subscription = this.dataService.currentAviController02Ip.subscribe(
                            (ip2) => this.aviController02Ip = ip2);
                        this.formGroup.get('aviController02Ip').setValue(this.aviController02Ip);
                        this.subscription = this.dataService.currentAviController02Fqdn.subscribe(
                            (fqdn2) => this.aviController02Fqdn = fqdn2);
                        this.formGroup.get('aviController02Fqdn').setValue(this.aviController02Fqdn);
                        this.subscription = this.dataService.currentAviController03Ip.subscribe(
                            (ip3) => this.aviController03Ip = ip3);
                        this.formGroup.get('aviController03Ip').setValue(this.aviController03Ip);
                        this.subscription = this.dataService.currentAviController03Fqdn.subscribe(
                            (fqdn3) => this.aviController03Fqdn = fqdn3);
                        this.formGroup.get('aviController03qdn').setValue(this.aviController03Fqdn);
                        this.subscription = this.dataService.currentAviClusterIp.subscribe(
                            (clusterip) => this.aviClusterIp = clusterip);
                        this.formGroup.get('aviClusterIp').setValue(this.aviClusterIp);
                        this.subscription = this.dataService.currentAviClusterFqdn.subscribe(
                            (clusterfqdn) => this.aviClusterFqdn = clusterfqdn);
                        this.formGroup.get('aviClusterFqdn').setValue(this.aviClusterFqdn);
                    }
                    this.subscription = this.dataService.currentAviController01Ip.subscribe(
                        (ip1) => this.aviController01Ip = ip1);
                    this.formGroup.get('aviController01Ip').setValue(this.aviController01Ip);
                    this.subscription = this.dataService.currentAviController01Fqdn.subscribe(
                        (fqdn1) => this.aviController01Fqdn = fqdn1);
                    this.formGroup.get('aviController01Fqdn').setValue(this.aviController01Fqdn);

                    this.subscription = this.dataService.currentAviSize.subscribe(
                        (size) => this.aviSizeForm = size);
                    this.formGroup.get('aviSize').setValue(this.aviSizeForm);

                    this.subscription = this.dataService.currentAviCertPath.subscribe(
                        (certpath) => this.aviCertPath = certpath);
                    this.formGroup.get('aviCertPath').setValue(this.aviCertPath);
                    this.subscription = this.dataService.currentAviCertKeyPath.subscribe(
                        (certkeypath) => this.aviCertKeyPath = certkeypath);
                    this.formGroup.get('aviCertKeyPath').setValue(this.aviCertKeyPath);
                    
                    this.subscription = this.dataService.currentAviVcdDisplayName.subscribe(
                        (displayname) => this.aviVcdDisplayName = displayname);
                    this.formGroup.get('aviVcdDisplayName').setValue(this.aviVcdDisplayName);

                } else {
                    this.subscription = this.dataService.currentAviClusterIp.subscribe(
                        (clusterip) => this.aviClusterIp = clusterip);
                    this.formGroup.get('aviClusterIp').setValue(this.aviClusterIp);
                    this.subscription = this.dataService.currentAviClusterFqdn.subscribe(
                        (clusterfqdn) => this.aviClusterFqdn = clusterfqdn);
                    this.formGroup.get('aviClusterFqdn').setValue(this.aviClusterFqdn);

                    this.subscription = this.dataService.currentAviUsername.subscribe(
                        (username) => this.aviUsername = username);
                    this.formGroup.get('aviUsername').setValue(this.aviUsername);
                    this.subscription = this.dataService.currentAviPasswordBase64.subscribe(
                        (pass) => this.aviPasswordBase64 = pass);
                    this.formGroup.get('aviPasswordBase64').setValue(this.aviPasswordBase64);

                    this.subscription = this.dataService.currentAviVcdDisplayName.subscribe(
                        (displayname) => this.aviVcdDisplayName = displayname);
                    if(this.aviVcdDisplayName in this.dataService.aviVcdDisplayNames){
                        this.formGroup.get('aviVcdDisplayName').setValue(this.aviVcdDisplayName);
                    } else {
                        this.formGroup.get('aviVcdDisplayName').setValue('IMPORT TO VCD');
                        this.formGroup.get('aviVcdDisplayNameInput').setValue(this.aviVcdDisplayName);
                    }
                }
            }
            this.toggleMarketPlace();
        });
    }

    ngOnChanges() {
        if(this.dataService.aviVcdDisplayNames.length !== 0 && this.dataService.aviVcdDisplayNames.indexOf(this.aviVcdDisplayName) !== -1) {
            if(this.formGroup.get('aviVcdDisplayName')) this.formGroup.get('aviVcdDisplayName').setValue(this.aviVcdDisplayName);
        } else {
            if(this.formGroup.get('aviVcdDisplayName')) this.formGroup.get('aviVcdDisplayName').setValue('IMPORT TO VCD');
            if(this.formGroup.get('aviVcdDisplayNameInput')) this.formGroup.get('aviVcdDisplayNameInput').setValue(this.aviVcdDisplayName);
        }
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        this.formGroup.get('vcenterSsoPasswordBase64').setValue('');
        if (!this.uploadStatus) {
            this.formGroup.get('vcenterSsoPasswordBase64').setValue('');
        }
        if(this.formGroup.get('enableAviHa').value) {
            this.formGroup.get('aviPasswordBase64').setValue('');
            this.formGroup.get('aviBackupPassphraseBase64').setValue('');
        }
    }

    // ======================================================= AVI CONTROLLER FILED ====================================================================
    toggleDeployAvi() {
        const greenfieldFields = [
            'vcenterAddress',
            'vcenterSsoUser',
            'vcenterSsoPasswordBase64',
            'vcenterDatacenter',
            'vcenterCluster',
            'vcenterDatastore',
            'contentLibraryName',
            'aviOvaName',
            'resourcePoolName',
            'aviMgmtNetworkName',
            'aviMgmtNetworkGatewayCidr',


            'aviBackupPassphraseBase64',
            'enableAviHa',
            'aviController01Ip',
            'aviController01Fqdn',
            'aviController02Ip',
            'aviController02Fqdn',
            'aviController03Ip',
            'aviController03Fqdn',

            'aviSize',
            'aviCertPath',
            'aviCertKeyPath',

        ];
        if (this.formGroup.get('deployAvi').value) {

            this.dataService.aviGreenfield = true;
            this.dataService.configureAviNsxtCloud = true;
            this.dataService.createSeGroup = true;

            this.resurrectField('vcenterAddress', [
                Validators.required, this.validationService.isValidIpOrFqdn(),
                this.validationService.noWhitespaceOnEnds(),
            ], this.formGroup.value['vcenterAddress']);
            this.resurrectField('vcenterSsoUser', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
            ], this.formGroup.value['vcenterSsoUser']);
            this.resurrectField('vcenterSsoPasswordBase64', [
                Validators.required,
            ], this.formGroup.value['vcenterSsoPasswordBase64']);
            this.resurrectField('vcenterDatacenter', [
                Validators.required,
            ], this.formGroup.value['vcenterDatacenter']);
            this.resurrectField('vcenterCluster', [
                Validators.required,
            ], this.formGroup.value['vcenterCluster']);
            this.resurrectField('vcenterDatastore', [
                Validators.required,
            ], this.formGroup.value['vcenterDatastore']);
            this.resurrectField('resourcePoolName', [], this.formGroup.value['resourcePoolName']);
            this.resurrectField('aviMgmtNetworkName', [
                Validators.required,
            ], this.formGroup.value['aviMgmtNetworkName']);
            this.resurrectField('aviMgmtNetworkGatewayCidr', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidIpNetworkSegment(),
            ], this.formGroup.value['aviMgmtNetworkGatewayCidr']);
            this.resurrectField('aviBackupPassphraseBase64', [
                Validators.required,
            ], this.formGroup.value['aviBackupPassphraseBase64']);
            this.resurrectField('aviController01Fqdn', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidFqdn(),
            ], this.formGroup.value['aviController01Fqdn']);
            this.resurrectField('aviController01Ip', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidIp(),
            ], this.formGroup.value['aviController01Ip']);
            this.resurrectField('aviSize', [
                Validators.required,
            ], this.formGroup.value['aviSize']);
        } else {
            this.dataService.aviGreenfield = false;

            greenfieldFields.forEach((field) => {
                this.disarmField(field, true);
            });

            this.resurrectField('aviClusterIp', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidIp(),
            ], this.formGroup.value['aviClusterIp']);
            this.resurrectField('aviClusterFqdn', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidFqdn(),
            ], this.formGroup.value['aviClusterFqdn']);
        }
    }
    // ====================================================== MARKETPLACE =============================================================================
    dumyTokenValidation() {
        let refreshToken = this.formGroup.controls['marketplaceRefreshToken'].value;
        this.validateToken = true;
        this.validateLoadingState = ClrLoadingState.DEFAULT;
    }

    verifyMarketplaceRefreshToken() {
        this.validateLoadingState = ClrLoadingState.LOADING;
        let refreshToken = this.formGroup.controls['marketplaceRefreshToken'].value;
        this.apiClient.verifyMarketplaceToken(refreshToken, 'vcd').subscribe((data: any) => {
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
                this.errorNotification = 'Marketplace validation: ' + err.msg;
            } else {
                this.validateToken = false;
                this.validateLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Validation of Marketplace Refresh Token has failed. Please ensure the env has connectivity to external networks.';
            }
        });
    }

    toggleMarketPlace() {
        const marketplaceFields = [
            'marketplaceRefreshToken',
        ];
        const contentLibFields = [
            'contentLibraryName',
            'aviOvaName',
        ];
        if (!this.formGroup.value['isMarketplace']) {
            this.resurrectField('contentLibraryName', [
                Validators.required
            ], this.formGroup.value['contentLibraryName']);
            this.resurrectField('aviOvaName', [
                Validators.required
            ], this.formGroup.value['aviOvaName']);
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

    //  ======================================================== GREENFIELD ===============================================================
    //  ======================================================== GREENFIELD: VSPHERE =====================================================
    /**
     * @method connectVC
     * helper method to make connection to VC environment, call retrieveDatacenters
     * method if VC connection successful
     */
     connectVC() {
        //####### REMOVE_ME ##########
        // this.thumbprint = "XYXYXYXYXYXYX";
        // FormMetaDataStore.deleteMetaDataEntry('aviControllerForm', 'thumbprint');
        // this.formGroup.controls['thumbprint'].setValue(this.thumbprint);
        // FormMetaDataStore.saveMetaDataEntry(this.formName, 'thumbprint', {
        //     label: 'SSL THUMBPRINT',
        //     displayValue: this.thumbprint,
        // });
        // this.sslThumbprintModal.open();
        // this.dumyFormFields();
        // this.errorNotification = '';
        // this.enableAllFormFields();
        // this.connected = true;
        // return;
        //####### REMOVE_ME ##########
        this.connectLoadingState = ClrLoadingState.LOADING;
        this.vcenterAddress = this.formGroup.controls['vcenterAddress'].value;
        this.getSSLThumbprint(this.vcenterAddress);
    }

    getSSLThumbprint(vcenterAddress) {
        let payload = {
            'envSpec': {
                'vcenterDetails': {
                    'vcenterAddress': vcenterAddress
                }
            }
        };
        this.apiClient.getSSLThumbprint('vcd', payload).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.thumbprint = data.SHA1;
                    this.getVsphereData();
                    this.formGroup.controls['thumbprint'].setValue(this.thumbprint);
                    FormMetaDataStore.saveMetaDataEntry(this.formName, 'thumbprint', {
                        label: 'SSL THUMBPRINT',
                        displayValue: this.thumbprint,
                    });
                    this.sslThumbprintModal.open();
                } else if (data.responseType === 'ERROR') {
                    this.connected = false;
                    this.connectLoadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = data.msg;
                }
            } else {
                this.connected = false;
                this.connectLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Some Error Occurred while Retrieving SSL Thumbprint';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.connected = false;
                this.connectLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: ' + err.msg;
            } else {
                this.connected = false;
                this.connectLoadingState = ClrLoadingState.DEFAULT;
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
        this.connectLoadingState = ClrLoadingState.LOADING;
        this.connected = true;
        this.errorNotification = null;
        this.connectLoadingState = ClrLoadingState.DEFAULT;
    }

    /**
     * @method getDisabled
     * helper method to get if connect btn should be disabled
     */
    getDisabled(): boolean {
        return !(this.formGroup.get('vcenterAddress').valid && this.formGroup.get('vcenterSsoUser').valid && this.formGroup.get('vcenterSsoPasswordBase64').valid);
    }

    disableFormFields() {
        this.formGroup.get('vcenterDatacenter').disable();
        this.formGroup.get('vcenterCluster').disable();
        this.formGroup.get('vcenterDatastore').disable();
        this.formGroup.get('resourcePoolName').disable();
        this.formGroup.get('contentLibraryName').disable();
        this.formGroup.get('aviOvaName').disable();
    }

    enableAllFormFields() {
        this.formGroup.get('vcenterDatacenter').enable();
        this.formGroup.get('vcenterCluster').enable();
        this.formGroup.get('vcenterDatacenter').enable();
        this.formGroup.get('resourcePoolName').enable();
        this.formGroup.get('contentLibraryName').enable();
        this.formGroup.get('aviMgmtNetworkName').enable();
    }

    dumyFormFields() {
        this.datacenters = ['Datacenter-1', 'Datacenter-2'];
        this.clusters = ['Cluster-1', 'Cluster-2'];
        this.datastores = ['Datastore-1', 'Datastore-2'];
        this.resourcePools = ['Resource-pool-1', 'Resource-pool-2'];
        this.contentLibs = ['Content-lib-1', 'Content-lib-2'];
        this.aviOvaImages = ['Ova-image-1', 'Ova-image-2'];
        this.apiClient.networks = ['Network-1', 'Network-2', 'Network-3', 'Network-4'];
        this.apiClient.dataProtectionCredentials = ['cred-1', 'cred-2'];
        this.apiClient.dataProtectionTargetLocations = ['loc-1', 'loc-2'];
        this.apiClient.clusterGroups = ['cg-1', 'cg-2'];
        this.fetchResources = true;
        this.fetchOvaImage = true;
    }

    getOvaImagesUnderContentLib(contentLibName: string) {
        //####### REMOVE_ME ##########
        // this.formGroup.get('aviOvaName').enable();
        // this.fetchOvaImage = true;
        // if (this.uploadStatus) {
        //     if (this.aviOvaName !== '') {
        //         if (this.aviOvaImages.indexOf(this.aviOvaName) === -1) {
        //             this.ovaImageError = true;
        //         } else {
        //             this.ovaImageError = false;
        //             this.formGroup.get('aviOvaName').setValue(this.aviOvaName);
        //         }
        //     }
        // }
        // return;
        //####### REMOVE_ME ##########
        let vCenterData = {
            "vcenterAddress": "",
            "vcenterSsoUser": "",
            "vcenterSsoPasswordBase64": "",
            'contentLibraryName': contentLibName,
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['vcenterSsoUser'] = this.formGroup.get('vcenterSsoUser').value;
        vCenterData['vcenterSsoPasswordBase64'] = this.formGroup.get('vcenterSsoPasswordBase64').value;

        this.apiClient.getOvaImagesUnderContentLibraryVsphere1('vcd', vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.aviOvaImages = data.CONTENT_LIBRARY_FILES;
                    this.formGroup.get('aviOvaName').enable();
                    this.fetchOvaImage = true;
                    this.aviOvaErrorNotification = null;
                    if (this.uploadStatus) {
                        if (this.aviOvaName !== '') {
                            if (this.aviOvaImages.indexOf(this.aviOvaName) === -1) {
                                this.ovaImageError = true;
                            } else {
                                this.ovaImageError = false;
                                this.formGroup.get('aviOvaName').setValue(this.aviOvaName);
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
        //####### REMOVE_ME ##########
        // this.formGroup.get('vcenterCluster').enable();
        // this.fetchCluster = true;
        // if (this.uploadStatus) {
        //     if (this.vcenterCluster !== '') {
        //         if (this.clusters.indexOf(this.vcenterCluster) !== -1) {
        //             this.formGroup.get('vcenterCluster').setValue(this.vcenterCluster);
        //         }
        //     }
        // }
        // this.getDatastoresUnderDatacenter(datacenter);
        // return;
        //####### REMOVE_ME ##########
        let vCenterData = {
            "vcenterAddress": "",
            "vcenterSsoUser": "",
            "vcenterSsoPasswordBase64": "",
            "vcenterDatacenter": datacenter,
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['vcenterSsoUser'] = this.formGroup.get('vcenterSsoUser').value;
        vCenterData['vcenterSsoPasswordBase64'] = this.formGroup.get('vcenterSsoPasswordBase64').value;

        this.apiClient.getClustersUnderDatacenterVsphere1('vcd', vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.clusters = data.CLUSTERS;
                    this.fetchCluster = true;
                    this.clusterErrorMsg = '';
                    if (this.uploadStatus) {
                        if (this.vcenterCluster !== '') {
                            if (this.clusters.indexOf(this.vcenterCluster) !== -1) {
                                this.formGroup.get('vcenterCluster').setValue(this.vcenterCluster);
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
        //####### REMOVE_ME ##########
        // this.formGroup.get('vcenterDatastore').enable();
        // this.fetchDatastore = true;
        // if (this.uploadStatus) {
        //     if (this.vcenterDatastore !== '') {
        //         if (this.datastores.indexOf(this.vcenterDatastore) !== -1) {
        //             this.formGroup.get('vcenterDatastore').setValue(this.vcenterDatastore);
        //         }
        //     }
        // }
        // return;
        //####### REMOVE_ME ##########
        let vCenterData = { 
            "vcenterAddress": "",
            "vcenterSsoUser": "",
            "vcenterSsoPasswordBase64": "",
            "vcenterDatacenter": datacenter,
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['vcenterSsoUser'] = this.formGroup.get('vcenterSsoUser').value;
        vCenterData['vcenterSsoPasswordBase64'] = this.formGroup.get('vcenterSsoPasswordBase64').value;

        this.apiClient.getDatastoresUnderDatacenterVsphere1('vcd', vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.datastores = data.DATASTORES;
                    this.formGroup.get('vcenterDatastore').enable();
                    this.fetchDatastore = true;
                    this.datastoreErrorMsg = '';
                    if (this.uploadStatus) {
                        if (this.vcenterDatastore !== '') {
                            if (this.datastores.indexOf(this.vcenterDatastore) !== -1) {
                                this.formGroup.get('vcenterDatastore').setValue(this.vcenterDatastore);
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
            "vcenterSsoUser": "",
            "vcenterSsoPasswordBase64": ""
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['vcenterSsoUser'] = this.formGroup.get('vcenterSsoUser').value;
        vCenterData['vcenterSsoPasswordBase64'] = this.formGroup.get('vcenterSsoPasswordBase64').value;

        this.apiClient.getVsphere1Data('vcd', vCenterData).subscribe((data: any) => {
              if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.datacenters = data.DATACENTERS;
                    this.contentLibs = data.CONTENTLIBRARY_NAMES;
                    this.resourcePools = data.RESOURCEPOOLS;
                    this.apiClient.networks = data.NETWORKS;
                    if (this.uploadStatus){
                        if (this.datacenters.indexOf(this.vcenterDatacenter) === -1) {
                            this.datacenterError = true;
                        } else {
                            this.datacenterError = false;
                            this.formGroup.get('vcenterDatacenter').setValue(this.vcenterDatacenter);
                            /**
                                This call will fetch all the cluster and datastores under the selected datacenter
                            */
                            this.getClustersUnderDatacenter(this.vcenterDatacenter);
                        }
                        if (!this.isMarketplace) {
                            if (this.contentLibs.indexOf(this.contentLibraryName) === -1) {
                                this.contentLibError = true;
                            } else {
                                this.contentLibError = false;
                                this.formGroup.get('contentLibraryName').setValue(this.contentLibraryName);
                                this.getOvaImagesUnderContentLib(this.contentLibraryName);
                            }
                        }
                        if (this.resourcePools.indexOf(this.resourcePoolName) === -1) {
                            this.resourcePoolError = true;
                        } else {
                            this.resourcePoolError = false;
                            this.formGroup.get('resourcePoolName').setValue(this.resourcePoolName);
                        }
                        if(this.apiClient.networks.indexOf(this.aviMgmtNetworkName) === -1) {
                            this.aviMgmtNetworkNameError = true;
                        } else {
                            this.aviMgmtNetworkNameError = false;
                            this.formGroup.get('aviMgmtNetworkName').setValue(this.aviMgmtNetworkName);
                        }
                    }
                    this.fetchResources = true;
                    this.errorNotification = null;
                    this.connected = true;
                    this.connectLoadingState = ClrLoadingState.DEFAULT;
                    this.enableAllFormFields();
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.connected = false;
                    this.errorNotification = 'vCenter: ' + data.msg;
                }
              } else {
                this.fetchResources = false;
                this.connected = false;
                this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources.';
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

    reloadVsphereData() {
        let vCenterData = {
            "vcenterAddress": "",
            "vcenterSsoUser": "",
            "vcenterSsoPasswordBase64": ""
        };

        vCenterData['vcenterAddress'] = this.formGroup.get('vcenterAddress').value;
        vCenterData['vcenterSsoUser'] = this.formGroup.get('vcenterSsoUser').value;
        vCenterData['vcenterSsoPasswordBase64'] = this.formGroup.get('vcenterSsoPasswordBase64').value;
        this.reloadLoadingState = ClrLoadingState.LOADING;
        this.apiClient.getVsphere1Data('vcd', vCenterData).subscribe((data: any) => {
              if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.datacenters = data.DATACENTERS;
                    this.contentLibs = data.CONTENTLIBRARY_NAMES;
                    this.resourcePools = data.RESOURCEPOOLS;
                    this.apiClient.networks = data.NETWORKS;
                    /**
                     * This will update the list of clusters as well
                     * and in turn make a call to getDatastoresUnderDatacenter as well
                     */
                    this.getClustersUnderDatacenter(this.formGroup.get('vcenterDatacenter').value);
                    /**
                     * This will update the list of ova images fetched from a content library
                     */
                    this.getOvaImagesUnderContentLib(this.formGroup.get('contentLibraryName').value);
                    this.fetchResources = true;
                    this.errorNotification = null;
                    this.connected = true;
                    this.loadData = true;
                    this.reloadLoadingState = ClrLoadingState.DEFAULT;
                    this.enableAllFormFields();
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = false;
                    this.loadData = false;
                    this.reloadLoadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = 'vCenter: ' + data.msg;
                }
              } else {
                this.fetchResources = false;
                this.loadData = false;
                this.reloadLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources. Please verify vCenter credentials';
              }
            }, (error: any) => {
              if (error.responseType === 'ERROR') {
                this.fetchResources = false;
                this.loadData = false;
                this.reloadLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: ' + error.msg;
              } else {
                this.fetchResources = false;
                this.loadData = false;
                this.reloadLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources. Please verify vCenter credentials';
              }
            });
    }

    /**
     * @method onContentLibChange
     * @desc This method is called anytime the Content library name value is modified from the UI template
     * @desc It will update the list of avi ova images in case a new content library is selected
     */
    onContentLibChange() {
        if (!this.formGroup.get('isMarketplace').value) {
            if (this.formGroup.get('contentLibraryName').value !== '') {
                this.formGroup.get('aviOvaName').disable();
                this.getOvaImagesUnderContentLib(this.formGroup.get('contentLibraryName').value);
            }
        }
    }

    /**
     * @method onDatacenterChange
     * @desc This method is called anytime the Datacenter value is modified from the UI template
     * @desc It will update the list of clusters and datastores in case a new datacenter is selected
     */
    onDatacenterChange() {
        if (this.formGroup.get('vcenterDatacenter').valid && this.formGroup.get('vcenterDatacenter').value !== '') {
            this.getClustersUnderDatacenter(this.formGroup.get('vcenterDatacenter').value);
        }
    }

    // ============================================= AVI management network ====================================================
    // ============================================= AVI Component Spec ========================================================
    
    public toggleEnableAviHa() {
        const aviHaFields = [
            "aviController02Fqdn",
            "aviController02Ip",
            "aviController03Fqdn",
            "aviController03Ip",
            "aviClusterFqdn",
            "aviClusterIp",
        ];
        if (this.formGroup.value['enableAviHa']) {
            this.resurrectField('aviController02Fqdn', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidFqdn(),
            ], this.formGroup.value['aviController02Fqdn']);
            this.resurrectField('aviController02Ip', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidIp(),
            ], this.formGroup.value['aviController02Ip']);
            this.resurrectField('aviController03Fqdn', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidFqdn(),
            ], this.formGroup.value['aviController03Fqdn']);
            this.resurrectField('aviController03Ip', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidIp(),
            ], this.formGroup.value['aviController03Ip']);
            this.resurrectField('aviClusterIp', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidIp(),
            ], this.formGroup.value['aviClusterIp']);
            this.resurrectField('aviClusterFqdn', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidFqdn(),
            ], this.formGroup.value['aviClusterFqdn']);
        } else {
            aviHaFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    public onAviVcdDisplayNameChange() {
        if(this.formGroup.get('aviVcdDisplayName').value === 'IMPORT TO VCD') {
            this.resurrectField('aviVcdDisplayNameInput', [Validators.required]);
        } else {
            this.disarmField('aviVcdDisplayNameInput', true);
        }
    }

    public nameResolutionTest() {
        //####### REMOVE_ME ##########
        // this.nameResolution = true;
        // return;
        //####### REMOVE_ME ##########
        let aviData = {
            'deployAvi': this.formGroup.get('deployAvi').value,
            "enableAviHa": this.formGroup.get("enableAviHa").value.toString(),
            "aviController01Fqdn": this.formGroup.get("aviController01Fqdn").value,
            "aviController01Ip": this.formGroup.get("aviController01Ip").value,
            "aviController02Fqdn": this.formGroup.get("aviController02Fqdn").value,
            "aviController02Ip": this.formGroup.get("aviController02Ip").value,
            "aviController03Fqdn": this.formGroup.get("aviController03Fqdn").value,
            "aviController03Ip": this.formGroup.get("aviController03Ip").value,
            "aviClusterFqdn": this.formGroup.get("aviClusterFqdn").value,
            "aviClusterIp": this.formGroup.get("aviClusterIp").value,
            "vcenterAddress": this.formGroup.get("vcenterAddress").value,
            "vcenterSsoUser": this.formGroup.get("vcenterSsoUser").value,
            "vcenterSsoPasswordBase64": this.formGroup.get("vcenterSsoPasswordBase64").value,
            "dnsServersIp": '',
        };

        this.dataService.currentDnsValue.subscribe(
            (dns) => aviData['dnsServersIp'] = dns);

        this.nameResolutionLoadingState = ClrLoadingState.LOADING;
        this.apiClient.aviNameResolutionForVCD('vcd', aviData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.nameResolution = true;
                    this.nameResolutionLoadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = null;
                } else if (data.responseType === 'ERROR') {
                    this.nameResolution = false;
                    this.errorNotification = data.msg;
                    this.nameResolutionLoadingState = ClrLoadingState.DEFAULT;
                }
            } else {
                this.nameResolution = false;
                this.errorNotification = "Some error occurred while validating name resolution for NSX ALB controller";
                this.nameResolutionLoadingState = ClrLoadingState.DEFAULT;
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.nameResolution = false;
                this.errorNotification = "Ping Test: " + err.msg;
                this.nameResolutionLoadingState = ClrLoadingState.DEFAULT;
            } else {
                this.nameResolution = false;
                this.errorNotification = "Some error occurred while validating name resolution for NSX ALB controller";
                this.nameResolutionLoadingState = ClrLoadingState.DEFAULT;
            }
        });
    }


    public getAVIVcdDisplayNames() {
        let vcdData = {
            'vcdAddress': '',
            'vcdSysAdminUserName': '',
            'vcdSysAdminPasswordBase64': '',
        };
        //####### REMOVE_ME ##########
        // this.fetchAviVcdDisplayNames = true;
        // return;
        //####### REMOVE_ME ##########
        this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
        this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
        this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);
        this.apiClient.listAVIVCDDisplayNames('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.aviVcdDisplayNames = data.AVI_VCD_LIST;
                    this.dataService.aviVcdDisplayNamesErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    this.dataService.aviVcdDisplayNamesErrorMessage = data.msg;
                }
            } else {
                this.dataService.aviVcdDisplayNamesErrorMessage = "Some error occurred while fetching AVI VCD Display names";
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.aviVcdDisplayNamesErrorMessage = "Fetch AVI VCD Display Names: " + err.msg;
            } else {
                this.dataService.aviVcdDisplayNamesErrorMessage = "Some error occurred while fetching AVI VCD Display names";
            }
        });
    }


    public validateGatewayCidrAndIp() {
        if(this.formGroup.get('deployAvi').value) {
            if(this.formGroup.get('aviMgmtNetworkGatewayCidr').valid && this.formGroup.get('aviMgmtNetworkGatewayCidr').value!== '') {
                const gatewayIp = this.formGroup.get('aviMgmtNetworkGatewayCidr').value;
                const block = new Netmask(gatewayIp);
                if (this.formGroup.get('aviController01Ip').valid && this.formGroup.get('aviController01Ip').value !== '') {
                    let controller1 = this.formGroup.get('aviController01Ip').value;
                    if(!block.contains(controller1)) {
                        this.apiClient.aviController01Error = true;
                    } else this.apiClient.aviController01Error = false;
                } else this.apiClient.aviController01Error = false;

                if (this.formGroup.get('aviController02Ip').valid && this.formGroup.get('aviController02Ip').value !== '') {
                    let controller2 = this.formGroup.get('aviController02Ip').value;
                    if(!block.contains(controller2)) {
                        this.apiClient.aviController02Error = true;
                    } else this.apiClient.aviController02Error = false;
                } else this.apiClient.aviController02Error = false;

                if (this.formGroup.get('aviController03Ip').valid && this.formGroup.get('aviController03Ip').value !== '') {
                    let controller3 = this.formGroup.get('aviController03Ip').value;
                    if(!block.contains(controller3)) {
                        this.apiClient.aviController03Error = true;
                    } else this.apiClient.aviController03Error = false;
                } else this.apiClient.aviController03Error = false;

                if (this.formGroup.get('aviClusterIp').valid && this.formGroup.get('aviClusterIp').value !== '') {
                    let controller4 = this.formGroup.get('aviClusterIp').value;
                    if(!block.contains(controller4)) {
                        this.apiClient.clusterIpError = true;
                    } else this.apiClient.clusterIpError = false;
                } else this.apiClient.clusterIpError = false;
            } else {
                this.apiClient.aviController01Error = false;
                this.apiClient.aviController02Error = false;
                this.apiClient.aviController03Error = false;
                this.apiClient.clusterIpError = false;
            }
        } else {
            this.apiClient.aviController01Error = false;
            this.apiClient.aviController02Error = false;
            this.apiClient.aviController03Error = false;
            this.apiClient.clusterIpError = false;
        }
    }
}

