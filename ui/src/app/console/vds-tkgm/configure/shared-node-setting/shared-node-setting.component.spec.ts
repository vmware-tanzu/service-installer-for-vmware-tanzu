/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { SharedModule } from 'src/app/shared/shared.module';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';
import { SharedNodeSettingComponent } from './shared-node-setting.component';

import { APIClient } from 'src/app/swagger/api-client.service';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';

describe('SharedNodeSettingComponent', () => {
    let component: SharedNodeSettingComponent;
    let fixture: ComponentFixture<SharedNodeSettingComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            imports: [
                ReactiveFormsModule,
                SharedModule
            ],
            providers: [
                ValidationService,
                FormBuilder,
                APIClient
            ],
            schemas: [
                CUSTOM_ELEMENTS_SCHEMA
            ],
            declarations: [SharedNodeSettingComponent]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        Broker.messenger = new Messenger();

        const fb = new FormBuilder();
        fixture = TestBed.createComponent(SharedNodeSettingComponent);
        component = fixture.componentInstance;
        component.formGroup = fb.group({
        });
        component.mgmtFormGroup = fb.group({});

        fixture.detectChanges();
    });

    it('should set correct value for card clicking', () => {
        component.cardClick('prod');
        expect(component.formGroup.controls['controlPlaneSetting'].value).toBe('prod')
    });

    it('should get correct env value', () => {
        component.cardClick('prod');
        expect(component.getEnvType()).toEqual('prod');
    });
});
