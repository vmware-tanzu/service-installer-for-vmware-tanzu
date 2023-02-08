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
     selector: 'app-catalog-step',
     templateUrl: './catalog.component.html',
     styleUrls: ['./catalog.component.scss'],
 })
export class CatalogComponent extends StepFormDirective implements OnInit {
    @Input() InputCatalogName: [];

    private cseOvaCatalogName;
    private k8sTemplatCatalogName;

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
        this.formGroup.addControl('cseOvaCatalogName', new FormControl('', [Validators.required]));
        this.formGroup.addControl('newCseOvaCatalogName', new FormControl('', []));

        this.formGroup.addControl('k8sTemplatCatalogName', new FormControl('', [Validators.required]));
        this.formGroup.addControl('newK8sTemplatCatalogName', new FormControl('', []));
   
        this.formGroup['canMoveToNext'] = () => {
            this.onCseCatalogChange();
            this.onK8sCatalogChange();
            return this.formGroup.valid;
        };
    
        setTimeout(_ => {
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentCseOvaCatalogName.subscribe((cseova) => this.cseOvaCatalogName = cseova);
                this.subscription = this.dataService.currentK8sTemplatCatalogName.subscribe((k8sOva) => this.k8sTemplatCatalogName = k8sOva);

                if(this.dataService.newOrgCreation) {
                    this.formGroup.get('cseOvaCatalogName').setValue("CREATE NEW");
                    this.formGroup.get('k8sTemplatCatalogName').setValue("CREATE NEW");
                    this.formGroup.get('newCseOvaCatalogName').setValue(this.cseOvaCatalogName);
                    this.formGroup.get('newK8sTemplatCatalogName').setValue(this.k8sTemplatCatalogName);
                } else {
                    if(this.dataService.catalogNames.indexOf(this.cseOvaCatalogName) !== -1){
                        this.formGroup.get('cseOvaCatalogName').setValue(this.cseOvaCatalogName);
                    } else {
                        if(this.cseOvaCatalogName === 'CREATE NEW') {
                            this.formGroup.get('cseOvaCatalogName').setValue('CREATE NEW');
                            this.formGroup.get('newCseOvaCatalogName').setValue(this.cseOvaCatalogName);
                        }
                    }
                    if(this.dataService.catalogNames.indexOf(this.k8sTemplatCatalogName) !== -1){
                        this.formGroup.get('k8sTemplatCatalogName').setValue(this.k8sTemplatCatalogName);
                    } else {
                        if(this.k8sTemplatCatalogName === 'CREATE NEW') {
                            this.formGroup.get('k8sTemplatCatalogName').setValue('CREATE NEW');
                            this.formGroup.get('newK8sTemplatCatalogName').setValue(this.k8sTemplatCatalogName);
                        }
                    }
                }
            } else {
                if(this.dataService.newOrgCreation) {
                    this.formGroup.get('cseOvaCatalogName').setValue("CREATE NEW");
                    this.formGroup.get('k8sTemplatCatalogName').setValue("CREATE NEW");
                }
            }
            this.onCseCatalogChange();
            this.onK8sCatalogChange();
        });
    }

    ngOnChanges() {
        if(this.dataService.catalogNames.length !== 0 && this.dataService.catalogNames.indexOf(this.cseOvaCatalogName) !== -1) {
            if(this.formGroup.get('cseOvaCatalogName')) this.formGroup.get('cseOvaCatalogName').setValue(this.cseOvaCatalogName);
        } else {
            if(this.formGroup.get('cseOvaCatalogName')) this.formGroup.get('cseOvaCatalogName').setValue('IMPORT TO VCD');
            if(this.formGroup.get('newCseOvaCatalogName')) this.formGroup.get('newCseOvaCatalogName').setValue(this.cseOvaCatalogName);
        }

        if(this.dataService.catalogNames.length !== 0 && this.dataService.catalogNames.indexOf(this.k8sTemplatCatalogName) !== -1) {
            if(this.formGroup.get('k8sTemplatCatalogName')) this.formGroup.get('k8sTemplatCatalogName').setValue(this.k8sTemplatCatalogName);
        } else {
            if(this.formGroup.get('k8sTemplatCatalogName')) this.formGroup.get('k8sTemplatCatalogName').setValue('IMPORT TO VCD');
            if(this.formGroup.get('newK8sTemplatCatalogName')) this.formGroup.get('newK8sTemplatCatalogName').setValue(this.k8sTemplatCatalogName);
        }
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
    }
 
 
    onCseCatalogChange() {
        if(this.formGroup.get('cseOvaCatalogName').value === 'CREATE NEW') {
            this.resurrectField('cseOvaCatalogName', [Validators.required], this.formGroup.get('cseOvaCatalogName').value);
            this.resurrectField('newCseOvaCatalogName', [Validators.required, this.validationService.noWhitespaceOnEnds()], this.formGroup.get('newCseOvaCatalogName').value);
        } else {
            ['newCseOvaCatalogName'].forEach((field) => this.disarmField(field, true));
        }
    }

    onK8sCatalogChange() {
        if(this.formGroup.get('k8sTemplatCatalogName').value === 'CREATE NEW') {
            this.resurrectField('k8sTemplatCatalogName', [Validators.required], this.formGroup.get('k8sTemplatCatalogName').value);
            this.resurrectField('newK8sTemplatCatalogName', [Validators.required, this.validationService.noWhitespaceOnEnds()], this.formGroup.get('newK8sTemplatCatalogName').value);
        } else {
            ['newK8sTemplatCatalogName'].forEach((field) => this.disarmField(field, true));
        }
    }

    public fetchCatalogsFromVCD() {
        let vcdData = {
            'vcdAddress': "",
            'vcdSysAdminUserName': "",
            'vcdSysAdminPasswordBase64': "",
            'svcOrgName': "",
        };
        let orgFullName = '';
        this.dataService.currentSvcOrgFullName.subscribe((fullName) => orgFullName = fullName);
        if(orgFullName === '') return;

        this.dataService.currentVcdAddress.subscribe((address) => vcdData['vcdAddress'] = address);
        this.dataService.currentVcdUsername.subscribe((username) => vcdData['vcdSysAdminUserName'] = username);
        this.dataService.currentVcdPassword.subscribe((password) => vcdData['vcdSysAdminPasswordBase64'] = password);
        this.dataService.currentSvcOrgName.subscribe((orgName) => vcdData['svcOrgName'] = orgName);

        this.apiClient.fetchCatalogsFromVCD('vcd', vcdData).subscribe((data: any) => {
            if (data && data !== null) {
                if (data.responseType === 'SUCCESS') {
                    this.dataService.catalogNames = data.CATALOG_LIST;
                    this.dataService.catalogNamesErrorMessage = null;
                } else if (data.responseType === 'ERROR') {
                    if (data.hasOwnProperty('msg')) {
                        this.dataService.catalogNamesErrorMessage = data.msg;
                    } else {
                        this.dataService.catalogNamesErrorMessage = 'Failed to fetch list of catalogs under org: '+vcdData['svcOrgName'];
                    }
                }
            } else {
                this.dataService.catalogNamesErrorMessage = 'Failed to fetch list of catalogs under org: '+vcdData['svcOrgName'];
            }
        }, (err: any) => {
            if (err.responseType === 'ERROR') {
                this.dataService.catalogNamesErrorMessage = err.msg;
            } else {
                this.dataService.catalogNamesErrorMessage = 'Failed to fetch list of catalogs under org: '+vcdData['svcOrgName'];
            }            
        });
    }
}
    