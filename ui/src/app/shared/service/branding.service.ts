/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { Injectable } from '@angular/core';

// Application imports
import { TkgEventType } from 'src/app/shared/service/Messenger';
import { AppEdition, brandingDefault, brandingTce, brandingTceStandalone } from '../constants/branding.constants';
import Broker from './broker';

export interface BrandingObj {
    logoClass: string;
    title: string;
    intro: string;
}

export interface BrandingData {
    title: string;
    landingPage: BrandingObj;
}

export interface EditionData {
    branding: BrandingData;
    clusterType: string;
    edition: AppEdition;
}

@Injectable({
    providedIn: 'root'
})
export class BrandingService {

    constructor() {
    }

    /**
     * @method setBrandingByEdition
     * Helper method used to set branding content in Messenger payload depending on which edition is detected.
     * Dispatches 'BRANDING_CHANGED' message with branding data as payload.
     * @param edition - Optional parameter. 'tce' or 'tce-standalone' to retrieve tce branding; otherwise retrieves
     * default branding.
     */
    private setBrandingByEdition(edition?: string): void {
        let brandingPayload: EditionData = brandingDefault;

        if (edition && edition === AppEdition.TCE) {
            brandingPayload = brandingTce;
        } else if (edition && edition === AppEdition.TCE_STANDALONE) {
            brandingPayload = brandingTceStandalone;
        }

        Broker.messenger.publish({
            type: TkgEventType.BRANDING_CHANGED,
            payload: brandingPayload
        });
    }
}
