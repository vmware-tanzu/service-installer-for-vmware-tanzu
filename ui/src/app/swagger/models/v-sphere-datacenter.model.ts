/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
export class VSphereDatacenter {
    public name: string;
    public moid: string;

    constructor(name: string, moid: string) {
        this.name = name;
        this.moid = moid;
    }
}
