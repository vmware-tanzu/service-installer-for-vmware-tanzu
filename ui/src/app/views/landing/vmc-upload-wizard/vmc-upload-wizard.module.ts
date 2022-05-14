import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';

import { SharedModule } from '../../../shared/shared.module';
import { LandingModule } from '../landing.module';
import { VMCUploadWizardRoutingModule } from './vmc-upload-wizard-routing.module';

import { ValidationService } from '../wizard/shared/validation/validation.service';
import { WizardSharedModule } from '../wizard/shared/wizard-shared.module';
import { VMCUploadWizardComponent } from './vmc-upload-wizard.component';
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
        WizardSharedModule,
        // WizardSharedModule
    ],
    providers: [
        ValidationService,
    ],
})
export class VMCUploadModule { }
