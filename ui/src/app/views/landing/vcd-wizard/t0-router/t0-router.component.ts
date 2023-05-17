/*
* Copyright 2021 VMware, Inc
* SPDX-License-Identifier: BSD-2-Clause
*/
/**
 * Angular Modules
 */
import { Component, Input, OnInit } from '@angular/core';
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
 
 
@Component({
    selector: 'app-t0-router-step',
    templateUrl: './t0-router.component.html',
    styleUrls: ['./t0-router.component.scss'],
})
export class T0GatewayComponent extends StepFormDirective implements OnInit {
    @Input() t0GatewayFromNsxt: [];
    @Input() InputTier0GatewayName: [];

    private importTier0 = false;
    // ======================== TIER 0 ROUTERS fetched from NSXT ===========================
    tier0Routers: any = [];
    private tier0Router;
    fetchT0FromNSXT = false;

    private tier0GatewayName; //VCD Display name for T0 Gateway
    tier0GatewayNames: any = [];
    fetchT0FromVCD = false;

    private extNetGatewayCIDR;
    private extNetStartIP;
    private extNetEndIP;

    extNetVerifiedErrorMsg = null;
    extNetVerified = false;

    // =========================== COMMON PROPERTIES ========================================
    private uploadStatus;
    subscription: Subscription;
 
    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                private apiClient: APIClient,
                public dataService: VCDDataService) {

        super();
    }
 
    ngOnInit() {
        super.ngOnInit();
        
        // =============================== T0 Router to be imported from NSXT ===========================
        this.formGroup.addControl('importTier0', new FormControl(false));
        this.formGroup.addControl('tier0Router', new FormControl('', []));
        this.formGroup.addControl('tier0GatewayName', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('extNetGatewayCIDR', new FormControl('', []));
        this.formGroup.addControl('extNetStartIP', new FormControl('', []));
        this.formGroup.addControl('extNetEndIP', new FormControl('', []));
 

        this.formGroup['canMoveToNext'] = () => {
            this.toggleImportTier0();
            if(this.formGroup.get('importTier0').value) {
                this.dataService.t0StartAddress = this.formGroup.get('extNetStartIP').value;
                this.dataService.t0EndAddress = this.formGroup.get('extNetEndIP').value;
                this.ipGatewayCheck();
                return this.formGroup.valid && this.extNetVerified;
            } else {
                this.fetchIpRangesForTier0();
                return this.formGroup.valid;
            }
        };
 
        setTimeout(_ => {
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentImportTier0.subscribe((importT0) => this.importTier0 = importT0)
                this.formGroup.get('importTier0').setValue(this.importTier0);
                if(this.importTier0) {
                    this.subscription = this.dataService.currentTier0Router.subscribe((router) => this.tier0Router = router);
                    if(this.dataService.t0GatewayFromNsxt.indexOf(this.tier0Router) !== -1) {
                        this.formGroup.get('tier0Router').setValue(this.tier0Router);
                    }
                    this.subscription = this.dataService.currentTier0GatewayName.subscribe((gw) => this.tier0GatewayName = gw);
                    this.formGroup.get('tier0GatewayName').setValue(this.tier0GatewayName);

                    this.subscription = this.dataService.currentExtNetgatewayCIDR.subscribe((cidr) => this.extNetGatewayCIDR = cidr);
                    this.formGroup.get('extNetGatewayCIDR').setValue(this.extNetGatewayCIDR);

                    this.subscription = this.dataService.currentExtNetStartIP.subscribe((startIp) => this.extNetStartIP = startIp);
                    this.formGroup.get('extNetStartIP').setValue(this.extNetStartIP);

                    this.subscription = this.dataService.currentExtNetEndIP.subscribe((endIp) => this.extNetEndIP = endIp);
                    this.formGroup.get('extNetEndIP').setValue(this.extNetEndIP);
                } else {
                    this.subscription = this.dataService.currentTier0GatewayName.subscribe((gw) => this.tier0GatewayName = gw);
                    if(this.dataService.t0GatewayFromVcd.indexOf(this.tier0GatewayName) !== -1) {
                        this.formGroup.get('tier0GatewayName').setValue(this.tier0GatewayName);
                    }
                }
                this.toggleImportTier0();
            }
        });
    }
 
    ngOnChanges() {
        if(this.dataService.t0GatewayFromNsxt.length !== 0 && this.dataService.t0GatewayFromNsxt.indexOf(this.tier0Router) !== -1) {
            if(this.formGroup.get('tier0Router')) this.formGroup.get('tier0Router').setValue(this.tier0Router);
        }
        if(!this.dataService.importTier0Nsxt) {
            if(this.dataService.t0GatewayFromVcd.length !== 0 && this.dataService.t0GatewayFromVcd.indexOf(this.tier0GatewayName) !== -1) {
                if(this.formGroup.get('tier0GatewayName')) this.formGroup.get('tier0GatewayName').setValue(this.tier0GatewayName);
            }
        }
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
    }


    public toggleImportTier0(){
        const importTier0Fields = [
            'tier0Router',
            'extNetGatewayCIDR',
            'extNetStartIP',
            'extNetEndIP',
        ];
        if(this.formGroup.get('importTier0').value) {
            this.dataService.importTier0Nsxt = true;
            this.resurrectField('tier0Router', [
                Validators.required,
            ], this.formGroup.value['tier0Router']);
            this.resurrectField('tier0GatewayName', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
            ], this.formGroup.value['tier0GatewayName']);
            this.resurrectField('extNetGatewayCIDR', [
                Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIpNetworkSegment(),
            ], this.formGroup.value['extNetGatewayCIDR']);
            this.resurrectField('extNetStartIP', [
                Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIp(),
            ], this.formGroup.value['extNetStartIP']);
            this.resurrectField('extNetEndIP', [
                Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIp(),
            ], this.formGroup.value['extNetEndIP']);           
        } else {
            this.dataService.importTier0Nsxt = false;
            importTier0Fields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }


    public fetchT0FromNsxt() {
        let nsxtData = {
            "nsxtAddress": "",
            "nsxtUser": "",
            "nsxtUserPasswordBase64": "",
        };
        this.dataService.currentNsxtAddress.subscribe((address) => nsxtData['nsxtAddress'] = address);
        this.dataService.currentNsxtUser.subscribe((username) => nsxtData['nsxtUser'] = username);
        this.dataService.currentNsxtUserPasswordBase64.subscribe((password) => nsxtData['nsxtUserPasswordBase64'] = password);

        this.apiClient.fetchT0FromNsxt('vcd', nsxtData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.t0GatewayFromNsxt = data.Tier0_GATEWAY_NSX;
                    this.dataService.t0GatewayFromNsxtErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.t0GatewayFromNsxtErrorMessage = data.msg;
                    } else {
                        this.dataService.t0GatewayFromNsxtErrorMessage = 'Failed to fetch list of Tier0 Routers from NSXT';
                    }
                }
            } else {
                this.dataService.t0GatewayFromNsxtErrorMessage = 'Failed to fetch list of Tier0 Routers from NSXT';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.t0GatewayFromNsxtErrorMessage = err.msg;
            } else {
                this.dataService.t0GatewayFromNsxtErrorMessage = 'Failed to fetch list of Tier0 Routers from NSXT';
            }
        });
    }

    public fetchT0FromVcd() {
        let vcdData = {
            'vcdAddress': "",
            'vcdSysAdminUserName': "",
            'vcdSysAdminPasswordBase64': "",
        };
        this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
        this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
        this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);

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


    public fetchIpRangesForTier0() {
        if(!this.dataService.importTier0Nsxt && this.formGroup.get('tier0GatewayName').value !== '') {
            let vcdData = {
                'vcdAddress': "",
                'vcdSysAdminUserName': "",
                'vcdSysAdminPasswordBase64': "",
                'tier0GatewayName': this.formGroup.get('tier0GatewayName').value,
            };
            this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
            this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
            this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);
    
            this.apiClient.fetchIpRangesForSelectedTier0('vcd', vcdData).subscribe((data: any) => {
                if (data && data !== null) {
                    if (data.responseType === 'SUCCESS') {
                        this.dataService.t0StartAddress = data.T0_GATEWAY_START_IP;
                        this.dataService.t0EndAddress = data.T0_GATEWAY_END_IP;
                        this.dataService.t0GatewayCidr = data.T0_GATEWAY_NW_CIDR;
                        this.dataService.tier0IpRangeErrorMessage = null;
                    } else if (data.responseType === 'ERROR') {
                        if (data.hasOwnProperty('msg')) {
                            this.dataService.tier0IpRangeErrorMessage = data.msg;
                        } else {
                            this.dataService.tier0IpRangeErrorMessage = 'Failed to fetch IP ranges for selected Tier0 Gateway: ' + vcdData['tier0GatewayName'];
                        }
                    }
                } else {
                    this.dataService.t0GatewayFromVcdErrorMessage = 'Failed to fetch IP ranges for selected Tier0 Gateway: ' + vcdData['tier0GatewayName'];
                }
            }, (err: any) => {
                if (err.responseType === 'ERROR') {
                    this.dataService.t0GatewayFromVcdErrorMessage = err.msg;
                } else {
                    this.dataService.t0GatewayFromVcdErrorMessage = 'Failed to fetch IP ranges for selected Tier0 Gateway: ' + vcdData['tier0GatewayName'];
                }
            });
        }
    }


    public ipGatewayCheck() {
        if (this.formGroup.get('extNetGatewayCIDR').valid &&
            this.formGroup.get('extNetStartIP').valid &&
            this.formGroup.get('extNetEndIP').valid) {
            
            if(this.formGroup.get('extNetGatewayCIDR').value !== '' && this.formGroup.get('extNetGatewayCIDR').value !== '' && this.formGroup.get('extNetGatewayCIDR').value !== '') {
                const gatewayIp = this.formGroup.get('extNetGatewayCIDR').value;
                const dhcpStart = this.formGroup.get('extNetStartIP').value;
                const dhcpEnd = this.formGroup.get('extNetEndIP').value;
                const block = new Netmask(gatewayIp);
                if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                    this.extNetVerified = true;
                    this.extNetVerifiedErrorMsg = null;
                } else {
                    let str='';
                    if (!block.contains(dhcpStart)) {
                        str = 'Start IP, ';
                    }
                    if (!block.contains(dhcpEnd)) {
                        str = str + 'End IP, ';
                    }
                    this.extNetVerifiedErrorMsg = str + ' outside of the provided subnet.';
                    this.extNetVerified = false;
                }
            }
        }
    }
}
 