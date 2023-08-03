/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';

import { SharedModule } from 'src/app/shared/shared.module';
import { LandingModule } from 'src/app/views/landing/landing.module';
import { VMCUploadWizardRoutingModule } from 'src/app/console/vmc-tkgm/upload/vmc-upload-wizard-routing.module';

import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { WizardSharedModule } from 'src/app/views/landing/wizard/shared/wizard-shared.module';
import { VMCUploadWizardComponent } from 'src/app/console/vmc-tkgm/upload/vmc-upload-wizard.component';
@NgModule({
    declarations: [
        VMCUploadWizardComponent,
    ],
    exports: [
    ],
    imports: [
        CommonModule,
        VMCUploadWizardRoutingModule,
        SharedModule,
        LandingModule,
        WizardSharedModule
    ],
    providers: [
        ValidationService,
    ],
})
export class VMCUploadModule { }
