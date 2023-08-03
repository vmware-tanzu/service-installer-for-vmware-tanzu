/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { SharedModule } from 'src/app/shared/shared.module';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';
import { TKGMgmtNetworkSettingComponent } from 'src/app/console/vcf-tkgm/configure/tkg-mgmt-data-network/tkg-mgmt-data.component';

import { APIClient } from 'src/app/swagger/api-client.service';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';

describe('TKGMgmtNetworkSettingComponent', () => {
    let component: TKGMgmtNetworkSettingComponent;
    let fixture: ComponentFixture<TKGMgmtNetworkSettingComponent>;

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
            declarations: [TKGMgmtNetworkSettingComponent]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        Broker.messenger = new Messenger();

        const fb = new FormBuilder();
        fixture = TestBed.createComponent(TKGMgmtNetworkSettingComponent);
        component = fixture.componentInstance;
        component.formGroup = fb.group({
        });

        fixture.detectChanges();
    });
});
