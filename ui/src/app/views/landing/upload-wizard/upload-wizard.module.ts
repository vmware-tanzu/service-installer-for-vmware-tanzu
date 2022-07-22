import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';

import { SharedModule } from '../../../shared/shared.module';
import { LandingModule } from '../landing.module';
import { UploadWizardRoutingModule } from './upload-wizard-routing.module';

import { ValidationService } from '../wizard/shared/validation/validation.service';
import { WizardSharedModule } from '../wizard/shared/wizard-shared.module';
import {UploadWizardComponent} from './upload-wizard.component';
@NgModule({
    declarations: [
        UploadWizardComponent,
    ],
    exports: [
    ],
    imports: [
        CommonModule,
        UploadWizardRoutingModule,
        SharedModule,
        LandingModule,
        WizardSharedModule,
        // WizardSharedModule
    ],
    providers: [
        ValidationService,
    ],
})
export class UploadModule { }
