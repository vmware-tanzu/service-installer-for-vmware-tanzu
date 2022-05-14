
// Angular modules
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// App imports
import { VSphereTkgsWizardComponent } from './vsphere-tkgs-wizard.component';

export const routes: Routes = [
    {
        path: '',
        component: VSphereTkgsWizardComponent,
    }
];

/**
 * @module VSphereTkgsWizardRoutingModule
 * @description
 * This is routing module for the wizard module.
 */
@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule]
})
export class VSphereTkgsWizardRoutingModule {}
