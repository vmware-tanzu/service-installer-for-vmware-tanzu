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
import { AuthGuard } from 'src/app/shared/service/auth.guard';
import {DeploymentTimelineComponent} from 'src/app/console/vds-tkgs/configure/shared/deployment-timeline/deployment-timeline.component';

export const routes: Routes = [
    {
        component: LandingComponent,
        path: '',
        children: [
            {
                path: '',
                component: StartComponent,
                canActivate: [AuthGuard]
            },
            {
                path: 'upload',
                loadChildren: () => import('src/app/console/vds-tkgm/upload/upload-wizard.module').then((m) => m.UploadModule),
                canActivate: [AuthGuard]
            },
            {
                path: 'vmc-upload',
                loadChildren: () => import('src/app/console/vmc-tkgm/upload/vmc-upload-wizard.module').then((m) => m.VMCUploadModule),
                canActivate: [AuthGuard]
            },
            {
                path: 'vsphere-nsxt-upload',
                loadChildren: () => import('src/app/console/vcf-tkgm/upload/vsphere-nsxt-upload-wizard.module')
                    .then((m) => m.VsphereNsxtUploadModule),
                canActivate: [AuthGuard]
            },
            {
                path: 'wizard',
                loadChildren: () => import('src/app/console/vds-tkgm/configure/vsphere-wizard.module').then((m) => m.WizardModule),
                canActivate: [AuthGuard]
            },
            {
                path: 'vmc-wizard',
                loadChildren: () => import('src/app/console/vmc-tkgm/configure/vmc-wizard.module').then((m) => m.VMCWizardModule),
                canActivate: [AuthGuard]
            },
            {
                path: 'vsphere-nsxt',
                loadChildren: () => import('src/app/console/vcf-tkgm/configure/vsphere-nsxt-wizard.module').then((m) => m.VsphereNsxtWizardModule),
                canActivate: [AuthGuard]
            },
            {
                path: 'vsphere-tkgs',
                loadChildren: () => import('src/app/console/vds-tkgs/configure/vsphere-tkgs-wizard.module').then((m) => m.VsphereTkgsWizardModule),
                canActivate: [AuthGuard]
            },
            {
                path: 'vsphere-tkgs-upload',
                loadChildren: () => import('src/app/console/vds-tkgs/upload/vsphere-tkgs-upload-wizard.module').then((m) => m.VsphereTkgsUploadWizardModule),
                canActivate: [AuthGuard]
            },
            {
                path: 'vcd-upload',
                loadChildren: () => import('src/app/console/vcd/upload/vcd-upload-wizard.module').then((m) => m.UploadModule),
                canActivate: [AuthGuard]
            },
            {
                path: 'vcd-wizard',
                loadChildren: () => import('src/app/console/vcd/configure/vcd-wizard.module').then((m) => m.VCDModule),
                canActivate: [AuthGuard]
            },
            {
                path: 'deploy-tkgs',
                component: DeploymentTimelineComponent,
                canActivate: [AuthGuard]
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
