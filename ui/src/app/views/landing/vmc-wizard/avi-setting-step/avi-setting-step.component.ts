/**
 * Angular Modules
 */
import { Component, Input, OnInit } from '@angular/core';
import {
    FormControl,
    Validators,
} from '@angular/forms';
import { Netmask } from 'netmask';
import { TkgEventType } from 'src/app/shared/service/Messenger';
import {ClrLoadingState} from '@clr/angular';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';

/**
 * App imports
 */
import { PROVIDERS, Providers } from '../../../../shared/constants/app.constants';
import { NodeType, aviSize } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
import Broker from 'src/app/shared/service/broker';
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import {Subscription} from 'rxjs';
import {VMCDataService} from "../../../../shared/service/vmc-data.service";

@Component({
    selector: 'app-avi-setting-step',
    templateUrl: './avi-setting-step.component.html',
    styleUrls: ['./avi-setting-step.component.scss']
})
export class AVINetworkSettingComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    @Input() errorNotification: any;

    loading: boolean = false;
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    PROVIDERS: Providers = PROVIDERS;
    nodeTypes: Array<NodeType> = [];
    aviSize: Array<NodeType> = aviSize;
    nodeType: string;

    networks = [];
    subscription: Subscription;
    segmentError = false;
    segmentErrorMsg = 'AVI Management Segment not found, please update the segment value from the drop-down list';
    segmentClusterError = false;
    segmentClusterErrorMsg = 'AVI Cluster VIP Segment not found, please update the segment value from the drop-down list';

    mgmtIPErrorMsg = '';
    aviMgmtIPVerified = false;
    clusterVipIPError = '';
    aviClusterVipIPVerified = false;
    aviSeIPError = '';
    aviSeIPVerified = false;

    private uploadStatus = false;
    private enableHA = false;
    private aviNodeSize: string;
    private clusterIp: string;

    private aviCertPath: string;
    private aviCertKeyPath: string;
//     private aviLicenseKey: string;
    private aviPassword: string;
    private aviBackupPassword: string;
    private aviSegmentName: string;
    private aviGatewayCidr: string;
    private aviDhcpStart: string;
    private aviDhcpEnd: string;
//     private aviClusterVipNetworkName: string;
    private aviClusterVipGatewayIp: string;
    private aviClusterVipStartRange: string;
    private aviClusterVipEndRange: string;
    private aviClusterVipSeStartRange: string;
    private aviClusterVipSeEndRange: string;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private dataService: VMCDataService) {

        super();
        this.nodeTypes = [...aviSize];
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'enableHA',
            new FormControl(false, [
                Validators.required
            ])
        );
        this.formGroup.addControl(
            'aviSize',
            new FormControl('', [
                Validators.required
            ])
        );
        this.formGroup.addControl(
            'clusterIp',
            new FormControl('', [
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('aviPassword',
            new FormControl('', [
                Validators.required,
                Validators.minLength(8),
                this.validationService.isValidAviPassword()
            ])
        );
        this.formGroup.addControl('aviBackupPassphrase',
            new FormControl('', [
                Validators.required,
                Validators.minLength(8),
                this.validationService.isValidAviPassword()
            ])
        );
        this.formGroup.addControl('aviCertPath',
            new FormControl('', [
                this.validationService.noWhitespaceOnEnds()
            ]));
        this.formGroup.addControl('aviCertKeyPath',
            new FormControl('', [
                this.validationService.noWhitespaceOnEnds()
            ]));
//         this.formGroup.addControl('aviLicenseKey',
//             new FormControl('', [
//                 this.validationService.noWhitespaceOnEnds()
//             ]));
//         this.formGroup.addControl('aviClusterVipNetworkName',
//             new FormControl('', [
//                 Validators.required
//             ])
//         );
        this.formGroup.addControl('aviMgmtGatewayIp',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('aviClusterVipGatewayIp',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('aviMgmtDhcpStartRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviMgmtDhcpEndRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviClusterVipStartRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviClusterVipEndRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviClusterVipSeStartRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('aviClusterVipSeEndRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()]));
        this.loadingState = ClrLoadingState.DEFAULT;
        this.formGroup['canMoveToNext'] = () => {
            return (this.formGroup.valid && this.apiClient.AviIpValidated);
        };
        setTimeout(_ => {
            this.resurrectField('aviBackupPassphrase',
                [Validators.required],
                this.formGroup.get('aviBackupPassphrase').value);
            this.resurrectField('aviPassword',
                [Validators.required],
                this.formGroup.get('aviPassword').value);
//             this.resurrectField('aviClusterVipNetworkName',
//                 [Validators.required],
//                 this.formGroup.get('aviClusterVipNetworkName').value);
            this.resurrectField('aviMgmtGatewayIp',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviMgmtGatewayIp').value);
            this.resurrectField('aviClusterVipGatewayIp',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviClusterVipGatewayIp').value);
            this.resurrectField('aviMgmtDhcpStartRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviMgmtDhcpStartRange').value);
            this.resurrectField('aviMgmtDhcpEndRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviMgmtDhcpEndRange').value);
            this.resurrectField('aviClusterVipStartRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviClusterVipStartRange').value);
            this.resurrectField('aviClusterVipEndRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviClusterVipEndRange').value);
            this.resurrectField('aviClusterVipSeStartRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviClusterVipSeStartRange').value);
            this.resurrectField('aviClusterVipSeEndRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviClusterVipSeEndRange').value);

//             this.formGroup.get('aviClusterVipNetworkName').valueChanges.subscribe(
//                 () => this.apiClient.aviClusterSegmentError = false);
            this.formGroup.get('aviMgmtGatewayIp').valueChanges.subscribe(
                () => this.apiClient.AviIpValidated = false);
            this.formGroup.get('aviClusterVipGatewayIp').valueChanges.subscribe(
                () => this.apiClient.AviIpValidated = false);
            this.formGroup.get('aviMgmtDhcpStartRange').valueChanges.subscribe(
                () => this.apiClient.AviIpValidated = false);
            this.formGroup.get('aviMgmtDhcpEndRange').valueChanges.subscribe(
                () => this.apiClient.AviIpValidated = false);
            this.formGroup.get('aviClusterVipStartRange').valueChanges.subscribe(
                () => this.apiClient.AviIpValidated = false);
            this.formGroup.get('aviClusterVipEndRange').valueChanges.subscribe(
                () => this.apiClient.AviIpValidated = false);
            this.formGroup.get('aviClusterVipSeStartRange').valueChanges.subscribe(
                () => this.apiClient.AviIpValidated = false);
            this.formGroup.get('aviClusterVipSeEndRange').valueChanges.subscribe(
                () => this.apiClient.AviIpValidated = false);
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                // AVI Controller Node FQDN and IP Set
                this.subscription = this.dataService.currentAviHA.subscribe(
                    (enableHa) => this.enableHA = enableHa);
                this.formGroup.get('enableHA').setValue(this.enableHA);
                if (this.enableHA) {
                    this.toggleEnableHA();
                    this.subscription = this.dataService.currentAviClusterIp.subscribe(
                        (aviClusterIp) => this.clusterIp = aviClusterIp);
                    this.formGroup.get('clusterIp').setValue(this.clusterIp);
//                     this.subscription = this.dataService.currentAviClusterFqdn.subscribe(
//                         (aviClusterFqdn) => this.clusterFqdn = aviClusterFqdn);
//                     this.formGroup.get('clusterFqdn').setValue(this.clusterFqdn);
                }
                this.subscription = this.dataService.currentAviSize.subscribe(
                    (size) => this.aviNodeSize = size);
                this.formGroup.get('aviSize').setValue(this.aviNodeSize);
//                 this.subscription = this.dataService.currentAviLicense.subscribe(
//                     (licenseKey) => this.aviLicenseKey = licenseKey);
//                 this.formGroup.get('aviLicenseKey').setValue(this.aviLicenseKey);
                this.subscription = this.dataService.currentAviCertPath.subscribe(
                    (certPath) => this.aviCertPath = certPath);
                this.formGroup.get('aviCertPath').setValue(this.aviCertPath);
                this.subscription = this.dataService.currentAviCertKeyPath.subscribe(
                    (certKeyPath) => this.aviCertKeyPath = certKeyPath);
                this.formGroup.get('aviCertKeyPath').setValue(this.aviCertKeyPath);
                this.subscription = this.dataService.currentAviPassword.subscribe(
                    (aviPass) => this.aviPassword = aviPass);
                this.formGroup.get('aviPassword').setValue(this.aviPassword);
                this.subscription = this.dataService.currentAviBackupPassword.subscribe(
                    (aviBackupPass) => this.aviBackupPassword = aviBackupPass);
                this.formGroup.get('aviBackupPassphrase').setValue(this.aviBackupPassword);

                this.subscription = this.dataService.currentAviGateway.subscribe(
                    (aviGateway) => this.aviGatewayCidr = aviGateway);
                this.formGroup.get('aviMgmtGatewayIp').setValue(this.aviGatewayCidr);
                this.subscription = this.dataService.currentAviDhcpStart.subscribe(
                    (aviDhcpStart) => this.aviDhcpStart = aviDhcpStart);
                this.formGroup.get('aviMgmtDhcpStartRange').setValue(this.aviDhcpStart);
                this.subscription = this.dataService.currentAviDhcpEnd.subscribe(
                    (aviDhcpEnd) => this.aviDhcpEnd = aviDhcpEnd);
                this.formGroup.get('aviMgmtDhcpEndRange').setValue(this.aviDhcpEnd);

//                 this.subscription = this.dataService.currentAviClusterVipNetworkName.subscribe(
//                     (clusterVipSegmentName) => this.aviClusterVipNetworkName = clusterVipSegmentName);
//                 console.log(this.apiClient.networks);
//                 console.log(this.aviClusterVipNetworkName);
//                 if(this.apiClient.networks.indexOf(this.aviClusterVipNetworkName) === -1) {
//                     this.apiClient.aviClusterSegmentError = true;
//                 } else {
//                     this.formGroup.get('aviClusterVipNetworkName').setValue(this.aviClusterVipNetworkName);
//                     this.apiClient.aviClusterSegmentError = false;
//                 }
                this.subscription = this.dataService.currentAviClusterVipGatewayIp.subscribe(
                    (aviClusterVipGateway) => this.aviClusterVipGatewayIp = aviClusterVipGateway);
                this.formGroup.get('aviClusterVipGatewayIp').setValue(this.aviClusterVipGatewayIp);
                this.subscription = this.dataService.currentAviClusterVipStartIp.subscribe(
                    (aviClusterVipStartIp) => this.aviClusterVipStartRange = aviClusterVipStartIp);
                this.formGroup.get('aviClusterVipStartRange').setValue(this.aviClusterVipStartRange);
                this.subscription = this.dataService.currentAviClusterVipEndIp.subscribe(
                    (aviClusterVipEndIp) => this.aviClusterVipEndRange = aviClusterVipEndIp);
                this.formGroup.get('aviClusterVipEndRange').setValue(this.aviClusterVipEndRange);
                this.subscription = this.dataService.currentAviClusterVipSeStartIp.subscribe(
                    (aviClusterVipSeStart) => this.aviClusterVipSeStartRange = aviClusterVipSeStart);
                this.formGroup.get('aviClusterVipSeStartRange').setValue(this.aviClusterVipSeStartRange);
                this.subscription = this.dataService.currentAviClusterVipSeEndIp.subscribe(
                    (aviClusterVipSeEnd) => this.aviClusterVipSeEndRange = aviClusterVipSeEnd);
                this.formGroup.get('aviClusterVipSeEndRange').setValue(this.aviClusterVipSeEndRange);
                this.onAviValidateClick();
            }
            });
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // don't fill password field with ****
        if (!this.uploadStatus) {
            this.formGroup.get('aviPassword').setValue('');
            this.formGroup.get('aviBackupPassphrase').setValue('');
//             this.formGroup.get('aviClusterVipNetworkName').setValue('');
        }
    }

    validateDisabled() {
        return !(this.formGroup.get('aviMgmtGatewayIp').valid &&
                this.formGroup.get('aviMgmtDhcpStartRange').valid &&
                this.formGroup.get('aviMgmtDhcpEndRange').valid &&
                this.formGroup.get('aviPassword').valid &&
                this.formGroup.get('aviBackupPassphrase').valid);

    }

     onAviValidateClick() {
        if (this.formGroup.get('aviMgmtGatewayIp').valid &&
            this.formGroup.get('aviMgmtDhcpStartRange').valid &&
            this.formGroup.get('aviMgmtDhcpEndRange').valid) {
            const gatewayIp = this.formGroup.get('aviMgmtGatewayIp').value;
            const dhcpStart = this.formGroup.get('aviMgmtDhcpStartRange').value;
            const dhcpEnd = this.formGroup.get('aviMgmtDhcpEndRange').value;
            const block = new Netmask(gatewayIp);
            if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                this.aviMgmtIPVerified = true;
                this.mgmtIPErrorMsg = '';
            } else {
                let str='';
                if (!block.contains(dhcpStart)) {
                    str = 'NSX ALB SE Start IP, ';
                }
                if (!block.contains(dhcpEnd)) {
                    str = str + 'NSX ALB SE End IP, ';
                }
                this.mgmtIPErrorMsg = str + ' outside of the provided subnet.';
                this.aviMgmtIPVerified = false;
                this.apiClient.AviIpValidated = false;
            }
        }
        if (this.formGroup.get('enableHA').value) {
            if(this.formGroup.get('aviMgmtGatewayIp').valid &&
                this.formGroup.get('clusterIp').valid) {
                const gatewayIp = this.formGroup.get('aviMgmtGatewayIp').value;
                const clusterIp = this.formGroup.get('clusterIp').value;
                const block = new Netmask(gatewayIp);
                if(block.contains(clusterIp)) {
                    this.apiClient.clusterIpError = false;
                } else {
                    this.apiClient.clusterIpError = true;
                }
            }
        } else {
            this.apiClient.clusterIpError = false;
        }
        if (this.formGroup.get('aviClusterVipGatewayIp').valid &&
            this.formGroup.get('aviClusterVipStartRange').valid &&
            this.formGroup.get('aviClusterVipEndRange').valid) {
            const gatewayIp = this.formGroup.get('aviClusterVipGatewayIp').value;
            const dhcpStart = this.formGroup.get('aviClusterVipStartRange').value;
            const dhcpEnd = this.formGroup.get('aviClusterVipEndRange').value;
            const block = new Netmask(gatewayIp);
            if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                this.aviClusterVipIPVerified = true;
                this.clusterVipIPError = '';
            } else {
                let str='';
                if (!block.contains(dhcpStart)) {
                    str = 'Start IP, ';
                }
                if (!block.contains(dhcpEnd)) {
                    str = str + 'End IP, ';
                }
                this.clusterVipIPError = 'AVI Cluster VIP Network ' + str + 'are outside of the provided subnet.';
                this.apiClient.AviIpValidated = false;
                this.aviClusterVipIPVerified = false;
            }
        }
        if (this.formGroup.get('aviClusterVipGatewayIp').valid &&
            this.formGroup.get('aviClusterVipSeStartRange').valid &&
            this.formGroup.get('aviClusterVipSeEndRange').valid) {
            const gatewayIp = this.formGroup.get('aviClusterVipGatewayIp').value;
            const dhcpStart = this.formGroup.get('aviClusterVipSeStartRange').value;
            const dhcpEnd = this.formGroup.get('aviClusterVipSeEndRange').value;
            const block = new Netmask(gatewayIp);
            if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                this.aviSeIPVerified = true;
                this.aviSeIPError = '';
            } else {
                let str='';
                if (!block.contains(dhcpStart)) {
                    str = 'Start IP, ';
                }
                if (!block.contains(dhcpEnd)) {
                    str = str + 'End IP, ';
                }
                this.aviSeIPError = 'AVI Cluster VIP Network SE ' + str + 'are outside of the provided subnet.';
                this.apiClient.AviIpValidated = false;
                this.aviSeIPVerified = false;
            }
        }
        if (this.aviMgmtIPVerified && this.aviClusterVipIPVerified && this.aviSeIPVerified && !this.apiClient.clusterIpError) {
            this.apiClient.AviIpValidated = true;
        } else {
            this.apiClient.AviIpValidated = false;
        }
    }

    toggleEnableHA() {
        const aviHaFields = [
            'clusterIp',
        ];
        if (this.formGroup.value['enableHA']) {
            this.resurrectField('clusterIp', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidIp(),
            ], this.formGroup.value['clusterIp']);
        } else {
            aviHaFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }
}
