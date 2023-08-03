/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { NgxJsonViewerModule } from 'ngx-json-viewer';
import { NgMultiSelectDropDownModule } from 'ng-multiselect-dropdown';
import { SharedModule } from 'src/app/shared/shared.module';
import { LandingModule } from 'src/app/views/landing/landing.module';
import { VSphereTkgsWizardRoutingModule } from 'src/app/console/vds-tkgs/configure/vsphere-tkgs-wizard-routing.module';

import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { WizardSharedModule } from 'src/app/views/landing/wizard/shared/wizard-shared.module';
import { AVINetworkSettingComponent } from 'src/app/console/vds-tkgs/configure/wcp/avi-setting-step/avi-setting-step.component';
import {  DnsNtpComponent } from 'src/app/console/vds-tkgs/configure/wcp/dns-ntp-step/dns-ntp.component';
import { ExtensionSettingComponent } from 'src/app/console/vds-tkgs/configure/namespace/extension-step/extension-step.component';

import { VSphereProviderStepComponent } from 'src/app/console/vds-tkgs/configure/wcp/provider-step/vsphere-provider-step.component';
import { TanzuSaasStepComponent } from 'src/app/console/vds-tkgs/configure/shared/tanzu-saas-step/tanzu-saas-setting-step.component';
import { VSphereTkgsWizardComponent } from 'src/app/console/vds-tkgs/configure/vsphere-tkgs-wizard.component';
import { ControlPlaneComponent } from 'src/app/console/vds-tkgs/configure/wcp/control-plane-setting/control-plane.component';
import { ContentLibComponent } from 'src/app/console/vds-tkgs/configure/namespace/content-lib-setting/content-lib.component';
import { StoragePolicyComponent } from 'src/app/console/vds-tkgs/configure/wcp/storage-policy-setting/storage-policy.component';
import { NodeSettingStepComponent } from 'src/app/console/vds-tkgs/configure/wcp/mgmt-network-setting/mgmt-nw.component';
import { WorkloadNodeSettingComponent } from 'src/app/console/vds-tkgs/configure/wcp/workload-network-setting/wrk-nw.component';
import { NamespaceComponent } from 'src/app/console/vds-tkgs/configure/namespace/namespace-setting/namespace.component';
import { WorkloadClusterComponent } from 'src/app/console/vds-tkgs/configure/namespace/wrk-cluster-setting/wrk-cluster.component';
import { EnvDetailsComponent } from 'src/app/console/vds-tkgs/configure/namespace/env-details-step/env-details.component';
import { WorkloadNamespaceComponent } from 'src/app/console/vds-tkgs/configure/namespace/workload-namespace-setting/workload-namespace-setting.component';
import { TKGSGlobalConfig } from 'src/app/console/vds-tkgs/configure/shared/tkgs-global-config/tkgs-global-config.component';
import { ProxySettingStepComponent } from 'src/app/console/vds-tkgs/configure/shared/proxy-setting-step/proxy-setting-step.component';
@NgModule({
    declarations: [
        VSphereTkgsWizardComponent,
        VSphereProviderStepComponent,
        ControlPlaneComponent,
        ContentLibComponent,
        StoragePolicyComponent,
        NodeSettingStepComponent,
        WorkloadNodeSettingComponent,
        AVINetworkSettingComponent,
        TanzuSaasStepComponent,
        DnsNtpComponent,
        NamespaceComponent,
        WorkloadClusterComponent,
        ExtensionSettingComponent,
        EnvDetailsComponent,
        WorkloadNamespaceComponent,
        TKGSGlobalConfig,
        ProxySettingStepComponent
    ],
    imports: [
        CommonModule,
        VSphereTkgsWizardRoutingModule,
        SharedModule,
        LandingModule,
        WizardSharedModule,
        NgxJsonViewerModule,
        NgMultiSelectDropDownModule
    ],
    exports: [
    ],
    providers: [
        ValidationService,
    ],
})
export class VsphereTkgsWizardModule { }
