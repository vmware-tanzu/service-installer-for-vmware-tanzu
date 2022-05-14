import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';

import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';
import { SharedModule } from 'src/app/shared/shared.module';
import { APIClient } from 'src/app/swagger/api-client.service';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { VsphereNsxtUploadWizardComponent } from './vsohere-nsxt-upload-wizard.component';
import { RouterTestingModule } from "@angular/router/testing";
import { VsphereNsxtWizardComponent } from "../vsphere-nsxt-wizard/vsphere-nsxt-wizard.component";

describe('VsphereNsxtUploadWizardComponent', () => {
    let component: VsphereNsxtUploadWizardComponent;
    let fixture: ComponentFixture<VsphereNsxtUploadWizardComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            declarations: [VsphereNsxtUploadWizardComponent],
            imports: [
                ReactiveFormsModule,
                SharedModule,
                RouterTestingModule.withRoutes([
                    { path: 'ui', component: VsphereNsxtUploadWizardComponent },
                ]),
            ],
            providers: [
                ValidationService,
                FormBuilder,
                APIClient,
            ],
            schemas: [
                CUSTOM_ELEMENTS_SCHEMA,
            ],
        })
            .compileComponents();
    }));

    beforeEach(() => {
        Broker.messenger = new Messenger();
        const fb = new FormBuilder();
        fixture = TestBed.createComponent(VsphereNsxtUploadWizardComponent);
        component = fixture.componentInstance;

        fixture.detectChanges();
    });
});
