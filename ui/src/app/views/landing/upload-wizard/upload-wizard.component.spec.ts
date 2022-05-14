import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';

import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';
import { SharedModule } from 'src/app/shared/shared.module';
import { APIClient } from 'src/app/swagger/api-client.service';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { UploadWizardComponent } from './upload-wizard.component';
import {RouterTestingModule} from "@angular/router/testing";
import {VSphereWizardComponent} from "../vsphere-wizard/vsphere-wizard.component";

describe('UploadWizardComponent', () => {
    let component: UploadWizardComponent;
    let fixture: ComponentFixture<UploadWizardComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            declarations: [UploadWizardComponent],
            imports: [
                ReactiveFormsModule,
                SharedModule,
                RouterTestingModule.withRoutes([
                    { path: 'ui', component: UploadWizardComponent },
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
        fixture = TestBed.createComponent(UploadWizardComponent);
        component = fixture.componentInstance;

        fixture.detectChanges();
    });
});
