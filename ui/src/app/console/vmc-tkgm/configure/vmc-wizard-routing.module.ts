/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular modules
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// App imports
import { VMCWizardComponent } from 'src/app/console/vmc-tkgm/configure/vmc-wizard.component';

export const routes: Routes = [
    {
        path: '',
        component: VMCWizardComponent,
    }
];

/**
 * @module VMCWizardRoutingModule
 * @description
 * This is routing module for the wizard module.
 */
 @NgModule({
     imports: [RouterModule.forChild(routes)],
     exports: [RouterModule]
 })
 export class VMCWizardRoutingModule {}
