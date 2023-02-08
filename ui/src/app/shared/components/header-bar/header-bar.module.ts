/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Copyright 2019 VMware, Inc. All Rights Reserved.
//

/**
 * Angular modules
 */
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Second party modules
 */

/**
 * App imports
 */
import { HeaderBarComponent } from './header-bar.component';
import { HEADER_IMPORTS } from './header-bar.imports';

@NgModule({
    imports: [
        ...HEADER_IMPORTS
    ],
    declarations: [HeaderBarComponent],
    providers: [],
    exports: [HeaderBarComponent]
})
export class HeaderBarModule {}
