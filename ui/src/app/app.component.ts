/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { Component } from '@angular/core';
import { Router } from '@angular/router';

// App imports
import { BasicSubscriber } from './shared/abstracts/basic-subscriber';
import { APP_ROUTES } from './shared/constants/routes.constants';
import { AuthGuard } from './shared/service/auth.guard';

@Component({
    selector: 'app-tkg-kickstart-ui',
    styleUrls: ['./app.component.scss'],
    templateUrl: './app.component.html',
})
export class AppComponent extends BasicSubscriber {
    constructor(
        public router: Router,
        public authGuard: AuthGuard
    ){
        super();
    }

    ngOnInit() : void {
        if(this.authGuard.isAuthenticated()) this.router.navigate([APP_ROUTES.LANDING]);
        else this.router.navigate([APP_ROUTES.LOGIN])
    }
}
