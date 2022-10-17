/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { TestBed } from '@angular/core/testing';

import { FormMetaDataService } from './form-meta-data.service';

describe('FormMetaDataService', () => {
    beforeEach(() => TestBed.configureTestingModule({}));

    it('should be created', () => {
        const service: FormMetaDataService = TestBed.get(FormMetaDataService);
        expect(service).toBeTruthy();
    });
});
