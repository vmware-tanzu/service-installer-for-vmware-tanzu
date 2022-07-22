import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';

import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';
import { SharedModule } from 'src/app/shared/shared.module';
import { APIClient } from 'src/app/swagger/api-client.service';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { VMCUploadWizardComponent } from './vmc-upload-wizard.component';
import { RouterTestingModule } from "@angular/router/testing";
import { VMCWizardComponent } from "../vmc-wizard/vmc-wizard.component";

describe('VMCUploadWizardComponent', () => {
    let component: VMCUploadWizardComponent;
    let fixture: ComponentFixture<VMCUploadWizardComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            declarations: [VMCUploadWizardComponent],
            imports: [
                ReactiveFormsModule,
                SharedModule,
                RouterTestingModule.withRoutes([
                    { path: 'ui', component: VMCUploadWizardComponent },
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
        fixture = TestBed.createComponent(VMCUploadWizardComponent);
        component = fixture.componentInstance;

        fixture.detectChanges();
    });
});
