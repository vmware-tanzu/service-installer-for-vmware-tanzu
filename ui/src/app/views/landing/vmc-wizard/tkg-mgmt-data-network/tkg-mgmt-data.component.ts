import { TkgEventType } from 'src/app/shared/service/Messenger';
/**
 * Angular Modules
 */
import { Component, OnInit, Input } from '@angular/core';
import {
    Validators,
    FormControl
} from '@angular/forms';
import { Netmask } from 'netmask';
import {ClrLoadingState} from '@clr/angular';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';

/**
 * App imports
 */
import { PROVIDERS, Providers } from '../../../../shared/constants/app.constants';
import { NodeType, vSphereNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
// import { KUBE_VIP, NSX_ADVANCED_LOAD_BALANCER } from '../../wizard/shared/components/steps/load-balancer/load-balancer-step.component';
import Broker from 'src/app/shared/service/broker';
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import {Subscription} from "rxjs";
import {VMCDataService} from "../../../../shared/service/vmc-data.service";

@Component({
    selector: 'app-tkg-mgmt-nw-setting-step',
    templateUrl: './tkg-mgmt-data.component.html',
    styleUrls: ['./tkg-mgmt-data.component.scss']
})
export class TKGMgmtNetworkSettingComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    @Input() errorNotification: string;

    PROVIDERS: Providers = PROVIDERS;
    networks = [];
    subscription: Subscription;
    validated: boolean = false;

    dhcpError = false;
    dhcpErrorMsg = '';
    serviceError = false;
    serviceErrorMsg = '';
    segmentError = false;
    segmentErrorMsg = 'TKG Management Data Segment not found, please update the segment value from the drop-down list';
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    private uploadStatus = false;

    private gatewayCidr: string;
    private dhcpStart: string;
    private dhcpEnd: string;
    private serviceStart: string;
    private serviceEnd: string;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private dataService: VMCDataService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();

        this.formGroup.addControl('TKGMgmtGatewayCidr',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('TKGMgmtDhcpStartRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('TKGMgmtDhcpEndRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('TKGMgmtServiceStartRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('TKGMgmtServiceEndRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );

        this.formGroup['canMoveToNext'] = () => {
            return (this.formGroup.valid && this.apiClient.TkgMgmtDataNwValidated);
        };

        setTimeout(_ => {
            this.resurrectField('TKGMgmtGatewayCidr',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('TKGMgmtGatewayCidr').value);
            this.resurrectField('TKGMgmtDhcpStartRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('TKGMgmtDhcpStartRange').value);
            this.resurrectField('TKGMgmtDhcpEndRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('TKGMgmtDhcpEndRange').value);
            this.resurrectField('TKGMgmtServiceStartRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('TKGMgmtServiceStartRange').value);
            this.resurrectField('TKGMgmtServiceEndRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('TKGMgmtServiceEndRange').value);
            // Track change in form control values

            this.formGroup.get('TKGMgmtGatewayCidr').valueChanges.subscribe(
                () => this.apiClient.TkgMgmtDataNwValidated = false);
            this.formGroup.get('TKGMgmtDhcpStartRange').valueChanges.subscribe(
                () => this.apiClient.TkgMgmtDataNwValidated = false);
            this.formGroup.get('TKGMgmtDhcpEndRange').valueChanges.subscribe(
                () => this.apiClient.TkgMgmtDataNwValidated = false);
            this.formGroup.get('TKGMgmtServiceStartRange').valueChanges.subscribe(
                () => this.apiClient.TkgMgmtDataNwValidated = false);
            this.formGroup.get('TKGMgmtServiceEndRange').valueChanges.subscribe(
                () => this.apiClient.TkgMgmtDataNwValidated = false);
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {

                this.subscription = this.dataService.currentTkgMgmtDataGateway.subscribe(
                    (gateway) => this.gatewayCidr = gateway);
                this.formGroup.get('TKGMgmtGatewayCidr').setValue(this.gatewayCidr);
                this.subscription = this.dataService.currentTkgMgmtDataDhcpStart.subscribe(
                    (dhcpStart) => this.dhcpStart = dhcpStart);
                this.formGroup.get('TKGMgmtDhcpStartRange').setValue(this.dhcpStart);
                this.subscription = this.dataService.currentTkgMgmtDataDhcpEnd.subscribe(
                    (dhcpEnd) => this.dhcpEnd = dhcpEnd);
                this.formGroup.get('TKGMgmtDhcpEndRange').setValue(this.dhcpEnd);

                this.subscription = this.dataService.currentTkgMgmtDataServiceStart.subscribe(
                    (serviceStart) => this.serviceStart = serviceStart);
                this.formGroup.get('TKGMgmtServiceStartRange').setValue(this.serviceStart);
                this.subscription = this.dataService.currentTkgMgmtDataServiceEnd.subscribe(
                    (serviceEnd) => this.serviceEnd = serviceEnd);
                this.formGroup.get('TKGMgmtServiceEndRange').setValue(this.serviceEnd);

                if (this.gatewayCidr!=='') {
                    const block = new Netmask(this.gatewayCidr);
                    if ((this.dhcpStart!=='') && (this.dhcpEnd!=='')) {
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
                        this.apiClient.TkgMgmtDataNwValidated = true;
                    } else {
                        this.apiClient.TkgMgmtDataNwValidated = false;
                    }
                }

            }
            });
    }

    setSavedDataAfterLoad() {
        if (this.hasSavedData()) {
            super.setSavedDataAfterLoad();
        }
    }

    getDisabled() {
        if(this.formGroup.get('TKGMgmtGatewayCidr').valid &&
            this.formGroup.get('TKGMgmtDhcpStartRange').valid &&
            this.formGroup.get('TKGMgmtDhcpEndRange').valid) {
                return true;
            } else {
                return false;
            }
    }

     onTkgMgmtDataValidateClick() {

        if(this.formGroup.get('TKGMgmtGatewayCidr').valid &&
            this.formGroup.get('TKGMgmtDhcpStartRange').valid &&
            this.formGroup.get('TKGMgmtDhcpEndRange').valid) {
            const gatewayIp = this.formGroup.get('TKGMgmtGatewayCidr').value;
            const block = new Netmask(gatewayIp);
            const dhcpStart = this.formGroup.get('TKGMgmtDhcpStartRange').value;
            const dhcpEnd = this.formGroup.get('TKGMgmtDhcpEndRange').value;
            if(block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                this.dhcpError = false;
            } else if (!block.contains(dhcpStart) && !block.contains(dhcpEnd)) {
                this.dhcpErrorMsg = 'DHCP Start and End IP are out of the provided subnet';
                this.dhcpError = true;
            } else if (!block.contains(dhcpStart)) {
                this.dhcpErrorMsg = 'DHCP Start IP is out of the provided subnet.';
                this.dhcpError = true;
            } else if (!block.contains(dhcpEnd)) {
                this.dhcpErrorMsg = 'DHCP End IP is out of the provided subnet';
                this.dhcpError = true;
            }
        }
        if (this.formGroup.get('TKGMgmtGatewayCidr').valid &&
            this.formGroup.get('TKGMgmtServiceStartRange').valid &&
            this.formGroup.get('TKGMgmtServiceEndRange').valid) {
            const gatewayIp = this.formGroup.get('TKGMgmtGatewayCidr').value;
            const block = new Netmask(gatewayIp);
            const serviceStart = this.formGroup.get('TKGMgmtServiceStartRange').value;
            const serviceEnd = this.formGroup.get('TKGMgmtServiceEndRange').value;
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
            this.apiClient.TkgMgmtDataNwValidated = true;
        } else {
            this.apiClient.TkgMgmtDataNwValidated = false;
        }
    }
}
