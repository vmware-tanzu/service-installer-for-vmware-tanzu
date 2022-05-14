// Angular imports
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ClarityIcons, userIcon } from '@cds/core/icon';
import '@cds/core/icon/register.js';
import { ClarityModule } from '@clr/angular';
import { NgMultiSelectDropDownModule } from 'ng-multiselect-dropdown';
import { NgxJsonViewerModule } from 'ngx-json-viewer';

ClarityIcons.addIcons(userIcon);

// Third-party imports
import { CodemirrorModule } from '@ctrl/ngx-codemirror';
import { LogMonitorModule } from 'ngx-log-monitor';

// Module imports
import { AppRoutingModule } from './app-routing.module';
import { SharedModule } from './shared/shared.module';

// Component imports
import { AppComponent } from './app.component';
import { HeaderBarModule } from './shared/components/header-bar/header-bar.module';

// Service imports
import { AppDataService } from './shared/service/app-data.service';
import { DataService } from './shared/service/data.service';
import { VMCDataService } from './shared/service/vmc-data.service';
import { VsphereNsxtDataService } from './shared/service/vsphere-nsxt-data.service';
import { VsphereTkgsService } from './shared/service/vsphere-tkgs-data.service';
import { WebsocketService } from './shared/service/websocket.service';

@NgModule({
    bootstrap: [AppComponent],
    declarations: [
        AppComponent,
    ],
    imports: [
        BrowserModule,
        AppRoutingModule,
        LogMonitorModule,
        BrowserAnimationsModule,
        HeaderBarModule,
        ClarityModule,
        SharedModule,
        CodemirrorModule,
        NgxJsonViewerModule,
        NgMultiSelectDropDownModule,
    ],
    providers: [
        AppDataService,
        WebsocketService,
        DataService,
        VMCDataService,
        VsphereNsxtDataService,
        VsphereTkgsService,
    ],
})
export class AppModule { }
