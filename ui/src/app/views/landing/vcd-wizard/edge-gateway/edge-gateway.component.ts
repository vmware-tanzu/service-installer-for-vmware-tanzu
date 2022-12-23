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
    selector: 'app-svc-org-edge-gw-step',
    templateUrl: './edge-gateway.component.html',
    styleUrls: ['./edge-gateway.component.scss'],
})
export class EdgeGatewayComponent extends StepFormDirective implements OnInit {

    @Input() InputTier0Start: string;
    @Input() InputTier0End: string;

    private tier1GatewayName;
    private isDedicated = false;
    private primaryIp;
    private ipAllocationStartIP;
    private ipAllocationEndIP;

    ipRangeValidated = false;
    staticIpRangeValidated = false;
    staticIpRangeErrorMessage;

    private networkName;
    private gatewayCIDR;
    private staticIpPoolStartAddress;
    private staticIpPoolEndAddress;
    private primaryDNS;
    private secondaryDNS;
    private dnsSuffix;
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
        this.formGroup.addControl('tier1GatewayName', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('isDedicated', new FormControl(false));
        this.formGroup.addControl('primaryIp', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIp()]));
        this.formGroup.addControl('ipAllocationStartIP', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIp()]));
        this.formGroup.addControl('ipAllocationEndIP', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIp()]));
  
        this.formGroup.addControl('t0Start', new FormControl('', []));
        this.formGroup.addControl('t0End', new FormControl('', []));

        this.formGroup.addControl('networkName', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('gatewayCIDR', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIpNetworkSegment()]));
        this.formGroup.addControl('staticIpPoolStartAddress', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIp()]));
        this.formGroup.addControl('staticIpPoolEndAddress', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIp()]));
        this.formGroup.addControl('primaryDNS', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('secondaryDNS', new FormControl('', [this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('dnsSuffix', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));

        this.formGroup['canMoveToNext'] = () => {
            this.ipGatewayCheck();
            this.staticIpGatewayCheck();
            return this.formGroup.valid && this.ipRangeValidated && this.staticIpRangeValidated;
        };
 
         this.formGroup.get('primaryIp').valueChanges.subscribe(() => this.ipRangeValidated = false);
        this.formGroup.get('ipAllocationStartIP').valueChanges.subscribe(() => this.ipRangeValidated = false);
        this.formGroup.get('ipAllocationEndIP').valueChanges.subscribe(() => this.ipRangeValidated = false);
  
        setTimeout(_ => {
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentTier1Gatewayname.subscribe((gw) => this.tier1GatewayName = gw);
                this.formGroup.get('tier1GatewayName').setValue(this.tier1GatewayName);

                this.subscription = this.dataService.currentIsDedicated.subscribe((dedicated) => this.isDedicated = dedicated);
                this.formGroup.get('isDedicated').setValue(this.isDedicated);

                this.subscription = this.dataService.currentPrimaryIp.subscribe((ip) => this.primaryIp = ip);
                this.formGroup.get('primaryIp').setValue(this.primaryIp);

                this.subscription = this.dataService.currentIpAllocationStartIP.subscribe((ip) => this.ipAllocationStartIP = ip);
                this.formGroup.get('ipAllocationStartIP').setValue(this.ipAllocationStartIP);

                this.subscription = this.dataService.currentIpAllocationEndIP.subscribe((ip) => this.ipAllocationEndIP = ip);
                this.formGroup.get('ipAllocationEndIP').setValue(this.ipAllocationEndIP);

                this.subscription = this.dataService.currentNetworkName.subscribe((name) => this.networkName = name);
                this.formGroup.get('networkName').setValue(this.networkName);

                this.subscription = this.dataService.currentGatewayCIDR.subscribe((cidr) => this.gatewayCIDR = cidr);
                this.formGroup.get('gatewayCIDR').setValue(this.gatewayCIDR);

                this.subscription = this.dataService.currentStaticIpPoolstartAddress.subscribe((start) => this.staticIpPoolStartAddress = start);
                this.formGroup.get('staticIpPoolStartAddress').setValue(this.staticIpPoolStartAddress);

                this.subscription = this.dataService.currentStaticIpPoolendAddress.subscribe((end) => this.staticIpPoolEndAddress = end);
                this.formGroup.get('staticIpPoolEndAddress').setValue(this.staticIpPoolEndAddress);

                this.subscription = this.dataService.currentPrimaryDNS.subscribe((primary) => this.primaryDNS = primary);
                this.formGroup.get('primaryDNS').setValue(this.primaryDNS);

                this.subscription = this.dataService.currentSecondaryDNS.subscribe((secondary) => this.secondaryDNS = secondary);
                this.formGroup.get('secondaryDNS').setValue(this.secondaryDNS);

                this.subscription = this.dataService.currentDnsSuffix.subscribe((suff) => this.dnsSuffix = suff);
                this.formGroup.get('dnsSuffix').setValue(this.dnsSuffix);
                this.ipGatewayCheck();
                this.staticIpGatewayCheck();
            }
            this.formGroup.get('t0Start').setValue(this.dataService.t0StartAddress);
            this.formGroup.get('t0Start').disable();
            this.formGroup.get('t0End').setValue(this.dataService.t0EndAddress);
            this.formGroup.get('t0End').disable();
        });
    }
  
    ngOnChanges() {
        // console.log("NG ON CHANGES");
        // console.log(this.dataService.t0StartAddress);
        // console.log(this.dataService.t0EndAddress);
        if(this.formGroup.get('t0Start')) {
            this.formGroup.get('t0Start').setValue(this.dataService.t0StartAddress);
            this.formGroup.get('t0Start').disable();
        }
        if(this.formGroup.get('t0End')) {
            this.formGroup.get('t0End').setValue(this.dataService.t0EndAddress);
            this.formGroup.get('t0End').disable();
        }
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
    }
 
 
    public ipGatewayCheck() {
        if (this.formGroup.get('primaryIp').valid &&
            this.formGroup.get('ipAllocationStartIP').valid &&
            this.formGroup.get('ipAllocationEndIP').valid) 
        {
            if(this.formGroup.get('primaryIp').value !== '' && this.formGroup.get('ipAllocationStartIP').value !== '' && this.formGroup.get('ipAllocationEndIP').value!==''){

                const primaryIp = this.formGroup.get('primaryIp').value;
                const ipAllocationStartIP = this.formGroup.get('ipAllocationStartIP').value;
                const ipAllocationEndIP = this.formGroup.get('ipAllocationEndIP').value;
                let gatewayIp;
                let block = null;

                if(this.dataService.t0GatewayCidr !== null) {
                    gatewayIp = this.dataService.t0GatewayCidr;
                    block = new Netmask(gatewayIp);

                    if (block.contains(ipAllocationStartIP) && block.contains(ipAllocationEndIP) && block.contains(primaryIp)) {
                        this.ipRangeValidated = true;
                        this.errorNotification = null;
                    } else {
                        let str='';
                        if (!block.contains(primaryIp)) {
                            str = 'Primary IP, ';
                        }
                        if (!block.contains(ipAllocationStartIP)) {
                            str = str + 'Start IP, ';
                        }
                        if (!block.contains(ipAllocationEndIP)) {
                            str = str + 'End IP, ';
                        }
                        this.errorNotification = str + ' outside of the provided subnet for Tier-0 Gateway - ' + gatewayIp;
                        this.ipRangeValidated = false;
                    }
                }
            }
        }
    }

    public staticIpGatewayCheck() {
        if (this.formGroup.get('gatewayCIDR').valid &&
            this.formGroup.get('staticIpPoolStartAddress').valid &&
            this.formGroup.get('staticIpPoolEndAddress').valid) 
        {
            if(this.formGroup.get('gatewayCIDR').value !== '' && this.formGroup.get('staticIpPoolStartAddress').value !== '' && this.formGroup.get('staticIpPoolEndAddress').value !== ''){

                const gatewayCIDR = this.formGroup.get('gatewayCIDR').value;
                const staticIpPoolStartAddress = this.formGroup.get('staticIpPoolStartAddress').value;
                const staticIpPoolEndAddress = this.formGroup.get('staticIpPoolEndAddress').value;

                const block = new Netmask(gatewayCIDR);
                if (block.contains(staticIpPoolStartAddress) && block.contains(staticIpPoolStartAddress)) {
                    this.staticIpRangeValidated = true;
                    this.staticIpRangeErrorMessage = '';
                } else {
                    let str='';
                    if (!block.contains(staticIpPoolStartAddress)) {
                        str = 'Static Pool Start IP, ';
                    }
                    if (!block.contains(staticIpPoolEndAddress)) {
                        str = str + 'Static Pool End IP ';
                    }
                    this.staticIpRangeErrorMessage = str + ' are outside of the provided subnet: ' + gatewayCIDR;
                    this.ipRangeValidated = false;
                }
            }
        }
    }
}
  