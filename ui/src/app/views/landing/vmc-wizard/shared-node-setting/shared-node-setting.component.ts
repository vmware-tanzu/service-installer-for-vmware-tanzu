/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
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
import { NodeType, sharedServiceNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
// import { KUBE_VIP, NSX_ADVANCED_LOAD_BALANCER } from '../../wizard/shared/components/steps/load-balancer/load-balancer-step.component';
import Broker from 'src/app/shared/service/broker';
import { WizardBaseDirective } from 'src/app/views/landing/wizard/shared/wizard-base/wizard-base';
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import {Subscription} from 'rxjs';
import {VMCDataService} from '../../../../shared/service/vmc-data.service';

@Component({
    selector: 'app-shared-node-setting-step',
    templateUrl: './shared-node-setting.component.html',
    styleUrls: ['./shared-node-setting.component.scss']
})
export class SharedNodeSettingComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    @Input() errorNotification: string;

    nodeTypes: Array<NodeType> = [];
    PROVIDERS: Providers = PROVIDERS;
    sharedServiceNodeTypes: Array<NodeType> = sharedServiceNodeTypes;
    nodeType: string;
    additionalNoProxyInfo: string;
    fullNoProxy: string;
    enableNetworkName = true;
    networks = [];
    mgmtSegmentName: string;
    wizardBase: WizardBaseDirective;

    subscription: Subscription;
    private uploadStatus = false;

    private controlPlaneSetting;
    private devInstanceType;
    private prodInstanceType;
    private sharedCluster;

    private sharedGateway;
    private workerNodeCount;
    private sharedDhcpStart;
    private sharedDhcpEnd;
    private sharedClusterCidr;
    private sharedServiceCidr;

    private enableHarbor;
    private harborFqdn;
    private harborPassword;
    private harborCertPath;
    private harborCertKeyPath;
    private sharedBaseImage;
    private sharedBaseImageVersion;
    // Storage Setting Fields
    private sharedCpu;
    private sharedMemory;
    private sharedStorage;
    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private  dataService: VMCDataService) {

        super();
        this.nodeTypes = [...sharedServiceNodeTypes];
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'controlPlaneSetting',
            new FormControl('', [
                Validators.required
            ])
        );
        this.formGroup.addControl(
            'devInstanceType',
            new FormControl('', [
                Validators.required
            ])
        );
        this.formGroup.addControl(
            'prodInstanceType',
            new FormControl('', [
                Validators.required
            ])
        );
        this.formGroup.addControl(
            'clusterName',
            new FormControl('', [
                this.validationService.isValidClusterName(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'gatewayAddress',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'sharedServiceDhcpStartRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'sharedServiceDhcpEndRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('workerNodeCount', new FormControl('',
            [Validators.required]));
        this.formGroup.addControl('clusterCidr',
            new FormControl('100.96.0.0/11', [Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('serviceCidr',
            new FormControl('100.64.0.0/13', [Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('baseImage', new FormControl('', [Validators.required]));
        this.formGroup.addControl('baseImageVersion', new FormControl('', [Validators.required]));
        this.formGroup.addControl('harborFqdn', new FormControl('',
            [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('harborPassword', new FormControl('',
            [Validators.required]));
        this.formGroup.addControl('harborCertPath', new FormControl('', [this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('harborCertKeyPath', new FormControl('', [this.validationService.noWhitespaceOnEnds()]));
        // Custom Storage Settings
        this.formGroup.addControl('sharedCpu',
            new FormControl('', [Validators.min(2)]));
        this.formGroup.addControl('sharedMemory',
            new FormControl('', [Validators.min(8)]));
        this.formGroup.addControl('sharedStorage',
            new FormControl('', [Validators.min(40)]));
        this.formGroup['canMoveToNext'] = () => {
            this.onTkgSharedValidateClick();
            this.setMinWorker();
            return (this.formGroup.valid && this.apiClient.TkgSharedNwValidated);
        };
        setTimeout(_ => {
            this.formGroup.get('controlPlaneSetting').valueChanges.subscribe(data => {
                if (data === 'dev') {
                    this.nodeType = 'dev';
                    this.formGroup.get('devInstanceType').setValidators([
                        Validators.required
                    ]);
                    this.formGroup.controls['prodInstanceType'].clearValidators();
                    this.formGroup.controls['prodInstanceType'].setValue('');
                } else if (data === 'prod') {
                    this.nodeType = 'prod';
                    this.formGroup.controls['prodInstanceType'].setValidators([
                        Validators.required
                    ]);
                    this.formGroup.get('devInstanceType').clearValidators();
                    this.formGroup.controls['devInstanceType'].setValue('');
                }
                this.formGroup.get('devInstanceType').updateValueAndValidity();
                this.formGroup.controls['prodInstanceType'].updateValueAndValidity();
            });
            this.formGroup.get('workerNodeCount').valueChanges.subscribe(data => {
                if(this.apiClient.tmcEnabled){
                    this.formGroup.get('workerNodeCount').setValidators([
                        Validators.required, Validators.min(3)]);
                }else{
                    this.formGroup.get('workerNodeCount').setValidators([
                        Validators.required, Validators.min(1)]);
                }
            });
            if (this.edition !== AppEdition.TKG) {
                this.resurrectField('clusterName',
                    [Validators.required,
                    this.validationService.isValidClusterName(),
                    this.validationService.noWhitespaceOnEnds()],
                    this.formGroup.get('clusterName').value);
            }
            this.resurrectField('gatewayAddress',
                [Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('gatewayAddress').value);
            this.resurrectField('sharedServiceDhcpStartRange',
                [Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('sharedServiceDhcpStartRange').value);
            this.resurrectField('sharedServiceDhcpEndRange',
                [Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('sharedServiceDhcpEndRange').value);
            this.resurrectField('workerNodeCount',
                [Validators.required],
                this.formGroup.get('workerNodeCount').value);
            this.resurrectField('clusterCidr',
                [Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('clusterCidr').value);
            this.resurrectField('serviceCidr',
                [Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('serviceCidr').value);
            this.formGroup.get('sharedServiceDhcpEndRange').valueChanges.subscribe(
                () => this.apiClient.TkgSharedNwValidated = false);
            this.formGroup.get('sharedServiceDhcpStartRange').valueChanges.subscribe(
                () => this.apiClient.TkgSharedNwValidated = false);

            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (!this.uploadStatus) {
//                 this.subscription = this.dataService.currentSharedGateway.subscribe(
//                     (gatewayIp) => this.sharedGateway = gatewayIp);
//                 this.formGroup.get('gatewayAddress').setValue(this.sharedGateway);
            }
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentSharedDeploymentType.subscribe(
                    (controlPlaneSetting) => this.controlPlaneSetting = controlPlaneSetting);
                this.formGroup.get('controlPlaneSetting').setValue(this.controlPlaneSetting);

                if (this.controlPlaneSetting === 'dev') {
                    this.subscription = this.dataService.currentSharedDeploymentSize.subscribe(
                        (devInstanceType) => this.devInstanceType = devInstanceType);
                    this.formGroup.get('devInstanceType').setValue(this.devInstanceType);
                } else if (this.controlPlaneSetting === 'prod') {
                    this.subscription = this.dataService.currentSharedDeploymentSize.subscribe(
                        (prodInstanceType) => this.prodInstanceType = prodInstanceType);
                    this.formGroup.get('prodInstanceType').setValue(this.prodInstanceType);
                }
                if (this.devInstanceType === 'custom' || this.prodInstanceType === 'custom'){
                    this.subscription = this.dataService.currentSharedCpu.subscribe(
                        (cpu) => this.sharedCpu = cpu);
                    this.formGroup.get('sharedCpu').setValue(this.sharedCpu);
                    this.subscription = this.dataService.currentSharedStorage.subscribe(
                        (storage) => this.sharedStorage = storage);
                    this.formGroup.get('sharedStorage').setValue(this.sharedStorage);
                    this.subscription = this.dataService.currentSharedMemory.subscribe(
                        (memory) => this.sharedMemory = memory);
                    this.formGroup.get('sharedMemory').setValue(this.sharedMemory);
                }
                this.subscription = this.dataService.currentSharedClusterName.subscribe(
                    (sharedCluster) => this.sharedCluster = sharedCluster);
                this.formGroup.get('clusterName').setValue(this.sharedCluster);

                this.subscription = this.dataService.currentSharedWorkerNodeCount.subscribe(
                    (workerNodeCount) => this.workerNodeCount = workerNodeCount);
                if (this.workerNodeCount >= 1) {
                    this.formGroup.get('workerNodeCount').setValue(this.workerNodeCount);
                }

                this.subscription = this.dataService.currentSharedGateway.subscribe(
                    (sharedGateway) => this.sharedGateway = sharedGateway);
                this.formGroup.get('gatewayAddress').setValue(this.sharedGateway);

                this.subscription = this.dataService.currentSharedDhcpStart.subscribe(
                    (dhcpStart) => this.sharedDhcpStart = dhcpStart);
                this.formGroup.get('sharedServiceDhcpStartRange').setValue(this.sharedDhcpStart);

                this.subscription = this.dataService.currentSharedDhcpEnd.subscribe(
                    (dhcpEnd) => this.sharedDhcpEnd = dhcpEnd);
                this.formGroup.get('sharedServiceDhcpEndRange').setValue(this.sharedDhcpEnd);
                this.subscription = this.dataService.currentSharedClusterCidr.subscribe(
                    (sharedClusterCidr) => this.sharedClusterCidr = sharedClusterCidr);
                this.formGroup.get('clusterCidr').setValue(this.sharedClusterCidr);
                this.subscription = this.dataService.currentSharedServiceCidr.subscribe(
                    (sharedServiceCidr) => this.sharedServiceCidr = sharedServiceCidr);
                this.formGroup.get('serviceCidr').setValue(this.sharedServiceCidr);
                this.subscription = this.dataService.currentSharedBaseImage.subscribe(
                    (sharedBaseImage) => this.sharedBaseImage = sharedBaseImage);
                this.subscription = this.dataService.currentSharedBaseImageVersion.subscribe(
                    (sharedBaseImageVersion) => this.sharedBaseImageVersion = sharedBaseImageVersion);
                if (this.apiClient.baseImage.indexOf(this.sharedBaseImage) !== -1) {
                    this.formGroup.get('baseImage').setValue(this.sharedBaseImage);
                    // this.getBaseOsVersion();
                }
                if (this.apiClient.baseImageVersion.indexOf(this.sharedBaseImageVersion) !== -1) {
                    this.formGroup.get('baseImageVersion').setValue(this.sharedBaseImageVersion);
                }

                this.subscription = this.dataService.currentHarborFqdn.subscribe(
                    (harborFqdn) => this.harborFqdn = harborFqdn);
                this.formGroup.get('harborFqdn').setValue(this.harborFqdn);
                this.subscription = this.dataService.currentHarborPassword.subscribe(
                    (harborPassword) => this.harborPassword = harborPassword);
                this.formGroup.get('harborPassword').setValue(this.harborPassword);
                this.subscription = this.dataService.currentHarborCertPath.subscribe(
                    (harborCertPath) => this.harborCertPath = harborCertPath);
                this.formGroup.get('harborCertPath').setValue(this.harborCertPath);
                this.subscription = this.dataService.currentHarborCertKey.subscribe(
                    (harborCertKeyPath) => this.harborCertKeyPath = harborCertKeyPath);
                this.formGroup.get('harborCertKeyPath').setValue(this.harborCertKeyPath);
                let gatewayIp = this.sharedGateway;
                if ((this.sharedGateway !== '') && (this.sharedDhcpStart !== '') && (this.sharedDhcpEnd !== '')) {
                    const block = new Netmask(gatewayIp);
                    if (block.contains(this.sharedDhcpStart) && block.contains(this.sharedDhcpEnd)) {
                        this.apiClient.TkgSharedNwValidated = true;
                        this.errorNotification = '';
                    } else if (!(block.contains(this.sharedDhcpStart)) && !(block.contains(this.sharedDhcpEnd))) {
                        this.apiClient.TkgSharedNwValidated = false;
                        this.errorNotification = 'DHCP Start and End IP is out of the provided subnet';
                    } else if (!block.contains(this.sharedDhcpStart)) {
                        this.apiClient.TkgSharedNwValidated = false;
                        this.errorNotification = 'DHCP Start IP is out of the provided subnet';
                    } else if (!block.contains(this.sharedDhcpEnd)) {
                         this.apiClient.TkgSharedNwValidated = false;
                         this.errorNotification = 'DHCP End IP is out of the provided subnet';
                    }
                }
                this.onTkgSharedValidateClick();
            }
        });
        this.networks = this.apiClient.networks;
        }

    setSavedDataAfterLoad() {
        if (this.hasSavedData()) {
            this.cardClick(this.getSavedValue('devInstanceType', '') === '' ? 'prod' : 'dev');
            super.setSavedDataAfterLoad();
            // set the node type ID by finding it by the node type name
            let savedNodeType = this.nodeTypes.find(n => n.name === this.getSavedValue('devInstanceType', ''));
            if (savedNodeType) {
                this.formGroup.get('devInstanceType').setValue(savedNodeType.id);
            }
            savedNodeType = this.nodeTypes.find(n => n.name === this.getSavedValue('prodInstanceType', ''));
            if (savedNodeType) {
                this.formGroup.get('prodInstanceType').setValue(savedNodeType.id);
            }
            if (!this.uploadStatus) {
                this.formGroup.get('harborPassword').setValue('');
            } else {
                this.formGroup.get('harborPassword').setValue('');
            }
        }
    }

    cardClick(envType: string) {
        this.formGroup.controls['controlPlaneSetting'].setValue(envType);
    }

    getEnvType(): string {
        return this.formGroup.controls['controlPlaneSetting'].value;
    }

    getBaseOsVersion() {
        this.apiClient.getKubeVersions('vmc').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.baseImageVersion = data.KUBE_VERSION_LIST;
                    this.formGroup.get('baseImageVersion').enable();
                    if (this.uploadStatus) {
                        if (this.sharedBaseImageVersion !== '') {
                            if (this.apiClient.baseImageVersion.indexOf(this.sharedBaseImageVersion) !== -1) {
                                this.formGroup.get('baseImageVersion').setValue(this.sharedBaseImageVersion);
                            }
                        }
                    }
                } else if (data.responseType === 'ERROR') {
                    this.errorNotification = 'Base OS Version: ' + data.msg;
                }
            } else {
                this.errorNotification = 'Base OS Version: Some Error occurred while fetching Kube Versions';
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.errorNotification = 'Base OS Version: ' + error.msg;
            } else {
                this.errorNotification = 'Base OS Version: Some Error occurred while fetching Kube Versions';
            }
        });
    }

    onBaseOsChange() {
        if (this.formGroup.get('baseImage').valid) {
            if (this.formGroup.get('baseImage').value !== '') {
                this.getBaseOsVersion();
            }
        }
    }

    setMinWorker() {
        if (this.apiClient.tmcEnabled) {
            this.formGroup.get('workerNodeCount').setValidators([Validators.min(3), Validators.required]);
        } else {
            this.formGroup.get('workerNodeCount').setValidators([Validators.min(1), Validators.required]);
        }
    }

    public onTkgSharedValidateClick() {
        if (this.formGroup.get('gatewayAddress').valid &&
            this.formGroup.get('sharedServiceDhcpStartRange').valid &&
            this.formGroup.get('sharedServiceDhcpEndRange').valid) {
            const gatewayIp = this.formGroup.get('gatewayAddress').value;
            const block = new Netmask(gatewayIp);
            const dhcpStart = this.formGroup.get('sharedServiceDhcpStartRange').value;
            const dhcpEnd = this.formGroup.get('sharedServiceDhcpEndRange').value;
            if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                this.apiClient.TkgSharedNwValidated = true;
                this.errorNotification = '';
            } else if (!(block.contains(dhcpStart)) && !(block.contains(dhcpEnd))) {
                this.apiClient.TkgSharedNwValidated = false;
                this.errorNotification = 'DHCP Start and End IP is out of the provided subnet';
            } else if (!block.contains(dhcpStart)) {
                this.apiClient.TkgSharedNwValidated = false;
                this.errorNotification = 'DHCP Start IP is out of the provided subnet';
            } else if (!block.contains(dhcpEnd)) {
                 this.apiClient.TkgSharedNwValidated = false;
                 this.errorNotification = 'DHCP End IP is out of the provided subnet';
            }
        }
    }
    checkCustom() {
        const storageFields = [
            'sharedCpu',
            'sharedMemory',
            'sharedStorage',
        ];
        if (this.formGroup.get('devInstanceType').valid ||
            this.formGroup.get('prodInstanceType').valid) {
            if (this.formGroup.get('devInstanceType').value === 'custom' ||
                this.formGroup.get('prodInstanceType').value === 'custom') {
                this.resurrectField('sharedCpu', [
                    Validators.required,
                    Validators.min(2)],
                    this.formGroup.value['sharedCpu']);
                this.resurrectField('sharedMemory', [
                    Validators.required,
                    Validators.min(8)],
                    this.formGroup.value['sharedMemory']);
                this.resurrectField('sharedStorage', [
                    Validators.required,
                    Validators.min(40)],
                    this.formGroup.value['sharedStorage']);
            } else {
                storageFields.forEach((field) => {
                    this.disarmField(field, true);
                });
            }
        }
    }
}
