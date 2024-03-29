/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular modules
import { TestBed, ComponentFixture, waitForAsync } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { APP_ROUTES } from 'src/app/shared/constants/routes.constants';

// App imports
import { StartComponent } from './start.component';

describe('StartComponent', () => {
    let fixture: ComponentFixture<StartComponent>;
    let component: StartComponent;
    let router: Router;
    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            imports: [
                RouterTestingModule
            ],
            declarations: [
                StartComponent
            ]
        }).compileComponents();
    }));

    beforeEach(() => {
        router = TestBed.inject(Router);
        fixture = TestBed.createComponent(StartComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should exist', () => {
        const landingComponent = fixture.debugElement.componentInstance;
        expect(landingComponent).toBeTruthy();
    });

    it('should navigate to wizard', () => {
        const routerSpy = spyOn(router, 'navigate').and.stub();
        component.navigateToWizard('vsphere');
        expect(routerSpy).toHaveBeenCalledWith([APP_ROUTES.WIZARD_MGMT_CLUSTER]);
        component.navigateToWizard('aws');
        expect(routerSpy).toHaveBeenCalledWith([APP_ROUTES.AWS_WIZARD]);
        component.navigateToWizard('azure');
        expect(routerSpy).toHaveBeenCalledWith([APP_ROUTES.AZURE_WIZARD]);
        component.navigateToWizard('vmc');
        expect(routerSpy).toHaveBeenCalledWith([APP_ROUTES.VMC_WIZARD]);
        component.navigateToWizard('vsphere-nsxt');
        expect(routerSpy).toHaveBeenCalledWith([APP_ROUTES.VSPHERE_NSXT_WIZARD]);
    });
});
