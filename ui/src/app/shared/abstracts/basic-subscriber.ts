/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import {Injectable, OnDestroy} from '@angular/core';
import { Subject } from 'rxjs';

/**
 * Base class tha should be extended by any class that want to have a flag indicating if the component
 * is still alive. This is useful to handle Observable subscriptions in order to unsubscribe. Instead
 * of doing unsubscribe() you can use operator .takeWhile(() => this.isAlive).
 */
@Injectable()
// tslint:disable-next-line:component-class-suffix
export abstract class BasicSubscriber implements OnDestroy {

    protected isAlive = true;
    protected unsubscribe: Subject<void> = new Subject();

    ngOnDestroy() {
        this.isAlive = false;
        this.unsubscribe.next();
        this.unsubscribe.complete();
    }
}
