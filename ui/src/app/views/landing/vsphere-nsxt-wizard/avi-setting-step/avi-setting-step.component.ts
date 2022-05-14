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
import { ClrLoadingState } from '@clr/angular';
import {debounceTime, distinctUntilChanged, takeUntil} from 'rxjs/operators';
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
import {VsphereNsxtDataService} from "../../../../shared/service/vsphere-nsxt-data.service";

const SupervisedField = ['aviControllerFqdn', 'aviControllerIp', 'aviControllerFqdn02', 'aviControllerIp02',
                        'aviControllerFqdn03', 'aviControllerIp03', 'clusterFqdn', 'clusterIp'];

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
    segmentClusterErrorMsg = 'TKG VIP Segment not found, please update the segment value from the drop-down list';

    nameResolution = false;

    private uploadStatus = false;
    private enableHA = false;
    private aviControllerFqdn: string;
    private aviNodeSize: string;
    private aviControllerIP: string;
    private aviControllerFqdn02: string;
    private aviControllerIp02: string;
    private aviControllerFqdn03: string;
    private aviControllerIp03: string;
    private clusterIp: string;
    private clusterFqdn: string;
    private aviCertPath: string;
    private aviCertKeyPath: string;
//     private aviLicenseKey: string;
    private aviPassword: string;
    private aviBackupPassword: string;
    private aviSegmentName: string;
    private aviGatewayCidr: string;
    private aviDhcpStart: string;
    private aviDhcpEnd: string;
    private aviClusterVipNetworkName: string;
    private aviClusterVipGatewayIp: string;
    private aviClusterVipStartRange: string;
    private aviClusterVipEndRange: string;
    private aviClusterVipSeStartRange: string;
    private aviClusterVipSeEndRange: string;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private dataService: VsphereNsxtDataService) {

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
            'aviControllerFqdn',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidFqdn(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'aviControllerIp',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds(),
            ])
        );
        this.formGroup.addControl(
            'clusterIp',
            new FormControl('', [
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'clusterFqdn',
            new FormControl('', [
                this.validationService.isValidFqdn(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'aviControllerFqdn02',
            new FormControl('', [
                this.validationService.isValidFqdn(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'aviControllerIp02',
            new FormControl('', [
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'aviControllerFqdn03',
            new FormControl('', [
                this.validationService.isValidFqdn(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'aviControllerIp03',
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
        this.formGroup.addControl('aviMgmtNetworkName',
            new FormControl('', [
                Validators.required,
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('aviClusterVipNetworkName',
            new FormControl('', [
                Validators.required,
                this.validationService.noWhitespaceOnEnds()
            ])
        );
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

        SupervisedField.forEach(field => {
            this.formGroup.get(field).valueChanges.pipe(
                debounceTime(500),
                distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                takeUntil(this.unsubscribe))
                .subscribe(() => {
                    this.nameResolution = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
            });
        });

        this.loadingState = ClrLoadingState.DEFAULT;
        this.formGroup['canMoveToNext'] = () => {
            return (this.formGroup.valid && this.apiClient.AviIpValidated && this.nameResolution);
        };
        setTimeout(_ => {
            this.resurrectField('aviControllerFqdn',
                [Validators.required, this.validationService.isValidFqdn(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviControllerFqdn').value);
            this.resurrectField('aviControllerIp',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviControllerIp').value);
            this.resurrectField('aviBackupPassphrase',
                [Validators.required,
                Validators.minLength(8),
                this.validationService.isValidAviPassword()],
                this.formGroup.get('aviBackupPassphrase').value);
            this.resurrectField('aviPassword',
                [Validators.required,
                Validators.minLength(8),
                this.validationService.isValidAviPassword()],
                this.formGroup.get('aviPassword').value);
            this.resurrectField('aviMgmtNetworkName',
                [Validators.required, this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviMgmtNetworkName').value);
            this.resurrectField('aviClusterVipNetworkName',
                [Validators.required, this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('aviClusterVipNetworkName').value);
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

            this.formGroup.get('aviMgmtNetworkName').valueChanges.subscribe(
                () => this.apiClient.aviSegmentError = false);
            this.formGroup.get('aviClusterVipNetworkName').valueChanges.subscribe(
                () => this.apiClient.aviClusterSegmentError = false);
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

            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                // AVI Controller Node FQDN and IP Set
                this.subscription = this.dataService.currentAviHA.subscribe(
                    (enableHa) => this.enableHA = enableHa);
                this.formGroup.get('enableHA').setValue(this.enableHA);
                if (this.enableHA) {
                    this.toggleEnableHA();
                    this.subscription = this.dataService.currentAviFqdn02.subscribe(
                        (controllerFqdn02) => this.aviControllerFqdn02 = controllerFqdn02);
                    this.formGroup.get('aviControllerFqdn02').setValue(this.aviControllerFqdn02);
                    this.subscription = this.dataService.currentAviFqdn03.subscribe(
                        (controllerFqdn03) => this.aviControllerFqdn03 = controllerFqdn03);
                    this.formGroup.get('aviControllerFqdn03').setValue(this.aviControllerFqdn03);
                    this.subscription = this.dataService.currentAviIp02.subscribe(
                        (controllerIp02) => this.aviControllerIp02 = controllerIp02);
                    this.formGroup.get('aviControllerIp02').setValue(this.aviControllerIp02);
                    this.subscription = this.dataService.currentAviIp03.subscribe(
                        (controllerIp03) => this.aviControllerIp03 = controllerIp03);
                    this.formGroup.get('aviControllerIp03').setValue(this.aviControllerIp03);
                    this.subscription = this.dataService.currentAviClusterIp.subscribe(
                        (aviClusterIp) => this.clusterIp = aviClusterIp);
                    this.formGroup.get('clusterIp').setValue(this.clusterIp);
                    this.subscription = this.dataService.currentAviClusterFqdn.subscribe(
                        (aviClusterFqdn) => this.clusterFqdn = aviClusterFqdn);
                    this.formGroup.get('clusterFqdn').setValue(this.clusterFqdn);
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

                this.subscription = this.dataService.currentAviFqdn.subscribe(
                    (aviFqdn) => this.aviControllerFqdn = aviFqdn);
                this.formGroup.get('aviControllerFqdn').setValue(this.aviControllerFqdn);
                this.subscription = this.dataService.currentAviIp.subscribe(
                    (aviIp) => this.aviControllerIP = aviIp);
                this.formGroup.get('aviControllerIp').setValue(this.aviControllerIP);

                this.subscription = this.dataService.currentAviPassword.subscribe(
                    (aviPass) => this.aviPassword = aviPass);
                this.formGroup.get('aviPassword').setValue(this.aviPassword);
                this.subscription = this.dataService.currentAviBackupPassword.subscribe(
                    (aviBackupPass) => this.aviBackupPassword = aviBackupPass);
                this.formGroup.get('aviBackupPassphrase').setValue(this.aviBackupPassword);

                this.subscription = this.dataService.currentAviSegment.subscribe(
                    (segmentName) => this.aviSegmentName = segmentName);
                    this.formGroup.get('aviMgmtNetworkName').setValue(this.aviSegmentName);

                this.subscription = this.dataService.currentAviGateway.subscribe(
                    (aviGateway) => this.aviGatewayCidr = aviGateway);
                this.formGroup.get('aviMgmtGatewayIp').setValue(this.aviGatewayCidr);
                this.subscription = this.dataService.currentAviDhcpStart.subscribe(
                    (aviDhcpStart) => this.aviDhcpStart = aviDhcpStart);
                this.formGroup.get('aviMgmtDhcpStartRange').setValue(this.aviDhcpStart);
                this.subscription = this.dataService.currentAviDhcpEnd.subscribe(
                    (aviDhcpEnd) => this.aviDhcpEnd = aviDhcpEnd);
                this.formGroup.get('aviMgmtDhcpEndRange').setValue(this.aviDhcpEnd);

                this.subscription = this.dataService.currentAviClusterVipNetworkName.subscribe(
                    (clusterVipSegmentName) => this.aviClusterVipNetworkName = clusterVipSegmentName);
                    this.formGroup.get('aviClusterVipNetworkName').setValue(this.aviClusterVipNetworkName);

                this.subscription = this.dataService.currentAviClusterVipGatewayIp.subscribe(
                    (aviClusterVipGateway) => this.aviClusterVipGatewayIp = aviClusterVipGateway);
                this.formGroup.get('aviClusterVipGatewayIp').setValue(this.aviClusterVipGatewayIp);
                this.subscription = this.dataService.currentAviClusterVipStartIp.subscribe(
                    (aviClusterVipStartIp) => this.aviClusterVipStartRange = aviClusterVipStartIp);
                this.formGroup.get('aviClusterVipStartRange').setValue(this.aviClusterVipStartRange);
                this.subscription = this.dataService.currentAviClusterVipEndIp.subscribe(
                    (aviClusterVipEndIp) => this.aviClusterVipEndRange = aviClusterVipEndIp);
                this.formGroup.get('aviClusterVipEndRange').setValue(this.aviClusterVipEndRange);
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
//             this.formGroup.get('aviMgmtNetworkName').setValue('')
        }
    }

    validateDisabled() {
        return !(this.formGroup.get('aviMgmtGatewayIp').valid &&
                this.formGroup.get('aviMgmtDhcpStartRange').valid &&
                this.formGroup.get('aviMgmtDhcpEndRange').valid &&
                this.formGroup.get('aviControllerIp').valid &&
                this.formGroup.get('aviPassword').valid &&
                this.formGroup.get('aviBackupPassphrase').valid &&
                this.formGroup.get('aviControllerFqdn').valid &&
                this.formGroup.get('aviMgmtNetworkName').valid);

    }

     onAviValidateClick() {
        let mgmtErrorMsg = '';
        let clusterVipError = '';
        let aviSeError = '';
        let aviClusterVipErrorMsg = '';
        let aviMgmtVerified = false;
        let aviClusterVipVerified = false;
        let aviSeVerified = false;

        if (this.formGroup.get('aviMgmtGatewayIp').valid &&
            this.formGroup.get('aviMgmtDhcpStartRange').valid &&
            this.formGroup.get('aviMgmtDhcpEndRange').valid) {
            const gatewayIp = this.formGroup.get('aviMgmtGatewayIp').value;
            const dhcpStart = this.formGroup.get('aviMgmtDhcpStartRange').value;
            const dhcpEnd = this.formGroup.get('aviMgmtDhcpEndRange').value;
            const block = new Netmask(gatewayIp);
            if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                aviMgmtVerified = true;
                mgmtErrorMsg = '';
            } else {
                let str='';
                if (!block.contains(dhcpStart)) {
                    str = 'NSX ALB SE Start IP, ';
                }
                if (!block.contains(dhcpEnd)) {
                    str = str + 'NSX ALB SE End IP, ';
                }
                mgmtErrorMsg = str + ' outside of the provided subnet.';
                aviMgmtVerified = false;
                this.apiClient.AviIpValidated = false;
            }
        }
        // Controller 01 Validation
        if (this.formGroup.get('aviControllerIp').valid && this.formGroup.get('aviMgmtGatewayIp').valid) {
            const mgmtGateway = this.formGroup.get('aviMgmtGatewayIp').value;
            const controllerIp = this.formGroup.get('aviControllerIp').value;
            const block = new Netmask(mgmtGateway);
            if(block.contains(controllerIp)) {
                this.apiClient.aviController01Error = false;
            } else {
                this.apiClient.aviController01Error = true;
            }
        }
        // Controller 02 Validation
        if (this.formGroup.get('enableHA').value) {
            if (this.formGroup.get('aviControllerIp02').valid && this.formGroup.get('aviMgmtGatewayIp').valid) {
                const mgmtGateway = this.formGroup.get('aviMgmtGatewayIp').value;
                const controllerIp = this.formGroup.get('aviControllerIp02').value;
                const block = new Netmask(mgmtGateway);
                if(block.contains(controllerIp)) {
                    this.apiClient.aviController02Error = false;
                } else {
                    this.apiClient.aviController02Error = true;
                }
            }
            if (this.formGroup.get('aviControllerIp03').valid && this.formGroup.get('aviMgmtGatewayIp').valid) {
                const mgmtGateway = this.formGroup.get('aviMgmtGatewayIp').value;
                const controllerIp = this.formGroup.get('aviControllerIp03').value;
                const block = new Netmask(mgmtGateway);
                if(block.contains(controllerIp)) {
                    this.apiClient.aviController03Error = false;
                } else {
                    this.apiClient.aviController03Error = true;
                }
            }
            if (this.formGroup.get('clusterIp').valid && this.formGroup.get('aviMgmtGatewayIp').valid) {
                const mgmtGateway = this.formGroup.get('aviMgmtGatewayIp').value;
                const clusterIp = this.formGroup.get('clusterIp').value;
                const block = new Netmask(mgmtGateway);
                if(block.contains(clusterIp)) {
                    this.apiClient.clusterIpError = false;
                } else {
                    this.apiClient.clusterIpError = true;
                }
            }
        }
        // Cluster VIP Network Validations
        if (this.formGroup.get('aviClusterVipGatewayIp').valid &&
            this.formGroup.get('aviClusterVipStartRange').valid &&
            this.formGroup.get('aviClusterVipEndRange').valid) {
            const gatewayIp = this.formGroup.get('aviClusterVipGatewayIp').value;
            const dhcpStart = this.formGroup.get('aviClusterVipStartRange').value;
            const dhcpEnd = this.formGroup.get('aviClusterVipEndRange').value;
            const block = new Netmask(gatewayIp);
            if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                aviClusterVipVerified = true;
                clusterVipError = '';
            } else {
                let str='';
                if (!block.contains(dhcpStart)) {
                    str = 'Start IP, ';
                }
                if (!block.contains(dhcpEnd)) {
                    str = str + 'End IP, ';
                }
                clusterVipError = 'TKG Cluster VIP Network ' + str + 'are outside of the provided subnet.';
                this.apiClient.AviIpValidated = false;
                aviClusterVipVerified = false;
            }
        }
        if (this.formGroup.get('enableHA').value){
            this.apiClient.AviIpValidated = (aviClusterVipVerified &&
                                             aviMgmtVerified &&
                                             !this.apiClient.aviController03Error &&
                                             !this.apiClient.aviController01Error &&
                                             !this.apiClient.aviController02Error &&
                                             !this.apiClient.clusterIpError);
        } else {
            this.apiClient.AviIpValidated = (aviClusterVipVerified &&
                                             aviMgmtVerified &&
                                             !this.apiClient.aviController01Error);
        }
        if (!this.apiClient.AviIpValidated){
            if (mgmtErrorMsg === '') {
                this.errorNotification = '';
            } else {
                this.errorNotification = mgmtErrorMsg;
            }
            if (this.errorNotification === '') {
                if (clusterVipError !== '') {
                    this.errorNotification = clusterVipError;
                }
            } else {
                if(clusterVipError !== '') {
                    this.errorNotification = this.errorNotification + '\n' + clusterVipError;
                }
            }
            if (this.errorNotification === '') {
            }
            this.apiClient.AviIpValidated = false;
        }
    }

    toggleEnableHA() {
        const aviHaFields = [
            'aviControllerFqdn02',
            'aviControllerIp02',
            'aviControllerFqdn03',
            'aviControllerIp03',
            'clusterIp',
            'clusterFqdn',
        ];
        if (this.formGroup.value['enableHA']) {
            this.resurrectField('aviControllerFqdn02', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidFqdn(),
            ], this.formGroup.value['aviControllerFqdn02']);
            this.resurrectField('aviControllerIp02', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidIp(),
            ], this.formGroup.value['aviControllerIp02']);
            this.resurrectField('aviControllerFqdn03', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidFqdn(),
            ], this.formGroup.value['aviControllerFqdn03']);
            this.resurrectField('aviControllerIp03', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidIp(),
            ], this.formGroup.value['aviControllerIp03']);
            this.resurrectField('clusterIp', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidIp(),
            ], this.formGroup.value['clusterIp']);
            this.resurrectField('clusterFqdn', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidFqdn(),
            ], this.formGroup.value['clusterFqdn']);
        } else {
            aviHaFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    public nameResolutionTest() {
        let aviData = {
            "enableAviHa": "",
            "fqdn01": "",
            "ip01": "",
            "fqdn02": "",
            "ip02": "",
            "fqdn03": "",
            "ip03": "",
            "clusterFqdn": "",
            "clusterIp": "",
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": "",
            "dnsServersIp": ""
        };
        aviData["enableAviHa"] = this.formGroup.get("enableHA").value;
        aviData["fqdn01"] = this.formGroup.get("aviControllerFqdn").value;
        aviData["ip01"] = this.formGroup.get("aviControllerIp").value;
        aviData["fqdn02"] = this.formGroup.get("aviControllerFqdn02").value;
        aviData["ip02"] = this.formGroup.get("aviControllerIp02").value;
        aviData["fqdn03"] = this.formGroup.get("aviControllerFqdn03").value;
        aviData["ip03"] = this.formGroup.get("aviControllerIp03").value;
        aviData["clusterFqdn"] = this.formGroup.get("clusterFqdn").value;
        aviData["clusterIp"] = this.formGroup.get("clusterIp").value;

        this.dataService.currentVcAddress.subscribe(
            (vcFqdn) => aviData['vcenterAddress'] = vcFqdn);
        this.dataService.currentVcUser.subscribe(
            (user) => aviData['ssoUser'] = user);
        this.dataService.currentVcPass.subscribe(
            (pass) => aviData['ssoPassword'] = pass);
        this.dataService.currentDnsValue.subscribe(
            (dns) => aviData['dnsServersIp'] = dns);
        this.loadingState = ClrLoadingState.LOADING;
        this.apiClient.aviNameResolution(aviData, 'vsphere').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.nameResolution = true;
                    this.loadingState = ClrLoadingState.DEFAULT;
                } else if (data.responseType === 'ERROR') {
                    this.nameResolution = false;
                    this.errorNotification = data.msg;
                    this.loadingState = ClrLoadingState.DEFAULT;
                }
            } else {
                this.nameResolution = false;
                this.errorNotification = "Some error occurred while validating name resolution for NSX ALB controller";
                this.loadingState = ClrLoadingState.DEFAULT;
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.nameResolution = false;
                this.errorNotification = "Ping Test: " + err.msg;
                this.loadingState = ClrLoadingState.DEFAULT;
            } else {
                this.nameResolution = false;
                this.errorNotification = "Some error occurred while validating name resolution for NSX ALB controller";
                this.loadingState = ClrLoadingState.DEFAULT;
            }
        });
    }

    getDisabled(): boolean {
        return !(this.formGroup.get('aviControllerFqdn').valid && this.formGroup.get('aviControllerIp').valid &&
                this.formGroup.get('aviControllerFqdn02').valid && this.formGroup.get('aviControllerIp02').valid &&
                this.formGroup.get('aviControllerFqdn03').valid && this.formGroup.get('aviControllerIp03').valid &&
                this.formGroup.get('clusterFqdn').valid && this.formGroup.get('clusterIp').valid);
    }
}
