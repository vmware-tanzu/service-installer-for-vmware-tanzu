import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { NgxJsonViewerModule } from 'ngx-json-viewer';
import { NgMultiSelectDropDownModule } from 'ng-multiselect-dropdown';
import { SharedModule } from '../../../shared/shared.module';
import { LandingModule } from '../landing.module';
import { VSphereTkgsWizardRoutingModule } from './vsphere-tkgs-wizard-routing.module';

import { ValidationService } from '../wizard/shared/validation/validation.service';
import { WizardSharedModule } from '../wizard/shared/wizard-shared.module';
import { AVINetworkSettingComponent } from './avi-setting-step/avi-setting-step.component';
// import {CustomRepoSettingComponent} from './custom-repo-step/custom-repo-setting-step.component';
import {  DnsNtpComponent } from './dns-ntp-step/dns-ntp.component';
import { ExtensionSettingComponent } from './extension-step/extension-step.component';
// import { InfraDataStepComponent } from './infra-details-step/infra-details-step.component';
// import { NodeSettingStepComponent } from './node-setting-step/node-setting-step.component';
import { VSphereProviderStepComponent } from './provider-step/vsphere-provider-step.component';
// import { SharedNodeSettingComponent } from './shared-node-setting/shared-node-setting.component';
import { TanzuSaasStepComponent } from './tanzu-saas-step/tanzu-saas-setting-step.component';
// import { TKGMgmtNetworkSettingComponent } from './tkg-mgmt-data-network/tkg-mgmt-data.component';
// import { TKGWorkloadNetworkSettingComponent } from './tkg-workload-data-network/tkg-workload-data.component';
import { VSphereTkgsWizardComponent } from './vsphere-tkgs-wizard.component';
import { ControlPlaneComponent } from './control-plane-setting/control-plane.component';
import { ContentLibComponent } from './content-lib-setting/content-lib.component';
import { StoragePolicyComponent } from './storage-policy-setting/storage-policy.component';
import { NodeSettingStepComponent } from './mgmt-network-setting/mgmt-nw.component';
import { WorkloadNodeSettingComponent } from './workload-network-setting/wrk-nw.component';
import { NamespaceComponent } from './namespace-setting/namespace.component';
import { WorkloadClusterComponent } from './wrk-cluster-setting/wrk-cluster.component';
import { EnvDetailsComponent } from './env-details-step/env-details.component';
import { WorkloadNamespaceComponent } from './workload-namespace-setting/workload-namespace-setting.component';
import { TKGSGlobalConfig } from './tkgs-global-config/tkgs-global-config.component';
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
