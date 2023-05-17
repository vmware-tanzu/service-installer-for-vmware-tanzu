/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { TestBed, waitForAsync } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { HttpClientModule } from '@angular/common/http';

import { AppDataService } from './app-data.service';
import { APIClient } from '../../swagger/api-client.service';

describe('AppDataService', () => {
    let service: AppDataService;

    beforeEach(() => TestBed.configureTestingModule({
        imports: [
            HttpClientTestingModule
        ],
        providers: [
            APIClient
        ]
    }));

    beforeEach(() => {
        service = TestBed.get(AppDataService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should provide getter/setter for providerType', waitForAsync(() => {
        const provider = service.getProviderType();

        service.setProviderType('aws');

        provider.subscribe(prov => {
            expect(prov).toBe('aws');
        })
    }));

    it('should provide getter/setter for hasPacificCluster', waitForAsync(() => {
        const isPacific = service.getIsProjPacific();

        service.setIsProjPacific(true);

        isPacific.subscribe(pacific => {
            expect(pacific).toBe(true);
        })
    }));

    it('should provide getter/setter for tkrVersion', waitForAsync(() => {
        const tkrVersion = service.getTkrVersion();

        service.setTkrVersion('1.17.3');

        tkrVersion.subscribe(ver => {
            expect(ver).toBe('1.17.3');
        })
    }));
});
