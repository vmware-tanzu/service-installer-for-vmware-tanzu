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
import { NodeType, vSphereNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
// import { KUBE_VIP, NSX_ADVANCED_LOAD_BALANCER } from '../../wizard/shared/components/steps/load-balancer/load-balancer-step.component';
import Broker from 'src/app/shared/service/broker';
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import {Subscription} from 'rxjs';
import {VMCDataService} from '../../../../shared/service/vmc-data.service';

@Component({
    selector: 'app-node-setting-step',
    templateUrl: './node-setting-step.component.html',
    styleUrls: ['./node-setting-step.component.scss']
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

    subscription: Subscription;
    segmentErrorMsg = 'Provided Management segment name is not found, please select again from the drop-down';
    private uploadStatus = false;

    private controlPlaneSetting;
    private devInstanceType;
    private prodInstanceType;
    private mgmtCluster;
    private mgmtSegment;
    private mgmtGateway;
    private mgmtClusterCidr;
    private mgmtServiceCidr;
    private mgmtBaseImage;
    // Storage Setting Fields
    private mgmtCpu;
    private mgmtMemory;
    private mgmtStorage;
//     private mgmtControlPlaneEndpoint;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private  dataService: VMCDataService) {

        super();
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
        this.formGroup.addControl('clusterCidr',
            new FormControl('100.96.0.0/11', [Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('serviceCidr',
            new FormControl('100.64.0.0/13', [Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('baseImage', new FormControl('', [Validators.required]));
        // Custom Storage Settings
        this.formGroup.addControl('mgmtCpu',
            new FormControl('', [Validators.min(2)]));
        this.formGroup.addControl('mgmtMemory',
            new FormControl('', [Validators.min(8)]));
        this.formGroup.addControl('mgmtStorage',
            new FormControl('', [Validators.min(40)]));
        this.networks = this.apiClient.networks;
        this.formGroup['canMoveToNext'] = () => {
            return (this.formGroup.valid && this.apiClient.TkgMgmtNwValidated);
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
            if (this.edition !== AppEdition.TKG) {
                this.resurrectField('clusterName',
                    [Validators.required, this.validationService.isValidClusterName(), this.validationService.noWhitespaceOnEnds()],
                    this.formGroup.get('clusterName').value);
                this.resurrectField('segmentName',
                    [Validators.required],
                    this.formGroup.get('segmentName').value);
                }
            this.resurrectField('gatewayAddress',
                [Validators.required,
                this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('gatewayAddress').value);
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
            this.formGroup.get('segmentName').valueChanges.subscribe(
                () => {
                    this.apiClient.mgmtSegmentError = false;
            });
            this.formGroup.get('gatewayAddress').valueChanges.subscribe(
                () => {
//                     this.apiClient.TkgMgmtNwValidated = false;
                    let gateway = this.formGroup.get('gatewayAddress').value;
                    this.dataService.changeMgmtGateway(gateway);
            });

            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (!this.uploadStatus) {
                this.dataService.changeMgmtGateway(this.formGroup.get('gatewayAddress').value);
            }
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentMgmtDeploymentType.subscribe(
                    (controlPlaneSetting) => this.controlPlaneSetting = controlPlaneSetting);
                this.formGroup.get('controlPlaneSetting').setValue(this.controlPlaneSetting);
                if (this.controlPlaneSetting === 'dev') {
                    this.subscription = this.dataService.currentMgmtDeploymentSize.subscribe(
                        (devInstanceType) => this.devInstanceType = devInstanceType);
                    this.formGroup.get('devInstanceType').setValue(this.devInstanceType);
                } else if (this.controlPlaneSetting === 'prod') {
                    this.subscription = this.dataService.currentMgmtDeploymentSize.subscribe(
                        (prodInstanceType) => this.prodInstanceType = prodInstanceType);
                    this.formGroup.get('prodInstanceType').setValue(this.prodInstanceType);
                }
                if (this.devInstanceType === 'custom' || this.prodInstanceType === 'custom'){
                    this.subscription = this.dataService.currentMgmtCpu.subscribe(
                        (cpu) => this.mgmtCpu = cpu);
                    this.formGroup.get('mgmtCpu').setValue(this.mgmtCpu);

                    this.subscription = this.dataService.currentMgmtStorage.subscribe(
                        (storage) => this.mgmtStorage = storage);
                    this.formGroup.get('mgmtStorage').setValue(this.mgmtStorage);

                    this.subscription = this.dataService.currentMgmtMemory.subscribe(
                        (memory) => this.mgmtMemory = memory);
                    this.formGroup.get('mgmtMemory').setValue(this.mgmtMemory);
                }
                this.subscription = this.dataService.currentMgmtClusterName.subscribe(
                    (mgmtCluster) => this.mgmtCluster = mgmtCluster);
                this.formGroup.get('clusterName').setValue(this.mgmtCluster);
                this.subscription = this.dataService.currentMgmtSegment.subscribe(
                    (mgmtSegment) => this.mgmtSegment = mgmtSegment);
                if (this.apiClient.networks.indexOf(this.mgmtSegment) === -1) {
                    this.apiClient.mgmtSegmentError = true;
                } else {
                    this.formGroup.get('segmentName').setValue(this.mgmtSegment);
                    this.apiClient.mgmtSegmentError = false;
                }
                this.subscription = this.dataService.currentMgmtBaseImage.subscribe(
                    (mgmtBaseImage) => this.mgmtBaseImage = mgmtBaseImage);
                if (this.apiClient.baseImage.indexOf(this.mgmtBaseImage) !== -1) {
                    this.formGroup.get('baseImage').setValue(this.mgmtBaseImage);
                }
                this.subscription = this.dataService.currentMgmtGateway.subscribe(
                    (mgmtGateway) => this.mgmtGateway = mgmtGateway);
                this.formGroup.get('gatewayAddress').setValue(this.mgmtGateway);
                this.subscription = this.dataService.currentMgmtClusterCidr.subscribe(
                    (mgmtClusterCidr) => this.mgmtClusterCidr = mgmtClusterCidr);
                this.formGroup.get('clusterCidr').setValue(this.mgmtClusterCidr);
                this.subscription = this.dataService.currentMgmtServiceCidr.subscribe(
                    (mgmtServiceCidr) => this.mgmtServiceCidr = mgmtServiceCidr);
                this.formGroup.get('serviceCidr').setValue(this.mgmtServiceCidr);
//                 this.onTkgMgmtValidateClick();
            }
            this.apiClient.TkgMgmtNwValidated = true;
        });
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
                this.formGroup.get('segmentName').setValue('');
            }
            else {
                this.formGroup.get('segmentName').setValue('');
            }
        }
    }

    cardClick(envType: string) {
        this.formGroup.controls['controlPlaneSetting'].setValue(envType);
    }

    getEnvType(): string {
        return this.formGroup.controls['controlPlaneSetting'].value;
    }

    public onTkgMgmtValidateClick() {
        let gatewayIp;
        this.apiClient.TkgMgmtNwValidated = true;
    }
    checkCustom() {
        const storageFields = [
            'mgmtCpu',
            'mgmtMemory',
            'mgmtStorage',
        ];
        if (this.formGroup.get('devInstanceType').valid ||
            this.formGroup.get('prodInstanceType').valid) {
            if (this.formGroup.get('devInstanceType').value === 'custom' ||
                this.formGroup.get('prodInstanceType').value === 'custom') {
                this.resurrectField('mgmtCpu', [
                    Validators.required,
                    Validators.min(2)],
                    this.formGroup.value['mgmtCpu']);
                this.resurrectField('mgmtMemory', [
                    Validators.required,
                    Validators.min(8)],
                    this.formGroup.value['mgmtMemory']);
                this.resurrectField('mgmtStorage', [
                    Validators.required,
                    Validators.min(40)],
                    this.formGroup.value['mgmtStorage']);
            } else {
                storageFields.forEach((field) => {
                    this.disarmField(field, true);
                });
            }
        }
    }
}
