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
    selector: 'app-svc-org-step',
    templateUrl: './svc-org.component.html',
    styleUrls: ['./svc-org.component.scss'],
})
export class ServiceOrganizationComponent extends StepFormDirective implements OnInit {
    @Input() InputSvcOrgName: [];
    fetchServiceOrgNames = false;
    private svcOrgName;
    svcOrgNames = [];
    private svcOrgFullName;

    private validatedSelectedOrg = false;

    // =========================== COMMON PROPERTIES ========================================
    private uploadStatus;
    subscription: Subscription;

    constructor(private validationService: ValidationService,
        private wizardFormService: VSphereWizardFormService,
        private apiClient: APIClient,
        public dataService: VCDDataService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();

        this.formGroup.addControl('svcOrgName', new FormControl('', [Validators.required]));
        this.formGroup.addControl('svcOrgNameInput', new FormControl('', []));
        this.formGroup.addControl('svcOrgFullName', new FormControl('', []));

        this.formGroup['canMoveToNext'] = () => {
            this.onSvcOrgNameChange();
            if(this.formGroup.get('svcOrgName').value !== 'CREATE NEW' && this.formGroup.get('svcOrgName').value !== '') {
                return this.formGroup.valid;
            }
            return this.formGroup.valid;
        };

        setTimeout(_ => {
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentSvcOrgName.subscribe(
                    (orgName) => this.svcOrgName = orgName);
                if(this.dataService.svcOrgNames.indexOf(this.svcOrgName) !== -1) {
                    this.formGroup.get('svcOrgName').setValue(this.svcOrgName);
                } else {
                    this.formGroup.get('svcOrgName').setValue('CREATE NEW');
                    this.formGroup.get('svcOrgNameInput').setValue(this.svcOrgName);
                }
                this.subscription = this.dataService.currentSvcOrgFullName.subscribe(
                    (fullname) => this.svcOrgFullName = fullname);
                this.formGroup.get('svcOrgFullName').setValue(this.svcOrgFullName);
                this.onSvcOrgNameChange();
            }
        });
    }


    ngOnChanges() {
        if(this.dataService.svcOrgNames.length !== 0 && this.dataService.svcOrgNames.indexOf(this.svcOrgName) !== -1){
            if(this.formGroup.get('svcOrgName')) this.formGroup.get('svcOrgName').setValue(this.svcOrgName);
        } else {
            if(this.formGroup.get('svcOrgName')) this.formGroup.get('svcOrgName').setValue('CREATE NEW');
            if(this.formGroup.get('svcOrgNameInput')) this.formGroup.get('svcOrgNameInput').setValue(this.svcOrgName);
        }
    }


    onSvcOrgNameChange() {
        const newOrgFields = [
            'svcOrgNameInput',
            'svcOrgFullName',
        ];
        if (this.formGroup.get('svcOrgName').value === 'CREATE NEW') {
            this.dataService.newOrgCreation = true;
            this.resurrectField('svcOrgNameInput', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
            ], this.formGroup.value['svcOrgNameInput']);
            this.resurrectField('svcOrgFullName', [
                Validators.required, this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['svcOrgFullName']);
        } else {
            this.dataService.newOrgCreation = false;
            newOrgFields.forEach((field) => {
                this.disarmField(field, true)
            });
            if(this.formGroup.get('svcOrgName').valid && this.formGroup.get('svcOrgName').value!== '') {
                // this.validateOrgPublishStatus(this.formGroup.get('svcOrgName').value);
                this.fetchCatalogsFromVCD(this.formGroup.get('svcOrgName').value);
            }
        }
    }

    public fetchSvcOrgNames() {
        let vcdData = {
            'vcdAddress': "",
            'vcdSysAdminUserName': "",
            'vcdSysAdminPasswordBase64': "",
        };
        this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
        this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
        this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);

        this.apiClient.fetchSvcOrgNames('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.svcOrgNames = data.ORG_LIST_VCD;
                    this.dataService.svcOrgNamesErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.svcOrgNamesErrorMessage = data.msg;
                    } else {
                        this.dataService.svcOrgNamesErrorMessage = 'Failed to fetch list service organizations';
                    }
                }
            } else {
                this.dataService.svcOrgNamesErrorMessage = 'Failed to fetch list of service organizations';
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.svcOrgNamesErrorMessage = err.msg;
            } else {
                this.dataService.svcOrgNamesErrorMessage = 'Failed to fetch list of service organizations';
            }            
        });
    }

    public fetchCatalogsFromVCD(orgname) {
        let vcdData = {
            'vcdAddress': "",
            'vcdSysAdminUserName': "",
            'vcdSysAdminPasswordBase64': "",
            'svcOrgName': orgname,
        };
        this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
        this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
        this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);

        this.apiClient.fetchCatalogsFromVCD('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.catalogNames = data.CATALOG_LIST;
                    this.dataService.catalogNamesErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.catalogNamesErrorMessage = data.msg;
                    } else {
                        this.dataService.catalogNamesErrorMessage = 'Failed to fetch list of catalogs under org: '+orgname;
                    }
                }
            } else {
                this.dataService.catalogNamesErrorMessage = 'Failed to fetch list of catalogs under org: '+orgname;
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.catalogNamesErrorMessage = err.msg;
            } else {
                this.dataService.catalogNamesErrorMessage = 'Failed to fetch list of catalogs under org: '+orgname;
            }            
        });
    }

    public validateOrgPublishStatus(orgname) {
        let vcdData = {
            'vcdAddress': "",
            'vcdSysAdminUserName': "",
            'vcdSysAdminPasswordBase64': "",
            'svcOrgName': orgname,
        };
        this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
        this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
        this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);

        this.apiClient.validateOrgPublishStatus('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.validatedSelectedOrg = true;
                    this.errorNotification = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.validatedSelectedOrg = false;
                        this.errorNotification = data.msg;
                    } else {
                        this.validatedSelectedOrg = false;
                        this.errorNotification = 'Failed to fetch list of catalogs under org: '+orgname;
                    }
                }
            } else {
                this.validatedSelectedOrg = false;
                this.errorNotification = 'Failed to fetch list of catalogs under org: '+orgname;
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.validatedSelectedOrg = false;
                this.errorNotification = err.msg;
            } else {
                this.validatedSelectedOrg = false;
                this.errorNotification = 'Failed to fetch list of catalogs under org: '+orgname;
            }            
        });        
    }
}