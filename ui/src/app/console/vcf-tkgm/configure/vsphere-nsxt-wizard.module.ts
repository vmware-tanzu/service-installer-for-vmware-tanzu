/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';

import { SharedModule } from 'src/app/shared/shared.module';
import { LandingModule } from 'src/app/views/landing/landing.module';
import { VSphereNsxtWizardRoutingModule } from './vsphere-nsxt-wizard-routing.module';

import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { WizardSharedModule } from 'src/app/views/landing/wizard/shared/wizard-shared.module';
import { AVINetworkSettingComponent } from 'src/app/console/vcf-tkgm/configure/avi-setting-step/avi-setting-step.component';
import { CustomRepoSettingComponent } from 'src/app/console/vcf-tkgm/configure/custom-repo-step/custom-repo-setting-step.component';
import { DnsNtpComponent } from 'src/app/console/vcf-tkgm/configure/dns-ntp-step/dns-ntp.component';
import { ExtensionSettingComponent } from 'src/app/console/vcf-tkgm/configure/extension-step/extension-step.component';
import { InfraDataStepComponent } from 'src/app/console/vcf-tkgm/configure/infra-details-step/infra-details-step.component';
import { NodeSettingStepComponent } from 'src/app/console/vcf-tkgm/configure/node-setting-step/node-setting-step.component';
import { VSphereProviderStepComponent } from 'src/app/console/vcf-tkgm/configure/provider-step/vsphere-provider-step.component';
import { SharedNodeSettingComponent } from 'src/app/console/vcf-tkgm/configure/shared-node-setting/shared-node-setting.component';
import { TanzuSaasStepComponent } from 'src/app/console/vcf-tkgm/configure/tanzu-saas-step/tanzu-saas-setting-step.component';
import { TKGMgmtNetworkSettingComponent } from 'src/app/console/vcf-tkgm/configure/tkg-mgmt-data-network/tkg-mgmt-data.component';
import { TKGWorkloadNetworkSettingComponent } from 'src/app/console/vcf-tkgm/configure/tkg-workload-data-network/tkg-workload-data.component';
import { VSphereNsxtWizardComponent } from 'src/app/console/vcf-tkgm/configure/vsphere-nsxt-wizard.component';
import { WorkloadNodeSettingComponent } from 'src/app/console/vcf-tkgm/configure/workload-node-setting/workload-node-setting.component';
@NgModule({
    declarations: [
        VSphereNsxtWizardComponent,
        VSphereProviderStepComponent,
        InfraDataStepComponent,
        NodeSettingStepComponent,
        WorkloadNodeSettingComponent,
        SharedNodeSettingComponent,
        AVINetworkSettingComponent,
        ExtensionSettingComponent,
        TKGMgmtNetworkSettingComponent,
        TKGWorkloadNetworkSettingComponent,
        TanzuSaasStepComponent,
        CustomRepoSettingComponent,
        DnsNtpComponent,
    ],
    imports: [
        CommonModule,
        VSphereNsxtWizardRoutingModule,
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
export class VsphereNsxtWizardModule { }
