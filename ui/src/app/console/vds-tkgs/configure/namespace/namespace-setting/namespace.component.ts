/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
/**
 * Angular Modules
 */
import { Component, OnInit, Input } from '@angular/core';
import {
    Validators,
    FormControl
} from '@angular/forms';
/**
 * App imports
 */
import { StepFormDirective } from 'src/app/views/landing/wizard/shared/step-form/step-form';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { Subscription } from 'rxjs';
import { VsphereTkgsService } from 'src/app/shared/service/vsphere-tkgs-data.service';

@Component({
    selector: 'app-namespace-spec-step',
    templateUrl: './namespace.component.html',
    styleUrls: ['./namespace.component.scss']
})
export class NamespaceComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;
    @Input() errorNotification: string;

    // Check if input spec is uploaded
    private uploadStatus = false;
    subscription: Subscription;
    displayInfo = false;
    private namespaceName;
    private namespaceDescription;
    private contentLib;
    public vmClass = [];
    private cpuLimit;
    private memLimit;
    private storageLimit;
    // List of selected VM Classes
    public selected = [];
    segmentErrorMsg = 'Provided Network Segment is not found, please select again from the drop-down';
    contentLibErrorMsg = 'Provided Content Library not found';
    public vmClassDisabled = true;

    public domainNames = [];
    public domainNameDisabled = true;
    public roles = ['OWNER', 'EDIT', 'VIEW'];
    public userORgroup = ['USER', 'GROUP'];
    public users = ['Admin', 'Guest', 'Test'];

    public disabled = false;
    public gotNamespaceInfo = false;

    constructor(private validationService: ValidationService,
                public apiClient: APIClient,
                private  dataService: VsphereTkgsService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'namespaceName',
            new FormControl('', [
                Validators.required,
            ])
        );
        this.formGroup.addControl(
            'newNamespaceName',
            new FormControl('', [])
        );
        this.formGroup.addControl(
            'namespaceDescription',
            new FormControl('', [])
        );

        this.formGroup.addControl(
            'contentLib',
            new FormControl('',
                [])
        );
        this.formGroup.addControl('vmClass',
            new FormControl('',
                [])
        );
        this.formGroup.addControl('cpuLimit',
            new FormControl('',
                [])
        );
        this.formGroup.addControl('memLimit',
            new FormControl('',
                [])
        );
        this.formGroup.addControl('storageLimit',
            new FormControl('',
                [])
        );
        this.formGroup.addControl('storageSpec',
            new FormControl('',
                []
        ));
        this.formGroup.addControl('newStoragePolicyLimit',
            new FormControl('',
                [])
        );
        this.formGroup.addControl('newStoragePolicy',
            new FormControl('',
                [])
        );
        this.formGroup['canMoveToNext'] = () => {
            if(this.formGroup.get('namespaceName').value === 'CREATE NEW'){
                this.AddNewPolicy();
                if (this.apiClient.storagePolicy.size > 0) {
                    return this.formGroup.valid;
                } else {
                    return false;
                }
            }else {
                return this.formGroup.valid;
            }
        };
        setTimeout(_ => {

            // Check for Input Spec Upload Status
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                // Set Namespace name from Input Spec
                this.subscription = this.dataService.currentNamespaceName.subscribe(
                    (namespaceName) => this.namespaceName = namespaceName);
                this.formGroup.get('namespaceName').setValue(this.namespaceName);
                // Set Namespace Description from Input Spec
                this.subscription = this.dataService.currentNamespaceDescription.subscribe(
                    (namespaceDescription) => this.namespaceDescription = namespaceDescription);
                this.formGroup.get('namespaceDescription').setValue(this.namespaceDescription);
                // Set Content Library from Input Spec
                this.subscription = this.dataService.currentNamespaceContentLib.subscribe(
                    (contentLib) => this.contentLib = contentLib);
                if (this.apiClient.contentLibs.indexOf(this.contentLib) === -1) {
                } else {
                    this.formGroup.get('contentLib').setValue(this.contentLib);
                }
                // Set CPU Limit from Input Spec
                this.subscription = this.dataService.currentCpuLimit.subscribe(
                    (cpuLimit) => this.cpuLimit = cpuLimit);
                this.formGroup.get('cpuLimit').setValue(this.cpuLimit);
                // Set Memory Limit from Input Spec
                this.subscription = this.dataService.currentMemoryLimit.subscribe(
                    (memLimit) => this.memLimit = memLimit);
                this.formGroup.get('memLimit').setValue(this.memLimit);
                // Set Storage Limit from Input Spec
                this.subscription = this.dataService.currentStorageLimit.subscribe(
                    (storageLimit) => this.storageLimit = storageLimit);
                this.formGroup.get('storageLimit').setValue(this.storageLimit);

            }
        });
    }

    setSavedDataAfterLoad() {
        if (this.hasSavedData()) {
        }
    }

    public fetchVMClasses() {
        // Dumy
        console.log('Inside VM Class Fetch');
        this.vmClass = ['Dumy-1', 'Dumy-2', 'Dumy-3'];
        this.vmClassDisabled = false;
    }

    public fetchDomainName() {
        // Dumy
        console.log('Inside Domain Name Fetch');
        this.domainNames = ['dom1', 'dom2', 'dom3'];
        this.domainNameDisabled = false;
    }

    public addAccessSpec(domain, role, userGroup, userVal) {
    }

    public deletePolicy(key: string) {
        this.apiClient.storagePolicy.delete(key);
        this.formGroup.get('storageSpec').setValue(this.apiClient.storagePolicy);
        for (let i = 0; i < this.apiClient.allowedStoragePolicy.length; i++) {
            if (this.apiClient.allowedStoragePolicy[i] === key) {
                this.apiClient.allowedStoragePolicy.splice(i, 1);
            }
        }
        this.AddNewPolicy();
    }
    public addStorageSpec(key: string, value: string) {
        if (key === '') {
            this.errorNotification = 'Policy name is required.';
        } else if (!this.apiClient.storagePolicy.has(key)) {
            this.apiClient.storagePolicy.set(key, value);
            this.apiClient.allowedStoragePolicy.push(key);
            this.formGroup.get('storageSpec').setValue(this.apiClient.storagePolicy);
            this.formGroup.controls.newStoragePolicy.setValue('');
            this.formGroup.controls.newStoragePolicyLimit.setValue('');
        } else {
            this.errorNotification = 'Storage Spec with same storage policy already exists';
        }
        this.AddNewPolicy();
    }

    public AddNewPolicy() {
        if (this.formGroup.get('newStoragePolicy').valid && this.formGroup.get('newStoragePolicyLimit').valid) {
            if (this.formGroup.get('newStoragePolicy').value !== '') {
                this.displayInfo = true;
            } else {
                this.displayInfo = false;
            }
        }
        if (this.apiClient.storagePolicy.size > 0) {
            this.resurrectField(
                'newStoragePolicy',
                [],
                this.formGroup.value.newStoragePolicy);
            this.resurrectField(
                'newStoragePolicyLimit',
                [],
                this.formGroup.value.newStoragePolicyLimit);
        } else {
            this.resurrectField(
                'newStoragePolicy',
                [Validators.required],
                this.formGroup.value.newStoragePolicy);
            this.resurrectField(
                'newStoragePolicyLimit',
                [],
                this.formGroup.value.newStoragePolicyLimit);
        }
    }

    public getNamespaceDetails(namespaceName){
        let vCenterData = {
            "address": this.apiClient.vcAddress,
            "user": this.apiClient.vcUser,
            "password": this.apiClient.vcPass,
            "namespace": namespaceName
        };
        this.apiClient.getNamespaceDetails(vCenterData, 'vsphere').subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.allowedStoragePolicy = data.STORAGE_POLICIES;
                    this.apiClient.selectedVmClass = data.VM_CLASSES;
                    this.gotNamespaceInfo = true;
                    this.errorNotification = null;
                } else if (data.responseType === 'ERROR') {
                    this.gotNamespaceInfo = false;
                    this.errorNotification = data.msg;
                }
            } else {
                this.gotNamespaceInfo = false;
                this.errorNotification = "Failed to capture Namespace storage spec";
            }
        }, (error: any) => {
            if (error.responseType === 'ERROR') {
                this.errorNotification = error.msg;
                this.gotNamespaceInfo = false;
            } else {
                this.gotNamespaceInfo = false;
                this.errorNotification = "Failed to capture Namespace storage spec";
            }
        });
    }
    public validateWrkNetwork() {
    }


    public addNewNamespace(){
        this.resurrectField('newNamespaceName', [
            Validators.required,
            this.validationService.noWhitespaceOnEnds(),
            this.validationService.isValidClusterName()],
            this.formGroup.value['newNamespaceName'])
        // Optional
        this.resurrectField('namespaceDescription', [
            this.validationService.noWhitespaceOnEnds()
        ], this.formGroup.value['namespaceDescription']);
        this.resurrectField('contentLib', [],
         this.formGroup.value['contentLib']);
        // Rqquired
        this.resurrectField('vmClass', [
            Validators.required],
         this.formGroup.value['vmClass']);
        this.resurrectField('cpuLimit', [
         this.validationService.noWhitespaceOnEnds()],
         this.formGroup.value['cpuLimit']);
        this.resurrectField('memLimit', [
         this.validationService.noWhitespaceOnEnds()],
         this.formGroup.value['memLimit']);
        this.resurrectField('storageLimit', [
         this.validationService.noWhitespaceOnEnds()],
         this.formGroup.value['storageLimit']);
        this.resurrectField('storageSpec', [],
         this.formGroup.value['storageSpec']);
        this.resurrectField('newStoragePolicyLimit', [],
         this.formGroup.value['newStoragePolicyLimit']);
        this.resurrectField('newStoragePolicy', [
            Validators.required],
         this.formGroup.value['newStoragePolicy']);
    }

    public useExistingNamespace(){
        const newNamespaceFields = [
            'newNamespaceName',
            'namespaceDescription',
            'contentLib',
            'vmClass',
            'cpuLimit',
            'memLimit',
            'storageLimit',
            'storageSpec',
            'newStoragePolicyLimit',
            'newStoragePolicy',
        ];
        newNamespaceFields.forEach((field) => {
            this.disarmField(field, false);
        });
    }

    public onNamespaceChange() {
        if (this.formGroup.get('namespaceName').value !== '' &&
            this.formGroup.get('namespaceName').value !== 'CREATE NEW') {
            if (this.apiClient.fetchNamespaceStorageSpec){
                this.getNamespaceDetails(this.formGroup.get('namespaceName').value);
            }
        }
    }

    public modifyFieldValidators(){
        if(this.formGroup.get('namespaceName').value === 'CREATE NEW') {
            this.addNewNamespace();
        } else {
            this.useExistingNamespace();
        }
        this.onNamespaceChange();
    }

}
