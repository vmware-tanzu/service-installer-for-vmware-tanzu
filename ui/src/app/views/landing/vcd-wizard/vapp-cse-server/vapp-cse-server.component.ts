/*
* Copyright 2021 VMware, Inc
* SPDX-License-Identifier: BSD-2-Clause
*/
/**
 * Angular Modules
 */
 import { Component, OnInit } from '@angular/core';
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
      selector: 'app-vapp-step',
      templateUrl: './vapp-cse-server.component.html',
      styleUrls: ['./vapp-cse-server.component.scss'],
  })
 export class vAppComponent extends StepFormDirective implements OnInit {
   
    private vAppName;
    private cseSvcAccountName;
    private cseSvcAccountPasswordBase64;
    private startAddress;
    private endAddress;
 
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
         this.formGroup.addControl('vAppName', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
         this.formGroup.addControl('cseSvcAccountName', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds()]));
         this.formGroup.addControl('cseSvcAccountPasswordBase64', new FormControl('', [Validators.required])); 

         this.formGroup.addControl('startAddress', new FormControl('', []));
         this.formGroup.addControl('endAddress', new FormControl('', []));
    
         this.formGroup['canMoveToNext'] = () => {
             return this.formGroup.valid;
         };
     
         setTimeout(_ => {
             this.subscription = this.dataService.currentInputFileStatus.subscribe(
                 (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentVappName.subscribe((vapp) => this.vAppName = vapp);
                this.formGroup.get('vAppName').setValue(this.vAppName);

                this.subscription = this.dataService.currentCseSvcAccountName.subscribe((acc) => this.cseSvcAccountName = acc);
                this.formGroup.get('cseSvcAccountName').setValue(this.cseSvcAccountName);

                this.subscription = this.dataService.currentCseSvcAccountPasswordBase64.subscribe((password) => this.cseSvcAccountPasswordBase64 = password);
                this.formGroup.get('cseSvcAccountPasswordBase64').setValue(this.cseSvcAccountPasswordBase64);
            }

            this.subscription = this.dataService.currentStaticIpPoolstartAddress.subscribe((start) => this.startAddress = start);
            this.formGroup.get('startAddress').setValue(this.startAddress);
            this.formGroup.get('startAddress').disable();

            this.subscription = this.dataService.currentStaticIpPoolendAddress.subscribe((end) => this.endAddress = end);
            this.formGroup.get('endAddress').setValue(this.endAddress);
            this.formGroup.get('endAddress').disable();
         });
     }
     
     setSavedDataAfterLoad() {
         super.setSavedDataAfterLoad();
     }

 }
     