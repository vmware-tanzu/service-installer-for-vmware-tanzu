/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular modules
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// App imports
import { VcdUploadWizardComponent } from 'src/app/console/vcd/upload/vcd-upload-wizard.component';

export const routes: Routes = [
    {
        component: VcdUploadWizardComponent,
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
export class VcdUploadWizardRoutingModule {}
