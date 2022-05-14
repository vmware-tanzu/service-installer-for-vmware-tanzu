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
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';

/**
 * App imports
 */
import { PROVIDERS, Providers } from '../../../../shared/constants/app.constants';
import { NodeType, vSphereNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
// import { KUBE_VIP, NSX_ADVANCED_LOAD_BALANCER } from '../../wizard/shared/components/steps/load-balancer/load-balancer-step.component';
import Broker from "src/app/shared/service/broker";
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import {Subscription} from "rxjs";
import {VMCDataService} from "../../../../shared/service/vmc-data.service";

@Component({
    selector: 'app-tkg-workload-nw-setting-step',
    templateUrl: './tkg-workload-data.component.html',
    styleUrls: ['./tkg-workload-data.component.scss']
})
export class TKGWorkloadNetworkSettingComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    @Input() errorNotification: string;
    PROVIDERS: Providers = PROVIDERS;
//     edition = 'tkg';
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
        private wizardFormService: VSphereWizardFormService,
        public apiClient: APIClient,
        private dataService: VMCDataService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl('TKGDataGatewayCidr',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('TKGDataDhcpStartRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('TKGDataDhcpEndRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('TKGWrkServiceStartRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('TKGWrkServiceEndRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );

        this.formGroup['canMoveToNext'] = () => {
            return (this.formGroup.valid && this.apiClient.TkgWrkDataNwValidated);
        };
        setTimeout(_ => {
            this.resurrectField('TKGDataGatewayCidr',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('TKGDataGatewayCidr').value);
            this.resurrectField('TKGDataDhcpStartRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('TKGDataDhcpStartRange').value);
            this.resurrectField('TKGDataDhcpEndRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('TKGDataDhcpEndRange').value);
            this.resurrectField('TKGWrkServiceStartRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('TKGWrkServiceStartRange').value);
            this.resurrectField('TKGWrkServiceEndRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('TKGWrkServiceEndRange').value);

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
