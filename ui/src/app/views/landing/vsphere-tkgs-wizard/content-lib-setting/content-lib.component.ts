/**
 * Angular Modules
 */
import { Component, Input, OnInit } from '@angular/core';
import {
    FormControl,
    Validators,
} from '@angular/forms';
import { Netmask } from 'netmask';
import { TkgEventType } from 'src/app/shared/service/Messenger';
import {ClrLoadingState} from '@clr/angular';
import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';

/**
 * App imports
 */
import { PROVIDERS, Providers } from '../../../../shared/constants/app.constants';
import { NodeType, tkgsControlPlaneNodes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
import Broker from 'src/app/shared/service/broker';
import { AppEdition } from 'src/app/shared/constants/branding.constants';
import {APIClient} from 'src/app/swagger/api-client.service';
import {Subscription} from "rxjs";
import {VsphereTkgsService} from "../../../../shared/service/vsphere-tkgs-data.service";
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


    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
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