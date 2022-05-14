
// Angular modules
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// App imports
import { VMCWizardComponent } from './vmc-wizard.component';

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