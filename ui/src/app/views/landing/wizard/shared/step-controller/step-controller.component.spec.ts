/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';

import { StepControllerComponent } from './step-controller.component';

describe('StepControllerComponent', () => {
  let component: StepControllerComponent;
  let fixture: ComponentFixture<StepControllerComponent>;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      declarations: [ StepControllerComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(StepControllerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
