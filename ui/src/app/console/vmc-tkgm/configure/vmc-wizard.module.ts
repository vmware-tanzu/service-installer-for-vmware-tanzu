/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';

import { SharedModule } from 'src/app/shared/shared.module';
import { LandingModule } from 'src/app/views/landing/landing.module';
import { VMCWizardRoutingModule } from 'src/app/console/vmc-tkgm/configure/vmc-wizard-routing.module';

import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { WizardSharedModule } from 'src/app/views/landing/wizard/shared/wizard-shared.module';
import { AVINetworkSettingComponent } from 'src/app/console/vmc-tkgm/configure/avi-setting-step/avi-setting-step.component';
import { DnsNtpComponent } from 'src/app/console/vmc-tkgm/configure/dns-ntp-step/dns-ntp.component';
import { ExtensionSettingComponent } from 'src/app/console/vmc-tkgm/configure/extension-step/extension-step.component';
import { NodeSettingStepComponent } from 'src/app/console/vmc-tkgm/configure/node-setting-step/node-setting-step.component';
import { VMCProviderStepComponent } from 'src/app/console/vmc-tkgm/configure/provider-step/vmc-provider-step.component';
import { SharedNodeSettingComponent } from 'src/app/console/vmc-tkgm/configure/shared-node-setting/shared-node-setting.component';
import { TanzuSaasStepComponent } from 'src/app/console/vmc-tkgm/configure/tanzu-saas-step/tanzu-saas-setting-step.component';
import { TKGMgmtNetworkSettingComponent } from 'src/app/console/vmc-tkgm/configure/tkg-mgmt-data-network/tkg-mgmt-data.component';
import { TKGWorkloadNetworkSettingComponent } from 'src/app/console/vmc-tkgm/configure/tkg-workload-data-network/tkg-workload-data.component';
import { VMCWizardComponent } from 'src/app/console/vmc-tkgm/configure/vmc-wizard.component';
import { WorkloadNodeSettingComponent } from 'src/app/console/vmc-tkgm/configure/workload-node-setting/workload-node-setting.component';
@NgModule({
    declarations: [
        VMCWizardComponent,
        VMCProviderStepComponent,
        NodeSettingStepComponent,
        WorkloadNodeSettingComponent,
        SharedNodeSettingComponent,
        AVINetworkSettingComponent,
        ExtensionSettingComponent,
        TKGMgmtNetworkSettingComponent,
        TKGWorkloadNetworkSettingComponent,
        TanzuSaasStepComponent,
        DnsNtpComponent,
    ],
    imports: [
        CommonModule,
        VMCWizardRoutingModule,
        SharedModule,
        LandingModule,
        WizardSharedModule,
    ],
    exports: [
    ],
    providers: [
        ValidationService,
    ],
})
export class VMCWizardModule { }
