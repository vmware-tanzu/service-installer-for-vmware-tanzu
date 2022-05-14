import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';

import { SharedModule } from '../../../shared/shared.module';
import { LandingModule } from '../landing.module';
import { VsphereNsxtUploadWizardRoutingModule } from './vsphere-nsxt-upload-wizard-routing.module';

import { ValidationService } from '../wizard/shared/validation/validation.service';
import { WizardSharedModule } from '../wizard/shared/wizard-shared.module';
import {VsphereNsxtUploadWizardComponent} from './vsphere-nsxt-upload-wizard.component';
@NgModule({
    declarations: [
        VsphereNsxtUploadWizardComponent,
    ],
    exports: [
    ],
    imports: [
        CommonModule,
        VsphereNsxtUploadWizardRoutingModule,
        SharedModule,
        LandingModule,
        WizardSharedModule,
        // WizardSharedModule
    ],
    providers: [
        ValidationService,
    ],
})
export class VsphereNsxtUploadModule { }
