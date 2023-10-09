/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
/**
 * Angular Modules
 */
import { Component, OnInit } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';
import { ClrLoadingState } from '@clr/angular';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { Subscription } from 'rxjs';
 /**
  * App imports
  */
import { APP_ROUTES, Routes } from 'src/app/shared/constants/routes.constants';
import { APIClient } from 'src/app/swagger/api-client.service';
import { VCDDataService } from 'src/app/shared/service/vcd-data.service';
import { StepFormDirective } from 'src/app/views/landing/wizard/shared/step-form/step-form';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';


const SupervisedField = ['vcdAddress', 'vcdSysAdminUserName', 'vcdSysAdminPasswordBase64'];


@Component({
    selector: 'app-vcd-spec-step',
    templateUrl: './vcd-spec.component.html',
    styleUrls: ['./vcd-spec.component.scss']
})
export class VCDSpecComponent extends StepFormDirective implements OnInit {

    APP_ROUTES: Routes = APP_ROUTES;

    connected: boolean = false;
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;

    subscription: Subscription;

    uploadStatus: boolean = false;

    private vcdAddress;
    private vcdSysAdminUserName;
    private vcdSysAdminPasswordBase64;
    // ============ GLobal CEIP Participation ==========
    isCeipEnabled = false;

    constructor(private validationService: ValidationService,
                private apiClient: APIClient,
                private dataService: VCDDataService) {
        super();
    }

    ngOnInit() {
        super.ngOnInit();
        // ============== VCD Deatils =============================
        this.formGroup.addControl('vcdAddress', new FormControl('', [Validators.required, this.validationService.isValidIpOrFqdn(), this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('vcdSysAdminUserName', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('vcdSysAdminPasswordBase64', new FormControl('', [Validators.required]));

        // =================== Global CEIP Participation =====================
        this.formGroup.addControl('isCeipEnabled', new FormControl(false));

        /**
         *  If VCD FQDN, username or password changes, following will be reset
         * Connect Button
         */
        SupervisedField.forEach(field => {
            this.formGroup.get(field).valueChanges
                .pipe(
                    debounceTime(500),
                    distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                    takeUntil(this.unsubscribe)
                )
                .subscribe(
                    () => {
                        this.connected = false;
                        this.loadingState = ClrLoadingState.DEFAULT;
                    }
                );
            }
        );

        // ==================== NEXT Button Validations ==========================
        this.formGroup['canMoveToNext'] = () => {
            return this.formGroup.valid && this.connected;
        };

        this.subscription = this.dataService.currentInputFileStatus.subscribe(
            (uploadStatus) => this.uploadStatus = uploadStatus);
        if (this.uploadStatus) {
            /**
             * If there's a file uploaded then read following from the file and update form fiels:
             * vcdAddress
             * vcdSysAdminUserName
             * vcdSysAdminPasswordBase64
             * isCeipEnabled
             */
            this.subscription = this.dataService.currentVcdAddress.subscribe(
                (address) => this.vcdAddress = address);
            this.formGroup.get('vcdAddress').setValue(this.vcdAddress);
            this.subscription = this.dataService.currentVcdUsername.subscribe(
                (username) => this.vcdSysAdminUserName = username);
            this.formGroup.get('vcdSysAdminUserName').setValue(this.vcdSysAdminUserName);
            this.subscription = this.dataService.currentVcdPassword.subscribe(
                (password) => this.vcdSysAdminPasswordBase64 = password);
            this.formGroup.get('vcdSysAdminPasswordBase64').setValue(this.vcdSysAdminPasswordBase64);

            this.subscription = this.dataService.currentCeipParticipation.subscribe(
                (ceip) => this.isCeipEnabled = ceip);
            this.formGroup.get('isCeipEnabled').setValue(this.isCeipEnabled);
        }
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // === So that the password field doesn't get filled with ******
        this.formGroup.get('vcdSysAdminPasswordBase64').setValue('');
    }

    /**
     * @method connectVCD
     * helper method to make connection to VCD environment
     * method if VCD connection successful
     * @param vcdAddress, vcdSysAdminUserName, vcdSysAdminPasswordBase64
     */
    connectVCD() {
        this.loadingState = ClrLoadingState.LOADING;
        let data = {
            'vcdAddress': this.formGroup.get('vcdAddress').value,
            'vcdSysAdminUserName': this.formGroup.get('vcdSysAdminUserName').value,
            'vcdSysAdminPasswordBase64': this.formGroup.get('vcdSysAdminPasswordBase64').value,
        };

        this.apiClient.connectToVCD('vcd', data).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.getAVIVcdDisplayNames();
                    this.getAviNsxCloudVcdDisplayNames();
                    this.fetchT0FromVcd();
                    this.fetchSvcOrgNames();
                    this.fetchProviderVdcNames();
                    this.fetchNetworkPoolNames();
                    this.fetchStoragePoliciesFromVcd();
                    this.fetchServiceEngineGroupNamesFromVCD();

                    this.connected = true;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    this.errorNotification = null;
                } else if (data.responseType === 'ERROR') {
                    this.connected = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
                    if(data.hasOwnProperty('msg')) this.errorNotification = data.msg;
                    else this.errorNotification = 'Some Error Occurred while connecting to VCD with given credentials, please check again';
                }
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'Some Error Occurred while connecting to VCD with given credentials, please check again';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'VCD: ' + err.msg;
            } else {
                this.connected = false;
                this.loadingState = ClrLoadingState.DEFAULT;
                this.errorNotification = 'VCD: Please verify VCD Address';
            }
        });
    }

    public getAVIVcdDisplayNames() {
        let vcdData = {
            'vcdAddress': this.formGroup.get('vcdAddress').value,
            'vcdSysAdminUserName': this.formGroup.get('vcdSysAdminUserName').value,
            'vcdSysAdminPasswordBase64': this.formGroup.get('vcdSysAdminPasswordBase64').value,
        };
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


    public getAviNsxCloudVcdDisplayNames() {
        let vcdData = {
            'vcdAddress': this.formGroup.get('vcdAddress').value,
            'vcdSysAdminUserName': this.formGroup.get('vcdSysAdminUserName').value,
            'vcdSysAdminPasswordBase64': this.formGroup.get('vcdSysAdminPasswordBase64').value,
        };

        this.apiClient.listNsxtCloudVcdDisplayNames('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.nsxtCloudVcdDisplayNames = data.NSXT_CLOUD_VCD_LIST;
                    this.dataService.nsxtCloudVcdDisplayNameErrorMessage = null;
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


    public fetchT0FromVcd() {
        let vcdData = {
            'vcdAddress': this.formGroup.get('vcdAddress').value,
            'vcdSysAdminUserName': this.formGroup.get('vcdSysAdminUserName').value,
            'vcdSysAdminPasswordBase64': this.formGroup.get('vcdSysAdminPasswordBase64').value,
        };

        this.apiClient.fetchT0FromVcd('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.t0GatewayFromVcd = data.Tier0_GATEWAY_VCD;
                    this.dataService.t0GatewayFromVcdErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.t0GatewayFromVcdErrorMessage = data.msg;
                    } else {
                        this.dataService.t0GatewayFromVcdErrorMessage = 'Failed to fetch list of Tier0 Gateways from VCD';
                    }
                }
            } else {
                this.dataService.t0GatewayFromVcdErrorMessage = 'Failed to fetch list of Tier0 Gateways from VCD';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.t0GatewayFromVcdErrorMessage = err.msg;
            } else {
                this.dataService.t0GatewayFromVcdErrorMessage = 'Failed to fetch list of Tier0 Gateways from VCD';
            }
        });
    }


    public fetchSvcOrgNames() {
        let vcdData = {
            'vcdAddress': this.formGroup.get('vcdAddress').value,
            'vcdSysAdminUserName': this.formGroup.get('vcdSysAdminUserName').value,
            'vcdSysAdminPasswordBase64': this.formGroup.get('vcdSysAdminPasswordBase64').value,
        };
        this.apiClient.fetchSvcOrgNames('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.svcOrgNames = data.ORG_LIST_VCD;
                    this.dataService.svcOrgNamesErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.svcOrgNamesErrorMessage = data.msg;
                    } else {
                        this.dataService.svcOrgNamesErrorMessage = 'Failed to fetch list service organizations';
                    }
                }
            } else {
                this.dataService.svcOrgNamesErrorMessage = 'Failed to fetch list of service organizations';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.svcOrgNamesErrorMessage = err.msg;
            } else {
                this.dataService.svcOrgNamesErrorMessage = 'Failed to fetch list of service organizations';
            }
        });
    }


    public fetchProviderVdcNames() {
        let vcdData = {
            'vcdAddress': this.formGroup.get('vcdAddress').value,
            'vcdSysAdminUserName': this.formGroup.get('vcdSysAdminUserName').value,
            'vcdSysAdminPasswordBase64': this.formGroup.get('vcdSysAdminPasswordBase64').value,
        };
        this.apiClient.fetchProviderVdcNames('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.providerVDCNames = data.PVDC_LIST;
                    this.dataService.providerVDCErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.providerVDCErrorMessage = data.msg;
                    } else {
                        this.dataService.providerVDCErrorMessage = 'Failed to fetch list of Provider VDCs';
                    }
                }
            } else {
                this.dataService.providerVDCErrorMessage = 'Failed to fetch list of Provider VDCs';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.providerVDCErrorMessage = err.msg;
            } else {
                this.dataService.providerVDCErrorMessage = 'Failed to fetch list of Provider VDCs';
            }
        });
    }


    public fetchNetworkPoolNames() {
        let vcdData = {
            'vcdAddress': this.formGroup.get('vcdAddress').value,
            'vcdSysAdminUserName': this.formGroup.get('vcdSysAdminUserName').value,
            'vcdSysAdminPasswordBase64': this.formGroup.get('vcdSysAdminPasswordBase64').value,
        };
        this.apiClient.fetchNetworkPoolNames('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.networkPoolNames = data.NP_LIST;
                    this.dataService.networkPoolNamesErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.networkPoolNames = data.msg;
                    } else {
                        this.dataService.networkPoolNamesErrorMessage = 'Failed to fetch list of network pools';
                    }
                }
            } else {
                this.dataService.networkPoolNamesErrorMessage = 'Failed to fetch list of network pools';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.networkPoolNamesErrorMessage = err.msg;
            } else {
                this.dataService.networkPoolNamesErrorMessage = 'Failed to fetch list of network pools';
            }
        });
    }


    public fetchStoragePoliciesFromVcd() {
        let vcdData = {
            'vcdAddress': this.formGroup.get('vcdAddress').value,
            'vcdSysAdminUserName': this.formGroup.get('vcdSysAdminUserName').value,
            'vcdSysAdminPasswordBase64': this.formGroup.get('vcdSysAdminPasswordBase64').value,
        };
        this.apiClient.fetchStoragePoliciesFromVdc('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.storagePolicies = data.STORAGE_POLICY_LIST;
                    this.dataService.storagePolicyErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.storagePolicyErrorMessage = data.msg;
                    } else {
                        this.dataService.storagePolicyErrorMessage = 'Failed to fetch storage policies from VCD environment';
                    }
                }
            } else {
                this.dataService.storagePolicyErrorMessage = 'Failed to fetch storage policies from VCD environment';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.storagePolicyErrorMessage = err.msg;
            } else {
                this.dataService.storagePolicyErrorMessage = 'Failed to fetch storage policies from VCD environment';
            }
        });
    }


    public fetchServiceEngineGroupNamesFromVCD() {
        let vcdData = {
            'vcdAddress': this.formGroup.get('vcdAddress').value,
            'vcdSysAdminUserName': this.formGroup.get('vcdSysAdminUserName').value,
            'vcdSysAdminPasswordBase64': this.formGroup.get('vcdSysAdminPasswordBase64').value,
        };

        this.apiClient.fetchServiceEngineGroupNamesFromVCD('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.serviceEngineGroupVcdDisplayNames = data.SEG_VDC_LIST;
                    this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = data.msg;
                    } else {
                        this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = 'Failed to fetch list service engine groups from VCD';
                    }
                }
            } else {
                this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = 'Failed to fetch list of service engine groups from VCD';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = err.msg;
            } else {
                this.dataService.serviceEngineGroupVcdDisplayNameErrorMessage = 'Failed to fetch list of service engine groups from VCD';
            }
        });
    }


    /**
      * @method getDisabled
      * helper method to get if connect btn should be disabled
      */
     getDisabled(): boolean {
        return !(this.formGroup.get('vcdAddress').valid && this.formGroup.get('vcdSysAdminUserName').valid && this.formGroup.get('vcdSysAdminPasswordBase64').valid);
    }

}
