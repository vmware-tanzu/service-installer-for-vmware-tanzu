/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular modules
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxJsonViewerModule } from 'ngx-json-viewer';
// Third party modules
import { LogMonitorModule } from 'ngx-log-monitor';

// App imports
import { LandingRoutingModule } from 'src/app/views/landing/landing-routing.module';
import { SharedModule } from 'src/app/shared/shared.module';
import { LoginComponent } from './login.component';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
@NgModule({
    declarations: [
        LoginComponent,
    ],
    imports: [
        CommonModule,
        LandingRoutingModule,
        LogMonitorModule,
        SharedModule,
        NgxJsonViewerModule
    ],
    exports: [
        // LoginComponent
    ],
    providers: [
        ValidationService
    ]
})

export class LoginModule {}
