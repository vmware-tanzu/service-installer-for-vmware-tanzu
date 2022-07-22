
/**
 * Angular Modules
 */
import { Component, OnInit } from '@angular/core';
import { FormControl , Validators} from '@angular/forms';
import { distinctUntilChanged, takeUntil } from 'rxjs/operators';
/**
 * App imports
 */
import { TkgEventType } from 'src/app/shared/service/Messenger';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { StepFormDirective } from 'src/app/views/landing/wizard/shared/step-form/step-form';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
import Broker from 'src/app/shared/service/broker';
import {Subscription} from "rxjs";
import { VsphereNsxtDataService } from "src/app/shared/service/vsphere-nsxt-data.service";

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
    private username: string;
    private password: string;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                private dataService: VsphereNsxtDataService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl('customRepoSetting', new FormControl(false));
        this.formGroup.addControl('repoImage', new FormControl('', []));
        this.formGroup.addControl('publicCaCert', new FormControl(true));
//         this.formGroup.addControl('repoUsername', new FormControl('', []));
//         this.formGroup.addControl('repoPassword', new FormControl('', []));
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
//                 this.subscription = this.dataService.currentRepoUsername.subscribe(
//                     (repoUsername) => this.username = repoUsername);
//                 this.formGroup.get('repoUsername').setValue(this.username);
//                 this.subscription = this.dataService.currentRepoPassword.subscribe(
//                     (repoPass) => this.password = repoPass);
// //                console.log(this.password);
//                 this.formGroup.get('repoPassword').setValue(this.password);
            }
        });
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // don't fill password field with ****
        if (!this.uploadStatus) {
//             this.formGroup.get('repoPassword').setValue('');
        }
    }

    toggleCustomRepoSetting() {
        const tmcSettingsFields = [
            'repoImage',
            'publicCaCert',
//             'repoUsername',
//             'repoPassword',
        ];
        if (this.formGroup.value['customRepoSetting']) {
            this.resurrectField('repoImage', [
                Validators.required, this.validationService.noWhitespaceOnEnds(),
                this.validationService.isHttpOrHttps()
            ], this.formGroup.value['repoImage']);
//             this.resurrectField('repoUsername',
//                 [this.validationService.noWhitespaceOnEnds()],
//                 this.formGroup.value['repoUsername']);
        } else {
            tmcSettingsFields.forEach((field) => {
                this.disarmField(field, true);
            });
        }
    }

    setPublicCertValue() {
        if (!this.formGroup.value['publicCaCert']) {
            this.formGroup.controls['publicCaCert'].setValue(false);
        }
    }
}
