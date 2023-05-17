/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular modules
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// App imports
import { VCDWizardComponent } from './vcd-wizard.component';

export const routes: Routes = [
    {
        path: '',
        component: VCDWizardComponent,
    }
];

/**
 * @module VCDWizardRoutingModule
 * @description
 * This is routing module for the wizard module.
 */
@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule]
})
export class VCDWizardRoutingModule {}
