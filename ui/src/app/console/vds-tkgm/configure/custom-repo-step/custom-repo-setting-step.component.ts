/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
/**
 * Angular Modules
 */
import { Component, OnInit } from '@angular/core';
import { FormControl , Validators} from '@angular/forms';
/**
 * App imports
 */
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { StepFormDirective } from 'src/app/views/landing/wizard/shared/step-form/step-form';
import { Subscription } from "rxjs";
import { DataService } from "src/app/shared/service/data.service";
import { APIClient } from 'src/app/swagger/api-client.service';

@Component({
    selector: 'app-customRepo-step',
    templateUrl: './custom-repo-setting-step.component.html',
    styleUrls: ['./custom-repo-setting-step.component.scss'],
})
export class CustomRepoSettingComponent extends StepFormDirective implements OnInit {

    enableNetworkName = true;
    subscription: Subscription;
    private uploadStatus = false;
    private enableRepo: boolean;
    private repoImage: string;
    private caCert: boolean;

    constructor(private validationService: ValidationService,
                private dataService: DataService,
                private apiClient: APIClient) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl('customRepoSetting', new FormControl(false));
        this.formGroup.addControl('repoImage', new FormControl('', []));
        this.formGroup.addControl('publicCaCert', new FormControl(true));
        setTimeout(_ => {
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentEnableRepo.subscribe(
                    (enableRepo) => this.enableRepo = enableRepo);
                this.formGroup.get('customRepoSetting').setValue(this.enableRepo);
                this.subscription = this.dataService.currentRepoImage.subscribe(
                    (repoImage) => this.repoImage = repoImage);
                this.formGroup.get('repoImage').setValue(this.repoImage);
                this.subscription = this.dataService.currentCaCert.subscribe(
                    (caCert) => this.caCert = caCert);
                this.formGroup.get('publicCaCert').setValue(this.caCert);
            }
        });
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // don't fill password field with ****
        if (!this.uploadStatus) {
        }
    }

    toggleCustomRepoSetting() {
        const tmcSettingsFields = [
            'repoImage',
            'publicCaCert',
            'repoUsername',
            'repoPassword',
        ];
        if (this.formGroup.value['customRepoSetting']) {
            this.resurrectField('repoImage', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isHttpOrHttps(),
            ], this.formGroup.value['repoImage']);
            this.apiClient.isAirgapped = true;
        } else {
            tmcSettingsFields.forEach((field) => {
                this.disarmField(field, true);
            });
            this.apiClient.isAirgapped = false;
        }
    }

    setPublicCertValue() {
        if (!this.formGroup.value['publicCaCert']) {
            this.formGroup.controls['publicCaCert'].setValue(false);
        }
    }
}
