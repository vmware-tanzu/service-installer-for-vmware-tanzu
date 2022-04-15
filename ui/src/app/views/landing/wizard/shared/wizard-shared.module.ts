/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxJsonViewerModule } from 'ngx-json-viewer';

import { SharedModule } from '../../../../shared/shared.module';
import { ValidationService } from './validation/validation.service';
// import { StepFormNotificationComponent } from './step-form-notification/step-form-notification.component';
import { StepControllerComponent } from './step-controller/step-controller.component';
// import { SharedRegisterTmcStepComponent } from './components/steps/register-tmc-step/register-tmc-step.component';
// import { SharedCeipStepComponent } from './components/steps/ceip-step/ceip-step.component';
// import { SharedNetworkStepComponent } from './components/steps/network-step/network-step.component';
// import { SharedLoadBalancerStepComponent } from './components/steps/load-balancer/load-balancer-step.component';
// import { InfraDataStepComponent } from '../vsphere-wizard/steps/infra-details-step/infra-details-step.component';
import { CodemirrorModule } from '@ctrl/ngx-codemirror';
// import { DeleteDataPopupComponent } from './components/delete-data-popup.component';
import { SSLThumbprintModalComponent } from './components/modals/ssl-thumbprint-modal/ssl-thumbprint-modal.component';
import { ViewJSONModalComponent } from './components/modals/view-json-modal/view-json-modal.component';
// import { SharedIdentityStepComponent } from './components/steps/identity-step/identity-step.component';
// import { TreeSelectComponent } from './tree-select/tree-select.component';
// import { AuditLoggingComponent } from './components/widgets/audit-logging/audit-logging.component';
// import { SharedOsImageStepComponent } from './components/steps/os-image-step/os-image-step.component';

@NgModule({
    declarations: [
        // StepFormNotificationComponent,
        StepControllerComponent,
        // SharedRegisterTmcStepComponent,
        // SharedCeipStepComponent,
        // SharedNetworkStepComponent,
        // SharedLoadBalancerStepComponent,
        // MetadataStepComponent,
        // DeleteDataPopupComponent,
        SSLThumbprintModalComponent,
        ViewJSONModalComponent
        // SharedIdentityStepComponent,
        // TreeSelectComponent,
        // AuditLoggingComponent,
        // SharedOsImageStepComponent
    ],
    imports: [
        CommonModule,
        SharedModule,
        CodemirrorModule,
        NgxJsonViewerModule
    ],
    exports: [
        // StepFormNotificationComponent,
        StepControllerComponent,
        // SharedRegisterTmcStepComponent,
        // SharedCeipStepComponent,
        // SharedNetworkStepComponent,
        // SharedLoadBalancerStepComponent,
        // MetadataStepComponent,
        // DeleteDataPopupComponent,
        SSLThumbprintModalComponent,
        ViewJSONModalComponent
        // SharedIdentityStepComponent,
        // TreeSelectComponent,
        // AuditLoggingComponent,
        // SharedOsImageStepComponent
    ],
    providers: [
        ValidationService
    ]
})
export class WizardSharedModule { }
