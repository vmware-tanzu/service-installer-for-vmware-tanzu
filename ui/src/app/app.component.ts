/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { Component } from '@angular/core';

// App imports
import { BasicSubscriber } from './shared/abstracts/basic-subscriber';

@Component({
    selector: 'app-tkg-kickstart-ui',
    styleUrls: ['./app.component.scss'],
    templateUrl: './app.component.html',
})
export class AppComponent extends BasicSubscriber {
}
