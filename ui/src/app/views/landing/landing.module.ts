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
// import { WcpRedirectComponent } from './wcp-redirect/wcp-redirect.component';
// import { IncompatibleComponent } from './incompatible/incompatible.component';
import { SharedModule } from '../../shared/shared.module';
// import { PreviewConfigComponent } from '../../shared/components/preview-config/preview-config.component';
// import { VmwCopyToClipboardButtonComponent } from '../../shared/components/copy-to-clipboard-button/copy-to-clipboard-button.component';
@NgModule({
    declarations: [
        LandingComponent,
        StartComponent,
        ConfirmComponent,
        DeployProgressComponent,
//         DeployProgressComponent,
//         WcpRedirectComponent,
//         IncompatibleComponent,
//         VmwCopyToClipboardButtonComponent,
//         PreviewConfigComponent
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
