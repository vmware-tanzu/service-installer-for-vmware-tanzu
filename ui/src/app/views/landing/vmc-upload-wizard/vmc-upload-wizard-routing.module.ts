
// Angular modules
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// App imports
import { VMCUploadWizardComponent } from './vmc-upload-wizard.component';

export const routes: Routes = [
    {
        component: VMCUploadWizardComponent,
        path: '',
    },
];

/**
 * @module VMCUploadWizardRoutingModule
 * @description
 * This is routing module for the wizard module.
 */
@NgModule({
    exports: [RouterModule],
    imports: [RouterModule.forChild(routes)],
})
export class VMCUploadWizardRoutingModule {}
