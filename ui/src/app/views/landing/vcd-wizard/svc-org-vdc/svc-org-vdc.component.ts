/*
* Copyright 2021 VMware, Inc
* SPDX-License-Identifier: BSD-2-Clause
*/
/**
 * Angular Modules
 */
 import { Component, Input, OnInit } from '@angular/core';
 import { Validators, FormControl } from '@angular/forms';
 import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
 /**
  * App imports
  */
 import { VCDDataService } from 'src/app/shared/service/vcd-data.service';
 import { APIClient } from 'src/app/swagger/api-client.service';
 import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
 import { ValidationService } from '../../wizard/shared/validation/validation.service';
 import { Subscription } from 'rxjs';
@Component({
    selector: 'app-svc-org-vdc-step',
    templateUrl: './svc-org-vdc.component.html',
    styleUrls: ['./svc-org-vdc.component.scss'],
})
export class ServiceOrganizationVDCComponent extends StepFormDirective implements OnInit {
    @Input() InputProviderVDC: [];
    @Input() InputNetworkPoolName: [];
    @Input() InputStoragePolicies;

    private svcOrgVdcName;
    private providerVDC;
    private cpuAllocation;
    private cpuGuaranteed;
    private memoryAllocation;
    private memoryGuaranteed;
    private vcpuSpeed;
    private isElastic;
    private includeMemoryOverhead;
    private vmQuota;
    private thinProvisioning;
    private fastProvisioning;
    private networkPoolName;
    private networkQuota;

    private defaultStoragePolicy;
    public defaultPolicyList = [];
    displayInfo = true;


    // =========================== COMMON PROPERTIES ========================================
    private uploadStatus;
    subscription: Subscription;

    constructor(private validationService: ValidationService,
        private wizardFormService: VSphereWizardFormService,
        public apiClient: APIClient,
        public dataService: VCDDataService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();

        this.formGroup.addControl('svcOrgVdcName', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('providerVDC', new FormControl('', [Validators.required]));

        this.formGroup.addControl('cpuAllocation', new FormControl('', [Validators.required])); // GHz
        this.formGroup.addControl('cpuGuaranteed', new FormControl('20', [Validators.required])); // in percentage
        this.formGroup.addControl('memoryAllocation', new FormControl('', [Validators.required])); // GB
        this.formGroup.addControl('memoryGuaranteed', new FormControl('20', [Validators.required])); // in percentage

        this.formGroup.addControl('vcpuSpeed', new FormControl('1', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('vmQuota', new FormControl('100', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
        this.formGroup.addControl('defaultStoragePolicy', new FormControl('', [Validators.required]));
        this.formGroup.addControl('networkPoolName', new FormControl('', [Validators.required]));
        this.formGroup.addControl('networkQuota', new FormControl('100', [Validators.required, this.validationService.noWhitespaceOnEnds()]));

        this.formGroup.addControl('storageLimit', new FormControl('', []));
        this.formGroup.addControl('storageSpec', new FormControl('', []));
        this.formGroup.addControl('newStoragePolicyLimit', new FormControl('', []));
        this.formGroup.addControl('newStoragePolicy', new FormControl('', []));

        this.formGroup.addControl('thinProvisioning', new FormControl(false));
        this.formGroup.addControl('fastProvisioning', new FormControl(false));
        this.formGroup.addControl('isElastic', new FormControl(false));
        this.formGroup.addControl('includeMemoryOverhead', new FormControl(false));

        this.formGroup['canMoveToNext'] = () => {
            this.AddNewPolicy();
            if (this.apiClient.storagePolicy.size > 0) {
                return this.formGroup.valid;
            } else {
                return false;
            }
        };

        setTimeout(_ => {
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentSvcOrgVdcName.subscribe(
                    (orgName) => this.svcOrgVdcName = orgName);
                this.formGroup.get('svcOrgVdcName').setValue(this.svcOrgVdcName);

                this.subscription = this.dataService.currentProviderVDC.subscribe(
                    (provider) => this.providerVDC = provider);
                if(this.dataService.providerVDCNames.indexOf(this.providerVDC) !== -1) {
                    this.formGroup.get('providerVDC').setValue(this.providerVDC);
                }

                this.subscription = this.dataService.currentCpuAllocation.subscribe((cpu) => this.cpuAllocation = cpu);
                this.formGroup.get('cpuAllocation').setValue(this.cpuAllocation);
                this.subscription = this.dataService.currentCpuGuaranteed.subscribe((cpu) => this.cpuGuaranteed = cpu);
                if(this.cpuGuaranteed !== '') this.formGroup.get('cpuGuaranteed').setValue(this.cpuGuaranteed);
                else this.formGroup.get('cpuGuaranteed').setValue('20');

                this.subscription = this.dataService.currentMemoryAllocation.subscribe((mem) => this.memoryAllocation = mem);
                this.formGroup.get('memoryAllocation').setValue(this.memoryAllocation);

                this.subscription = this.dataService.currentMemoryGuaranteed.subscribe((mem) => this.memoryGuaranteed = mem);
                if(this.memoryGuaranteed !== '') this.formGroup.get('memoryGuaranteed').setValue(this.memoryGuaranteed);
                else this.formGroup.get('memoryGuaranteed').setValue('20');

                this.subscription = this.dataService.currentVcpuSpeed.subscribe((speed) => this.vcpuSpeed = speed);
                if(this.vcpuSpeed !== '') this.formGroup.get('vcpuSpeed').setValue(this.vcpuSpeed);
                else this.formGroup.get('vcpuSpeed').setValue('1');

                this.subscription = this.dataService.currentIsElastic.subscribe((elastic) => this.isElastic = elastic);
                this.formGroup.get('isElastic').setValue(this.isElastic);
                this.subscription = this.dataService.currentIncludeMemoryOverhead.subscribe((overhead) => this.includeMemoryOverhead = overhead);
                this.formGroup.get('includeMemoryOverhead').setValue(this.includeMemoryOverhead);
                this.subscription = this.dataService.currentThinProvisioning.subscribe((thin) => this.thinProvisioning = thin);
                this.formGroup.get('thinProvisioning').setValue(this.thinProvisioning);
                this.subscription = this.dataService.currentFastProvisioning.subscribe((fast) => this.fastProvisioning = fast);
                this.formGroup.get('fastProvisioning').setValue(this.fastProvisioning);         
                
                this.subscription = this.dataService.currentNetworkPoolName.subscribe((pool) => this.networkPoolName = pool);
                if(this.dataService.networkPoolNames.indexOf(this.networkPoolName) !== -1) {
                    this.formGroup.get('networkPoolName').setValue(this.networkPoolName);
                }
                this.subscription = this.dataService.currentVmQuota.subscribe((vm) => this.vmQuota = vm);
                if(this.vmQuota !== '') this.formGroup.get('vmQuota').setValue(this.vmQuota);
                else this.formGroup.get('vmQuota').setValue('100');
                this.subscription = this.dataService.currentNetworkQuota.subscribe((nw) => this.networkQuota = nw);
                if(this.networkQuota !== '') this.formGroup.get('networkQuota').setValue(this.networkQuota);
                else this.formGroup.get('networkQuota').setValue('100');

                this.subscription = this.dataService.currentDefaultStoragePolicy.subscribe((defaultPolicy) => this.defaultStoragePolicy = defaultPolicy);
                if([...this.apiClient.storagePolicy.keys()].indexOf(this.defaultStoragePolicy) !== -1) {
                    this.formGroup.get('defaultStoragePolicy').setValue(this.defaultStoragePolicy);
                }
            }
        });
    }


    ngOnChanges() {
        if(this.dataService.providerVDCNames.length !== 0 && this.dataService.providerVDCNames.indexOf(this.providerVDC) !== -1){
            if(this.formGroup.get('providerVDC')) this.formGroup.get('providerVDC').setValue(this.providerVDC);
        }
        if(this.dataService.networkPoolNames.length !== 0 && this.dataService.networkPoolNames.indexOf(this.networkPoolName) !== -1){
            if(this.formGroup.get('networkPoolName')) this.formGroup.get('networkPoolName').setValue(this.networkPoolName);
        }
        this.defaultPolicyList = [...this.apiClient.storagePolicy.keys()];
        if(this.defaultPolicyList.indexOf(this.defaultStoragePolicy) !== -1) {
            if(this.formGroup.get('defaultStoragePolicy')) this.formGroup.get('defaultStoragePolicy').setValue(this.defaultStoragePolicy);
        }
    }


    public toggleIncludeMemoryOverhead() {}

    public toggleIsElastic() {}

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
//             this.apiClient.storageSpec = this.storagePolicy;
            this.formGroup.get('storageSpec').setValue(this.apiClient.storagePolicy);
            this.formGroup.controls.newStoragePolicy.setValue('');
            this.formGroup.controls.newStoragePolicyLimit.setValue('');
//             console.log(this.apiClient.allowedStoragePolicy);
        } else {
            this.errorNotification = 'Storage Spec with same storage policy already exists';
        }
        this.defaultPolicyList = [...this.apiClient.storagePolicy.keys()];
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
        this.defaultPolicyList = [...this.apiClient.storagePolicy.keys()];
    }


    public fetchProviderVdcNames() {
        let vcdData = {
            'vcdAddress': "",
            'vcdSysAdminUserName': "",
            'vcdSysAdminPasswordBase64': "",
        };
        this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
        this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
        this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);

        this.apiClient.fetchProviderVdcNames('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.providerVDCNames = data.PVDC_LIST;
                    this.dataService.providerVDCErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.providerVDCErrorMessage = data.msg;
                    } else {
                        this.dataService.providerVDCErrorMessage = 'Failed to fetch list of Provider VDCs';
                    }
                }
            } else {
                this.dataService.providerVDCErrorMessage = 'Failed to fetch list of Provider VDCs';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                // tslint:disable-next-line:max-line-length
                this.dataService.providerVDCErrorMessage = err.msg;
            } else {
                this.dataService.providerVDCErrorMessage = 'Failed to fetch list of Provider VDCs';
            }
        });
    }

    public fetchNetworkPoolNames() {
        let vcdData = {
            'vcdAddress': "",
            'vcdSysAdminUserName': "",
            'vcdSysAdminPasswordBase64': "",
        };
        this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
        this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
        this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);

        this.apiClient.fetchNetworkPoolNames('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.networkPoolNames = data.NP_LIST;
                    this.dataService.networkPoolNamesErrorMessage = null;

                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.networkPoolNames = data.msg;
                    } else {
                        this.dataService.networkPoolNamesErrorMessage = 'Failed to fetch list of network pools';
                    }
                }
            } else {
                this.dataService.networkPoolNamesErrorMessage = 'Failed to fetch list of network pools';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                // tslint:disable-next-line:max-line-length
                this.dataService.networkPoolNamesErrorMessage = err.msg;
            } else {
                this.dataService.networkPoolNamesErrorMessage = false;
                this.errorNotification = 'Failed to fetch list of network pools';
            }
        });
    }

    public fetchStoragePoliciesFromVcd() {
        let vcdData = {
            'vcdAddress': "",
            'vcdSysAdminUserName': "",
            'vcdSysAdminPasswordBase64': "",
        };
        this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
        this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
        this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);

        this.apiClient.fetchStoragePoliciesFromVdc('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.apiClient.storagePolicies = data.STORAGE_POLICY_LIST;
                    this.dataService.storagePolicyErrorMessage = null;

                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.storagePolicyErrorMessage = data.msg;
                    } else {
                        this.dataService.storagePolicyErrorMessage = 'Failed to fetch storage policies from VCD environment';
                    }
                }
            } else {
                this.dataService.storagePolicyErrorMessage = 'Failed to fetch storage policies from VCD environment';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.storagePolicyErrorMessage = err.msg;
            } else {
                this.dataService.storagePolicyErrorMessage = 'Failed to fetch storage policies from VCD environment';
            }
        });
    }
}