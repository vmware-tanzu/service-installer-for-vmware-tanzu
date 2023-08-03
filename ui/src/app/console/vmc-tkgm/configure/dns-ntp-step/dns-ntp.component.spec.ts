/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';

import { SharedModule } from 'src/app/shared/shared.module';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { DnsNtpComponent } from 'src/app/console/vmc-tkgm/configure/dns-ntp-step/dns-ntp.component';
import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';

describe('DumyComponent', () => {
    let component: DnsNtpComponent;
    let fixture: ComponentFixture<DnsNtpComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            imports: [
                ReactiveFormsModule,
                SharedModule,
            ],
            providers: [
                ValidationService,
                FormBuilder,
                APIClient,
            ],
            schemas: [
                CUSTOM_ELEMENTS_SCHEMA,
            ],
            declarations: [DnsNtpComponent],
        })
            .compileComponents();
    }));

    beforeEach(() => {
        Broker.messenger = new Messenger();
        const fb = new FormBuilder();
        fixture = TestBed.createComponent(DnsNtpComponent);
        component = fixture.componentInstance;
        component.formGroup = fb.group({
        });

        fixture.detectChanges();
    });
});
