/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
/**
 * Angular Modules
 */
 import { Component, Input, OnInit, ViewChild } from '@angular/core';
 import { Validators, FormControl } from '@angular/forms';
 import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
 import { Netmask } from 'netmask';
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
 
const SupervisedField = ['vcenterAddress', 'vcenterSsoUser', 'vcenterSsoPasswordBase64'];
const NSXTFields = ['nsxtAddress', 'nsxtUser', 'nsxtUserPasswordBase64'];
 @Component({
     selector: 'app-avi-nsx-cloud-step',
     templateUrl: './avi-nsx-cloud.component.html',
     styleUrls: ['./avi-nsx-cloud.component.scss'],
 })
export class AviNsxCloudComponent extends StepFormDirective implements OnInit {
    @Input() InputNsxtCloudsInALB: [];
    @Input() InputNsxtCloudVcdDisplayName: [];
    @Input() InputConfigureNSXTCloud;
    // =========================== COMMON PROPERTIES ========================================
    private uploadStatus;
    subscription: Subscription;
    // =========================== AVI PROPERTIES ========================================
    private configureAviNsxtCloud;
    // =========================== NSX DETAILS ========================================
    nsxtConnected: boolean = false;
    nsxtConnectLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    private nsxtAddress;
    private nsxtUser;
    private nsxtUserPasswordBase64;

    tier1Routers = [];
    nsxtOverlays = [];

    nsxtTier1RouterError: boolean = false;
    nsxtOverlayError: boolean = false;
    fetchNsxtResources: boolean = false;

    // ===================================== AVI NSX CLOUD NAME ===============================================
    private fetchNsxtCloudConfiguredInAvi = false;
    nsxtCloudsInAvi = [];
    private aviNsxCloudName;
    // =========================== VSPHERE PROPERTIES ========================================
    @ViewChild(SSLThumbprintModalComponent) sslThumbprintModal: SSLThumbprintModalComponent;
 
    dataLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    
    validateLoadingState: ClrLoadingState = ClrLoadingState.DEFAULT;

    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    vcenterAddress;
    private vcenterSsoUser;
    private vcenterSsoPasswordBase64;
    thumbprint;

    fetchResources: boolean = false;
    fetchDatastore: boolean = false;
    fetchCluster = false;
    connected: boolean = false;
    // =========================== NSXT TIER 1 SE NETWORK ========================================
    private nsxtTier1SeMgmtNetworkName;
    private nsxtOverlay;
    // =========================== AVI SE MANAGEMENT NETWORK =====================================
    aviSeMgmtNetworkVerified = false;
    aviSeMgmtNetworkVerifiedErrorMsg = null;
    private aviSeMgmtNetworkName;
    private aviSeMgmtNetworkGatewayCidr;
    private aviSeMgmtNetworkDhcpStartRange;
    private aviSeMgmtNetworkDhcpEndRange;
    // ============================== AVI NSXT CLOUD VCD DISPLAY NAME =============================
    private nsxtCloudVcdDisplayName;
    aviNsxCloudVcdDisplayNames = [];

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                private apiClient: APIClient,
                public dataService: VCDDataService) {

        super();
    }
 
    ngOnInit() {
        super.ngOnInit();
 
        this.formGroup.addControl('configureAviNsxtCloud', new FormControl(false));
        // ============================== GREENFIELD ==========================================
 
        // NSXT DETAILS
        this.formGroup.addControl('nsxtAddress', new FormControl('', [Validators.required, this.validationService.isValidIpOrFqdn(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('nsxtUser', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('nsxtUserPasswordBase64', new FormControl('', [Validators.required]));
 
        // AVI NSX CLOUD NAME
        this.formGroup.addControl('aviNsxCloudName', new FormControl('', [Validators.required]));

        // VSPHERE
        this.formGroup.addControl('thumbprint', new FormControl('', [])); // Fetched from Backend, no use on UI
        this.formGroup.addControl('vcenterAddress', new FormControl('', [Validators.required, this.validationService.isValidIpOrFqdn(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('vcenterSsoUser', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('vcenterSsoPasswordBase64', new FormControl('', [Validators.required]));

        // NSXT TIER 1 SE NETWORK
        this.formGroup.addControl('nsxtTier1SeMgmtNetworkName', new FormControl('', []));
        this.formGroup.addControl('nsxtOverlay', new FormControl('', [Validators.required]));

        // AVI SE MANAGEMENT NETWORK
        this.formGroup.addControl('aviSeMgmtNetworkName', new FormControl('', []));
        this.formGroup.addControl('aviSeMgmtNetworkGatewayCidr', new FormControl('', []));
        this.formGroup.addControl('aviSeMgmtNetworkDhcpStartRange', new FormControl('', []));
        this.formGroup.addControl('aviSeMgmtNetworkDhcpEndRange', new FormControl('', []));

        // AVI NSXT CLOUD VCD DISPLAY NAME
        this.formGroup.addControl('nsxtCloudVcdDisplayName', new FormControl('', [Validators.required]));
        this.formGroup.addControl('nsxtCloudVcdDisplayNameInput', new FormControl('', []));

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
                    this.loadingState = ClrLoadingState.DEFAULT;
                });
        });
        NSXTFields.forEach(field => {
            // tslint:disable-next-line:max-line-length
            this.formGroup.get(field).valueChanges.pipe(
                debounceTime(500),
                distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                takeUntil(this.unsubscribe))
                .subscribe(() => {
                    this.nsxtConnected = false;
                    this.nsxtConnectLoadingState = ClrLoadingState.DEFAULT;
                    this.formGroup.get('nsxtTier1SeMgmtNetworkName').setValue('');
                    this.tier1Routers = [];
                    this.formGroup.get('nsxtTier1SeMgmtNetworkName').disable();

                    this.formGroup.get('nsxtOverlay').setValue('');
                    this.nsxtOverlays = [];
                    this.formGroup.get('nsxtOverlay').disable();
                });
        });

        this.formGroup['canMoveToNext'] = () => {
            this.toggleConfigureAviNsxtCloud();
            let result = this.formGroup.valid && this.fetchNsxtResources && this.nsxtConnected && this.connected;

            if(this.formGroup.get('configureAviNsxtCloud').value) {
                this.aviSeMgmtIpGatewayCheck();
                result = result && this.fetchResources && this.connected && this.aviSeMgmtNetworkVerified;
            }
            return result;
            // return this.formGroup.valid && this.fetchNsxtResources && this.nsxtConnected && this.fetchResources && this.fetchDatastore && this.connected && this.aviSeMgmtNetworkVerified && this.fetchCluster;
            // } else {
            //     return this.formGroup.valid && this.nsxtConnected && this.connected;
            // }
        };

        setTimeout(_ => {
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                // ===================================== GREENFIELD ============================================
                this.subscription = this.dataService.currentConfigureNsxtCloud.subscribe(
                    (configure) => this.configureAviNsxtCloud = configure);
                this.formGroup.get('configureAviNsxtCloud').setValue(this.configureAviNsxtCloud);
                this.subscription = this.dataService.currentNsxtAddress.subscribe(
                    (address) => this.nsxtAddress = address);
                this.formGroup.get('nsxtAddress').setValue(this.nsxtAddress);
                this.subscription = this.dataService.currentNsxtUser.subscribe(
                    (user) => this.nsxtUser = user);
                this.formGroup.get('nsxtUser').setValue(this.nsxtUser);
                this.subscription = this.dataService.currentNsxtUserPasswordBase64.subscribe(
                    (address) => this.nsxtUserPasswordBase64 = address);
                this.formGroup.get('nsxtUserPasswordBase64').setValue(this.nsxtUserPasswordBase64);
                
                this.subscription = this.dataService.currentAviNsxCloudName.subscribe(
                    (cloudName) => this.aviNsxCloudName = cloudName);

                this.subscription = this.dataService.currentVcenterAddressCloud.subscribe(
                    (address) => this.vcenterAddress = address);
                this.formGroup.get('vcenterAddress').setValue(this.vcenterAddress);
                this.subscription = this.dataService.currentVcenterSsoUserCloud.subscribe(
                    (address) => this.vcenterSsoUser = address);
                this.formGroup.get('vcenterSsoUser').setValue(this.vcenterSsoUser);
                this.subscription = this.dataService.currentVcenterSsoPasswordBase64Cloud.subscribe(
                    (address) => this.vcenterSsoPasswordBase64 = address);
                this.formGroup.get('vcenterSsoPasswordBase64').setValue(this.vcenterSsoPasswordBase64);

                this.subscription = this.dataService.currentNsxtCloudVcdDisplayName.subscribe(
                    (name) => this.nsxtCloudVcdDisplayName = name);

                this.subscription = this.dataService.currentNsxtOverlay.subscribe(
                    (overlay) => this.nsxtOverlay = overlay);

                if(this.configureAviNsxtCloud) {
                    this.subscription = this.dataService.currentNsxtTier1SeMgmtNetworkName.subscribe(
                        (tier1_gw) => this.nsxtTier1SeMgmtNetworkName = tier1_gw);

                    this.subscription = this.dataService.currentAviSeMgmtNetworkName.subscribe(
                        (nw) => this.aviSeMgmtNetworkName = nw);
                    this.formGroup.get('aviSeMgmtNetworkName').setValue(this.aviSeMgmtNetworkName);
                    this.subscription = this.dataService.currentAviSeMgmtNetworkGatewayCidr.subscribe(
                        (gw) => this.aviSeMgmtNetworkGatewayCidr = gw);
                    this.formGroup.get('aviSeMgmtNetworkGatewayCidr').setValue(this.aviSeMgmtNetworkGatewayCidr);
                    this.subscription = this.dataService.currentAviSeMgmtNetworkDhcpStartRange.subscribe(
                        (startIp) => this.aviSeMgmtNetworkDhcpStartRange = startIp);
                    this.formGroup.get('aviSeMgmtNetworkDhcpStartRange').setValue(this.aviSeMgmtNetworkDhcpStartRange);
                    this.subscription = this.dataService.currentAviSeMgmtNetworkDhcpEndRange.subscribe(
                        (endIp) => this.aviSeMgmtNetworkDhcpEndRange = endIp);
                    this.formGroup.get('aviSeMgmtNetworkDhcpEndRange').setValue(this.aviSeMgmtNetworkDhcpEndRange);
                    this.aviSeMgmtIpGatewayCheck();

                    this.formGroup.get('nsxtCloudVcdDisplayName').setValue(this.nsxtCloudVcdDisplayName);
                    this.formGroup.get('aviNsxCloudName').setValue(this.aviNsxCloudName);
                } else {
                    if(this.dataService.nsxtCloudsInALB.indexOf(this.aviNsxCloudName) !== -1) {
                        this.formGroup.get('aviNsxCloudName').setValue(this.aviNsxCloudName);
                    }
                    if(this.dataService.nsxtCloudVcdDisplayNames.indexOf(this.nsxtCloudVcdDisplayName) !== -1) {
                        this.formGroup.get('nsxtCloudVcdDisplayName').setValue(this.nsxtCloudVcdDisplayName);
                    } else {
                        this.formGroup.get('nsxtCloudVcdDisplayName').setValue("IMPORT TO VCD");
                        this.formGroup.get('nsxtCloudVcdDisplayNameInput').setValue(this.nsxtCloudVcdDisplayName);
                    }
                }

            }
            // this.toggleMarketPlace();
        });
    }
 
    ngOnChanges() {
        if(this.formGroup.get('configureAviNsxtCloud')){
            this.formGroup.get('configureAviNsxtCloud').setValue(this.dataService.configureAviNsxtCloud);
        }
        if(this.dataService.nsxtCloudsInALB.length !== 0 && this.dataService.nsxtCloudsInALB.indexOf(this.aviNsxCloudName) !== -1) {
            if(this.formGroup.get('aviNsxCloudName')) this.formGroup.get('aviNsxCloudName').setValue(this.aviNsxCloudName);
        }
        if(this.dataService.nsxtCloudVcdDisplayNames.length !== 0 && this.dataService.nsxtCloudVcdDisplayNames.indexOf(this.nsxtCloudVcdDisplayName) !== -1) {
            if(this.formGroup.get('nsxtCloudVcdDisplayName')) this.formGroup.get('nsxtCloudVcdDisplayName').setValue(this.nsxtCloudVcdDisplayName);
        } else {
            if(this.formGroup.get('nsxtCloudVcdDisplayName')) this.formGroup.get('nsxtCloudVcdDisplayName').setValue('IMPORT TO VCD');
            if(this.formGroup.get('nsxtCloudVcdDisplayNameInput')) this.formGroup.get('nsxtCloudVcdDisplayNameInput').setValue(this.nsxtCloudVcdDisplayName);
        }
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        this.formGroup.get('nsxtUserPasswordBase64').setValue('');
        if (!this.uploadStatus) {
            this.formGroup.get('nsxtUserPasswordBase64').setValue('');
        }
    }
 
    public onAviCloudVcdDisplayNameChange() {
        if(this.formGroup.get('nsxtCloudVcdDisplayName').value === 'IMPORT TO VCD') {
            this.resurrectField('nsxtCloudVcdDisplayNameInput', [Validators.required]);
        } else {
            this.disarmField('nsxtCloudVcdDisplayNameInput', true);
        }
    }


    // ======================================================= AVI CONTROLLER FILED ====================================================================
    public toggleConfigureAviNsxtCloud() {
        const greenfieldFields = [
            'nsxtTier1SeMgmtNetworkName',
            'aviSeMgmtNetworkName',
            'aviSeMgmtNetworkGatewayCidr',
            'aviSeMgmtNetworkDhcpStartRange',
            'aviSeMgmtNetworkDhcpEndRange',
        ];
        if (this.formGroup.get('configureAviNsxtCloud').value) {
            this.dataService.configureAviNsxtCloud = true;
            this.dataService.createSeGroup = true;

            this.resurrectField('aviNsxCloudName', [
                Validators.required, this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['aviNsxCloudName']);

            this.resurrectField('nsxtTier1SeMgmtNetworkName', [
                Validators.required,
            ], this.formGroup.value['nsxtTier1SeMgmtNetworkName']);

            this.resurrectField('aviSeMgmtNetworkName', [
                Validators.required,
                this.validationService.noWhitespaceOnEnds(),
            ], this.formGroup.value['aviSeMgmtNetworkName']);

            this.resurrectField('aviSeMgmtNetworkGatewayCidr', [
                Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds(),
            ], this.formGroup.value['aviSeMgmtNetworkGatewayCidr']);

            this.resurrectField('aviSeMgmtNetworkDhcpStartRange', [
                Validators.required, this.validationService.isValidIpOrFqdn(),
                this.validationService.noWhitespaceOnEnds(),
            ], this.formGroup.value['aviSeMgmtNetworkDhcpStartRange']);

            this.resurrectField('aviSeMgmtNetworkDhcpEndRange', [
                Validators.required, this.validationService.isValidIpOrFqdn(),
                this.validationService.noWhitespaceOnEnds(),
            ], this.formGroup.value['aviSeMgmtNetworkDhcpEndRange']);
        } else {
            this.dataService.configureAviNsxtCloud = false;
            // this.getNsxtCloudConfiguredInAvi();
            this.resurrectField('aviNsxCloudName', [
                Validators.required,
            ], this.formGroup.value['aviNsxCloudName']);

            greenfieldFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    public getAviNsxCloudVcdDisplayNames() {
        let vcdData = {
            'vcdAddress': '',
            'vcdSysAdminUserName': '',
            'vcdSysAdminPasswordBase64': '',
        };
        this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
        this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
        this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);

        this.apiClient.listNsxtCloudVcdDisplayNames('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.nsxtCloudVcdDisplayNames = data.NSXT_CLOUD_VCD_LIST;
                    this.dataService.nsxtCloudVcdDisplayNameErrorMessage = null;
                    if(this.uploadStatus) {
                        if(this.dataService.nsxtCloudVcdDisplayNames.indexOf(this.nsxtCloudVcdDisplayName)) {
                            this.formGroup.get('nsxtCloudVcdDisplayName').setValue(this.nsxtCloudVcdDisplayName);
                        }
                    }
                } else if (data.responseType === 'ERROR') {
                    this.dataService.nsxtCloudVcdDisplayNameErrorMessage = data.msg;
                }
            } else {
                this.dataService.nsxtCloudVcdDisplayNameErrorMessage = "Some error occurred while fetching AVI NSX Cloud VCD display names";
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.nsxtCloudVcdDisplayNameErrorMessage = "Fetch AVI NSX Cloud VCD Display Names: " + err.msg;
            } else {
                this.dataService.nsxtCloudVcdDisplayNameErrorMessage = "Some error occurred while fetching AVI NSX Cloud VCD display names";
            }
        });
    }

    /**
     * @method: This method will list all the NSXT clouds that are configured in AVI
     */
    public getNsxtCloudConfiguredInAvi() {
        let nsxtCloudData;
        if(this.dataService.aviGreenfield) {
            nsxtCloudData = {
                'deployAvi': 'true',
                'aviController01Ip': '',
                'aviUsername': '',
                'aviPasswordBase64': '',
            };
            this.dataService.currentAviController01Ip.subscribe((ip1) => nsxtCloudData['aviController01Ip'] = ip1);
            if(nsxtCloudData['aviController01Ip'] === '') return;
         } else {
            nsxtCloudData = {
                'deployAvi': 'false',
                'aviClusterIp': '',
                'aviUsername': '',
                'aviPasswordBase64': '',                
            };
            this.dataService.currentAviClusterIp.subscribe((ip) => nsxtCloudData['aviClusterIp'] = ip);
            if(nsxtCloudData['aviClusterIp'] === '') return;
        }

        this.dataService.currentAviUsername.subscribe((user) => nsxtCloudData['aviUsername'] = user);
        this.dataService.currentAviPasswordBase64.subscribe((pass) => nsxtCloudData['aviPasswordBase64'] = pass);

        this.apiClient.listNSXTCloudsConfiguredInAVI('vcd', nsxtCloudData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.nsxtCloudsInALB = data.NSXT_CLOUDS;
                    if(this.uploadStatus) {
                        if(this.dataService.nsxtCloudsInALB.indexOf(this.aviNsxCloudName) !== -1) {
                            this.formGroup.get('aviNsxCloudName').setValue(this.aviNsxCloudName);
                        }
                    }
                    this.dataService.nsxtCloudsInAlbErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    this.dataService.nsxtCloudsInAlbErrorMessage = data.msg;
                }
            } else {
                this.dataService.nsxtCloudsInAlbErrorMessage = "Some error occurred while fetching NSXT Clouds configured in AVI";
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.nsxtCloudsInAlbErrorMessage = "Fetch NSXT Clouds configured in AVI: " + err.msg;
            } else {
                this.dataService.nsxtCloudsInAlbErrorMessage = "Some error occurred while fetching NSXT Clouds configured in AVI";
            }
        });
    }

    /**
     * @method getNsxtDisabled
     * helper method to get if connect btn for NSXT should be disabled
     */
    public getNsxtDisabled(){
        return !(this.formGroup.get('nsxtAddress').valid && this.formGroup.get('nsxtUser').valid && this.formGroup.get('nsxtUserPasswordBase64').valid);
    }

    public connectNSXT() {
        //####### REMOVE_ME ##########
        // this.tier1Routers = ['router-1', 'router-2'];
        // this.nsxtOverlays = ['overlay-1', 'overlay-2'];
        // this.dataService.t0GatewayFromNsxt = ['t0-gw-nsx-1', 'to-gw-nsx-2'];
        // this.fetchNsxtResources = true;
        // this.nsxtConnected = true;
        // if (this.uploadStatus){
        //     if (this.tier1Routers.indexOf(this.nsxtTier1SeMgmtNetworkName) === -1) {
        //         this.nsxtTier1RouterError = true;
        //     } else {
        //         this.nsxtTier1RouterError = false;
        //         this.formGroup.get('nsxtTier1SeMgmtNetworkName').setValue(this.nsxtTier1SeMgmtNetworkName);
        //     }
        //     if (this.nsxtOverlays.indexOf(this.nsxtOverlay) === -1) {
        //         this.nsxtOverlayError = true;
        //     } else {
        //         this.nsxtOverlayError = false;
        //         this.formGroup.get('nsxtOverlay').setValue(this.nsxtOverlay);
        //     }
        // }
        // this.enableAllNSXTFormFields();
        // return;
        //####### REMOVE_ME ##########
        let nsxtData = {
            "nsxtAddress": "",
            "nsxtUsername": "",
            "nsxtPassword": ""
        };
    
        nsxtData['nsxtAddress'] = this.formGroup.get('nsxtAddress').value;
        nsxtData['nsxtUsername'] = this.formGroup.get('nsxtUser').value;
        nsxtData['nsxtPassword'] = this.formGroup.get('nsxtUserPasswordBase64').value;

        this.nsxtConnectLoadingState = ClrLoadingState.LOADING;
        this.apiClient.getNsxtData(nsxtData, 'vcd').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.tier1Routers = data.TIER1_DETAILS; 
                    this.nsxtOverlays = data.OVERLAY_LIST;
                    this.fetchT0FromNsxt();
                    if (this.uploadStatus && this.formGroup.get('configureAviNsxtCloud').value){
                        if (this.tier1Routers.indexOf(this.nsxtTier1SeMgmtNetworkName) === -1) {
                            this.nsxtTier1RouterError = true;
                        } else {
                            this.nsxtTier1RouterError = false;
                            this.formGroup.get('nsxtTier1SeMgmtNetworkName').setValue(this.nsxtTier1SeMgmtNetworkName);
                        }
                    }
                    if(this.uploadStatus){
                        if (this.nsxtOverlays.indexOf(this.nsxtOverlay) === -1) {
                            this.nsxtOverlayError = true;
                        } else {
                            this.nsxtOverlayError = false;
                            this.formGroup.get('nsxtOverlay').setValue(this.nsxtOverlay);
                        }
                    }
                } else if (data.responseType === 'ERROR') {
                    this.fetchNsxtResources = false;
                    this.nsxtConnected = false;
                    this.nsxtConnectLoadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = 'NSX-T: ' + data.msg;
                }
            } else {
                this.fetchNsxtResources = false;
                this.nsxtConnected = false;
                this.nsxtConnectLoadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'NSX-T: Some Error Occurred while Fetching Resources. Please verify NSX-T credentials.';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.fetchNsxtResources = false;
                this.nsxtConnected = false;
                this.nsxtConnectLoadingState = ClrLoadingState.ERROR;
                this.errorNotification = 'NSX-T: ' + error.msg;
            } else {
                this.fetchNsxtResources = false;
                this.nsxtConnected = false;
                this.nsxtConnectLoadingState = ClrLoadingState.ERROR;
                this.errorNotification = 'NSX-T: Some Error Occurred while Fetching Resources. Please verify NSX-T credentials.';
            }
        });
    }

    public fetchT0FromNsxt() {
        let nsxtData = {
            "nsxtAddress": this.formGroup.get('nsxtAddress').value,
            "nsxtUser": this.formGroup.get('nsxtUser').value,
            "nsxtUserPasswordBase64": this.formGroup.get('nsxtUserPasswordBase64').value
        };

        this.apiClient.fetchT0FromNsxt('vcd', nsxtData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.t0GatewayFromNsxt = data.Tier0_GATEWAY_NSX;
                    this.dataService.t0GatewayFromNsxtErrorMessage = null;
                    this.getNsxtCloudConfiguredInAvi();
                    this.fetchNsxtResources = true;
                    this.errorNotification = null;
                    this.nsxtConnected = true;
                    this.enableAllNSXTFormFields();
                    this.nsxtConnectLoadingState = ClrLoadingState.DEFAULT;

                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.t0GatewayFromNsxtErrorMessage = data.msg;
                    } else {
                        this.dataService.t0GatewayFromNsxtErrorMessage = 'Failed to fetch list of Tier0 Routers from NSXT';
                    }
                    this.fetchNsxtResources = true;
                    this.errorNotification = null;
                    this.nsxtConnected = true;
                    this.enableAllNSXTFormFields();
                    this.nsxtConnectLoadingState = ClrLoadingState.DEFAULT;
                }
            } else {
                this.dataService.t0GatewayFromNsxtErrorMessage = 'Failed to fetch list of Tier0 Routers from NSXT';
                this.fetchNsxtResources = true;
                this.errorNotification = null;
                this.nsxtConnected = true;
                this.enableAllNSXTFormFields();
                this.nsxtConnectLoadingState = ClrLoadingState.DEFAULT;
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.t0GatewayFromNsxtErrorMessage = err.msg;
                this.fetchNsxtResources = true;
                this.errorNotification = null;
                this.nsxtConnected = true;
                this.enableAllNSXTFormFields();
                this.nsxtConnectLoadingState = ClrLoadingState.DEFAULT;
            } else {
                this.dataService.t0GatewayFromNsxtErrorMessage = 'Failed to fetch list of Tier0 Routers from NSXT';
                this.fetchNsxtResources = true;
                this.errorNotification = null;
                this.nsxtConnected = true;
                this.enableAllNSXTFormFields();
                this.nsxtConnectLoadingState = ClrLoadingState.DEFAULT;
            }
        });
    }


    public onAviNsxCloudNameChange() {
        if(!this.dataService.configureAviNsxtCloud) {
            if(this.formGroup.get('aviNsxCloudName').valid && this.formGroup.get('aviNsxCloudName').value!== '') {
                this.fetchServiceEngineGroupNamesFromALB(this.formGroup.get('aviNsxCloudName').value);
            }
        }
        
    }

    public fetchServiceEngineGroupNamesFromALB(cloudname) {
        let segData = {
            'deployAvi': this.dataService.aviGreenfield.toString(),
            'aviController01Ip': '',
            'aviClusterIp': '',
            'aviUsername': '',
            'aviPasswordBase64': '',
            'aviNsxCloudName': cloudname
        };

        if(this.dataService.aviGreenfield) {
            this.dataService.currentAviController01Ip.subscribe((ip1) => segData['aviController01Ip'] = ip1);
        } else {
            this.dataService.currentAviClusterIp.subscribe((ip) => segData['aviClusterIp'] = ip);
        }
        this.dataService.currentAviUsername.subscribe((user) => segData['aviUsername'] = user);
        this.dataService.currentAviPasswordBase64.subscribe((pass) => segData['aviPasswordBase64'] = pass);

        this.apiClient.fetchServiceEngineGroupNamesFromALB('vcd', segData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.serviceEngineGroupnamesAlb = data.SEG_LIST_AVI;
                    this.dataService.serviceEngineGroupnameAlbErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    this.dataService.serviceEngineGroupnameAlbErrorMessage = data.msg;
                }
            } else {
                this.dataService.serviceEngineGroupnameAlbErrorMessage = "Some error occurred while fetching Service Engine groups for the provided NSXT cloud";
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.serviceEngineGroupnameAlbErrorMessage = err.msg;
            } else {
                this.dataService.serviceEngineGroupnameAlbErrorMessage = "Some error occurred while fetching Service Engine groups for the provided NSXT cloud";
            }
        });
    }

    public enableAllNSXTFormFields() {
        this.formGroup.get('nsxtTier1SeMgmtNetworkName').enable();
        this.formGroup.get('nsxtOverlay').enable();
    }

    public disableAllNSXTFormFields() {
        this.formGroup.get('nsxtTier1SeMgmtNetworkName').disable();
        this.formGroup.get('nsxtOverlay').disable();
    }
    //  ======================================================== GREENFIELD: VSPHERE =====================================================
    /**
     * @method getDisabled
     * helper method to get if connect btn should be disabled
     */
     getDisabled(): boolean {
        return !(this.formGroup.get('vcenterAddress').valid && this.formGroup.get('vcenterSsoUser').valid && this.formGroup.get('vcenterSsoPasswordBase64').valid);
    }

    enableAllFormFields() {
        // this.formGroup.get('vcenterDatacenter').enable();
        // this.formGroup.get('vcenterContentSeLibrary').enable();
    }    

    dumyFormFields() {
        this.apiClient.networks = ['Network-1', 'Network-2', 'Network-3', 'Network-4'];
        this.fetchResources = true;
    } 
       
    /**
     * @method connectVC
     * helper method to make connection to VC environment, call retrieveDatacenters
     * method if VC connection successful
     */
     connectVC() {
        this.loadingState = ClrLoadingState.LOADING;
        this.vcenterAddress = this.formGroup.controls['vcenterAddress'].value;
        this.getSSLThumbprint(this.vcenterAddress);


        // Remove from 556 to 569
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
    }

    getSSLThumbprint(vcenterAddress) {
        //####### REMOVE_ME ##########
        // this.thumbprint = "XYXYXYXYXYXYX";
        // this.formGroup.controls['thumbprint'].setValue(this.thumbprint);
        // FormMetaDataStore.saveMetaDataEntry(this.formName, 'thumbprint', {
        //     label: 'SSL THUMBPRINT',
        //     displayValue: this.thumbprint,
        // });
        // this.sslThumbprintModal.open();
        // if(this.formGroup.get('configureAviNsxtCloud').value) {
        //     this.getVsphereData();
        // }
        // return;
        //####### REMOVE_ME ##########
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
        this.errorNotification = null;
        this.loadingState = ClrLoadingState.DEFAULT;
    }

    getVsphereData() {
        //####### REMOVE_ME ##########
        // this.datacenters = ['dc-1', 'dc-2'];
        // this.contentLibs = ['lib-1', 'lib-2'];
        // this.contentLibs.push('CREATE NEW');
        // if (this.uploadStatus){
        //     if (this.datacenters.indexOf(this.vcenterDatacenter) === -1) {
        //         this.datacenterError = true;
        //     } else {
        //         this.datacenterError = false;
        //         this.formGroup.get('vcenterDatacenter').setValue(this.vcenterDatacenter);
        //         this.getClustersUnderDatacenter(this.vcenterDatacenter);
        //     }
        //     if (this.contentLibs.indexOf(this.vcenterContentSeLibrary) === -1) {
        //         this.contentLibError = true;
        //     } else {
        //         this.contentLibError = false;
        //         this.formGroup.get('vcenterContentSeLibrary').setValue(this.vcenterContentSeLibrary);
        //         if(this.vcenterContentSeLibrary === 'CREATE NEW') this.onContentLibraryChange();
        //     }
        // }
        // this.fetchResources = true;
        // this.errorNotification = null;
        // this.connected = true;
        // this.loadingState = ClrLoadingState.DEFAULT;
        // this.enableAllFormFields();
        // return;
        //####### REMOVE_ME ##########
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
                    this.dataService.vc2Datacenters = data.DATACENTERS;
                    this.dataService.vc2ContentLibs = data.CONTENTLIBRARY_NAMES;

                    this.fetchResources = true;
                    this.errorNotification = null;
                    this.connected = true;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    this.enableAllFormFields();
                } else if (data.responseType === 'ERROR') {
                    this.fetchResources = true;
                    this.connected = true;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    // this.errorNotification = 'vCenter: ' + data.msg;
                }
              } else {
                this.fetchResources = true;
                this.connected = true;
                this.loadingState = ClrLoadingState.DEFAULT;
                // this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources.';
              }
            }, (error: any) => {
              if (error.responseType === 'ERROR') {
                this.fetchResources = true;
                this.connected = true;
                this.loadingState = ClrLoadingState.DEFAULT;
                // this.errorNotification = 'vCenter: ' + error.msg;
              } else {
                this.fetchResources = true;
                this.connected = true;
                this.loadingState = ClrLoadingState.DEFAULT;
                // this.errorNotification = 'vCenter: Some Error Occurred while Fetching Resources. Please verify vCenter credentials.';
              }
        });
    }


    /**
     * @method: This will validate whether the provided DHCP start and end IPs are part of the Gateway CIDR.
     */
    public aviSeMgmtIpGatewayCheck() {
        if (this.formGroup.get('aviSeMgmtNetworkGatewayCidr').valid && this.formGroup.get('aviSeMgmtNetworkGatewayCidr').value !== '' &&
            this.formGroup.get('aviSeMgmtNetworkDhcpStartRange').valid && this.formGroup.get('aviSeMgmtNetworkDhcpStartRange').value !== '' &&
            this.formGroup.get('aviSeMgmtNetworkDhcpEndRange').valid && this.formGroup.get('aviSeMgmtNetworkDhcpEndRange').value !== '') {

            const gatewayIp = this.formGroup.get('aviSeMgmtNetworkGatewayCidr').value;
            const dhcpStart = this.formGroup.get('aviSeMgmtNetworkDhcpStartRange').value;
            const dhcpEnd = this.formGroup.get('aviSeMgmtNetworkDhcpEndRange').value;

            const block = new Netmask(gatewayIp);
            if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                this.aviSeMgmtNetworkVerified = true;
                this.aviSeMgmtNetworkVerifiedErrorMsg = null;
            } else {
                let str='';
                if (!block.contains(dhcpStart)) {
                    str = 'NSX ALB SE Start IP, ';
                }
                if (!block.contains(dhcpEnd)) {
                    str = str + 'NSX ALB SE End IP, ';
                }
                this.aviSeMgmtNetworkVerifiedErrorMsg = str + ' outside of the provided subnet.';
                this.aviSeMgmtNetworkVerified = false;
            }
        }
    }
 }
 
 