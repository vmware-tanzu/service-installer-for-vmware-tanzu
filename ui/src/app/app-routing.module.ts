// Angular imports
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// App imports

const routes: Routes = [
    {
        path: '',
        pathMatch: 'full',
        redirectTo: 'ui',
    },
    {
        loadChildren: () => (import('./views/landing/landing.module').then((m) => (m.LandingModule))),
        path: 'ui',
    }
];

@NgModule({
    exports: [RouterModule],
    imports: [RouterModule.forRoot(routes, { useHash: true, relativeLinkResolution: 'legacy' })],
})
export class AppRoutingModule { }
