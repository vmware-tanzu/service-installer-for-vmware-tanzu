/*
* Copyright 2021 VMware, Inc
* SPDX-License-Identifier: BSD-2-Clause
*/
/**
 * Angular Modules
 */
import { Component, OnInit } from '@angular/core';
import { Validators, FormControl } from '@angular/forms';
/**
 * App imports
 */
import { VCDDataService } from 'src/app/shared/service/vcd-data.service';
import { StepFormDirective } from 'src/app/views/landing/wizard/shared/step-form/step-form';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
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

    ipAssignments = ["MANUAL", "POOL"];
    // =========================== COMMON PROPERTIES ========================================
    private uploadStatus;
    subscription: Subscription;

    constructor(private validationService: ValidationService,
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

        this.formGroup.addControl('ipAssignment', new FormControl('', [Validators.required]));
        this.formGroup.addControl('ip', new FormControl('', [Validators.required, this.validationService.noWhitespaceOnEnds(), this.validationService.isValidIp()]));

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

    ipAssignmentChange() {
        if(this.formGroup.get('ipAssignment').value === 'MANUAL') {
            this.resurrectField('ip', [Validators.required, this.validationService.isValidIp(), this.validationService.noWhitespaceOnEnds()], this.formGroup.get('ip').value);
        }
        else {
            ['ip'].forEach((field) => this.disarmField(field, true));
        }
    }

}
