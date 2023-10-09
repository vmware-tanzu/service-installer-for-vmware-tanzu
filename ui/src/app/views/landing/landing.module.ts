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
import { LandingComponent } from './landing.component';
import { LandingRoutingModule } from './landing-routing.module';
import { StartComponent } from './start/start.component';
import { ConfirmComponent } from './confirm/confirm.component';
import { SharedModule } from '../../shared/shared.module';
import { HeaderBarModule } from 'src/app/shared/components/header-bar/header-bar.module';
@NgModule({
    declarations: [
        LandingComponent,
        StartComponent,
        ConfirmComponent
    ],
    imports: [
        CommonModule,
        LandingRoutingModule,
        LogMonitorModule,
        SharedModule,
        NgxJsonViewerModule,
        HeaderBarModule
    ],
    exports: [
        ConfirmComponent,
    ]
})

export class LandingModule {}
