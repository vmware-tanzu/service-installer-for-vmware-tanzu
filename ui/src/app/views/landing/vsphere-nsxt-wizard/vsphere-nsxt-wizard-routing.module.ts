
// Angular modules
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// App imports
import { VSphereNsxtWizardComponent } from './vsphere-nsxt-wizard.component';

export const routes: Routes = [
    {
        path: '',
        component: VSphereNsxtWizardComponent,
    }
];

/**
 * @module VSphereNsxtWizardRoutingModule
 * @description
 * This is routing module for the wizard module.
 */
@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule]
})
export class VSphereNsxtWizardRoutingModule {}
