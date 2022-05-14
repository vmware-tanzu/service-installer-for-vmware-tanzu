
// Angular modules
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// App imports
import { UploadWizardComponent } from './upload-wizard.component';

export const routes: Routes = [
    {
        component: UploadWizardComponent,
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
export class UploadWizardRoutingModule {}
