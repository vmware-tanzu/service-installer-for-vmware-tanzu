/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';

import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';
import { SharedModule } from 'src/app/shared/shared.module';
import { APIClient } from 'src/app/swagger/api-client.service';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { VsphereTkgsUploadWizardComponent } from 'src/app/console/vds-tkgs/upload/vsphere-tkgs-upload-wizard.component';
import { RouterTestingModule } from "@angular/router/testing";

describe('VsphereTkgsUploadWizardComponent', () => {
    let component: VsphereTkgsUploadWizardComponent;
    let fixture: ComponentFixture<VsphereTkgsUploadWizardComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            declarations: [VsphereTkgsUploadWizardComponent],
            imports: [
                ReactiveFormsModule,
                SharedModule,
                RouterTestingModule.withRoutes([
                    { path: 'ui', component: VsphereTkgsUploadWizardComponent },
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
        fixture = TestBed.createComponent(VsphereTkgsUploadWizardComponent);
        component = fixture.componentInstance;

        fixture.detectChanges();
    });
});
