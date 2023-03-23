/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { Directive, ElementRef, HostListener } from '@angular/core';

@Directive({
    selector: '[keyboardListener]'
})
export class KeyboardListenerDirective {
    element: HTMLElement;
    constructor(el: ElementRef) {
        this.element = el.nativeElement;
    }

    @HostListener('keydown.enter', ['$event']) onKeyboardEnter(event: KeyboardEvent) {
        this.element.click();
    }
    @HostListener('keydown.space', ['$event']) onKeyboardSpace(event: KeyboardEvent) {
        this.element.click();
    }
}
