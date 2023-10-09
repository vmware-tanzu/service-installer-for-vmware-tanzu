/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { Component, Input, OnInit } from '@angular/core';

@Component({
    selector: 'app-view-json-modal',
    templateUrl: './view-json-modal.component.html',
    styleUrls: ['./view-json-modal.component.scss']
})
export class ViewJSONModalComponent implements OnInit {
    @Input() payload;
    @Input() env;
    public inputFilename;

    viewJson: boolean;

    constructor() {}

    ngOnInit(): void {
        this.viewJson = false;
    }

    open(filename) {
        this.inputFilename = filename;
        this.viewJson = true;
    }

    close() {
        this.viewJson = false;
    }

    continueBtnHandler() {
        this.viewJson = false;
        this.onDownload();
    }

    download(content, fileName, contentType) {
        const a = document.createElement("a");
        const file = new Blob([content], { type: contentType });
        a.href = URL.createObjectURL(file);
        a.download = fileName;
        a.click();
    }

    onDownload () {
        this.download(JSON.stringify(this.payload, null,'\t'), this.inputFilename, "json");
    }

}
