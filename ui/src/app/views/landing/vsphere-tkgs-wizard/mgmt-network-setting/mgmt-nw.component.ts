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
import { ClrLoadingState } from '@clr/angular';
import { distinctUntilChanged, takeUntil, debounceTime } from 'rxjs/operators';
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

const SupervisedField = ['startAddress'];

@Component({
    selector: 'app-mgmt-nw-step',
    templateUrl: './mgmt-nw.component.html',
    styleUrls: ['./mgmt-nw.component.scss']
})
export class NodeSettingStepComponent extends StepFormDirective implements OnInit {
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
    loadingState: ClrLoadingState = ClrLoadingState.DEFAULT;
    subscription: Subscription;
    segmentErrorMsg = 'Provided Management segment name is not found, please select again from the drop-down';
    private uploadStatus = false;

    private mgmtSegment;
    private mgmtGateway;
    private mgmtStartIp;
    private mgmtDnsServer;
    private mgmtSearchDomain;
    private mgmtNtpServer;

    public pingTest = false;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private  dataService: VsphereTkgsService) {

        super();
        this.nodeTypes = [...vSphereNodeTypes];
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'segmentName',
            new FormControl('', [Validators.required]));
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
            'dnsServer',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIps(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('ntpServer',
            new FormControl('', [
                Validators.required,
                this.validationService.isCommaSeparatedIpsOrFqdn(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('searchDomain',
            new FormControl('', [
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        SupervisedField.forEach(field => {
            this.formGroup.get(field).valueChanges.pipe(
                debounceTime(500),
                distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr)),
                takeUntil(this.unsubscribe))
                .subscribe(() => {
                    this.pingTest = false;
                    this.loadingState = ClrLoadingState.DEFAULT;
            });
        });
        this.networks = this.apiClient.networks;
        this.formGroup['canMoveToNext'] = () => {
            return (this.formGroup.valid && this.apiClient.TkgMgmtNwValidated);
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
            this.resurrectField('dnsServer',
                [Validators.required, this.validationService.isValidIps(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('dnsServer').value);
            this.resurrectField('ntpServer',
                [Validators.required, this.validationService.isCommaSeparatedIpsOrFqdn(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('ntpServer').value);
            this.resurrectField('searchDomain',
                [this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('searchDomain').value);

            this.formGroup.get('segmentName').valueChanges.subscribe(
                () => {
                this.apiClient.mgmtSegmentError = false;
                this.segmentErrorMsg = null;
            });

            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentMgmtSegment.subscribe(
                    (mgmtSegment) => this.mgmtSegment = mgmtSegment);
                if (this.apiClient.networks.indexOf(this.mgmtSegment) === -1) {
                    this.apiClient.mgmtSegmentError = true;
                } else {
                    this.formGroup.get('segmentName').setValue(this.mgmtSegment);
                    this.apiClient.mgmtSegmentError = false;
                }
                this.subscription = this.dataService.currentMgmtGateway.subscribe(
                    (mgmtGateway) => this.mgmtGateway = mgmtGateway);
                this.formGroup.get('gatewayAddress').setValue(this.mgmtGateway);
                this.subscription = this.dataService.currentMgmtStartAddress.subscribe(
                    (mgmtStartIp) => this.mgmtStartIp = mgmtStartIp);
                this.formGroup.get('startAddress').setValue(this.mgmtStartIp);

                this.subscription = this.dataService.currentMgmtDnsValue.subscribe(
                    (dnsServer) => this.mgmtDnsServer = dnsServer);
                this.formGroup.get('dnsServer').setValue(this.mgmtDnsServer);
                this.subscription = this.dataService.currentMgmtNtpValue.subscribe(
                    (ntpServer) => this.mgmtNtpServer = ntpServer);
                this.formGroup.get('ntpServer').setValue(this.mgmtNtpServer);
                this.subscription = this.dataService.currentMgmtSearchDomainValue.subscribe(
                    (searchDomain) => this.mgmtSearchDomain = searchDomain);
                this.formGroup.get('searchDomain').setValue(this.mgmtSearchDomain);
            } else if(!this.uploadStatus) {
                this.subscription = this.dataService.currentDnsValue.subscribe(
                    (dns) => this.mgmtDnsServer = dns);
                this.formGroup.get('dnsServer').setValue(this.mgmtDnsServer);
                this.subscription = this.dataService.currentNtpValue.subscribe(
                    (ntp) => this.mgmtNtpServer = ntp);
                this.formGroup.get('ntpServer').setValue(this.mgmtNtpServer);
                this.subscription = this.dataService.currentSearchDomainValue.subscribe(
                    (searchDomain) => this.mgmtSearchDomain = searchDomain);
                this.formGroup.get('searchDomain').setValue(this.mgmtSearchDomain);
            }
            this.validateMgmtNetwork();
        });
    }

    setSavedDataAfterLoad() {
        if (this.hasSavedData()) {
            this.formGroup.get('segmentName').setValue('');
        }
    }


    public validateMgmtNetwork() {
        if (this.formGroup.get('gatewayAddress').valid &&
            this.formGroup.get('startAddress').valid) {
            const gatewayIp = this.formGroup.get('gatewayAddress').value;
            const startIp = this.formGroup.get('startAddress').value;
            const block = new Netmask(gatewayIp);
            if (block.contains(startIp)) {
                this.apiClient.TkgMgmtNwValidated = true;
                this.errorNotification = null;
            } else {
                this.apiClient.TkgMgmtNwValidated = false;
                this.errorNotification = "The Start IP is out of the provided subnet.";
            }
        }
    }

    public pingTestMgmt() {
        this.loadingState = ClrLoadingState.LOADING;
        let vCenterData = {
            "vcenterAddress": "",
            "ssoUser": "",
            "ssoPassword": "",
            "cluster": "",
            "datacenter": "",
            "startIp": ""
        };
        this.dataService.currentVcAddress.subscribe(
            (vcFqdn) => vCenterData['vcenterAddress'] = vcFqdn);
        this.dataService.currentVcUser.subscribe(
            (user) => vCenterData['ssoUser'] = user);
        this.dataService.currentVcPass.subscribe(
            (pass) => vCenterData['ssoPassword'] = pass);
        this.dataService.currentCluster.subscribe(
            (cluster) => vCenterData['cluster'] = cluster);
        this.dataService.currentDatacenter.subscribe(
            (datacenter) => vCenterData['datacenter'] = datacenter);
        vCenterData['startIp'] = this.formGroup.get('startAddress').value;
        this.apiClient.pingTestSupervisor(vCenterData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.pingTest = true;
                    this.loadingState = ClrLoadingState.DEFAULT;
                } else if (data.responseType === 'ERROR') {
                    this.pingTest = false;
                    this.errorNotification = data.msg;
                    this.loadingState = ClrLoadingState.DEFAULT;
                }
            } else {
                this.pingTest = false;
                this.errorNotification = "Ping test failed for Supervisor Control Plane VMs' network interface Ips";
                this.loadingState = ClrLoadingState.DEFAULT;
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.pingTest = false;
                this.errorNotification = "Ping Test: " + err.msg;
                this.loadingState = ClrLoadingState.DEFAULT;
            } else {
                this.pingTest = false;
                this.errorNotification = "Ping test failed for Supervisor Control Plane VMs' network interface Ips";
                this.loadingState = ClrLoadingState.DEFAULT;
            }
        });
    }

    onStartIpChange(){
        if(this.formGroup.get('startAddress').valid){
            if (this.formGroup.get('startAddress').value !== ""){
                this.pingTestMgmt();
            }
        }
    }


    getDisabled(): boolean {
        return !(this.formGroup.get('startAddress').valid);
    }
}
