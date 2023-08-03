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
import { DeployProgressComponent } from './deploy-progress/deploy-progress.component';
import { SharedModule } from '../../shared/shared.module';
@NgModule({
    declarations: [
        LandingComponent,
        StartComponent,
        ConfirmComponent,
        DeployProgressComponent,
    ],
    imports: [
        CommonModule,
        LandingRoutingModule,
        LogMonitorModule,
        SharedModule,
        NgxJsonViewerModule
    ],
    exports: [
        ConfirmComponent,
    ]
})

export class LandingModule {}
