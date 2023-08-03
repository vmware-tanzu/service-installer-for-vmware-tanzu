/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { NgxJsonViewerModule } from 'ngx-json-viewer';
import { SharedModule } from 'src/app/shared/shared.module';
import { LandingModule } from 'src/app/views/landing/landing.module';
import { VCDWizardRoutingModule } from 'src/app/console/vcd/configure/vcd-wizard-routing.module';

import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { WizardSharedModule } from 'src/app/views/landing/wizard/shared/wizard-shared.module';

import { VCDWizardComponent } from 'src/app/console/vcd/configure/vcd-wizard.component';

import { DnsNtpComponent } from 'src/app/console/vcd/configure/dns-ntp/dns-ntp.component';
import { VCDSpecComponent } from 'src/app/console/vcd/configure/vcd-spec/vcd-spec.component';
import { AviControllerComponent } from 'src/app/console/vcd/configure/avi-controller/avi-controller.component';
import { AviNsxCloudComponent } from 'src/app/console/vcd/configure/avi-nsx-cloud/avi-nsx-cloud.component';

import { T0GatewayComponent } from 'src/app/console/vcd/configure/t0-router/t0-router.component';
import { ServiceOrganizationComponent } from 'src/app/console/vcd/configure/svc-org/svc-org.component';
import { ServiceOrganizationVDCComponent } from 'src/app/console/vcd/configure/svc-org-vdc/svc-org-vdc.component';
import { EdgeGatewayComponent } from 'src/app/console/vcd/configure/edge-gateway/edge-gateway.component';
import { ServiceEngineGroupComponent } from 'src/app/console/vcd/configure/seg/seg.component';
import { CatalogComponent } from 'src/app/console/vcd/configure/catalog/catalog.component';
import { vAppComponent } from 'src/app/console/vcd/configure/vapp-cse-server/vapp-cse-server.component';

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
