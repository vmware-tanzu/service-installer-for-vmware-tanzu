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
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
/**
 * App imports
 */
import { PROVIDERS, Providers } from '../../../../shared/constants/app.constants';
import { NodeType, vSphereNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
import {APIClient} from 'src/app/swagger/api-client.service';
import {Subscription} from 'rxjs';
import { VsphereTkgsService } from 'src/app/shared/service/vsphere-tkgs-data.service';

@Component({
    selector: 'app-workload-cluster-step',
    templateUrl: './wrk-cluster.component.html',
    styleUrls: ['./wrk-cluster.component.scss']
})
export class WorkloadClusterComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    @Input() errorNotification: string;

    private namespaceName: string;
    private clusterName: string;
    private allowedStorageClass = [];
    private defaultStorageClass: string;
    private nodeStorageClass: string;
    private serviceCidr: string;
    private podCidr: string;
    private controlPlaneVmClass: string;
    private workerVmClass: string;
    private workerNodeCount;
    private enableHA;
    // TSM Input fields
    private exactName;
    private startsWithName;
    enableTsm = false;

    public allowedStorageOption = [];

    subscription: Subscription;
    segmentErrorMsg = 'Provided Workload Network Segment is not found, please select again from the drop-down';
    private uploadStatus = false;


    private namespaceDescription;
    private networkSegment;
    public vmClass = [];
    public vmClassDisabled = true;
    public domainNames = [];
    public domainNameDisabled = true;
    public roles = ['OWNER', 'EDIT', 'VIEW'];
    public userORgroup = ['USER', 'GROUP'];
    public users = ['Admin', 'Guest', 'Test'];


    selection: any;
    stateList: any[];
    public disabled = false;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private  dataService: VsphereTkgsService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'clusterName',
            new FormControl('', [
                Validators.required,
                this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidClusterName()
            ])
        );
        this.formGroup.addControl(
            'nodeStorageClass',
            new FormControl('',
                [Validators.required
            ])
        );
        this.formGroup.addControl(
            'clusterVersion',
            new FormControl('',
                [Validators.required
            ])
        );
        this.formGroup.addControl(
            'defaultStorageClass',
            new FormControl('',
                [Validators.required])
        );
        this.formGroup.addControl('allowedStorageClass',
            new FormControl('',
                [Validators.required
            ])
        );

        this.formGroup.addControl('controlPlaneVmClass',
            new FormControl('',
                [Validators.required
            ])
        );
        this.formGroup.addControl('workerVmClass',
            new FormControl('',
                [Validators.required
            ])
        );
        this.formGroup.addControl('enableHA', new FormControl(false));
        this.formGroup.addControl('podCidr',
            new FormControl('192.168.0.0/16', [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('serviceCidr',
            new FormControl('10.96.0.0/12', [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('workerNodeCount', new FormControl('',
            [Validators.required, Validators.pattern('^[0-9]*$')]));
        this.formGroup.addControl('tsmSettings', new FormControl(false));
        this.formGroup.addControl('exactName', new FormControl('', []));
        this.formGroup.addControl('startsWithName', new FormControl('', []));
        setTimeout(_ => {
            this.resurrectField('clusterName',
                [Validators.required,
                this.validationService.noWhitespaceOnEnds(),
                this.validationService.isValidClusterName()],
                this.formGroup.get('clusterName').value);

            this.resurrectField('nodeStorageClass',
                [Validators.required],
                this.formGroup.get('nodeStorageClass').value);
            this.resurrectField('defaultStorageClass',
                [Validators.required],
                this.formGroup.get('defaultStorageClass').value);
            this.resurrectField('allowedStorageClass',
                [Validators.required],
                this.formGroup.get('allowedStorageClass').value);
            this.resurrectField('podCidr',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('podCidr').value);
            this.resurrectField('serviceCidr',
                [Validators.required, this.validationService.isValidIpNetworkSegment(),
                this.validationService.noWhitespaceOnEnds()],
                this.formGroup.get('serviceCidr').value);
            this.resurrectField('controlPlaneVmClass',
                [Validators.required],
                this.formGroup.get('controlPlaneVmClass').value);
            this.resurrectField('workerVmClass',
                [Validators.required],
                this.formGroup.get('workerVmClass').value);
            this.resurrectField('workerNodeCount',
                [Validators.required],
                this.formGroup.get('workerNodeCount').value);
            // Check for Upload status on Input Spec File
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                // Set Workload Cluster Name from Input Spec
                this.subscription = this.dataService.currentWrkClusterName.subscribe(
                    (clusterName) => this.clusterName = clusterName);
                this.formGroup.get('clusterName').setValue(this.clusterName);
                // Set Workload Namespace Name from Input Spec
                // this.subscription = this.dataService.currentWrkNamespaceName.subscribe(
                //     (namespaceName) => this.namespaceName = namespaceName);
                // this.formGroup.get()
                // Set Workload Service CIDR from Input Spec
                this.subscription = this.dataService.currentServiceCidr.subscribe(
                    (serviceCidr) => this.serviceCidr = serviceCidr);
                if (this.serviceCidr !== '') {
                    this.formGroup.get('serviceCidr').setValue(this.serviceCidr);
                }
                // Set Workload Pod CIDR from Input Spec
                this.subscription = this.dataService.currentPodCidr.subscribe(
                    (podCidr) => this.podCidr = podCidr);
                if (this.podCidr !== '') {
                    this.formGroup.get('podCidr').setValue(this.podCidr);
                }

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
                    (workerNodeCount) => this.workerNodeCount = workerNodeCount);
                if (this.workerNodeCount >= 1) {
                    this.formGroup.get('workerNodeCount').setValue(this.workerNodeCount);
                }
                // Set Enable HA from Input Spec
                this.subscription = this.dataService.currentEnableHA.subscribe(
                    (enableHA) => this.enableHA = enableHA);
                this.formGroup.get('enableHA').setValue(this.enableHA);
            }
            this.toggleTSMSetting();
            });
    }

    setSavedDataAfterLoad() {
        if (this.hasSavedData()) {
        }
    }

    toggleTSMSetting() {
        const tsmSettingsFields = [
            'exactName',
            'startsWithName',
        ];
        if (this.apiClient.tmcEnabled && this.formGroup.value['tsmSettings']) {
            this.resurrectField('workerNodeCount', [Validators.min(3), Validators.required], this.formGroup.value['workerNodeCount']);
            this.resurrectField('exactName', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['exactName']);
            this.resurrectField('startsWithName', [this.validationService.noWhitespaceOnEnds()], this.formGroup.value['startsWithName']);
        } else {
            this.resurrectField('workerNodeCount', [Validators.min(1), Validators.required], this.formGroup.value['workerNodeCount']);
            tsmSettingsFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    toggleHarborSetting() {
        const harborSettingsFields = [
            'harborFqdn',
            'harborPassword',
            'harborCertPath',
            'harborCertKeyPath',
        ];
        if (this.formGroup.value['harborSettings']) {
            this.resurrectField('harborFqdn', [
                this.validationService.noWhitespaceOnEnds(),
                Validators.required,
                this.validationService.isValidFqdn()],
                this.formGroup.value['harborFqdn']);
            this.resurrectField('harborPassword', [
                Validators.required],
                this.formGroup.value['harborPassword']);
        } else {
            harborSettingsFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    public fetchVMClasses() {
        //Dumy
//         console.log("Inside VM Class Fetch");
        this.vmClass = ['Dumy-1', 'Dumy-2', 'Dumy-3'];
        this.vmClassDisabled = false;
//         this.formGroup.get('vmClass').enable();

//         let payload = {};
//         this.apiClient.getVmClasses(payload).subscribe((data: any) => {
//             if (data && data !== null) {
//                 if (data.responseType === 'SUCCESS') {
//                     this.vmClass = data.;
//                     this.formGroup.get('vmClass').enable();
//                 } else if(data.responseType === 'ERROR') {
//                     this.errorNotification = "VM Classes: " + data.msg;
//                     this.formGroup.get('vmClass').disable();
//                 }
//             } else {
//                 this.errorNotification = 'Some Error Occurred while Retrieving VM Classes';
//                 this.formGroup.get('vmClass').disable();
//             }
//         }, (err: any) => {
//             if (err.responseType === 'ERROR') {
//                 this.errorNotification = "VM Classes: " + data.msg;
//                 this.formGroup.get('vmClass').disable();
//             } else {
//                 this.errorNotification = 'Some Error Occurred while Retrieving VM Classes';
//                 this.formGroup.get('vmClass').disable();
//             }
//         });
    }

    public fetchDomainName() {
        //Dumy
//         console.log("Inside Domain Name Fetch");
        this.domainNames = ['dom1', 'dom2', 'dom3'];
        this.domainNameDisabled = false;
//         this.formGroup.get('vmClass').enable();

//         let payload = {};
//         this.apiClient.getDomainName(payload).subscribe((data: any) => {
//             if (data && data !== null) {
//                 if (data.responseType === 'SUCCESS') {
//                     this.domainName = data.;
//                     this.domainNameDisabled = false;
//                 } else if(data.responseType === 'ERROR') {
//                     this.errorNotification = "Domain Name: " + data.msg;
//                     this.domainNameDisabled = true;
//                 }
//             } else {
//                 this.errorNotification = 'Some Error Occurred while Retrieving Domain Name';
//                 this.domainNameDisabled = true;
//             }
//         }, (err: any) => {
//             if (err.responseType === 'ERROR') {
//                 this.errorNotification = "Domain Name: " + data.msg;
//                 this.domainNameDisabled = true;
//             } else {
//                 this.errorNotification = 'Some Error Occurred while Retrieving Domain Name';
//                 this.domainNameDisabled = true;
//             }
//         });
    }

    public addAccessSpec(domain, role, userGroup, userVal) {
    }

    public updateAllowedStorageClass() {
//         console.log(this.formGroup.get('allowedStorageClass').value);
        this.allowedStorageOption = this.formGroup.get('allowedStorageClass').value;
    }

    public validateWrkNetwork() {
//          console.log(this.formGroup.get('vmClass').value);
//         if (this.formGroup.get('gatewayAddress').valid &&
//             this.formGroup.get('startAddress').valid &&
//             this.formGroup.get('endAddress').valid) {
//             const gatewayIp = this.formGroup.get('gatewayAddress').value;
//             const startIp = this.formGroup.get('startAddress').value;
//             const endIp = this.formGroup.get('endAddress').value;
//             const block = new Netmask(gatewayIp);
//             if (block.contains(startIp) && block.contains(endIp)) {
//                 this.apiClient.TkgMgmtNwValidated = true;
//                 this.errorNotification = null;
//             } else if (block.contains(startIp)) {
//                 this.apiClient.TkgMgmtNwValidated = false;
//                 this.errorNotification = "The End IP is out of the provided subnet.";
//             } else if (block.contains(endIp)) {
//                 this.apiClient.TkgMgmtNwValidated = false;
//                 this.errorNotification = "The Start IP is out of the provided subnet.";
//             } else {
//                 this.apiClient.TkgMgmtNwValidated = false;
//                 this.errorNotification = "The Start and End IP are out of the provided subnet.";
//             }
//         }
    }

    public setEnableHA() {

    }

    public onClusterVersionChange(){
        if(this.formGroup.get('clusterVersion').valid){
            if(this.formGroup.get('clusterVersion').value !== ""){
                let clusterVersion = this.formGroup.get('clusterVersion').value;
                if(["v1.20.7+vmware.1-tkg.1.7fb9067", "v1.20.9+vmware.1-tkg.1.a4cee5b", "v1.21.2+vmware.1-tkg.1.ee25d55", "v1.21.6+vmware.1-tkg.1.b3d708a", "v1.21.6+vmware.1-tkg.1"].indexOf(clusterVersion) === -1){
                    this.apiClient.clusterVersionMismatch = true;
//                     this.formGroup.get('harborSettings').setValue(false);
//                     this.toggleHarborSetting();
//                     this.formGroup.get('harborSettings').disable();
                } else {
                    this.apiClient.clusterVersionMismatch = false;
//                     this.formGroup.get('harborSettings').enable();
                }
            }
        }
    }

}
