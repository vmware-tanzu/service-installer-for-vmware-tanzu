/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';

import { AngularStepperReactiveStepperComponent } from './stack.component';

describe('AngularStepperReactiveStepperComponent', () => {
    let component: AngularStepperReactiveStepperComponent;
    let fixture: ComponentFixture<AngularStepperReactiveStepperComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            declarations: [ AngularStepperReactiveStepperComponent ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(AngularStepperReactiveStepperComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
