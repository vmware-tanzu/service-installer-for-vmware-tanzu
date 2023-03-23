/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { Directive, ElementRef, AfterViewInit } from '@angular/core';

@Directive({
    selector: '[removeAriaLabelledBy]'
})
export class RemoveAriaLabelledByDirective implements AfterViewInit {
    private panel: HTMLElement;

    constructor(el: ElementRef) {
        this.panel = el.nativeElement;
    }
    ngAfterViewInit(): void {
        this.panel.querySelector('[role="region"]').removeAttribute('aria-labelledby');
    }
}
