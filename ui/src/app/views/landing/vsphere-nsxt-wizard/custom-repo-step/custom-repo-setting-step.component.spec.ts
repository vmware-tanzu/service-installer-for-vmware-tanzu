import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';

import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';
import { SharedModule } from 'src/app/shared/shared.module';
import { APIClient } from 'src/app/swagger/api-client.service';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { CustomRepoSettingComponent } from './custom-repo-setting-step.component';

describe('CustomRepoSettingComponent', () => {
    let component: CustomRepoSettingComponent;
    let fixture: ComponentFixture<CustomRepoSettingComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            declarations: [CustomRepoSettingComponent],
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
        })
            .compileComponents();
    }));

    beforeEach(() => {
        Broker.messenger = new Messenger();
        const fb = new FormBuilder();
        fixture = TestBed.createComponent(CustomRepoSettingComponent);
        component = fixture.componentInstance;
        component.formGroup = fb.group({
        });

        fixture.detectChanges();
    });
});
