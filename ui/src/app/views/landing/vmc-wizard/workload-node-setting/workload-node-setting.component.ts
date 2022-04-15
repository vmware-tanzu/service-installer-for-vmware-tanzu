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
import { NodeType, vSphereNodeTypes, toNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
// import { KUBE_VIP, NSX_ADVANCED_LOAD_BALANCER } from '../../wizard/shared/components/steps/load-balancer/load-balancer-step.component';
import Broker from 'src/app/shared/service/broker';
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import {Subscription} from 'rxjs';
import {VMCDataService} from '../../../../shared/service/vmc-data.service';

@Component({
    selector: 'app-workload-node-setting-step',
    templateUrl: './workload-node-setting.component.html',
    styleUrls: ['./workload-node-setting.component.scss']
})
export class WorkloadNodeSettingComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    @Input() errorNotification: string;
    nodeTypes: Array<NodeType> = [];
    toNodeTypes: Array<NodeType> = [];
    PROVIDERS: Providers = PROVIDERS;
    vSphereNodeTypes: Array<NodeType> = vSphereNodeTypes;
    toClusterNodeTypes: Array<NodeType> = toNodeTypes;
    nodeType: string;
    additionalNoProxyInfo: string;
    fullNoProxy: string;
    enableNetworkName = true;
    networks = [];

    segmentErrorMsg = 'Workload Segment not found, please update the segment value from the drop-down list';
    subscription: Subscription;
    private uploadStatus = false;

    private controlPlaneSetting;
    private devInstanceType;
    private prodInstanceType;
    private wrkCluster;

    private wrkGateway;
    private workerNodeCount;
    private wrkDhcpStart;
    private wrkDhcpEnd;
    private wrkClusterCidr;
    private wrkServiceCidr;
    private enableTsm: boolean;
    private exactName;
    private startsWithName;
    private wrkBaseImage;
    private wrkBaseImageVersion;
    // Storage Setting Fields
    private wrkCpu;
    private wrkMemory;
    private wrkStorage;
//     private wrkControlPlaneEndpoint;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private  dataService: VMCDataService) {

        super();
        this.toClusterNodeTypes = [...toNodeTypes];
        this.nodeTypes = [...vSphereNodeTypes];
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
            'workloadDhcpStartRange',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl(
            'workloadDhcpEndRange',
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
        this.formGroup.addControl('tsmSettings', new FormControl(false));
        this.formGroup.addControl('exactName', new FormControl('', [this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('startsWithName', new FormControl('', [this.validationService.noWhitespaceOnEnds()]));
        // Custom Storage Settings
        this.formGroup.addControl('wrkCpu',
            new FormControl('', [Validators.min(2)]));
        this.formGroup.addControl('wrkMemory',
            new FormControl('', [Validators.min(8)]));
        this.formGroup.addControl('wrkStorage',
            new FormControl('', [Validators.min(40)]));
        this.formGroup['canMoveToNext'] = () => {
            this.onTkgWrkValidateClick();
            this.setMinWorker();
            return (this.formGroup.valid && this.apiClient.TkgWrkNwValidated);
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
                    [Validators.required, this.validationService.isValidClusterName(),
                    this.validationService.noWhitespaceOnEnds()],
                    this.formGroup.get('clusterName').value);
                }
            this.resurrectField('gatewayAddress',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('gatewayAddress').value);
            this.resurrectField('workloadDhcpStartRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('workloadDhcpStartRange').value);
            this.resurrectField('workloadDhcpEndRange',
                [Validators.required, this.validationService.isValidIp(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('workloadDhcpEndRange').value);
            this.resurrectField('workerNodeCount',
                [Validators.required],
                this.formGroup.get('workerNodeCount').value);
            this.resurrectField('clusterCidr',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('clusterCidr').value);
            this.resurrectField('serviceCidr',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('serviceCidr').value);
            this.formGroup.get('gatewayAddress').valueChanges.subscribe(
                () => this.apiClient.TkgWrkNwValidated = false);
            this.formGroup.get('workloadDhcpStartRange').valueChanges.subscribe(
                () => this.apiClient.TkgWrkNwValidated = false);
            this.formGroup.get('workloadDhcpEndRange').valueChanges.subscribe(
                () => this.apiClient.TkgWrkNwValidated = false);

            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (!this.uploadStatus) {
            }
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentWrkDeploymentType.subscribe(
                (controlPlaneSetting) => this.controlPlaneSetting = controlPlaneSetting);
                this.formGroup.get('controlPlaneSetting').setValue(this.controlPlaneSetting);
                if (this.controlPlaneSetting === 'dev') {
                    this.subscription = this.dataService.currentWrkDeploymentSize.subscribe(
                        (devInstanceType) => this.devInstanceType = devInstanceType);
                    if (this.apiClient.toEnabled) {
                        if (['large', 'extra-large'].indexOf(this.devInstanceType) !== -1) {
                            this.formGroup.get('devInstanceType').setValue(this.devInstanceType);
                        }
                    } else {
                        if (['medium', 'large', 'extra-large'].indexOf(this.devInstanceType) !== -1) {
                            this.formGroup.get('devInstanceType').setValue(this.devInstanceType);
                        }
                    }
                } else if (this.controlPlaneSetting === 'prod') {
                    this.subscription = this.dataService.currentWrkDeploymentSize.subscribe(
                        (prodInstanceType) => this.prodInstanceType = prodInstanceType);
                    if (this.apiClient.toEnabled) {
                        if (['large', 'extra-large'].indexOf(this.prodInstanceType) !== -1) {
                            this.formGroup.get('prodInstanceType').setValue(this.prodInstanceType);
                        }
                    } else {
                        if (['medium', 'large', 'extra-large'].indexOf(this.prodInstanceType) !== -1) {
                            this.formGroup.get('prodInstanceType').setValue(this.prodInstanceType);
                        }
                    }
                }
                if (this.devInstanceType === 'custom' || this.prodInstanceType === 'custom'){
                    this.subscription = this.dataService.currentWrkCpu.subscribe(
                        (cpu) => this.wrkCpu = cpu);
                    this.formGroup.get('wrkCpu').setValue(this.wrkCpu);
                    this.subscription = this.dataService.currentWrkStorage.subscribe(
                        (storage) => this.wrkStorage = storage);
                    this.formGroup.get('wrkStorage').setValue(this.wrkStorage);
                    this.subscription = this.dataService.currentWrkMemory.subscribe(
                        (memory) => this.wrkMemory = memory);
                    this.formGroup.get('wrkMemory').setValue(this.wrkMemory);
                }
                this.subscription = this.dataService.currentWrkClusterName.subscribe(
                    (wrkCluster) => this.wrkCluster = wrkCluster);
                this.formGroup.get('clusterName').setValue(this.wrkCluster);
                this.subscription = this.dataService.currentWrkGateway.subscribe(
                    (wrkGateway) => this.wrkGateway = wrkGateway);
                this.formGroup.get('gatewayAddress').setValue(this.wrkGateway);
                this.subscription = this.dataService.currentWrkClusterCidr.subscribe(
                    (wrkClusterCidr) => this.wrkClusterCidr = wrkClusterCidr);
                this.formGroup.get('clusterCidr').setValue(this.wrkClusterCidr);
                this.subscription = this.dataService.currentWrkServiceCidr.subscribe(
                    (wrkServiceCidr) => this.wrkServiceCidr = wrkServiceCidr);
                this.formGroup.get('serviceCidr').setValue(this.wrkServiceCidr);

                this.subscription = this.dataService.currentWrkBaseImage.subscribe(
                    (wrkBaseImage) => this.wrkBaseImage = wrkBaseImage);
                this.subscription = this.dataService.currentWrkBaseImageVersion.subscribe(
                    (wrkBaseImageVersion) => this.wrkBaseImageVersion = wrkBaseImageVersion);
                if (this.apiClient.baseImage.indexOf(this.wrkBaseImage) !== -1) {
                    this.formGroup.get('baseImage').setValue(this.wrkBaseImage);
                    // this.getBaseOsVersion();
                }
                if (this.apiClient.baseImageVersion.indexOf(this.wrkBaseImageVersion) !== -1) {
                    this.formGroup.get('baseImageVersion').setValue(this.wrkBaseImageVersion);
                }

                this.subscription = this.dataService.currentWrkDhcpStart.subscribe(
                    (dhcpStart) => this.wrkDhcpStart = dhcpStart);
                this.formGroup.get('workloadDhcpStartRange').setValue(this.wrkDhcpStart);
                this.subscription = this.dataService.currentWrkDhcpEnd.subscribe(
                    (dhcpEnd) => this.wrkDhcpEnd = dhcpEnd);
                this.formGroup.get('workloadDhcpEndRange').setValue(this.wrkDhcpEnd);

                if ((this.wrkGateway !== '') && (this.wrkDhcpStart !== '') && (this.wrkDhcpEnd !== '')) {
                    const block = new Netmask(this.wrkGateway);
                    if (block.contains(this.wrkDhcpStart) && block.contains(this.wrkDhcpEnd)) {
                        this.apiClient.TkgWrkNwValidated = true;
                        this.errorNotification = '';
                    } else if (!block.contains(this.wrkDhcpStart) && !block.contains(this.wrkDhcpEnd)) {
                        this.apiClient.TkgWrkNwValidated = false;
                        this.errorNotification = 'DHCP Start and End IP is out of the provided subnet';
                    } else if (!block.contains(this.wrkDhcpStart)) {
                        this.apiClient.TkgWrkNwValidated = false;
                        this.errorNotification = 'DHCP Start IP is out of the provided subnet';
                    } else if (!block.contains(this.wrkDhcpEnd)) {
                        this.apiClient.TkgSharedNwValidated = false;
                        this.errorNotification = 'DHCP End IP is out of the provided subnet';
                    }
                }
//                 let tmc = this.form.get('vmcTanzuSaasSettingForm').get('tmcSettings').value;
                if (this.apiClient.tmcEnabled) {
                    this.subscription = this.dataService.currentEnableTSM.subscribe(
                        (tsmEnable) => this.enableTsm = tsmEnable);
                    this.formGroup.get('tsmSettings').setValue(this.enableTsm);
                    this.toggleTSMSetting();
                    if (this.enableTsm) {
                        this.subscription = this.dataService.currentExactNamespaceExclusion.subscribe(
                            (tsmExactName) => this.exactName = tsmExactName);
                        this.formGroup.get('exactName').setValue(this.exactName);
                        this.subscription = this.dataService.currentStartsWithNamespaceExclusion.subscribe(
                            (tsmStartsWith) => this.startsWithName = tsmStartsWith);
                        this.formGroup.get('startsWithName').setValue(this.startsWithName);
                    }
                } else {
                    this.formGroup.get('tsmSettings').setValue(false);
                    this.formGroup.get('exactName').setValue('');
                    this.formGroup.get('startsWithName').setValue('');
                }
                this.subscription = this.dataService.currentWrkWorkerNodeCount.subscribe(
                    (worker) => this.workerNodeCount = worker);
                if (this.apiClient.tmcEnabled) {
                    if (this.workerNodeCount >= 3) {
                        this.formGroup.get('workerNodeCount').setValue(this.workerNodeCount);
                    }
                } else {
                    if (this.workerNodeCount >= 1) {
                        this.formGroup.get('workerNodeCount').setValue(this.workerNodeCount);
                    }
                }
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
        }
    }

    cardClick(envType: string) {
        this.formGroup.controls['controlPlaneSetting'].setValue(envType);
    }

    getEnvType(): string {
        return this.formGroup.controls['controlPlaneSetting'].value;
    }

    setMinWorker() {
        if (this.apiClient.tmcEnabled) {
            this.formGroup.get('workerNodeCount').setValidators([Validators.min(3), Validators.required]);
        } else {
            this.formGroup.get('workerNodeCount').setValidators([Validators.min(1), Validators.required]);
        }
    }

    toggleTSMSetting() {
        const tsmSettingsFields = [
            'exactName',
            'startsWithName',
        ];
        if (this.apiClient.tmcEnabled && this.formGroup.value['tsmSettings']) {
            this.resurrectField('exactName', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['exactName']);
            this.resurrectField('startsWithName', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['startsWithName']);
        } else {
            tsmSettingsFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    getBaseOsVersion() {
        this.apiClient.getKubeVersions('vmc').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.baseImageVersion = data.KUBE_VERSION_LIST;
                    this.formGroup.get('baseImageVersion').enable();
                    if (this.uploadStatus) {
                        if (this.wrkBaseImageVersion !== '') {
                            if (this.apiClient.baseImageVersion.indexOf(this.wrkBaseImageVersion) !== -1) {
                                this.formGroup.get('baseImageVersion').setValue(this.wrkBaseImageVersion);
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

    public onTkgWrkValidateClick() {
        if (this.formGroup.get('gatewayAddress').valid &&
            this.formGroup.get('workloadDhcpStartRange').valid &&
            this.formGroup.get('workloadDhcpEndRange').valid) {
            const gatewayIp = this.formGroup.get('gatewayAddress').value;
            const dhcpStart = this.formGroup.get('workloadDhcpStartRange').value;
            const dhcpEnd = this.formGroup.get('workloadDhcpEndRange').value;
            const block = new Netmask(gatewayIp);
            if (block.contains(dhcpStart) && block.contains(dhcpEnd)) {
                this.apiClient.TkgWrkNwValidated = true;
                this.errorNotification = '';
            } else if (!(block.contains(dhcpStart)) && !(block.contains(dhcpEnd))) {
                this.apiClient.TkgWrkNwValidated = false;
                this.errorNotification = 'DHCP Start and End IP is out of the provided subnet';
            } else if (!block.contains(dhcpStart)) {
                this.apiClient.TkgWrkNwValidated = false;
                this.errorNotification = 'DHCP Start IP is out of the provided subnet';
            } else if (!block.contains(dhcpEnd)) {
                this.apiClient.TkgSharedNwValidated = false;
                this.errorNotification = 'DHCP End IP is out of the provided subnet';
            }
        }
    }
    checkCustom() {
        const storageFields = [
            'wrkCpu',
            'wrkMemory',
            'wrkStorage',
        ];
        if (this.formGroup.get('devInstanceType').valid ||
            this.formGroup.get('prodInstanceType').valid) {
            if (this.formGroup.get('devInstanceType').value === 'custom' ||
                this.formGroup.get('prodInstanceType').value === 'custom') {
                this.resurrectField('wrkCpu', [
                    Validators.required,
                    Validators.min(2)],
                    this.formGroup.value['wrkCpu']);
                this.resurrectField('wrkMemory', [
                    Validators.required,
                    Validators.min(8)],
                    this.formGroup.value['wrkMemory']);
                this.resurrectField('wrkStorage', [
                    Validators.required,
                    Validators.min(40)],
                    this.formGroup.value['wrkStorage']);
            } else {
                storageFields.forEach((field) => {
                    this.disarmField(field, true);
                });
            }
        }
    }
}
