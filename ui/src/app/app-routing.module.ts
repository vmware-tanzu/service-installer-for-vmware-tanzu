/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from './shared/service/auth.guard';
import { LoginComponent } from './views/landing/login/login.component';

// App imports

const routes: Routes = [
    {
        path: '',
        pathMatch: 'full',
        redirectTo: 'login',
    },
    {
        component: LoginComponent,
        path: 'login',
    },
    {
        loadChildren: () => (import('./views/landing/landing.module').then((m) => (m.LandingModule))),
        path: 'ui',
        canActivate: [AuthGuard]
    },
];

@NgModule({
    exports: [RouterModule],
    imports: [RouterModule.forRoot(routes, { useHash: true, relativeLinkResolution: 'legacy' })],
})
export class AppRoutingModule { }
