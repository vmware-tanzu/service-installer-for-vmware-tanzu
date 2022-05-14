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
import {DataService} from "../../../../shared/service/data.service";

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
    segmentError = false;
    segmentErrorMsg = 'TKG Management Data Segment not found, please update the segment value from the drop-down list';
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    private uploadStatus = false;
    private segment: string;
    private gatewayCidr: string;
    private dhcpStart: string;
    private dhcpEnd: string;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private dataService: DataService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl('TKGMgmtSegmentName',
            new FormControl('', [
                Validators.required
            ])
        );
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
        this.formGroup['canMoveToNext'] = () => {
            return (this.formGroup.valid && this.apiClient.TkgMgmtDataNwValidated);
        };

        setTimeout(_ => {
            this.resurrectField('TKGMgmtSegmentName',
                [Validators.required],
                this.formGroup.get('TKGMgmtSegmentName').value);
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
            // Track change in form control values
            this.formGroup.get('TKGMgmtSegmentName').valueChanges.subscribe(
                () => this.apiClient.tkgMgmtDataSegmentError = false);
            this.formGroup.get('TKGMgmtGatewayCidr').valueChanges.subscribe(
                () => this.apiClient.TkgMgmtDataNwValidated = false);
            this.formGroup.get('TKGMgmtDhcpStartRange').valueChanges.subscribe(
                () => this.apiClient.TkgMgmtDataNwValidated = false);
            this.formGroup.get('TKGMgmtDhcpEndRange').valueChanges.subscribe(
                () => this.apiClient.TkgMgmtDataNwValidated = false);
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentTkgMgmtDataSegment.subscribe(
                    (segment) => this.segment = segment);
                if (this.apiClient.networks.indexOf(this.segment) === -1) {
                    this.apiClient.tkgMgmtDataSegmentError = true;
                } else {
                    this.formGroup.get('TKGMgmtSegmentName').setValue(this.segment);
                    this.apiClient.tkgMgmtDataSegmentError = false;
                }
                this.subscription = this.dataService.currentTkgMgmtDataGateway.subscribe(
                    (gateway) => this.gatewayCidr = gateway);
                this.formGroup.get('TKGMgmtGatewayCidr').setValue(this.gatewayCidr);
                this.subscription = this.dataService.currentTkgMgmtDataDhcpStart.subscribe(
                    (dhcpStart) => this.dhcpStart = dhcpStart);
                this.formGroup.get('TKGMgmtDhcpStartRange').setValue(this.dhcpStart);
                this.subscription = this.dataService.currentTkgMgmtDataDhcpEnd.subscribe(
                    (dhcpEnd) => this.dhcpEnd = dhcpEnd);
                this.formGroup.get('TKGMgmtDhcpEndRange').setValue(this.dhcpEnd);
                if ((this.gatewayCidr!=='') && (this.dhcpStart !== '') && (this.dhcpEnd!=='')){
                    const block = new Netmask(this.gatewayCidr);
                    if(block.contains(this.dhcpStart) && block.contains(this.dhcpEnd)) {
                        this.apiClient.TkgMgmtDataNwValidated = true;
                    } else if (!block.contains(this.dhcpStart) && !block.contains(this.dhcpEnd)) {
                        this.errorNotification = 'DHCP Start and End IP are out of the provided subnet';
                        this.apiClient.TkgMgmtDataNwValidated = false;
                    } else if (!block.contains(this.dhcpStart)) {
                        this.errorNotification = 'DHCP Start IP is out of the provided subnet.';
                        this.apiClient.TkgMgmtDataNwValidated = false;
                    } else if (!block.contains(this.dhcpEnd)) {
                        this.errorNotification = 'DHCP End IP is out of the provided subnet';
                        this.apiClient.TkgMgmtDataNwValidated = false;
                    }
                }
            }
            });
    }

    setSavedDataAfterLoad() {
        if (this.hasSavedData()) {
            super.setSavedDataAfterLoad();
            this.formGroup.get('TKGMgmtSegmentName').setValue('');
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
        if(this.formGroup.valid) {
            this.errorNotification = '';
            const gatewayIp = this.formGroup.get('TKGMgmtGatewayCidr').value;
            const dhcpStart = this.formGroup.get('TKGMgmtDhcpStartRange').value;
            const dhcpEnd = this.formGroup.get('TKGMgmtDhcpEndRange').value;
            const block = new Netmask(gatewayIp);
            if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                this.apiClient.TkgMgmtDataNwValidated = true;
                this.validated = true;
                this.errorNotification = '';
            } else if (!block.contains(dhcpStart) && !block.contains(dhcpEnd)) {
                this.errorNotification = 'DHCP Start and End IP are out of the provided subnet';
                this.apiClient.TkgMgmtDataNwValidated = false;
            } else if (!block.contains(dhcpStart)) {
                this.errorNotification = 'DHCP Start IP is out of the provided subnet.';
                this.apiClient.TkgMgmtDataNwValidated = false;
            } else if (!block.contains(dhcpEnd)) {
                this.errorNotification = 'DHCP End IP is out of the provided subnet';
                this.apiClient.TkgMgmtDataNwValidated = false;
            }
        }
    }
}
