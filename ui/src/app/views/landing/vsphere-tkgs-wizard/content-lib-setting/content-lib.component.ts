/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
/**
 * Angular Modules
 */
import { Component, Input, OnInit } from '@angular/core';
import {
    FormControl,
    Validators,
} from '@angular/forms';

/**
 * App imports
 */
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { APIClient } from 'src/app/swagger/api-client.service';
import { Subscription } from "rxjs";
import { VsphereTkgsService } from "../../../../shared/service/vsphere-tkgs-data.service";
@Component({
    selector: 'app-content-lib-step',
    templateUrl: './content-lib.component.html',
    styleUrls: ['./content-lib.component.scss']
})
export class ContentLibComponent extends StepFormDirective implements OnInit {
    @Input() errorNotification: any;

    subscription: Subscription;
    private uploadStatus = false;
    private subscribedContentLib;
    public subscribedContentLibs = ['Lib-1', 'Lib-2'];


    constructor(public apiClient: APIClient,
                private dataService: VsphereTkgsService) {

        super();
    }
    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'subscribedContentLib',
            new FormControl('', [
                Validators.required
        ]));

        setTimeout(_ => {
            this.resurrectField('subscribedContentLib',
            [Validators.required],
            this.formGroup.get('subscribedContentLib').value);

            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentContentLib.subscribe(
                    (size) => this.subscribedContentLib = size);
                this.formGroup.get('subscribedContentLib').setValue(this.subscribedContentLib);
            }
        });
    }
}
