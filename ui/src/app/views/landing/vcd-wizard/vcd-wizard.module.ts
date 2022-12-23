/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { NgxJsonViewerModule } from 'ngx-json-viewer';
import { SharedModule } from '../../../shared/shared.module';
import { LandingModule } from '../landing.module';
import { VCDWizardRoutingModule } from './vcd-wizard-routing.module';

import { ValidationService } from '../wizard/shared/validation/validation.service';
import { WizardSharedModule } from '../wizard/shared/wizard-shared.module';

import { VCDWizardComponent } from './vcd-wizard.component';

import { DnsNtpComponent } from './dns-ntp/dns-ntp.component';
import { VCDSpecComponent } from './vcd-spec/vcd-spec.component';
import { AviControllerComponent } from './avi-controller/avi-controller.component';
import { AviNsxCloudComponent } from './avi-nsx-cloud/avi-nsx-cloud.component';

import { T0GatewayComponent } from './t0-router/t0-router.component';
import { ServiceOrganizationComponent } from './svc-org/svc-org.component';
import { ServiceOrganizationVDCComponent } from './svc-org-vdc/svc-org-vdc.component';
import { EdgeGatewayComponent } from './edge-gateway/edge-gateway.component';
import { ServiceEngineGroupComponent } from './seg/seg.component';
import { CatalogComponent } from './catalog/catalog.component';
import { vAppComponent } from './vapp-cse-server/vapp-cse-server.component';

@NgModule({
    declarations: [
        VCDWizardComponent,
        DnsNtpComponent,
        VCDSpecComponent,
        AviControllerComponent,
        AviNsxCloudComponent,
        T0GatewayComponent,
        ServiceOrganizationComponent,
        ServiceOrganizationVDCComponent,
        EdgeGatewayComponent,
        ServiceEngineGroupComponent,
        CatalogComponent,
        vAppComponent,
    ],
    imports: [
        CommonModule,
        VCDWizardRoutingModule,
        SharedModule,
        LandingModule,
        WizardSharedModule,
        NgxJsonViewerModule
    ],
    exports: [
    ],
    providers: [
        ValidationService,
    ],
})
export class VCDModule { }
