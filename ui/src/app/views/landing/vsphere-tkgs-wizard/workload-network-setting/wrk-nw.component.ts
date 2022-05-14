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
import { distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';

/**
 * App imports
 */
import { PROVIDERS, Providers } from '../../../../shared/constants/app.constants';
import { NodeType, vSphereNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
import Broker from 'src/app/shared/service/broker';
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import {Subscription} from "rxjs";
import { VsphereTkgsService } from 'src/app/shared/service/vsphere-tkgs-data.service';

@Component({
    selector: 'app-wrk-nw-step',
    templateUrl: './wrk-nw.component.html',
    styleUrls: ['./wrk-nw.component.scss']
})
export class WorkloadNodeSettingComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    @Input() errorNotification: string;

    nodeTypes: Array<NodeType> = [];
    PROVIDERS: Providers = PROVIDERS;
    vSphereNodeTypes: Array<NodeType> = vSphereNodeTypes;
    nodeType: string;
    additionalNoProxyInfo: string;
    fullNoProxy: string;
    enableNetworkName = true;
    networks = [];

    subscription: Subscription;
    segmentErrorMsg = 'Provided Workload Network Segment is not found, please select again from the drop-down';
    private uploadStatus = false;

    private wrkSegment;
    private wrkGateway;
    private wrkStartIp;
    private wrkEndIp;
    private wrkDnsServer;
    private wrkNtpServer;
    private serviceCidr;
    private workloadSegmentName;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private  dataService: VsphereTkgsService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'segmentName',
            new FormControl('', [Validators.required]));
        this.formGroup.addControl('workloadSegmentName',
            new FormControl('', [
                Validators.required,
                this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidClusterName()]
        ));
        this.formGroup.addControl(
            'gatewayAddress',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'startAddress',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'endAddress',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'dnsServer',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIps(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'ntpServer',
            new FormControl('', [
                Validators.required,
                this.validationService.isCommaSeparatedIpsOrFqdn(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'serviceCidr',
            new FormControl('10.96.0.0/22', [
                Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.networks = this.apiClient.networks;
        this.formGroup['canMoveToNext'] = () => {
            return (this.formGroup.valid && this.apiClient.TkgWrkNwValidated);
        };
        setTimeout(_ => {

            this.resurrectField('segmentName',
                [Validators.required],
                this.formGroup.get('segmentName').value);
            this.resurrectField('gatewayAddress',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('gatewayAddress').value);
            this.resurrectField('startAddress',
                [Validators.required, this.validationService.isValidIp()],
                this.formGroup.get('startAddress').value);
            this.resurrectField('endAddress',
                [Validators.required, this.validationService.isValidIp()],
                this.formGroup.get('endAddress').value);
            this.resurrectField('dnsServer',
                [Validators.required, this.validationService.isValidIps(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('dnsServer').value);
            this.resurrectField('ntpServer',
                [Validators.required, this.validationService.isCommaSeparatedIpsOrFqdn(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('ntpServer').value);
            this.resurrectField('serviceCidr',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('serviceCidr').value);

            this.formGroup.get('segmentName').valueChanges.subscribe(
                () => {
                this.apiClient.wrkSegmentError = false;
                this.segmentErrorMsg = null;
            });

            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentWrkSegment.subscribe(
                    (wrkSegment) => this.wrkSegment = wrkSegment);
                if (this.apiClient.networks.indexOf(this.wrkSegment) === -1) {
                    this.apiClient.wrkSegmentError = true;
                } else {
                    this.formGroup.get('segmentName').setValue(this.wrkSegment);
                    this.apiClient.wrkSegmentError = false;
                }
                this.subscription = this.dataService.currentWrkGateway.subscribe(
                    (wrkGateway) => this.wrkGateway = wrkGateway);
                this.formGroup.get('gatewayAddress').setValue(this.wrkGateway);
                this.subscription = this.dataService.currentWrkStartAddress.subscribe(
                    (wrkStartIp) => this.wrkStartIp = wrkStartIp);
                this.formGroup.get('startAddress').setValue(this.wrkStartIp);
                this.subscription = this.dataService.currentWrkEndAddress.subscribe(
                    (wrkEndIp) => this.wrkEndIp = wrkEndIp);
                this.formGroup.get('endAddress').setValue(this.wrkEndIp);
                this.subscription = this.dataService.currentWrkDnsValue.subscribe(
                    (dnsServer) => this.wrkDnsServer = dnsServer);
                this.formGroup.get('dnsServer').setValue(this.wrkDnsServer);
                this.subscription = this.dataService.currentWrkNtpValue.subscribe(
                    (ntpServer) => this.wrkNtpServer = ntpServer);
                this.formGroup.get('ntpServer').setValue(this.wrkNtpServer);
                this.subscription = this.dataService.currentWrkServiceCidr.subscribe(
                    (serviceCidr) => this.serviceCidr = serviceCidr);
                this.formGroup.get('serviceCidr').setValue(this.serviceCidr);
                this.subscription = this.dataService.currentWorkloadSegmentName.subscribe(
                    (networkName) => this.workloadSegmentName = networkName);
                this.formGroup.get('workloadSegmentName').setValue(this.workloadSegmentName);
            } else if(!this.uploadStatus) {
                this.subscription = this.dataService.currentDnsValue.subscribe(
                    (dns) => this.wrkDnsServer = dns);
                this.formGroup.get('dnsServer').setValue(this.wrkDnsServer);
                this.subscription = this.dataService.currentNtpValue.subscribe(
                    (ntp) => this.wrkNtpServer = ntp);
                this.formGroup.get('ntpServer').setValue(this.wrkNtpServer);
            }
            this.validateWrkNetwork();
        });
    }

    setSavedDataAfterLoad() {
        if (this.hasSavedData()) {
            this.formGroup.get('segmentName').setValue('');
        }
    }


    public validateWrkNetwork() {
        if (this.formGroup.get('gatewayAddress').valid &&
            this.formGroup.get('startAddress').valid &&
            this.formGroup.get('endAddress').valid) {
            const gatewayIp = this.formGroup.get('gatewayAddress').value;
            const startIp = this.formGroup.get('startAddress').value;
            const endIp = this.formGroup.get('endAddress').value;
            const block = new Netmask(gatewayIp);
            if (block.contains(startIp) && block.contains(endIp)) {
                this.apiClient.TkgWrkNwValidated = true;
                this.errorNotification = null;
            } else if (block.contains(startIp)) {
                this.apiClient.TkgWrkNwValidated = false;
                this.errorNotification = "The End IP is out of the provided subnet.";
            } else if (block.contains(endIp)) {
                this.apiClient.TkgWrkNwValidated = false;
                this.errorNotification = "The Start IP is out of the provided subnet.";
            } else {
                this.apiClient.TkgWrkNwValidated = false;
                this.errorNotification = "The Start and End IP are out of the provided subnet.";
            }
        }
    }

}
