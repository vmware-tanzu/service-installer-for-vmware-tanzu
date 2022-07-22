import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { FormBuilder, FormControl, ReactiveFormsModule } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
import { VSphereWizardFormServiceStub } from 'src/app/testing/vsphere-wizard-form.service.stub';
import { SharedModule } from '../../../shared/shared.module';
import { APIClient } from '../../../swagger/api-client.service';
import { FormMetaDataStore } from '../wizard/shared/FormMetaDataStore';
import { VMCWizardComponent } from './vmc-wizard.component';

describe('VMCWizardComponent', () => {
    let component: VMCWizardComponent;
    let fixture: ComponentFixture<VMCWizardComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            imports: [
                RouterTestingModule,
                ReactiveFormsModule,
                BrowserAnimationsModule,
                RouterTestingModule.withRoutes([
                    { path: 'vmc-upload', component: VMCWizardComponent },
                ]),
                SharedModule,
            ],
            providers: [
                APIClient,
                FormBuilder,
                { provide: VSphereWizardFormService},
            ],
            schemas: [
                CUSTOM_ELEMENTS_SCHEMA,
            ],
            declarations: [
                VMCWizardComponent
            ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        Broker.messenger = new Messenger();
        const fb = new FormBuilder();
        fixture = TestBed.createComponent(VMCWizardComponent);
        component = fixture.componentInstance;
        component.form = fb.group({
            vmcProviderForm: fb.group({
            }),
            vmcMgmtNodeSettingForm: fb.group({
            }),
            vmcSharedServiceNodeSettingForm: fb.group({
            }),
            vmcWorkloadNodeSettingForm: fb.group({
            }),
            vmcAVINetworkSettingForm: fb.group({
            }),
            vmcExtensionSettingForm: fb.group({
            }),
            vmcTKGMgmtDataNWForm: fb.group({
            }),
            vmcTKGWorkloadDataNWForm: fb.group({
            }),
            vmcTanzuSaasSettingForm: fb.group({
            }),
            dnsNtpForm: fb.group({
            }),
        });
        component.clusterType = 'management';
        fixture.detectChanges();
    });

    afterEach(() => {
        fixture.destroy();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should call getStepList in reviewConfiguration', () => {
        const getStepListSpy = spyOn(FormMetaDataStore, 'getStepList').and.callThrough();
        component.getWizardValidity();
        expect(getStepListSpy).toHaveBeenCalled();
    });

    it('getWizardValidity should return false when getStepList is empty', () => {
        expect(component['getWizardValidity']()).toBeFalsy();
    });

    it('getStepDescription should return correct description when wizard is not filled', () => {
        expect(component['getStepDescription']('provider')).toBe(
            'Validate the vSphere provider account for Tanzu Kubernetes Grid');
    });

//     it('getStepDescription should return correct summary for wizard input', () => {
//         const fb = new FormBuilder();
//         component.form.controls['vsphereProviderForm'] = fb.group({
//             vcenterAddress: new FormControl('vcAddr'),
//             datacenter: new FormControl('dc'),
//         });
//
//         expect(component['getStepDescription']('provider')).toBe(
//             'vCenter vcAddr connected');
//     });

    it('should call create vsphere api when deploying', () => {
        const apiSpy = spyOn(component['apiClient'], 'createVSphereRegionalCluster').and.callThrough();
        component.providerType = 'vmc';
        component.deploy();
        expect(apiSpy).toHaveBeenCalled();
    });
});
