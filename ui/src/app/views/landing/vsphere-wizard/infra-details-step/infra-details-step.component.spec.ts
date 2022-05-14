import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { FormBuilder } from '@angular/forms';

import { SharedModule } from 'src/app/shared/shared.module';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { APIClient } from 'src/app/swagger/api-client.service';
import { InfraDataStepComponent } from './infra-details-step.component';
import Broker from 'src/app/shared/service/broker';
import { Messenger } from 'src/app/shared/service/Messenger';

describe('InfraDataStepComponent', () => {
    let component: InfraDataStepComponent;
    let fixture: ComponentFixture<InfraDataStepComponent>;

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
            declarations: [InfraDataStepComponent],
        })
            .compileComponents();
    }));

    beforeEach(() => {
        Broker.messenger = new Messenger();
        const fb = new FormBuilder();
        fixture = TestBed.createComponent(InfraDataStepComponent);
        component = fixture.componentInstance;
        component.formGroup = fb.group({
        });

        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    describe('should generate a full no proxy list', () => {
        it ('should return empty string', () => {
            component.generateFullNoProxy();
            expect(component.fullNoProxy).toBe('');
        });

        it('should have a complete no proxy list', () => {
            component.additionalNoProxyInfo = '10.0.0.0/16,169.254.0.0/16';
            component.formGroup.setValue({
                proxySettings: true,
                httpProxyUrl: 'http://myproxy.com',
                httpProxyUsername: 'username1',
                httpProxyPassword: 'password1',
                isSameAsHttp: true,
                httpsProxyUrl: 'http://myproxy.com',
                httpsProxyUsername: 'username1',
                httpsProxyPassword: 'password1',
                cniType: 'Antrea',
                clusterServiceCidr: '100.64.0.0/13',
                clusterPodCidr: '100.96.0.0/11',
                noProxy: 'noproxy.yourdomain.com,192.168.0.0/24'
            });
            expect(component.fullNoProxy).toBe('noproxy.yourdomain.com,192.168.0.0/24,10.0.0.0/16,169.254.0.0/16,' +
                '100.64.0.0/13,100.96.0.0/11,localhost,127.0.0.1,.svc,.svc.cluster.local');
        });

        it('should generate complete no proxy list correctly if there are more commas in the noProxy field', () => {
            component.additionalNoProxyInfo = '10.0.0.0/16,169.254.0.0/16';
            component.formGroup.setValue({
                proxySettings: true,
                // tslint:disable-next-line:object-literal-sort-keys
                httpProxyUrl: 'http://myproxy.com',
                httpProxyUsername: 'username1',
                httpProxyPassword: 'password1',
                isSameAsHttp: true,
                httpsProxyUrl: 'http://myproxy.com',
                httpsProxyUsername: 'username1',
                httpsProxyPassword: 'password1',
                cniType: 'Antrea',
                clusterServiceCidr: '100.64.0.0/13',
                clusterPodCidr: '100.96.0.0/11',
                noProxy: 'noproxy.yourdomain.com,192.168.0.0/24,,,,,',
            });
            expect(component.fullNoProxy).toBe('noproxy.yourdomain.com,192.168.0.0/24,10.0.0.0/16,169.254.0.0/16,' +
                '100.64.0.0/13,100.96.0.0/11,localhost,127.0.0.1,.svc,.svc.cluster.local');
        });

    });
});
