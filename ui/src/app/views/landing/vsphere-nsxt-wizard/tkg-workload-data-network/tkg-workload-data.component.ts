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
import {VsphereNsxtDataService} from "../../../../shared/service/vsphere-nsxt-data.service";

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
    segmentErrorMsg = 'TKG Workload Data Segment not found, please update the segment value from the drop-down list';
    private uploadStatus = false;
    private segment: string;
    private gatewayCidr: string;
    private dhcpStart: string;
    private dhcpEnd: string;
    constructor(private validationService: ValidationService,
        private wizardFormService: VSphereWizardFormService,
        public apiClient: APIClient,
        private dataService: VsphereNsxtDataService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl('TKGDataSegmentName',
            new FormControl('', [
                Validators.required, this.validationService.noWhitespaceOnEnds()
            ])
        );
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
        this.formGroup['canMoveToNext'] = () => {
            return (this.formGroup.valid && this.apiClient.TkgWrkDataNwValidated);
        };
        setTimeout(_ => {
            this.displayForm = true;
            this.resurrectField('TKGDataSegmentName',
                [Validators.required, this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('TKGDataSegmentName').value);
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
//             this.formGroup.get('TKGDataSegmentName').valueChanges.subscribe(
//                 () => this.apiClient.tkgWrkDataSegmentError = false)
            this.formGroup.get('TKGDataGatewayCidr').valueChanges.subscribe(
                () => this.apiClient.TkgWrkDataNwValidated = false);
            this.formGroup.get('TKGDataDhcpStartRange').valueChanges.subscribe(
                () => this.apiClient.TkgWrkDataNwValidated = false);
            this.formGroup.get('TKGDataDhcpEndRange').valueChanges.subscribe(
                () => this.apiClient.TkgWrkDataNwValidated = false);
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentTkgWrkDataSegment.subscribe(
                    (segment) => this.segment = segment);
                this.formGroup.get('TKGDataSegmentName').setValue(this.segment);

                this.subscription = this.dataService.currentTkgWrkDataGateway.subscribe(
                    (gateway) => this.gatewayCidr = gateway);
                this.formGroup.get('TKGDataGatewayCidr').setValue(this.gatewayCidr);
                this.subscription = this.dataService.currentTkgWrkDataDhcpStart.subscribe(
                    (dhcpStart) => this.dhcpStart = dhcpStart);
                this.formGroup.get('TKGDataDhcpStartRange').setValue(this.dhcpStart);
                this.subscription = this.dataService.currentTkgWrkDataDhcpEnd.subscribe(
                    (dhcpEnd) => this.dhcpEnd = dhcpEnd);
                this.formGroup.get('TKGDataDhcpEndRange').setValue(this.dhcpEnd);
                if ((this.gatewayCidr!== '') && (this.dhcpStart!=='') && (this.dhcpEnd!=='')) {
                    const block = new Netmask(this.gatewayCidr);
                    if (block.contains(this.dhcpStart) && block.contains(this.dhcpEnd)) {
                        this.apiClient.TkgWrkDataNwValidated = true;
                        this.errorNotification = '';
                    } else if (!block.contains(this.dhcpStart) && !block.contains(this.dhcpEnd)) {
                        this.errorNotification = 'DHCP Start and End IP are out of the provided subnet';
                        this.apiClient.TkgWrkDataNwValidated = false;
                    } else if (!block.contains(this.dhcpStart)) {
                        this.errorNotification = 'DHCP Start IP is out of the provided subnet.';
                        this.apiClient.TkgWrkDataNwValidated = false;
                    } else if (!block.contains(this.dhcpEnd)) {
                        this.errorNotification = 'DHCP End IP is out of the provided subnet';
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
//                 this.formGroup.get('TKGDataSegmentName').setValue('');
            }
        }
    }

    onTkgMgmtDataValidateClick() {
        if(this.formGroup.valid) {
            this.errorNotification = '';
            const gatewayIp = this.formGroup.get('TKGDataGatewayCidr').value;
            const dhcpStart = this.formGroup.get('TKGDataDhcpStartRange').value;
            const dhcpEnd = this.formGroup.get('TKGDataDhcpEndRange').value;
            const block = new Netmask(gatewayIp);
            if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                this.apiClient.TkgWrkDataNwValidated = true;
                this.errorNotification = '';
            } else if (!block.contains(dhcpStart) && !block.contains(dhcpEnd)) {
                this.errorNotification = 'DHCP Start and End IP are out of the provided subnet';
                this.apiClient.TkgWrkDataNwValidated = false;
            } else if (!block.contains(dhcpStart)) {
                this.errorNotification = 'DHCP Start IP is out of the provided subnet.';
                this.apiClient.TkgWrkDataNwValidated = false;
            } else if (!block.contains(dhcpEnd)) {
                this.errorNotification = 'DHCP End IP is out of the provided subnet';
                this.apiClient.TkgWrkDataNwValidated = false;
            }
        }
        }

}
