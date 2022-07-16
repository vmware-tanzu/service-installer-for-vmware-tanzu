/**
 * Angular Modules
 */
 import { Component, Input, OnInit } from '@angular/core';
 import {
     FormControl,
     Validators,
 } from '@angular/forms';
 import {ClrLoadingState} from '@clr/angular';
 import { VSphereWizardFormService } from 'src/app/shared/service/vsphere-wizard-form.service';
 
 /**
  * App imports
  */
 import { StepFormDirective } from '../../wizard/shared/step-form/step-form';
 import { ValidationService } from '../../wizard/shared/validation/validation.service';
 import {APIClient} from 'src/app/swagger/api-client.service';
 import {Subscription} from "rxjs";
 import {VsphereTkgsService} from "../../../../shared/service/vsphere-tkgs-data.service";
 @Component({
     selector: 'app-global-config-step',
     templateUrl: './tkgs-global-config.component.html',
     styleUrls: ['./tkgs-global-config.component.scss']
 })
 export class TKGSGlobalConfig extends StepFormDirective implements OnInit {
    @Input() errorNotification: any;
 
    subscription: Subscription;
    private uploadStatus = false; 
    private defaultCNI;

    //Proxy fields
    private isSameAsHttp;
    private httpProxyUrl;
    private httpProxyUsername;
    private httpProxyPassword;
    private httpsProxyUrl;
    private httpsProxyUsername;
    private httpsProxyPassword;
    private noProxy;
    private enableProxy;
    private proxyCert;

    private tkgsCerts;

    constructor(private validationService: ValidationService,
                private wizardFormService: VSphereWizardFormService,
                public apiClient: APIClient,
                private dataService: VsphereTkgsService) {

        super();
    }
    ngOnInit() {
        super.ngOnInit();
        this.formGroup.addControl(
            'defaultCNI',
            new FormControl('antrea', []));

            const fieldsMapping = [
            ['httpProxyUrl', ''],
            ['httpProxyUsername', ''],
            ['httpProxyPassword', ''],
            ['httpsProxyUrl', ''],
            ['httpsProxyUsername', ''],
            ['httpsProxyPassword', ''],
            ['noProxy', ''],
            ['proxyCert', ''],
        ];
        fieldsMapping.forEach(field => {
            this.formGroup.addControl(field[0], new FormControl(field[1], []));
        });
        this.formGroup.addControl('proxySettings', new FormControl(false));
        this.formGroup.addControl('isSameAsHttp', new FormControl(true));

        this.formGroup.addControl('tkgsCerts',
            new FormControl('',[]));
        this.formGroup.addControl('newCertType',
            new FormControl('', [])
        );
        this.formGroup.addControl('newCertValue',
            new FormControl('',
                [this.validationService.noWhitespaceOnEnds()])
        );

        setTimeout(_ => {
        //  this.resurrectField('defaultCNI',
        //  [],
        //  this.formGroup.get('defaultCNI').value);

            this.subscription = this.dataService.currentInputFileStatus.subscribe(
                (uploadStatus) => this.uploadStatus = uploadStatus);
            if (this.uploadStatus) {
                this.subscription = this.dataService.currentDefaultCNI.subscribe(
                    (cni) => this.defaultCNI = cni);
                this.formGroup.get('defaultCNI').setValue(this.defaultCNI);

                // Proxy fields
                this.subscription = this.dataService.currentTkgsEnableProxy.subscribe(
                    (enableProxy) => this.enableProxy = enableProxy);
                this.formGroup.get('proxySettings').setValue(this.enableProxy);
                if (this.enableProxy) {
                    this.apiClient.arcasProxyEnabled = true;
                    this.toggleProxySetting();
                } else {
                    this.apiClient.arcasProxyEnabled = false;
                    this.toggleProxySetting();
                }
                this.subscription = this.dataService.currentTkgsHttpProxyUrl.subscribe(
                    (httpProxyUrl) => this.httpProxyUrl = httpProxyUrl);
                this.formGroup.get('httpProxyUrl').setValue(this.httpProxyUrl);
                this.subscription = this.dataService.currentTkgsHttpProxyUsername.subscribe(
                    (httpProxyUsername) => this.httpProxyUsername = httpProxyUsername);
                this.formGroup.get('httpProxyUsername').setValue(this.httpProxyUsername);
                this.subscription = this.dataService.currentTkgsHttpProxyPassword.subscribe(
                    (httpProxyPassword) => this.httpProxyPassword = httpProxyPassword);
                this.formGroup.get('httpProxyPassword').setValue(this.httpProxyPassword);
                this.subscription = this.dataService.currentTkgsIsSameAsHttp.subscribe(
                    (isSameAsHttp) => this.isSameAsHttp = isSameAsHttp);
                this.formGroup.get('isSameAsHttp').setValue(this.isSameAsHttp);
                this.subscription = this.dataService.currentTkgsHttpsProxyUrl.subscribe(
                    (httpsProxyUrl) => this.httpsProxyUrl = httpsProxyUrl);
                this.formGroup.get('httpsProxyUrl').setValue(this.httpsProxyUrl);
                this.subscription = this.dataService.currentTkgsHttpsProxyUsername.subscribe(
                    (httpsProxyUsername) => this.httpsProxyUsername = httpsProxyUsername);
                this.formGroup.get('httpsProxyUsername').setValue(this.httpsProxyUsername);
                this.subscription = this.dataService.currentTkgsHttpsProxyPassword.subscribe(
                    (httpsProxyPassword) => this.httpsProxyPassword = httpsProxyPassword);
                this.formGroup.get('httpsProxyPassword').setValue(this.httpsProxyPassword);
                this.subscription = this.dataService.currentTkgsNoProxy.subscribe(
                    (noProxy) => this.noProxy = noProxy);
                this.formGroup.get('noProxy').setValue(this.noProxy);
                this.subscription = this.dataService.currentTkgsProxyCert.subscribe(
                    (cert) => this.proxyCert = cert);
                this.formGroup.get('proxyCert').setValue(this.proxyCert);

                // this.subscription = this.dataService.currentTkgsAdditionalCaPaths.subscribe(
                //     (cni) => this.caPaths = cni);
                // this.formGroup.get('defaultCNI').setValue(this.caPaths);
            }
        });
    }

    setSavedDataAfterLoad() {
        super.setSavedDataAfterLoad();
        // don't fill password field with ****
        if (!this.uploadStatus) {
            this.formGroup.get('httpProxyPassword').setValue('');
            this.formGroup.get('httpsProxyPassword').setValue('');
        }
    }

    toggleProxySetting() {
        const proxySettingFields = [
            'httpProxyUrl',
            'httpProxyUsername',
            'httpProxyPassword',
            'isSameAsHttp',
            'httpsProxyUrl',
            'httpsProxyUsername',
            'httpsProxyPassword',
            'noProxy',
            'proxyCert',
        ];
        if (this.formGroup.value['proxySettings']) {
            this.apiClient.arcasProxyEnabled = true;
            this.resurrectField('httpProxyUrl', [
                Validators.required,
                this.validationService.isHttpOrHttps(),
                this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['httpProxyUrl']);
            this.resurrectField('httpProxyUsername', [
                this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['httpProxyUsername']);
            this.resurrectField('noProxy', [
                this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['noProxy']);
            this.resurrectField('proxyCert', [
                this.validationService.noWhitespaceOnEnds()
            ], this.formGroup.value['proxyCert']);
            if (!this.formGroup.value['isSameAsHttp']) {
                this.resurrectField('httpsProxyUrl', [
                    Validators.required,
                    this.validationService.isHttpOrHttps(),
                    this.validationService.noWhitespaceOnEnds()
                ], this.formGroup.value['httpsProxyUrl']);
                 this.resurrectField('httpsProxyUsername', [
                     this.validationService.noWhitespaceOnEnds()
                 ], this.formGroup.value['httpsProxyUsername']);
            } else {
                const httpsFields = [
                    'httpsProxyUrl',
                    'httpsProxyUsername',
                    'httpsProxyPassword',
                ];
                httpsFields.forEach((field) => {
                    this.disarmField(field, true);
                });
            }
        } 
        // else {
        //     if (this.apiClient.proxyConfiguredVCF) {
        //         this.disableProxy();
        //     }
        //     this.apiClient.arcasProxyEnabled = false;
        //     proxySettingFields.forEach((field) => {
        //         this.disarmField(field, true);
        //     });
        // }
    }

    deleteCert(certValue: string) {
        this.apiClient.tkgsAdditionalCerts.delete(certValue);
        this.formGroup.get('tkgsCerts').setValue(this.apiClient.tkgsAdditionalCerts);
    }

    addCert(type: string, value: string) {
        let errorList = [];
        if(!this.apiClient.tkgsAdditionalCerts.has(value)) {
            this.apiClient.tkgsAdditionalCerts.set(value, type);
            this.formGroup.get('tkgsCerts').setValue(this.apiClient.tkgsAdditionalCerts);
            this.formGroup.get('newCertType').setValue('');
            this.formGroup.get('newCertValue').setValue('');
        } else {
            this.errorNotification = "Additional certificate with the same name already exists!";
        }
    }

}