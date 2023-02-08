/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ComponentFixture, fakeAsync, TestBed, tick, waitForAsync } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';

import { VSphereProviderStepComponent } from './vsphere-provider-step.component';
import { SharedModule } from 'src/app/shared/shared.module';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { SSLThumbprintModalComponent } from '../../wizard/shared/components/modals/ssl-thumbprint-modal/ssl-thumbprint-modal.component';
import { of } from 'rxjs';
import { delay } from 'rxjs/operators';
import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';

describe('VSphereProviderStepComponent', () => {
    let component: VSphereProviderStepComponent;
    let fixture: ComponentFixture<VSphereProviderStepComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            imports: [
                RouterTestingModule.withRoutes([
                    { path: 'ui', component: VSphereProviderStepComponent }
                ]),
                ReactiveFormsModule,
                SharedModule,
                BrowserAnimationsModule
            ],
            providers: [
                ValidationService,
                FormBuilder,
                APIClient
            ],
            schemas: [
                CUSTOM_ELEMENTS_SCHEMA
            ],
            declarations: [
                VSphereProviderStepComponent,
                SSLThumbprintModalComponent
            ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        Broker.messenger = new Messenger();

        const fb = new FormBuilder();
        fixture = TestBed.createComponent(VSphereProviderStepComponent);
        component = fixture.componentInstance;
        component.formGroup = fb.group({
        });

        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should open SSL thumbprint modal when connect vc', fakeAsync(() => {
        const apiSpy = spyOn(component['apiClient'], 'getVsphereThumbprint').and.returnValue(of({insecure: false}).pipe(delay(1)));
        spyOn(component.sslThumbprintModal, 'open');
        component.connectVC();
        tick(1);
        expect(apiSpy).toHaveBeenCalled();
        expect(component.sslThumbprintModal.open).toHaveBeenCalled();
    }));

    it('should call get datacenter when retrieve trigger datacenter', () => {
        const apiSpy = spyOn(component['apiClient'], 'getVSphereDatacenters').and.callThrough();
        component.retrieveDatacenters();
        expect(apiSpy).toHaveBeenCalled();
    });

    it('should return disabled when username is not valid', () => {
        expect(component.getDisabled()).toBeTruthy();
    });

    it('should set vsphere modal open when show method is triggered', () => {
        component.showVSphereWithK8Modal();
        expect(component.vSphereWithK8ModalOpen).toBeTruthy();
    });
});
