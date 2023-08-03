/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular modules
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// App imports
import { LandingComponent } from './landing.component';
import { StartComponent } from './start/start.component';
import {DeployProgressComponent} from './deploy-progress/deploy-progress.component';

export const routes: Routes = [
    {
        component: LandingComponent,
        path: '',
        children: [
            {
                path: '',
                component: StartComponent,
            },
            {
                path: 'upload',
                loadChildren: () => import('src/app/console/vds-tkgm/upload/upload-wizard.module').then((m) => m.UploadModule),
            },
            {
                path: 'vmc-upload',
                loadChildren: () => import('src/app/console/vmc-tkgm/upload/vmc-upload-wizard.module').then((m) => m.VMCUploadModule),
            },
            {
                path: 'vsphere-nsxt-upload',
                loadChildren: () => import('src/app/console/vcf-tkgm/upload/vsphere-nsxt-upload-wizard.module')
                    .then((m) => m.VsphereNsxtUploadModule),
            },
            {
                path: 'wizard',
                loadChildren: () => import('src/app/console/vds-tkgm/configure/vsphere-wizard.module').then((m) => m.WizardModule),
            },
            {
                path: 'vmc-wizard',
                loadChildren: () => import('src/app/console/vmc-tkgm/configure/vmc-wizard.module').then((m) => m.VMCWizardModule),
            },
            {
                path: 'vsphere-nsxt',
                loadChildren: () => import('src/app/console/vcf-tkgm/configure/vsphere-nsxt-wizard.module').then((m) => m.VsphereNsxtWizardModule),
            },
            {
                path: 'vsphere-tkgs',
                loadChildren: () => import('src/app/console/vds-tkgs/configure/vsphere-tkgs-wizard.module').then((m) => m.VsphereTkgsWizardModule),
            },
            {
                path: 'vsphere-tkgs-upload',
                loadChildren: () => import('src/app/console/vds-tkgs/upload/vsphere-tkgs-upload-wizard.module').then((m) => m.VsphereTkgsUploadWizardModule),
            },
            {
                path: 'vcd-upload',
                loadChildren: () => import('src/app/console/vcd/upload/vcd-upload-wizard.module').then((m) => m.UploadModule),
            },
            {
                path: 'vcd-wizard',
                loadChildren: () => import('src/app/console/vcd/configure/vcd-wizard.module').then((m) => m.VCDModule),
            },
            {
                path: 'deploy-progress',
                component: DeployProgressComponent
            },
        ],
    },
];

/**
 * @module LandingRoutingModule
 * @description
 * This is routing module for the landing module.
 */
@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule],
})
export class LandingRoutingModule {}
