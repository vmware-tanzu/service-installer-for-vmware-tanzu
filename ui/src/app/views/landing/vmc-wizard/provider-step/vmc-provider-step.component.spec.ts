import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ComponentFixture, fakeAsync, TestBed, tick, waitForAsync } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';

import { VMCProviderStepComponent } from './vmc-provider-step.component';
import { SharedModule } from 'src/app/shared/shared.module';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { of } from 'rxjs';
import { delay } from 'rxjs/operators';
import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';

describe('VMCProviderStepComponent', () => {
    let component: VMCProviderStepComponent;
    let fixture: ComponentFixture<VMCProviderStepComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            imports: [
                RouterTestingModule.withRoutes([
                    { path: 'ui', component: VMCProviderStepComponent }
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
                VMCProviderStepComponent,
            ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        Broker.messenger = new Messenger();

        const fb = new FormBuilder();
        fixture = TestBed.createComponent(VMCProviderStepComponent);
        component = fixture.componentInstance;
        component.formGroup = fb.group({
        });

        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

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
