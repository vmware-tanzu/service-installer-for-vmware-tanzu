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
import { NodeType, tkgsControlPlaneNodes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { APIClient } from 'src/app/swagger/api-client.service';
import { Subscription } from "rxjs";
import { VsphereTkgsService } from "../../../../shared/service/vsphere-tkgs-data.service";
@Component({
    selector: 'app-control-plane-setting-step',
    templateUrl: './control-plane.component.html',
    styleUrls: ['./control-plane.component.scss']
})
export class ControlPlaneComponent extends StepFormDirective implements OnInit {
    @Input() errorNotification: any;

    subscription: Subscription;
    nodeTypes: Array<NodeType> = [];
    tkgsControlPlaneNodes: Array<NodeType> = tkgsControlPlaneNodes;
    nodeType: string;

    private uploadStatus = false;
    private controlPlaneSize;

    constructor(public apiClient: APIClient,
                private dataService: VsphereTkgsService) {

        super();
        this.nodeTypes = [...tkgsControlPlaneNodes];
    }
    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'controlPlaneSize',
            new FormControl('', [
                Validators.required
        ]));

        setTimeout(_ => {
            this.resurrectField('controlPlaneSize',
                [Validators.required],
                this.formGroup.get('controlPlaneSize').value);

            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentControlPlaneSize.subscribe(
                    (size) => this.controlPlaneSize = size);
                if (this.controlPlaneSize.toUpperCase() === 'TINY') {
                    this.formGroup.get('controlPlaneSize').setValue(this.controlPlaneSize.toUpperCase());
                } else if (this.controlPlaneSize.toUpperCase() === 'SMALL') {
                    this.formGroup.get('controlPlaneSize').setValue(this.controlPlaneSize.toUpperCase());
                } else if (this.controlPlaneSize.toUpperCase() === 'MEDIUM') {
                    this.formGroup.get('controlPlaneSize').setValue(this.controlPlaneSize.toUpperCase());
                } else if (this.controlPlaneSize.toUpperCase() === 'LARGE') {
                    this.formGroup.get('controlPlaneSize').setValue(this.controlPlaneSize.toUpperCase());
                }
            }
        });
    }
}
