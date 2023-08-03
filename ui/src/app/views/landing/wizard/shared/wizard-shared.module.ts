/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxJsonViewerModule } from 'ngx-json-viewer';

import { SharedModule } from '../../../../shared/shared.module';
import { ValidationService } from './validation/validation.service';
import { StepControllerComponent } from './step-controller/step-controller.component';
import { CodemirrorModule } from '@ctrl/ngx-codemirror';
import { SSLThumbprintModalComponent } from './components/modals/ssl-thumbprint-modal/ssl-thumbprint-modal.component';
import { ViewJSONModalComponent } from './components/modals/view-json-modal/view-json-modal.component';
import { SharedIdentityStepComponent } from './components/identity-management-step/identity-management-step.component';

@NgModule({
    declarations: [
        StepControllerComponent,
        SSLThumbprintModalComponent,
        ViewJSONModalComponent,
        SharedIdentityStepComponent,
    ],
    imports: [
        CommonModule,
        SharedModule,
        CodemirrorModule,
        NgxJsonViewerModule
    ],
    exports: [
        StepControllerComponent,
        SSLThumbprintModalComponent,
        ViewJSONModalComponent,
        SharedIdentityStepComponent
    ],
    providers: [
        ValidationService
    ]
})
export class WizardSharedModule { }
