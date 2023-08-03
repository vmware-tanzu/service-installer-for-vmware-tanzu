/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
/**
 * Angular Modules
 */
import { Component, OnInit, Input } from '@angular/core';
import {
    Validators,
    FormControl
} from '@angular/forms';
import { Netmask } from 'netmask';

/**
 * App imports
 */
import { PROVIDERS, Providers } from 'src/app/shared/constants/app.constants';
import { StepFormDirective } from 'src/app/views/landing/wizard/shared/step-form/step-form';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { Subscription } from "rxjs";
import { VMCDataService } from "src/app/shared/service/vmc-data.service";

@Component({
    selector: 'app-tkg-workload-nw-setting-step',
    templateUrl: './tkg-workload-data.component.html',
    styleUrls: ['./tkg-workload-data.component.scss']
})
export class TKGWorkloadNetworkSettingComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    @Input() errorNotification: string;
    PROVIDERS: Providers = PROVIDERS;
    displayForm = false;
    networks = [];
    subscription: Subscription;
    dhcpError = false;
    dhcpErrorMsg = '';
    serviceError = false;
    serviceErrorMsg = '';
    segmentError = false;
    segmentErrorMsg = 'TKG Workload Data Segment not found, please update the segment value from the drop-down list';

    private uploadStatus = false;

    private gatewayCidr: string;
    private dhcpStart: string;
    private dhcpEnd: string;
    private serviceStart: string;
    private serviceEnd: string;

    constructor(private validationService: ValidationService,
        public apiClient: APIClient,
        private dataService: VMCDataService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'workloadClusterSettings',
            new FormControl(false)
        );
        this.formGroup.addControl(
            'TKGDataGatewayCidr',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'TKGDataDhcpStartRange',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'TKGDataDhcpEndRange',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'TKGWrkServiceStartRange',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'TKGWrkServiceEndRange',
            new FormControl('', [])
        );

        this.formGroup['canMoveToNext'] = () => {
            this.toggleWorkloadClusterSettings();
            this.onTkgWrkDataValidateClick();
            if (this.apiClient.workloadDataSettings){
                return (this.formGroup.valid && this.apiClient.TkgWrkDataNwValidated);
            } else {
                return this.formGroup.valid;
            }
        };
        setTimeout(_ => {
            if(this.apiClient.workloadDataSettings) {
                this.resurrectField('TKGDataGatewayCidr',[
                    Validators.required,
                    this.validationService.isValidIpNetworkSegment(),
                    this.validationService.noWhitespaceOnEnds()
                ], this.formGroup.get('TKGDataGatewayCidr').value);
                this.resurrectField('TKGDataDhcpStartRange',[
                    Validators.required,
                    this.validationService.isValidIp(),
                    this.validationService.noWhitespaceOnEnds()
                ], this.formGroup.get('TKGDataDhcpStartRange').value);
                this.resurrectField('TKGDataDhcpEndRange',[
                    Validators.required,
                    this.validationService.isValidIp(),
                    this.validationService.noWhitespaceOnEnds()
                ], this.formGroup.get('TKGDataDhcpEndRange').value);
                this.resurrectField('TKGWrkServiceStartRange', [
                    Validators.required,
                    this.validationService.isValidIp(),
                    this.validationService.noWhitespaceOnEnds()
                ], this.formGroup.get('TKGWrkServiceStartRange').value);
                this.resurrectField('TKGWrkServiceEndRange', [
                    Validators.required,
                    this.validationService.isValidIp(),
                    this.validationService.noWhitespaceOnEnds()
                ], this.formGroup.get('TKGWrkServiceEndRange').value);

                this.formGroup.get('TKGDataGatewayCidr').valueChanges.subscribe(
                    () => this.apiClient.TkgWrkDataNwValidated = false);
                this.formGroup.get('TKGDataDhcpStartRange').valueChanges.subscribe(
                    () => this.apiClient.TkgWrkDataNwValidated = false);
                this.formGroup.get('TKGDataDhcpEndRange').valueChanges.subscribe(
                    () => this.apiClient.TkgWrkDataNwValidated = false);
                this.formGroup.get('TKGWrkServiceStartRange').valueChanges.subscribe(
                    () => this.apiClient.TkgWrkDataNwValidated = false);
                this.formGroup.get('TKGWrkServiceEndRange').valueChanges.subscribe(
                    () => this.apiClient.TkgWrkDataNwValidated = false);
                this.subscription = this.dataService.currentInputFileStatus.subscribe(
                    (uploadStatus) => this.uploadStatus = uploadStatus);

                if (this.uploadStatus) {
                    this.subscription = this.dataService.currentTkgWrkDataGateway.subscribe(
                        (gateway) => this.gatewayCidr = gateway);
                    this.formGroup.get('TKGDataGatewayCidr').setValue(this.gatewayCidr);
                    this.subscription = this.dataService.currentTkgWrkDataDhcpStart.subscribe(
                        (dhcpStart) => this.dhcpStart = dhcpStart);
                    this.formGroup.get('TKGDataDhcpStartRange').setValue(this.dhcpStart);
                    this.subscription = this.dataService.currentTkgWrkDataDhcpEnd.subscribe(
                        (dhcpEnd) => this.dhcpEnd = dhcpEnd);
                    this.formGroup.get('TKGDataDhcpEndRange').setValue(this.dhcpEnd);

                    this.subscription = this.dataService.currentTkgWrkDataServiceStart.subscribe(
                        (serviceStart) => this.serviceStart = serviceStart);
                    this.formGroup.get('TKGWrkServiceStartRange').setValue(this.serviceStart);
                    this.subscription = this.dataService.currentTkgWrkDataServiceEnd.subscribe(
                        (serviceEnd) => this.serviceEnd = serviceEnd);
                    this.formGroup.get('TKGWrkServiceEndRange').setValue(this.serviceEnd);

                    if (this.gatewayCidr!=='') {
                        const block = new Netmask(this.gatewayCidr);
                        if ( (this.dhcpStart!=='') && (this.dhcpEnd!=='') ) {
                            if(block.contains(this.dhcpStart) && block.contains(this.dhcpEnd)) {
                                this.dhcpError = false;
                            } else if (!block.contains(this.dhcpStart) && !block.contains(this.dhcpEnd)) {
                                this.dhcpErrorMsg = 'DHCP Start and End IP are out of the provided subnet';
                                this.dhcpError = true;
                            } else if (!block.contains(this.dhcpStart)) {
                                this.dhcpErrorMsg = 'DHCP Start IP is out of the provided subnet.';
                                this.dhcpError = true;
                            } else if (!block.contains(this.dhcpEnd)) {
                                this.dhcpErrorMsg = 'DHCP End IP is out of the provided subnet';
                                this.dhcpError = true;
                            }
                        }
                        if ( (this.serviceStart!=='') && (this.serviceEnd!=='') ) {
                            if (block.contains(this.serviceStart) && block.contains(this.serviceEnd)) {
                                this.serviceError = false;
                            } else if (!block.contains(this.dhcpStart) && !block.contains(this.dhcpEnd)) {
                                this.serviceErrorMsg = 'Service Start and End IP are out of the provided subnet';
                                this.serviceError = true;
                            } else if (!block.contains(this.serviceStart)) {
                                this.serviceErrorMsg = 'Service Start IP is out of the provided subnet';
                                this.serviceError = true;
                            } else if (!block.contains(this.serviceEnd)) {
                                this.serviceErrorMsg = 'Service End IP is out of the provided subnet';
                                this.serviceError = true;
                            }
                        }
                        if (!(this.dhcpError) && !(this.serviceError)) {
                            this.apiClient.TkgWrkDataNwValidated = true;
                        } else {
                            this.apiClient.TkgWrkDataNwValidated = false;
                        }
                    }
                }
            }

            });
        this.networks = this.apiClient.networks;
    }

    setSavedDataAfterLoad() {
        if (this.hasSavedData()) {
            super.setSavedDataAfterLoad();
            if (!this.uploadStatus) {
            }
        }
    }

    onTkgWrkDataValidateClick() {
        if (this.apiClient.workloadDataSettings){
            if (this.formGroup.get('TKGDataGatewayCidr').valid &&
                this.formGroup.get('TKGDataDhcpStartRange').valid &&
                this.formGroup.get('TKGDataDhcpEndRange').valid) {
                const gatewayIp = this.formGroup.get('TKGDataGatewayCidr').value;
                const block = new Netmask(gatewayIp);
                const dhcpStart = this.formGroup.get('TKGDataDhcpStartRange').value;
                const dhcpEnd = this.formGroup.get('TKGDataDhcpEndRange').value;
                if(block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                    this.dhcpError = false;
                } else if (!block.contains(dhcpStart) && !block.contains(dhcpEnd)) {
                    this.dhcpErrorMsg = 'DHCP Start and End IP are out of the provided subnet';
                    this.dhcpError = true;
                } else if (!block.contains(dhcpStart)) {
                    this.dhcpErrorMsg = 'DHCP Start IP is out of the provided subnet';
                    this.dhcpError = true;
                } else if (!block.contains(dhcpEnd)) {
                    this.dhcpErrorMsg = 'DHCP End IP is out of the provided subnet';
                    this.dhcpError = true;
                }
            }
            if (this.formGroup.get('TKGDataGatewayCidr').valid &&
                this.formGroup.get('TKGWrkServiceStartRange').valid &&
                this.formGroup.get('TKGWrkServiceEndRange').valid) {
                const gatewayIp = this.formGroup.get('TKGDataGatewayCidr').value;
                const block = new Netmask(gatewayIp);
                const serviceStart = this.formGroup.get('TKGWrkServiceStartRange').value;
                const serviceEnd = this.formGroup.get('TKGWrkServiceEndRange').value;
                if (block.contains(serviceStart) && block.contains(serviceEnd)) {
                    this.serviceError = false;
                } else if (!block.contains(serviceStart) && !block.contains(serviceEnd)) {
                    this.serviceErrorMsg = 'Service Start and End IP are out of the provided subnet';
                    this.serviceError = true;
                } else if (!block.contains(serviceStart)) {
                    this.serviceErrorMsg = 'Service Start IP is out of the provided subnet';
                    this.serviceError = true;
                } else if (!block.contains(serviceEnd)) {
                    this.serviceErrorMsg = 'Service End IP is out of the provided subnet';
                    this.serviceError = true;
                }
            }

            if (!(this.dhcpError) && !(this.serviceError)) {
                this.apiClient.TkgWrkDataNwValidated = true;
            } else {
                this.apiClient.TkgWrkDataNwValidated = false;
            }
        }
    }

    toggleWorkloadClusterSettings() {
        const mandatoryWorkloadFields = [
            'TKGDataGatewayCidr',
            'TKGDataDhcpStartRange',
            'TKGDataDhcpEndRange',
            'TKGWrkServiceStartRange',
            'TKGWrkServiceEndRange',
        ];

        if (this.formGroup.value['workloadClusterSettings']) {
            this.apiClient.workloadDataSettings = true;
            this.resurrectField('TKGDataGatewayCidr', [Validators.required, this.validationService.isValidIpNetworkSegment(), this.validationService.noWhitespaceOnEnds()], this.formGroup.value['TKGDataGatewayCidr']);
            this.resurrectField('TKGDataDhcpStartRange', [Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIp()], this.formGroup.value['TKGDataDhcpStartRange']);
            this.resurrectField('TKGDataDhcpEndRange', [Validators.required, this.validationService.isValidIp(), this.validationService.noWhitespaceOnEnds()], this.formGroup.value['TKGDataDhcpEndRange']);

            this.resurrectField('TKGWrkServiceStartRange', [Validators.required, this.validationService.isValidIp(), this.validationService.noWhitespaceOnEnds()], this.formGroup.value['TKGWrkServiceStartRange']);
            this.resurrectField('TKGWrkServiceEndRange', [Validators.required, this.validationService.isValidIp(), this.validationService.noWhitespaceOnEnds()], this.formGroup.value['TKGWrkServiceEndRange']);
        } else {
            this.apiClient.workloadDataSettings = false;
            mandatoryWorkloadFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

}
