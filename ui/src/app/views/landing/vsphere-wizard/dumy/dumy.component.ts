/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
/**
 * Angular Modules
 */
import { Component, OnInit, Input } from '@angular/core';
import {
    Validators,
    FormControl
} from '@angular/forms';

/**
 * App imports
 */
import { DataService } from 'src/app/shared/service/data.service';
import { NodeType, vSphereNodeTypes } from 'src/app/views/landing/wizard/shared/constants/wizard.constants';
import { PROVIDERS, Providers } from '../../../../shared/constants/app.constants';
import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
import { ValidationService } from '../../wizard/shared/validation/validation.service';
import { Subscription } from 'rxjs';

@Component({
    selector: 'app-dumy-step',
    templateUrl: './dumy.component.html',
    styleUrls: ['./dumy.component.scss'],
})
export class DumyComponent extends StepFormDirective implements OnInit {
    @Input() providerType: string;

    nodeTypes: Array<NodeType> = [];
    PROVIDERS: Providers = PROVIDERS;
    vSphereNodeTypes: Array<NodeType> = vSphereNodeTypes;
    nodeType: string;

    displayForm = false;
    additionalNoProxyInfo: string;
    fullNoProxy: string;
    enableNetworkName = true;
    networks = [];

    private dnsServer;
    private ntpServer;
    private searchDomain;
    private uploadStatus;
    subscription: Subscription;


    constructor(private validationService: ValidationService,
                private dataService: DataService) {

        super();
    }

    ngOnInit() {
        super.ngOnInit();

        this.formGroup.addControl(
            'dnsServer',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIps(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('ntpServer',
            new FormControl('', [
                Validators.required,
                this.validationService.isCommaSeparatedIpsOrFqdn(),
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        this.formGroup.addControl('searchDomain',
            new FormControl('', [
                this.validationService.noWhitespaceOnEnds()
            ])
        );
        setTimeout(_ => {
            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentDnsValue.subscribe(
                    (dnsServer) => this.dnsServer = dnsServer);
                this.formGroup.get('dnsServer').setValue(this.dnsServer);
                this.subscription = this.dataService.currentNtpValue.subscribe(
                    (ntpServer) => this.ntpServer = ntpServer);
                this.formGroup.get('ntpServer').setValue(this.ntpServer);
                this.subscription = this.dataService.currentSearchDomainValue.subscribe(
                    (searchDomain) => this.searchDomain = searchDomain);
                this.formGroup.get('searchDomain').setValue(this.searchDomain);
            }
        });
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // don't fill password field with ****
        if (!this.uploadStatus) {
            this.formGroup.get('dnsServer').setValue('');
            this.formGroup.get('ntpServer').setValue('');
        }
    }
}
