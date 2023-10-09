/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular modules
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// App imports
import { VsphereTkgsUploadWizardComponent } from 'src/app/console/vds-tkgs/upload/vsphere-tkgs-upload-wizard.component';

export const routes: Routes = [
    {
        component: VsphereTkgsUploadWizardComponent,
        path: '',
    },
];

/**
 * @module UploadWizardRoutingModule
 * @description
 * This is routing module for the wizard module.
 */
@NgModule({
    exports: [RouterModule],
    imports: [RouterModule.forChild(routes)],
})
export class VsphereTkgsUploadWizardRoutingModule {}
